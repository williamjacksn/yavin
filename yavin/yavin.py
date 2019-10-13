import apscheduler.schedulers.background
import decimal
import email.message
import flask
import functools
import jwt
import logging
import requests
import smtplib
import sys
import urllib.parse
import uuid
import waitress
import werkzeug.middleware.proxy_fix
import werkzeug.utils
import xml.etree.ElementTree
import yavin.config
import yavin.db
import yavin.util

config = yavin.config.Config()
scheduler = apscheduler.schedulers.background.BackgroundScheduler()

app = flask.Flask(__name__)
app.wsgi_app = werkzeug.middleware.proxy_fix.ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_port=1)

app.config['APPLICATION_ROOT'] = config.application_root
app.config['PREFERRED_URL_SCHEME'] = config.scheme
app.config['SECRET_KEY'] = config.secret_key
app.config['SERVER_NAME'] = config.server_name

if config.scheme == 'https':
    app.config['SESSION_COOKIE_SECURE'] = True

app.jinja_env.filters['datetime'] = yavin.util.clean_datetime


def secure(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        session_email = flask.session.get('email')
        if session_email is None:
            return flask.redirect(flask.url_for('index'))
        if session_email == config.admin_email:
            return f(*args, **kwargs)
        return flask.render_template('not-authorized.html')
    return decorated_function


@app.before_request
def before_request():
    app.logger.debug(f'{flask.request.method} {flask.request.path}')
    if config.permanent_sessions:
        flask.session.permanent = True
    flask.g.db = yavin.db.YavinDatabase(config.dsn)


@app.route('/')
def index():
    session_email = flask.session.get('email')
    if session_email is None:
        return flask.render_template('index.html')
    flask.g.pages = {
        'captains_log': 'Captain&#x02bc;s log',
        'electricity': 'Electricity',
        'files': 'Files',
        'jar': 'Jar',
        'library': 'Library',
        'movie_night': 'Movie night',
        'weight': 'Weight'
    }
    return flask.render_template('signed-in.html')


@app.route('/captains-log')
@secure
def captains_log():
    db: yavin.db.YavinDatabase = flask.g.db
    flask.g.records = db.get_captains_log_entries()
    return flask.render_template('captains-log.html')


@app.route('/captains-log/delete', methods=['POST'])
@secure
def captains_log_delete():
    db: yavin.db.YavinDatabase = flask.g.db
    db.delete_captains_log_entry(flask.request.form.get('id'))
    return flask.redirect(flask.url_for('captains_log'))


@app.route('/captains-log/incoming', methods=['POST'])
def captains_log_incoming():
    db: yavin.db.YavinDatabase = flask.g.db
    app.logger.debug(f'json: {flask.request.json}')
    auth_phrase: str = flask.request.json['auth-phrase']
    if auth_phrase.lower() == config.admin_auth_phrase:
        app.logger.debug('Authorization accepted')
        log_text = flask.request.json['log-text']
        db.add_captains_log_entry(log_text)
        return 'Log recorded.'
    return 'Authorization failure.'


@app.route('/captains-log/update', methods=['POST'])
@secure
def captains_log_update():
    db: yavin.db.YavinDatabase = flask.g.db
    log_text = flask.request.form.get('log_text')
    db.update_captains_log_entry(flask.request.form.get('id'), log_text)
    return flask.redirect(flask.url_for('captains_log'))


@app.route('/electricity')
@secure
def electricity():
    db: yavin.db.YavinDatabase = flask.g.db
    flask.g.records = db.get_electricity()
    return flask.render_template('electricity.html')


@app.route('/electricity/add', methods=['POST'])
def electricity_add():
    db: yavin.db.YavinDatabase = flask.g.db
    bill_date = yavin.util.str_to_date(flask.request.form.get('bill_date'))
    kwh = int(flask.request.form.get('kwh'))
    charge = decimal.Decimal(flask.request.form.get('charge'))
    bill = decimal.Decimal(flask.request.form.get('bill'))
    db.add_electricity(bill_date, kwh, charge, bill)
    return flask.redirect(flask.url_for('electricity'))


@app.route('/files')
@secure
def files():
    return flask.render_template('files.html')


@app.route('/files/upload', methods=['POST'])
@secure
def files_upload():
    app.logger.debug(f'files: {flask.request.files}')
    file = flask.request.files.get('file')
    filename = werkzeug.utils.secure_filename(file.filename)
    file.save(str(config.file_upload_dir / filename))
    return flask.redirect(flask.url_for('files'))


@app.route('/jar')
@secure
def jar():
    db: yavin.db.YavinDatabase = flask.g.db
    flask.g.today = yavin.util.today()
    flask.g.jar_entries = db.get_recent_jar_entries()
    return flask.render_template('jar.html')


@app.route('/jar/add', methods=['POST'])
@secure
def jar_add():
    db: yavin.db.YavinDatabase = flask.g.db
    entry_date = yavin.util.str_to_date(flask.request.form.get('entry_date'))
    app.logger.info(f'Adding new jar entry for {entry_date}')
    db.add_jar_entry(entry_date)
    return flask.redirect(flask.url_for('jar'))


@app.route('/library')
@secure
def library():
    db: yavin.db.YavinDatabase = flask.g.db
    flask.g.library_credentials = db.get_library_credentials()
    flask.g.library_books = db.get_library_books()
    return flask.render_template('library.html')


@app.route('/library/add', methods=['POST'])
@secure
def library_add():
    db: yavin.db.YavinDatabase = flask.g.db
    params = {
        'display_name': flask.request.form.get('display_name'),
        'library': flask.request.form.get('library'),
        'username': flask.request.form.get('username'),
        'password': flask.request.form.get('password')
    }
    db.add_library_credential(params)
    scheduler.add_job(library_sync)
    return flask.redirect(flask.url_for('library'))


@app.route('/library/delete', methods=['POST'])
@secure
def library_delete():
    db: yavin.db.YavinDatabase = flask.g.db
    db.delete_library_credential(flask.request.form)
    scheduler.add_job(library_sync)
    return flask.redirect(flask.url_for('library'))


@app.route('/library/renew', methods=['POST'])
@secure
def library_renew():
    db: yavin.db.YavinDatabase = flask.g.db
    item_id = flask.request.form.get('item_id')
    app.logger.info(f'Attempting to renew item {item_id}')
    lib_cred = db.get_book_credentials({'item_id': item_id})
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
        db.update_due_date({'due': new_due, 'item_id': item_id})
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
    db: yavin.db.YavinDatabase = flask.g.db
    flask.g.people = db.get_movie_night_people()
    flask.g.picks = db.get_movie_night_picks()
    flask.g.today = yavin.util.today()
    return flask.render_template('movie-night.html')


@app.route('/movie-night/add-person', methods=['POST'])
@secure
def movie_night_add_person():
    db: yavin.db.YavinDatabase = flask.g.db
    params = {'person': flask.request.form.get('person')}
    db.add_movie_night_person(params)
    return flask.redirect(flask.url_for('movie_night'))


@app.route('/movie-night/add-pick', methods=['POST'])
@secure
def movie_night_add_pick():
    db: yavin.db.YavinDatabase = flask.g.db
    params = {
        'pick_date': flask.request.form.get('pick_date'),
        'person_id': flask.request.form.get('person_id'),
        'pick_text': flask.request.form.get('pick_text'),
        'pick_url': flask.request.form.get('pick_url')
    }
    app.logger.debug(params)
    db.add_movie_night_pick(params)
    return flask.redirect(flask.url_for('movie_night'))


@app.route('/movie-night/delete-pick', methods=['POST'])
@secure
def movie_night_delete_pick():
    db: yavin.db.YavinDatabase = flask.g.db
    params = {
        'id': flask.request.form.get('id')
    }
    db.delete_movie_night_pick(params)
    return flask.redirect(flask.url_for('movie_night'))


@app.route('/movie-night/edit-pick', methods=['POST'])
@secure
def movie_night_edit_pick():
    db: yavin.db.YavinDatabase = flask.g.db
    params = {
        'id': flask.request.form.get('id'),
        'pick_date': flask.request.form.get('pick_date'),
        'person_id': flask.request.form.get('person_id'),
        'pick_text': flask.request.form.get('pick_text'),
        'pick_url': flask.request.form.get('pick_url'),
    }
    db.edit_movie_night_pick(params)
    return flask.redirect(flask.url_for('movie_night'))


@app.route('/weight')
@secure
def weight():
    db: yavin.db.YavinDatabase = flask.g.db
    flask.g.today = yavin.util.today()
    flask.g.default_weight = db.get_weight_most_recent()
    flask.g.weight_entries = db.get_recent_weight_entries()
    return flask.render_template('weight.html')


@app.route('/weight/add', methods=['POST'])
@secure
def weight_add():
    db: yavin.db.YavinDatabase = flask.g.db
    entry_date = yavin.util.str_to_date(flask.request.form.get('entry_date'))
    entry_weight = flask.request.form.get('weight')
    app.logger.info(f'Attempting to add new weight entry for {entry_date}: {entry_weight} lbs')
    msg = db.add_weight_entry(entry_date, entry_weight)
    if msg is not None:
        flask.flash(msg, 'alert-danger')
    return flask.redirect(flask.url_for('weight'))


@app.route('/authorize')
def authorize():
    for key, value in flask.request.values.items():
        app.logger.debug(f'{key}: {value}')
    if flask.session.get('state') != flask.request.values.get('state'):
        return 'State mismatch', 401
    discovery_document = requests.get(config.openid_discovery_document).json()
    token_endpoint = discovery_document.get('token_endpoint')
    data = {
        'code': flask.request.values.get('code'),
        'client_id': config.openid_client_id,
        'client_secret': config.openid_client_secret,
        'redirect_uri': flask.url_for('authorize', _external=True),
        'grant_type': 'authorization_code'
    }
    resp = requests.post(token_endpoint, data=data).json()
    id_token = resp.get('id_token')
    algorithms = discovery_document.get('id_token_signing_alg_values_supported')
    claim = jwt.decode(id_token, verify=False, algorithms=algorithms)
    flask.session['email'] = claim.get('email')
    return flask.redirect(flask.url_for('index'))


@app.route('/sign-in')
def sign_in():
    state = str(uuid.uuid4())
    flask.session['state'] = state
    redirect_uri = flask.url_for('authorize', _external=True)
    query = {
        'client_id': config.openid_client_id,
        'response_type': 'code',
        'scope': 'openid email profile',
        'redirect_uri': redirect_uri,
        'state': state
    }
    discovery_document = requests.get(config.openid_discovery_document).json()
    auth_endpoint = discovery_document.get('authorization_endpoint')
    auth_url = f'{auth_endpoint}?{urllib.parse.urlencode(query)}'
    return flask.redirect(auth_url, 307)


@app.route('/sign-out')
def sign_out():
    flask.session.pop('email', None)
    return flask.redirect(flask.url_for('index'))


def library_sync():
    app.logger.info('Syncing library data')
    with app.app_context():
        db = yavin.db.YavinDatabase(config.dsn)
        db.clear_library_books()
        for lib_cred in db.get_library_credentials():
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
            db.update_balance({'id': lib_cred['id'], 'balance': 0})
            for alert in account_et.findall('alerts'):
                if alert.get('balance'):
                    params = {
                        'id': lib_cred['id'],
                        'balance': int(alert.get('balance'))
                    }
                    db.update_balance(params)
            for item in account_et.findall('item'):
                params = {
                    'credential_id': lib_cred['id'],
                    'title': item.get('title').replace('\xad', ''),
                    'due': item.get('due_raw'),
                    'renewable': item.get('renewable') == '1',
                    'item_id': item.get('id'),
                    'medium': item.get('medium').replace('\xad', '')
                }
                db.add_library_book(params)


def library_notify():
    app.logger.info('Checking for due library items')
    with app.app_context():
        db = yavin.db.YavinDatabase(config.dsn)
        lib_url = flask.url_for('library')
        app.logger.debug(f'url for library: {lib_url}')
        for book in db.get_library_books():
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
                content = flask.render_template('email-library-item-due.jinja2', lib_url=lib_url)
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
        db = yavin.db.YavinDatabase(config.dsn)
        db.migrate()

        scheduler.start()
        scheduler.add_job(library_sync, 'interval', hours=6, start_date=yavin.util.in_two_minutes())
        scheduler.add_job(library_notify, 'cron', day='*', hour='3')

        url_prefix = config.application_root
        if url_prefix == '/':
            url_prefix = ''
        waitress.serve(app, port=config.port, url_prefix=url_prefix, url_scheme=config.scheme, ident=None)
