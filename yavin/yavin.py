import apscheduler.schedulers.background
import datetime
import flask
import flask_oauth2_login
import flask_sslify
import functools
import logging
import os
import requests
import sys
import waitress
import xml.etree.ElementTree
import yavin.db
import yavin.util

log = logging.getLogger(__name__)

app = flask.Flask(__name__)

DEFAULTS = {
    'GOOGLE_LOGIN_REDIRECT_SCHEME': 'http',
    'LOGLEVEL': 'DEBUG',
    'PORT': 8080,
    'URL_PREFIX': ''
}

for key in ['ADMIN_EMAIL', 'DATABASE_URL', 'GOOGLE_LOGIN_CLIENT_ID', 'GOOGLE_LOGIN_CLIENT_SECRET',
            'GOOGLE_LOGIN_REDIRECT_SCHEME', 'LOGLEVEL', 'PORT', 'SECRET_KEY', 'UNIX_SOCKET', 'URL_PREFIX']:
    app.config[key] = os.environ.get(key, DEFAULTS.get(key))

if app.config['GOOGLE_LOGIN_REDIRECT_SCHEME'].lower() == 'https':
    sslify = flask_sslify.SSLify(app)

scheduler = apscheduler.schedulers.background.BackgroundScheduler()
scheduler.start()

google_login = flask_oauth2_login.GoogleLogin(app)


@google_login.login_success
def login_success(_, profile):
    flask.session['profile'] = profile
    log.debug('Google login success, redirecting to: {}'.format(flask.url_for('index')))
    return flask.redirect(flask.url_for('index'))


@google_login.login_failure
def login_failure(e):
    return flask.jsonify(errors=str(e))


