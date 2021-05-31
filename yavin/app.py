import decimal
import flask
import functools
import jwt
import logging
import requests
import requests.utils
import sys
import urllib.parse
import uuid
import waitress
import werkzeug.middleware.proxy_fix
import werkzeug.utils
import yavin.db
import yavin.settings
import yavin.tasks
import yavin.util

settings = yavin.settings.Settings()

app = flask.Flask(__name__)
app.wsgi_app = werkzeug.middleware.proxy_fix.ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_port=1)

app.config['APPLICATION_ROOT'] = settings.application_root
app.config['PREFERRED_URL_SCHEME'] = settings.scheme
app.config['SECRET_KEY'] = settings.secret_key
app.config['SERVER_NAME'] = settings.server_name

if settings.scheme == 'https':
    app.config['SESSION_COOKIE_SECURE'] = True

app.jinja_env.filters['datetime'] = yavin.util.clean_datetime


def secure(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        session_email = flask.session.get('email')
        if session_email is None:
            return flask.redirect(flask.url_for('index'))
        if session_email == settings.admin_email:
            return f(*args, **kwargs)
        return flask.render_template('not-authorized.html')
    return decorated_function


@app.before_request
def before_request():
    app.logger.debug(f'{flask.request.method} {flask.request.path}')
    if settings.permanent_sessions:
        flask.session.permanent = True
    flask.g.db = yavin.db.YavinDatabase(settings.dsn)
    flask.g.settings = settings


@app.get('/')
def index():
    session_email = flask.session.get('email')
    if session_email is None:
        return flask.render_template('index.html')
    flask.g.pages = {
        'captains_log': 'Captain&#x02bc;s log',
        'electricity': 'Electricity',
        'jar': 'Jar',
        'library': 'Library',
        'movie_night': 'Movie night',
        'phone': 'Phone usage',
        'weight': 'Weight'
    }
    return flask.render_template('signed-in.html')


@app.get('/captains-log')
@secure
def captains_log():
    db: yavin.db.YavinDatabase = flask.g.db
    flask.g.records = db.get_captains_log_entries()
    return flask.render_template('captains-log.html')


@app.post('/captains-log/delete')
@secure
def captains_log_delete():
    db: yavin.db.YavinDatabase = flask.g.db
    db.delete_captains_log_entry(flask.request.form.get('id'))
    return flask.redirect(flask.url_for('captains_log'))


@app.post('/captains-log/incoming')
def captains_log_incoming():
    db: yavin.db.YavinDatabase = flask.g.db
    app.logger.debug(f'json: {flask.request.json}')
    auth_phrase: str = flask.request.json['auth-phrase']
    if auth_phrase.lower() == settings.admin_auth_phrase:
        app.logger.debug('Authorization accepted')
        log_text = flask.request.json['log-text']
        db.add_captains_log_entry(log_text)
        return 'Log recorded.'
    return 'Authorization failure.'


@app.post('/captains-log/update')
@secure
def captains_log_update():
    db: yavin.db.YavinDatabase = flask.g.db
    log_text = flask.request.form.get('log_text')
    db.update_captains_log_entry(flask.request.form.get('id'), log_text)
    return flask.redirect(flask.url_for('captains_log'))


@app.get('/electricity')
@secure
def electricity():
    db: yavin.db.YavinDatabase = flask.g.db
    flask.g.records = db.get_electricity()
    return flask.render_template('electricity.html')


@app.post('/electricity/add')
def electricity_add():
    db: yavin.db.YavinDatabase = flask.g.db
    bill_date = yavin.util.str_to_date(flask.request.form.get('bill_date'))
    kwh = int(flask.request.form.get('kwh'))
    charge = decimal.Decimal(flask.request.form.get('charge'))
    bill = decimal.Decimal(flask.request.form.get('bill'))
    db.add_electricity(bill_date, kwh, charge, bill)
    return flask.redirect(flask.url_for('electricity'))


@app.get('/jar')
@secure
def jar():
    db: yavin.db.YavinDatabase = flask.g.db
    flask.g.today = yavin.util.today()
    flask.g.jar_entries = db.get_recent_jar_entries()
    return flask.render_template('jar.html')


@app.post('/jar/add')
@secure
def jar_add():
    db: yavin.db.YavinDatabase = flask.g.db
    entry_date = yavin.util.str_to_date(flask.request.form.get('entry_date'))
    app.logger.info(f'Adding new jar entry for {entry_date}')
    db.add_jar_entry(entry_date)
    return flask.redirect(flask.url_for('jar'))


@app.get('/library')
@secure
def library():
    db: yavin.db.YavinDatabase = flask.g.db
    flask.g.library_credentials = db.get_library_credentials()
    flask.g.library_books = db.get_library_books()
    return flask.render_template('library.html')


@app.post('/library/add')
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
    yavin.tasks.scheduler.add_job(yavin.tasks.library_sync)
    return flask.redirect(flask.url_for('library'))


@app.post('/library/delete')
@secure
def library_delete():
    db: yavin.db.YavinDatabase = flask.g.db
    db.delete_library_credential(flask.request.form)
    yavin.tasks.scheduler.add_job(yavin.tasks.library_sync)
    return flask.redirect(flask.url_for('library'))


@app.post('/library/renew')
@secure
def library_renew():
    item_id = flask.request.form.get('item_id')
    yavin.tasks.library_renew(item_id)
    return flask.redirect(flask.url_for('library'))


@app.get('/library/notify-now')
@secure
def library_notify_now():
    app.logger.info('Got library notification request')
    yavin.tasks.scheduler.add_job(yavin.tasks.library_notify, args=[app])
    return flask.redirect(flask.url_for('library'))


@app.get('/library/sync-now')
@secure
def library_sync_now():
    app.logger.info('Got library sync request')
    yavin.tasks.scheduler.add_job(yavin.tasks.library_sync)
    return flask.redirect(flask.url_for('library'))


@app.get('/movie-night')
@secure
def movie_night():
    db: yavin.db.YavinDatabase = flask.g.db
    flask.g.people = db.get_movie_night_people()
    flask.g.picks = db.get_movie_night_picks()
    flask.g.today = yavin.util.today()
    return flask.render_template('movie-night.html')


@app.post('/movie-night/add-person')
@secure
def movie_night_add_person():
    db: yavin.db.YavinDatabase = flask.g.db
    params = {'person': flask.request.form.get('person')}
    db.add_movie_night_person(params)
    return flask.redirect(flask.url_for('movie_night'))


@app.post('/movie-night/add-pick')
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


@app.post('/movie-night/delete-pick')
@secure
def movie_night_delete_pick():
    db: yavin.db.YavinDatabase = flask.g.db
    params = {
        'id': flask.request.form.get('id')
    }
    db.delete_movie_night_pick(params)
    return flask.redirect(flask.url_for('movie_night'))


@app.post('/movie-night/edit-pick')
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


@app.get('/phone')
@secure
def phone():
    db: yavin.db.YavinDatabase = flask.g.db
    flask.g.records = db.get_phone_usage()
    return flask.render_template('phone.html')


@app.post('/phone/add')
@secure
def phone_add():
    db: yavin.db.YavinDatabase = flask.g.db
    v = flask.request.values
    db.add_phone_usage(v.get('start-date'), v.get('end-date'), v.get('minutes'), v.get('messages'), v.get('megabytes'))
    return flask.redirect(flask.url_for('phone'))


@app.get('/weight')
@secure
def weight():
    db: yavin.db.YavinDatabase = flask.g.db
    flask.g.today = yavin.util.today()
    flask.g.default_weight = db.get_weight_most_recent()
    flask.g.weight_entries = db.get_recent_weight_entries()
    return flask.render_template('weight.html')


@app.post('/weight/add')
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


@app.get('/authorize')
def authorize():
    for key, value in flask.request.values.items():
        app.logger.debug(f'{key}: {value}')
    if flask.session.get('state') != flask.request.values.get('state'):
        return 'State mismatch', 401
    discovery_document = requests.get(settings.openid_discovery_document).json()
    token_endpoint = discovery_document.get('token_endpoint')
    data = {
        'code': flask.request.values.get('code'),
        'client_id': settings.openid_client_id,
        'client_secret': settings.openid_client_secret,
        'redirect_uri': flask.url_for('authorize', _external=True),
        'grant_type': 'authorization_code'
    }
    resp = requests.post(token_endpoint, data=data).json()
    id_token = resp.get('id_token')
    algorithms = discovery_document.get('id_token_signing_alg_values_supported')
    claim = jwt.decode(id_token, options={'verify_signature': False}, algorithms=algorithms)
    flask.session['email'] = claim.get('email')
    return flask.redirect(flask.url_for('index'))


@app.get('/sign-in')
def sign_in():
    state = str(uuid.uuid4())
    flask.session['state'] = state
    redirect_uri = flask.url_for('authorize', _external=True)
    query = {
        'client_id': settings.openid_client_id,
        'response_type': 'code',
        'scope': 'openid email profile',
        'redirect_uri': redirect_uri,
        'state': state
    }
    discovery_document = requests.get(settings.openid_discovery_document).json()
    auth_endpoint = discovery_document.get('authorization_endpoint')
    auth_url = f'{auth_endpoint}?{urllib.parse.urlencode(query)}'
    return flask.redirect(auth_url, 307)


@app.get('/sign-out')
def sign_out():
    flask.session.pop('email', None)
    return flask.redirect(flask.url_for('index'))


def main():
    logging.basicConfig(format=settings.log_format, level='DEBUG', stream=sys.stdout)
    app.logger.debug(f'yavin {settings.version}')
    app.logger.debug(f'Changing log level to {settings.log_level}')
    logging.getLogger().setLevel(settings.log_level)

    if settings.dsn is None:
        app.logger.critical('Missing environment variable DSN; I cannot start without a database')
    else:
        db = yavin.db.YavinDatabase(settings.dsn)
        db.migrate()

        yavin.tasks.scheduler.start()
        yavin.tasks.scheduler.add_job(yavin.tasks.library_sync, 'interval', hours=6,
                                      start_date=yavin.util.in_two_minutes())
        yavin.tasks.scheduler.add_job(yavin.tasks.library_notify, 'cron', day='*', hour='3', args=[app])

        url_prefix = settings.application_root
        if url_prefix == '/':
            url_prefix = ''
        waitress.serve(app, port=settings.port, threads=settings.web_server_threads, url_prefix=url_prefix,
                       url_scheme=settings.scheme, ident=None)
