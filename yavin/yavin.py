import apscheduler.schedulers.background
import email.message
import flask
import flask_oauth2_login
import flask_sslify
import functools
import inspect
import logging
import requests
import smtplib
import sys
import waitress
import xml.etree.ElementTree
import yavin.config
import yavin.db
import yavin.util

config = yavin.config.Config()
scheduler = apscheduler.schedulers.background.BackgroundScheduler()

app = flask.Flask(__name__)

app.config['APPLICATION_ROOT'] = config.application_root
app.config['GOOGLE_LOGIN_CLIENT_ID'] = config.google_login_client_id
app.config['GOOGLE_LOGIN_CLIENT_SECRET'] = config.google_login_client_secret
app.config['GOOGLE_LOGIN_REDIRECT_SCHEME'] = config.scheme
app.config['PREFERRED_URL_SCHEME'] = config.scheme
app.config['SECRET_KEY'] = config.secret_key
app.config['SERVER_NAME'] = config.server_name

app.jinja_env.filters['datetime'] = yavin.util.clean_datetime

if config.scheme.lower() == 'https':
    flask_sslify.SSLify(app)

google_login = flask_oauth2_login.GoogleLogin(app)


@google_login.login_success
def login_success(_, profile):
    flask.session['profile'] = profile
    idx_url = flask.url_for('index')
    app.logger.debug(f'Google login success, redirecting to: {idx_url}')
    return flask.redirect(idx_url)


@google_login.login_failure
def login_failure(e):
    return flask.jsonify(errors=str(e))


