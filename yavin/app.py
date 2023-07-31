import decimal
import flask
import functools
import jwt
import logging
import lxml.html
import requests
import requests.utils
import urllib.parse
import uuid
import waitress
import werkzeug.middleware.proxy_fix
import werkzeug.utils
import yavin.db
import yavin.settings
import yavin.tasks
import yavin.util

log = logging.getLogger(__name__)

__version__ = '2023.2'

settings = yavin.settings.Settings()

app = flask.Flask(__name__)
app.wsgi_app = werkzeug.middleware.proxy_fix.ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_port=1)

app.config.update(
    PREFERRED_URL_SCHEME=settings.scheme,
    SECRET_KEY=settings.secret_key,
    SERVER_NAME=settings.server_name,
    SESSION_COOKIE_SAMESITE='Lax'
)

if settings.scheme == 'https':
    app.config['SESSION_COOKIE_SECURE'] = True

app.jinja_env.filters['datetime'] = yavin.util.clean_datetime


def permission_required(permission: str):
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            app.logger.debug(f'Checking permission for {flask.g.email}')
            if flask.g.email is None:
                return flask.redirect(flask.url_for('index'))
            if 'admin' in flask.g.permissions or permission in flask.g.permissions:
                return f(*args, **kwargs)
            return flask.render_template('not-authorized.html')
        return decorated_function
    return decorator


@app.before_request
def before_request():
    log.debug(f'{flask.request.method} {flask.request.path}')
    flask.session.permanent = True
    flask.g.db = yavin.db.YavinDatabase(settings.dsn)
    flask.g.settings = settings
    flask.g.app_settings = flask.g.db.settings_list()
    flask.g.version = __version__
    flask.g.email = flask.session.get('email')
    flask.g.permissions = flask.g.db.user_permissions_get(flask.g.email)


@app.get('/')
def index():
    session_email = flask.session.get('email')
    if session_email is None:
        return flask.render_template('index.html')
    flask.g.pages = [
        {
            'title': 'Balances',
            'view': 'balances',
            'visible': 'balances' in flask.g.permissions or 'admin' in flask.g.permissions,
        },
        {
            'title': 'Billboard Hot 100 #1',
            'view': 'billboard',
            'visible': 'billboard' in flask.g.permissions or 'admin' in flask.g.permissions,
        },
        {
            'title': 'Captain&#x02bc;s log',
            'view': 'captains_log',
            'visible': 'captains-log' in flask.g.permissions or 'admin' in flask.g.permissions,
        },
        {
            'title': 'Electricity',
            'view': 'electricity',
            'visible': 'electricity' in flask.g.permissions or 'admin' in flask.g.permissions,
        },
        {
            'title': 'Expenses',
            'view': 'expenses',
            'visible': 'expenses' in flask.g.permissions or 'admin' in flask.g.permissions,
        },
        {
            'title': 'Jar',
            'view': 'jar',
            'visible': 'jar' in flask.g.permissions or 'admin' in flask.g.permissions,
        },
        {
            'title': 'Library',
            'view': 'library',
            'visible': 'library' in flask.g.permissions or 'admin' in flask.g.permissions,
        },
        {
            'title': 'Movie night',
            'view': 'movie_night',
            'visible': 'movie-night' in flask.g.permissions or 'admin' in flask.g.permissions,
        },
        {
            'title': 'Packages',
            'view': 'packages',
            'visible': 'packages' in flask.g.permissions or 'admin' in flask.g.permissions,
        },
        {
            'title': 'Phone usage',
            'view': 'phone',
            'visible': 'phone' in flask.g.permissions or 'admin' in flask.g.permissions,
        },
        {
            'title': 'Weight',
            'view': 'weight',
            'visible': 'weight' in flask.g.permissions or 'admin' in flask.g.permissions,
        },
    ]
    return flask.render_template('signed-in.html')


@app.get('/app-settings')
@permission_required('admin')
def app_settings():
    return flask.render_template('app-settings.html')


@app.post('/app-settings/update')
@permission_required('admin')
def app_settings_update():
    db: yavin.db.YavinDatabase = flask.g.db

    text_settings = [
        'expenses_db',
        'smtp_from_address',
        'smtp_password',
        'smtp_server',
        'smtp_username',
    ]
    for k, v in flask.request.values.items():
        log.debug(f'{k}: {v!r}')
        if k in text_settings:
            if v == '':
                db.settings_delete(k)
            else:
                db.settings_update(k, v)

    bool_settings = [
        'debug_layout',
    ]
    for setting_id in bool_settings:
        setting_value = 'true' if setting_id in flask.request.values else 'false'
        db.settings_update(setting_id, setting_value)

    return flask.redirect(flask.url_for('app_settings'))