def secure(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        profile = flask.session.get('profile')
        if profile is None:
            return flask.redirect(flask.url_for('index'))
        if profile.get('email') == app.config['ADMIN_EMAIL']:
            return f(*args, **kwargs)
        return flask.render_template('not_authorized.html')
    return decorated_function


def _get_db():
    _db = flask.g.get('_db')
    if _db is None:
        _db = yavin.db.YavinDatabase(app.config['DATABASE_URL'])
        flask.g._db = _db
    return _db


@app.route('/')
def index():
    profile = flask.session.get('profile')
    if profile is None:
        return flask.render_template('index.html', c={'sign_in_url': google_login.authorization_url()})
    return flask.render_template('signed_in.html')


@app.route('/electricity')
@secure
def electricity():
    c = {'records': _get_db().get_electricity()}
    return flask.render_template('electricity.html', c=c)


@app.route('/electricity/add', methods=['POST'])
def electricity_add():
    _get_db().add_electricity(flask.request.form)
    return flask.redirect(flask.url_for('electricity'))


@app.route('/jar')
@secure
def jar():
    c = {'today': yavin.util.today(), 'jar_entries': _get_db().get_recent_jar_entries()}
    return flask.render_template('jar.html', c=c)


@app.route('/jar/add', methods=['POST'])
@secure
def jar_add():
    entry_date = yavin.util.str_to_date(flask.request.form.get('entry_date'))
    log.debug('Adding new jar entry for {}'.format(entry_date))
    _get_db().add_jar_entry(entry_date)
    return flask.redirect(flask.url_for('jar'))


@app.route('/library')
@secure
def library():
    c = {
        'library_credentials': _get_db().get_library_credentials(),
        'library_books': _get_db().get_library_books()
    }
    return flask.render_template('library.html', c=c)


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
    lib_cred = _get_db().get_book_credentials({'item_id': item_id})
    s = requests.Session()
    login_url = f'https://{lib_cred["library"]}.biblionix.com/catalog/ajax_backend/login.xml.pl'
    login_data = {'username': lib_cred['username'], 'password': lib_cred['password']}
    login = s.post(url=login_url, data=login_data)
    login_et = xml.etree.ElementTree.XML(login.text)
    session_key = login_et.get('session')
    account_url = f'https://{lib_cred["library"]}.biblionix.com/catalog/ajax_backend/account.xml.pl'
    account_data = {'session': session_key}
    s.post(url=account_url, data=account_data)
    requests.utils.add_dict_to_cookiejar(s.cookies, {'session': session_key})
    renew_url = f'https://{lib_cred["library"]}.biblionix.com/catalog/ajax_backend/account_command.xml.pl'
    renew_data = {'command': 'renew', 'checkout': item_id}
    renew = s.post(url=renew_url, data=renew_data)
    log.debug(renew.text)
    renew_et = xml.etree.ElementTree.XML(renew.text)
    if renew_et.get('success') == '1':
        item = renew_et.find('item')
        new_due = datetime.datetime.strptime(item.get('due'), '%m\u2011%d\u2011%Y').date()
        _get_db().update_due_date({'due': new_due, 'item_id': item_id})
    return flask.redirect(flask.url_for('library'))


@app.route('/movie_night')
@secure
def movie_night():
    c = {'people': list(_get_db().get_movie_night_people()), 'picks': _get_db().get_movie_night_picks(),
         'today': yavin.util.today()}
    return flask.render_template('movie_night.html', c=c)


@app.route('/movie_night/add_person', methods=['POST'])
@secure
def movie_night_add_person():
    params = {'person': flask.request.form.get('person')}
    _get_db().add_movie_night_person(params)
    return flask.redirect(flask.url_for('movie_night'))


@app.route('/movie_night/add_pick', methods=['POST'])
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
    _db = _get_db()
    c = {'today': yavin.util.today(), 'default_weight': _db.get_weight_most_recent(),
         'weight_entries': _db.get_recent_weight_entries()}
    return flask.render_template('weight.html', c=c)


@app.route('/weight/add', methods=['POST'])
@secure
def weight_add():
    entry_date = yavin.util.str_to_date(flask.request.form.get('entry_date'))
    entry_weight = flask.request.form.get('weight')
    log.debug('Attempting to add new weight entry for {}: {} lbs'.format(entry_date, entry_weight))
    msg = _get_db().add_weight_entry(entry_date, entry_weight)
    if msg is not None:
        flask.flash(msg, 'alert-danger')
    return flask.redirect(flask.url_for('weight'))


@app.route('/sign_out')
def sign_out():
    flask.session.pop('profile', None)
    return flask.redirect(flask.url_for('index'))


@scheduler.scheduled_job('interval', hours=24)
def library_sync():
    log.debug('Syncing library data')
    with app.app_context():
        _get_db().clear_library_books()
        for lib_cred in _get_db().get_library_credentials():
            s = requests.Session()
            login_url = f'https://{lib_cred["library"]}.biblionix.com/catalog/ajax_backend/login.xml.pl'
            login_data = {'username': lib_cred['username'], 'password': lib_cred['password']}
            login = s.post(url=login_url, data=login_data)
            login_et = xml.etree.ElementTree.XML(login.text)
            session_key = login_et.get('session')
            account_url = f'https://{lib_cred["library"]}.biblionix.com/catalog/ajax_backend/account.xml.pl'
            account_data = {'session': session_key}
            account = s.post(url=account_url, data=account_data)
            log.debug(account.text)
            account_et = xml.etree.ElementTree.XML(account.text)
            _get_db().update_balance({'id': lib_cred['id'], 'balance': 0})
            for alert in account_et.findall('alerts'):
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


def main():
    c = app.config
    logging.basicConfig(stream=sys.stdout, level=c['LOGLEVEL'])
    with app.app_context():
        _get_db().migrate()
    scheduler.add_job(library_sync)
    if c['UNIX_SOCKET']:
        waitress.serve(app, unix_socket=c['UNIX_SOCKET'], url_prefix=c['URL_PREFIX'],
                       url_scheme=c['GOOGLE_LOGIN_REDIRECT_SCHEME'])
    else:
        waitress.serve(app, port=c['PORT'], url_prefix=c['URL_PREFIX'], url_scheme=c['GOOGLE_LOGIN_REDIRECT_SCHEME'])