def secure(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        profile = flask.session.get('profile')
        if profile is None:
            return flask.redirect(flask.url_for('index'))
        if profile.get('email') == config.admin_email:
            return f(*args, **kwargs)
        return flask.render_template('not_authorized.html')
    return decorated_function


def _get_db():
    _db = flask.g.get('_db')
    if _db is None:
        _db = yavin.db.YavinDatabase(config.dsn)
        flask.g._db = _db
    return _db


@app.before_request
def log_request():
    app.logger.debug(f'{flask.request.method} {flask.request.path}')


@app.before_request
def make_session_permanent():
    if config.permanent_sessions:
        flask.session.permanent = True


@app.route('/')
def index():
    profile = flask.session.get('profile')
    if profile is None:
        flask.g.auth_url = google_login.authorization_url()
        return flask.render_template('index.html')
    return flask.render_template('signed_in.html')


@app.route('/captains-log')
@secure
def captains_log():
    flask.g.records = _get_db().get_captains_log_entries()
    return flask.render_template('captains-log.html')


@app.route('/captains-log/delete', methods=['POST'])
@secure
def captains_log_delete():
    id_ = flask.request.form.get('id')
    _get_db().delete_captains_log_entry(id_)
    return flask.redirect(flask.url_for('captains_log'))


@app.route('/captains-log/incoming', methods=['POST'])
def captains_log_incoming():
    app.logger.debug(f'json: {flask.request.json}')
    auth_phrase: str = flask.request.json['auth-phrase']
    if auth_phrase.lower() == config.admin_auth_phrase:
        app.logger.debug('Authorization accepted')
        log_text = flask.request.json['log-text']
        _get_db().add_captains_log_entry(log_text)
        return 'Log recorded.'
    return 'Authorization failure.'


@app.route('/captains-log/update', methods=['POST'])
@secure
def captains_log_update():
    id_ = flask.request.form.get('id')
    log_text = flask.request.form.get('log_text')
    _get_db().update_captains_log_entry(id_, log_text)
    return flask.redirect(flask.url_for('captains_log'))


@app.route('/electricity')
@secure
def electricity():
    flask.g.records = _get_db().get_electricity()
    return flask.render_template('electricity.html')


@app.route('/electricity/add', methods=['POST'])
def electricity_add():
    _get_db().add_electricity(flask.request.form)
    return flask.redirect(flask.url_for('electricity'))


@app.route('/jar')
@secure
def jar():
    flask.g.today = yavin.util.today()
    flask.g.jar_entries = _get_db().get_recent_jar_entries()
    return flask.render_template('jar.html')


@app.route('/jar/add', methods=['POST'])
@secure
def jar_add():
    entry_date = yavin.util.str_to_date(flask.request.form.get('entry_date'))
    app.logger.info(f'Adding new jar entry for {entry_date}')
    _get_db().add_jar_entry(entry_date)
    return flask.redirect(flask.url_for('jar'))


@app.route('/library')
@secure
def library():
    flask.g.library_credentials = _get_db().get_library_credentials()
    flask.g.library_books = _get_db().get_library_books()
    return flask.render_template('library.html')


@app.route('/library/add', methods=['POST'])
@secure
def library_add():
    params = {
        'display_name': flask.request.form.get('display_name'),
        'library': flask.request.form.get('library'),
        'username': flask.request.form.get('username'),
        'password': flask.request.form.get('password')
    }
    _get_db().add_library_credential(params)
    scheduler.add_job(library_sync)
    return flask.redirect(flask.url_for('library'))


@app.route('/library/delete', methods=['POST'])
@secure
def library_delete():
    _get_db().delete_library_credential(flask.request.form)
    scheduler.add_job(library_sync)
    return flask.redirect(flask.url_for('library'))


@app.route('/library/renew', methods=['POST'])
@secure
def library_renew():
    item_id = flask.request.form.get('item_id')
    app.logger.info(f'Attempting to renew item {item_id}')
    lib_cred = _get_db().get_book_credentials({'item_id': item_id})
    lib_url = lib_cred['library']
    s = requests.Session()
    login_url = f'https://{lib_url}.biblionix.com/catalog/ajax_backend/login.xml.pl'
    login_data = {'username': lib_cred['username'], 'password': lib_cred['password']}
    login = s.post(url=login_url, data=login_data)
    login_et = xml.etree.ElementTree.XML(login.text)
    session_key = login_et.get('session')
    account_url = f'https://{lib_url}.biblionix.com/catalog/ajax_backend/account.xml.pl'
    account_data = {'session': session_key}
    s.post(url=account_url, data=account_data)
    requests.utils.add_dict_to_cookiejar(s.cookies, {'session': session_key})
    renew_url = f'https://{lib_url}.biblionix.com/catalog/ajax_backend/account_command.xml.pl'
    renew_data = {'command': 'renew', 'checkout': item_id}
    renew = s.post(url=renew_url, data=renew_data)
    app.logger.debug(renew.text)
    renew_et = xml.etree.ElementTree.XML(renew.text)
    if renew_et.get('success') == '1':
        item = renew_et.find('item')
        new_due = yavin.util.clean_due_date(item.get('due'))
        _get_db().update_due_date({'due': new_due, 'item_id': item_id})
    return flask.redirect(flask.url_for('library'))


@app.route('/library/notify-now')
@secure
def library_notify_now():
    app.logger.info('Got library notification request')
    scheduler.add_job(library_notify)
    return flask.redirect(flask.url_for('library'))


@app.route('/library/sync-now')
@secure
def library_sync_now():
    app.logger.info('Got library sync request')
    scheduler.add_job(library_sync)
    return flask.redirect(flask.url_for('library'))


@app.route('/movie-night')
@secure
def movie_night():
    flask.g.people = list(_get_db().get_movie_night_people())
    flask.g.picks = _get_db().get_movie_night_picks()
    flask.g.today = yavin.util.today()
    return flask.render_template('movie_night.html')


@app.route('/movie-night/add-person', methods=['POST'])
@secure
def movie_night_add_person():
    params = {'person': flask.request.form.get('person')}
    _get_db().add_movie_night_person(params)
    return flask.redirect(flask.url_for('movie_night'))


@app.route('/movie-night/add-pick', methods=['POST'])
@secure
def movie_night_add_pick():
    params = {
        'pick_date': flask.request.form.get('pick_date'),
        'person_id': flask.request.form.get('person_id'),
        'pick_text': flask.request.form.get('pick_text')
    }
    _get_db().add_movie_night_pick(params)
    return flask.redirect(flask.url_for('movie_night'))


@app.route('/weight')
@secure
def weight():
    flask.g.today = yavin.util.today()
    flask.g.default_weight = _get_db().get_weight_most_recent()
    flask.g.weight_entries = _get_db().get_recent_weight_entries()
    return flask.render_template('weight.html')


@app.route('/weight/add', methods=['POST'])
@secure
def weight_add():
    entry_date = yavin.util.str_to_date(flask.request.form.get('entry_date'))
    entry_weight = flask.request.form.get('weight')
    app.logger.info(f'Attempting to add new weight entry for {entry_date}: {entry_weight} lbs')
    msg = _get_db().add_weight_entry(entry_date, entry_weight)
    if msg is not None:
        flask.flash(msg, 'alert-danger')
    return flask.redirect(flask.url_for('weight'))


@app.route('/sign-out')
def sign_out():
    flask.session.pop('profile', None)
    return flask.redirect(flask.url_for('index'))


def library_sync():
    app.logger.info('Syncing library data')
    with app.app_context():
        _get_db().clear_library_books()
        for lib_cred in _get_db().get_library_credentials():
            app.logger.info(f'Syncing library data for {lib_cred["display_name"]}')
            lib_url = lib_cred['library']
            s = requests.Session()
            login_url = f'https://{lib_url}.biblionix.com/catalog/ajax_backend/login.xml.pl'
            login_data = {'username': lib_cred['username'], 'password': lib_cred['password']}
            login = s.post(url=login_url, data=login_data)
            app.logger.info(f'Received {len(login.content)} bytes from {login_url}')
            app.logger.debug(login.text)
            login_et = xml.etree.ElementTree.XML(login.text)
            session_key = login_et.get('session')
            account_url = f'https://{lib_url}.biblionix.com/catalog/ajax_backend/account.xml.pl'
            account_data = {'session': session_key}
            account = s.post(url=account_url, data=account_data)
            app.logger.info(f'Received {len(account.content)} bytes from {account_url}')
            app.logger.debug(account.text)
            account_et = xml.etree.ElementTree.XML(account.text)
            _get_db().update_balance({'id': lib_cred['id'], 'balance': 0})
            for alert in account_et.findall('alerts'):
                if alert.get('balance'):
                    params = {
                        'id': lib_cred['id'],
                        'balance': int(alert.get('balance'))
                    }
                    _get_db().update_balance(params)
            for item in account_et.findall('item'):
                params = {
                    'credential_id': lib_cred['id'],
                    'title': item.get('title').replace('\xad', ''),
                    'due': item.get('due_raw'),
                    'renewable': item.get('renewable') == '1',
                    'item_id': item.get('id'),
                    'medium': item.get('medium').replace('\xad', '')
                }
                _get_db().add_library_book(params)


def library_notify():
    app.logger.info('Checking for due library items')
    with app.app_context():
        lib_url = flask.url_for('library')
        app.logger.debug(f'url for library: {lib_url}')
        for book in _get_db().get_library_books():
            title = book['title']
            due = book['due']
            app.logger.debug(f'{title} is due on {due}')
            if book['due'] <= yavin.util.today():
                app.logger.info(f'** {title} is due today or overdue')
                app.logger.info('Sending notification email')
                msg = email.message.EmailMessage()
                msg['Subject'] = 'Library alert'
                msg['From'] = config.admin_email
                msg['To'] = config.admin_email
                content = inspect.cleandoc(f'''
                    Hello,

                    Something is due (or possibly overdue) at the library today.

                    {lib_url}

                    (This is an automated message.)
                ''')
                msg.set_content(content)
                with smtplib.SMTP_SSL(host='smtp.gmail.com') as s:
                    s.login(user=config.admin_email, password=config.admin_password)
                    s.send_message(msg)
                break


def main():
    logging.basicConfig(format=config.log_format, level='DEBUG', stream=sys.stdout)
    app.logger.debug(f'yavin {config.version}')
    app.logger.debug(f'Changing log level to {config.log_level}')
    logging.getLogger().setLevel(config.log_level)

    if config.dsn is None:
        app.logger.critical('Missing environment variable DSN; I cannot start without a database')
    else:
        with app.app_context():
            _get_db().migrate()

        scheduler.start()

        scheduler.add_job(library_sync, 'interval', hours=6, start_date=yavin.util.in_two_minutes())
        scheduler.add_job(library_notify, 'cron', day='*', hour='3')

        url_prefix = config.application_root
        if url_prefix == '/':
            url_prefix = ''
        waitress.serve(app, port=config.port, url_prefix=url_prefix, url_scheme=config.scheme)