@app.get('/balances')
@permission_required('balances')
def balances():
    flask.g.accounts = flask.g.db.balances_accounts_list()
    return flask.render_template('balances.html')


@app.get('/balances/<uuid:account_id>')
@permission_required('balances')
def balances_detail(account_id: uuid.UUID):
    flask.g.account_id = account_id
    flask.g.transactions = flask.g.db.balances_transactions_list(account_id)
    flask.g.account_name = flask.g.transactions[0].get('account_name')
    flask.g.account_balance = flask.g.transactions[0].get('account_balance')
    flask.g.today = yavin.util.today()
    return flask.render_template('balances-detail.html')


@app.post('/balances/add-transaction')
@permission_required('balances')
def balances_add_tx():
    account_id = flask.request.values.get('account-id')
    params = {
        'account_id': account_id,
        'tx_date': flask.request.values.get('tx-date'),
        'tx_description': flask.request.values.get('tx-description'),
        'tx_value': flask.request.values.get('tx-value'),
    }
    flask.g.db.balances_transactions_add(params)
    return flask.redirect(flask.url_for('balances_detail', account_id=account_id))


@app.get('/billboard')
@permission_required('billboard')
def billboard():
    url = 'https://www.billboard.com/charts/hot-100/'
    resp = requests.get(url)
    resp.raise_for_status()
    doc = lxml.html.document_fromstring(resp.content)
    title_h3 = doc.cssselect('h3')[0]
    div = title_h3.getparent()
    artist_p = div.cssselect('p')[0]
    flask.g.title = str(title_h3.text_content()).strip()
    flask.g.artist = str(artist_p.text_content()).strip()
    app.logger.debug(f'Current number 1 song is {flask.g.title} by {flask.g.artist}')
    return flask.render_template('billboard.html')


@app.get('/captains-log')
@permission_required('captains-log')
def captains_log():
    db: yavin.db.YavinDatabase = flask.g.db
    flask.g.records = db.captains_log_list()
    return flask.render_template('captains-log.html')


@app.post('/captains-log/delete')
@permission_required('captains-log')
def captains_log_delete():
    db: yavin.db.YavinDatabase = flask.g.db
    db.captains_log_delete(flask.request.form.get('id'))
    return flask.redirect(flask.url_for('captains_log'))


@app.post('/captains-log/incoming')
def captains_log_incoming():
    db: yavin.db.YavinDatabase = flask.g.db
    log.debug(f'json: {flask.request.json}')
    auth_phrase: str = flask.request.json['auth-phrase']
    if auth_phrase.lower() == settings.admin_auth_phrase:
        log.debug('Authorization accepted')
        log_text = flask.request.json['log-text']
        db.captains_log_insert(log_text)
        return 'Log recorded.'
    return 'Authorization failure.'


@app.post('/captains-log/update')
@permission_required('captains-log')
def captains_log_update():
    db: yavin.db.YavinDatabase = flask.g.db
    log_text = flask.request.form.get('log_text')
    db.captains_log_update(flask.request.form.get('id'), log_text)
    return flask.redirect(flask.url_for('captains_log'))


@app.get('/electricity')
@permission_required('electricity')
def electricity():
    db: yavin.db.YavinDatabase = flask.g.db
    flask.g.records = db.electricity_list()
    return flask.render_template('electricity.html')


@app.post('/electricity/add')
@permission_required('electricity')
def electricity_add():
    db: yavin.db.YavinDatabase = flask.g.db
    bill_date = yavin.util.str_to_date(flask.request.form.get('bill_date'))
    kwh = int(flask.request.form.get('kwh'))
    charge = decimal.Decimal(flask.request.form.get('charge'))
    bill = decimal.Decimal(flask.request.form.get('bill'))
    db.electricity_insert(bill_date, kwh, charge, bill)
    return flask.redirect(flask.url_for('electricity'))


@app.get('/expenses')
@permission_required('expenses')
def expenses():
    ex_db_path = flask.g.app_settings.get('expenses_db')
    if ex_db_path is None:
        return flask.redirect(flask.url_for('app_settings'))
    ex_db = yavin.db.ExpensesDatabase(flask.g.app_settings.get('expenses_db'))
    try:
        start_date = yavin.util.str_to_date(flask.request.values.get('start_date'))
    except (TypeError, ValueError):
        start_date = None
    try:
        end_date = yavin.util.str_to_date(flask.request.values.get('end_date'))
    except (TypeError, ValueError):
        end_date = None
    if start_date is None:
        if end_date is None:
            start_date = yavin.util.today().replace(day=1)
            end_date = yavin.util.today()
            log.debug(f'No dates provided, using {start_date} to {end_date}')
        else:
            start_date = yavin.util.add_days(end_date, -30)
            log.debug(f'Only end_date provided, using {start_date} to {end_date}')
    else:
        if end_date is None:
            end_date = yavin.util.add_days(start_date, 30)
            log.debug(f'Only start_date provided, using {start_date} to {end_date}')
        elif start_date > end_date:
            start_date, end_date = end_date, start_date
            log.debug(f'Dates are out of order, using {start_date} to {end_date}')
        else:
            log.debug(f'Both dates provided, using {start_date} to {end_date}')
    flask.g.start_date = start_date
    flask.g.end_date = end_date
    flask.g.expenses = ex_db.get_expenses('Root Account:Expenses%', start_date, end_date)
    flask.g.total = sum([e['amount'] for e in flask.g.expenses], 0)
    return flask.render_template('expenses.html')


@app.get('/jar')
@permission_required('jar')
def jar():
    db: yavin.db.YavinDatabase = flask.g.db
    flask.g.today = yavin.util.today()
    flask.g.jar_entries = db.jar_entries_list()
    return flask.render_template('jar.html')


@app.post('/jar/add')
@permission_required('jar')
def jar_add():
    db: yavin.db.YavinDatabase = flask.g.db
    entry_date = yavin.util.str_to_date(flask.request.form.get('entry_date'))
    log.info(f'Adding new jar entry for {entry_date}')
    db.jar_entries_insert(entry_date)
    return flask.redirect(flask.url_for('jar'))


@app.get('/library')
@permission_required('library')
def library():
    db: yavin.db.YavinDatabase = flask.g.db
    flask.g.library_credentials = db.library_credentials_list()
    flask.g.library_books = db.library_books_list()
    return flask.render_template('library.html')


@app.post('/library/add')
@permission_required('library')
def library_add():
    db: yavin.db.YavinDatabase = flask.g.db
    params = {
        'display_name': flask.request.form.get('display_name'),
        'library': flask.request.form.get('library'),
        'username': flask.request.form.get('username'),
        'password': flask.request.form.get('password')
    }
    db.library_credentials_insert(params)
    yavin.tasks.scheduler.add_job(yavin.tasks.library_sync)
    return flask.redirect(flask.url_for('library'))


@app.post('/library/delete')
@permission_required('library')
def library_delete():
    db: yavin.db.YavinDatabase = flask.g.db
    db.library_credentials_delete(flask.request.form)
    yavin.tasks.scheduler.add_job(yavin.tasks.library_sync)
    return flask.redirect(flask.url_for('library'))


@app.post('/library/renew')
@permission_required('library')
def library_renew():
    item_id = flask.request.form.get('item_id')
    yavin.tasks.library_renew(item_id)
    return flask.redirect(flask.url_for('library'))


@app.get('/library/notify-now')
@permission_required('library')
def library_notify_now():
    log.info('Got library notification request')
    yavin.tasks.scheduler.add_job(yavin.tasks.library_notify, args=[app])
    return flask.redirect(flask.url_for('library'))


@app.get('/library/sync-now')
@permission_required('library')
def library_sync_now():
    log.info('Got library sync request')
    yavin.tasks.scheduler.add_job(yavin.tasks.library_sync)
    return flask.redirect(flask.url_for('library'))


@app.get('/movie-night')
@permission_required('movie-night')
def movie_night():
    db: yavin.db.YavinDatabase = flask.g.db
    flask.g.people = db.movie_people_list()
    flask.g.picks = db.movie_picks_list()
    flask.g.today = yavin.util.today()
    return flask.render_template('movie-night.html')


@app.post('/movie-night/add-person')
@permission_required('movie-night')
def movie_night_add_person():
    db: yavin.db.YavinDatabase = flask.g.db
    params = {'person': flask.request.form.get('person')}
    db.movie_people_insert(params)
    return flask.redirect(flask.url_for('movie_night'))


@app.post('/movie-night/add-pick')
@permission_required('movie-night')
def movie_night_add_pick():
    db: yavin.db.YavinDatabase = flask.g.db
    params = {
        'pick_date': flask.request.form.get('pick_date'),
        'person_id': flask.request.form.get('person_id'),
        'pick_text': flask.request.form.get('pick_text'),
        'pick_url': flask.request.form.get('pick_url')
    }
    log.debug(params)
    db.movie_picks_insert(params)
    return flask.redirect(flask.url_for('movie_night'))


@app.post('/movie-night/delete-pick')
@permission_required('movie-night')
def movie_night_delete_pick():
    db: yavin.db.YavinDatabase = flask.g.db
    params = {
        'id': flask.request.form.get('id')
    }
    db.movie_picks_delete(params)
    return flask.redirect(flask.url_for('movie_night'))


@app.post('/movie-night/edit-pick')
@permission_required('movie-night')
def movie_night_edit_pick():
    db: yavin.db.YavinDatabase = flask.g.db
    params = {
        'id': flask.request.form.get('id'),
        'pick_date': flask.request.form.get('pick_date'),
        'person_id': flask.request.form.get('person_id'),
        'pick_text': flask.request.form.get('pick_text'),
        'pick_url': flask.request.form.get('pick_url'),
    }
    db.movie_picks_update(params)
    return flask.redirect(flask.url_for('movie_night'))


@app.get('/packages')
@permission_required('packages')
def packages():
    db: yavin.db.YavinDatabase = flask.g.db
    flask.g.packages = db.packages_list()
    return flask.render_template('packages.html')


@app.post('/packages/update')
@permission_required('packages')
def packages_update():
    for k, v in flask.request.values.lists():
        log.debug(f'{k}: {v}')
    params = {
        'arrived_at': flask.request.values.get('arrived-at') or None,
        'expected_at': flask.request.values.get('expected-at') or None,
        'notes': flask.request.values.get('notes'),
        'shipper': flask.request.values.get('shipper'),
        'tracking_number': flask.request.values.get('tracking-number'),
    }
    db: yavin.db.YavinDatabase = flask.g.db
    db.packages_update(**params)
    return flask.redirect(flask.url_for('packages'))


@app.get('/phone')
@permission_required('phone')
def phone():
    db: yavin.db.YavinDatabase = flask.g.db
    flask.g.records = db.phone_usage_list()
    return flask.render_template('phone.html')


@app.post('/phone/add')
@permission_required('phone')
def phone_add():
    db: yavin.db.YavinDatabase = flask.g.db
    v = flask.request.values
    db.phone_usage_insert(v.get('start-date'), v.get('end-date'), v.get('minutes'), v.get('messages'), v.get('megabytes'))
    return flask.redirect(flask.url_for('phone'))


@app.get('/user-permissions')
@permission_required('admin')
def user_permissions():
    flask.g.users = flask.g.db.user_permissions_list()
    return flask.render_template('user-permissions.html')

@app.get('/weight')
@permission_required('weight')
def weight():
    db: yavin.db.YavinDatabase = flask.g.db
    flask.g.today = yavin.util.today()
    flask.g.default_weight = db.weight_entries_get_most_recent()
    flask.g.weight_entries = db.weight_entries_list()
    return flask.render_template('weight.html')


@app.post('/weight/add')
@permission_required('weight')
def weight_add():
    db: yavin.db.YavinDatabase = flask.g.db
    entry_date = yavin.util.str_to_date(flask.request.form.get('entry_date'))
    entry_weight = flask.request.form.get('weight')
    log.info(f'Attempting to add new weight entry for {entry_date}: {entry_weight} lbs')
    msg = db.weight_entries_insert(entry_date, decimal.Decimal(entry_weight))
    if msg is not None:
        flask.flash(msg, 'alert-danger')
    return flask.redirect(flask.url_for('weight'))


@app.get('/authorize')
def authorize():
    for key, value in flask.request.values.items():
        log.debug(f'{key}: {value}')
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
    log.info(f'Welcome to Yavin {__version__}')
    if settings.dsn is None:
        log.critical('Missing environment variable DSN; I cannot start without a database')
    else:
        db = yavin.db.YavinDatabase(settings.dsn)
        db.migrate()

        if settings.admin_email:
            db.user_permissions_add(settings.admin_email, 'admin')

        yavin.tasks.scheduler.start()
        yavin.tasks.scheduler.add_job(yavin.tasks.library_sync, 'interval', hours=6,
                                      start_date=yavin.util.in_two_minutes())
        yavin.tasks.scheduler.add_job(yavin.tasks.library_notify, 'cron', day='*', hour='3', args=[app])

        waitress.serve(app, port=settings.port, threads=settings.web_server_threads, url_scheme=settings.scheme,
                       ident=None)
