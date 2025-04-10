import datetime
import decimal
import flask
import functools
import httpx
import jwt
import logging
import urllib.parse
import uuid
import waitress
import werkzeug.middleware.proxy_fix
import werkzeug.utils
import yavin.components
import yavin.db
import yavin.settings
import yavin.tasks
import yavin.util

log = logging.getLogger(__name__)

__version__ = "2024.8"

settings = yavin.settings.Settings()

app = flask.Flask(__name__)
app.wsgi_app = werkzeug.middleware.proxy_fix.ProxyFix(
    app.wsgi_app, x_for=1, x_proto=1, x_port=1
)

app.config.update(
    PREFERRED_URL_SCHEME=settings.scheme,
    SECRET_KEY=settings.secret_key,
    SERVER_NAME=settings.server_name,
    SESSION_COOKIE_SAMESITE="Lax",
)

if settings.scheme == "https":
    app.config["SESSION_COOKIE_SECURE"] = True

app.jinja_env.filters["datetime"] = yavin.util.clean_datetime


def permission_required(permission: str):
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            app.logger.debug(f"Checking permission for {flask.g.email}")
            if flask.g.email is None:
                return flask.redirect(flask.url_for("index"))
            if "admin" in flask.g.permissions or permission in flask.g.permissions:
                return f(*args, **kwargs)
            return yavin.components.not_authorized(flask.g.email, flask.g.permissions)

        return decorated_function

    return decorator


@app.before_request
def before_request():
    log.debug(f"{flask.request.method} {flask.request.path}")
    flask.session.permanent = True
    flask.g.db = yavin.db.YavinDatabase(settings.dsn)
    flask.g.settings = settings
    flask.g.app_settings = flask.g.db.settings_list()
    flask.g.version = __version__
    flask.g.email = flask.session.get("email")
    flask.g.permissions = flask.g.db.user_permissions_get(flask.g.email)


@app.get("/")
def index():
    session_email = flask.session.get("email")
    if session_email is None:
        return yavin.components.index_signed_out()
    cards = [
        {
            "url": flask.url_for("dashboard_card_balances"),
            "visible": "balances" in flask.g.permissions
            or "admin" in flask.g.permissions,
        },
        {
            "url": flask.url_for("dashboard_card_billboard"),
            "visible": "billboard" in flask.g.permissions
            or "admin" in flask.g.permissions,
        },
        {
            "url": flask.url_for("dashboard_card_captains_log"),
            "visible": "captains-log" in flask.g.permissions
            or "admin" in flask.g.permissions,
        },
        {
            "url": flask.url_for("dashboard_card_electricity"),
            "visible": "electricity" in flask.g.permissions
            or "admin" in flask.g.permissions,
        },
        {
            "url": flask.url_for("dashboard_card_expenses"),
            "visible": "expenses" in flask.g.permissions
            or "admin" in flask.g.permissions,
        },
        {
            "url": flask.url_for("dashboard_card_jar"),
            "visible": "jar" in flask.g.permissions or "admin" in flask.g.permissions,
        },
        {
            "url": flask.url_for("dashboard_card_library"),
            "visible": "library" in flask.g.permissions
            or "admin" in flask.g.permissions,
        },
        {
            "url": flask.url_for("dashboard_card_movie_night"),
            "visible": "movie-night" in flask.g.permissions
            or "admin" in flask.g.permissions,
        },
        {
            "url": flask.url_for("dashboard_card_phone"),
            "visible": "phone" in flask.g.permissions or "admin" in flask.g.permissions,
        },
        {
            "url": flask.url_for("dashboard_card_tithing"),
            "visible": "tithing" in flask.g.permissions
            or "admin" in flask.g.permissions,
        },
        {
            "url": flask.url_for("dashboard_card_weight"),
            "visible": "weight" in flask.g.permissions
            or "admin" in flask.g.permissions,
        },
    ]
    return yavin.components.index_signed_in(session_email, flask.g.permissions, cards)


@app.get("/app-settings")
@permission_required("admin")
def app_settings():
    return yavin.components.app_settings()


@app.post("/app-settings/update")
@permission_required("admin")
def app_settings_update():
    db: yavin.db.YavinDatabase = flask.g.db

    text_settings = [
        "expenses_db",
        "smtp_from_address",
        "smtp_password",
        "smtp_server",
        "smtp_username",
    ]
    for k, v in flask.request.values.items():
        log.debug(f"{k}: {v!r}")
        if k in text_settings:
            if v == "":
                db.settings_delete(k)
            else:
                db.settings_update(k, v)

    bool_settings = [
        "debug_layout",
    ]
    for setting_id in bool_settings:
        setting_value = "true" if setting_id in flask.request.values else "false"
        db.settings_update(setting_id, setting_value)

    return flask.redirect(flask.url_for("app_settings"))


@app.get("/balances")
@permission_required("balances")
def balances():
    flask.g.accounts = flask.g.db.balances_accounts_list()
    return yavin.components.balances()


@app.get("/balances/<uuid:account_id>")
@permission_required("balances")
def balances_detail(account_id: uuid.UUID):
    flask.g.account_id = account_id
    flask.g.transactions = flask.g.db.balances_transactions_list(account_id)
    flask.g.account_name = flask.g.transactions[0].get("account_name")
    flask.g.account_balance = flask.g.transactions[0].get("account_balance")
    return yavin.components.balances_detail()


@app.post("/balances/add-transaction")
@permission_required("balances")
def balances_add_tx():
    account_id = flask.request.values.get("account-id")
    params = {
        "account_id": account_id,
        "tx_date": flask.request.values.get("tx-date"),
        "tx_description": flask.request.values.get("tx-description"),
        "tx_value": flask.request.values.get("tx-value"),
    }
    flask.g.db.balances_transactions_add(params)
    return flask.redirect(flask.url_for("balances_detail", account_id=account_id))


@app.get("/billboard")
@permission_required("billboard")
def billboard():
    flask.g.latest = flask.g.db.billboard_get_latest()
    if flask.g.latest is None:
        yavin.tasks.billboard_number_one_fetch()
        flask.g.latest = flask.g.db.billboard_get_latest()
    return yavin.components.billboard()


@app.get("/captains-log")
@permission_required("captains-log")
def captains_log():
    db: yavin.db.YavinDatabase = flask.g.db
    flask.g.records = db.captains_log_list()
    return flask.render_template("captains-log.html")


@app.post("/captains-log/delete")
@permission_required("captains-log")
def captains_log_delete():
    db: yavin.db.YavinDatabase = flask.g.db
    db.captains_log_delete(flask.request.form.get("id"))
    return flask.redirect(flask.url_for("captains_log"))


@app.post("/captains-log/incoming")
def captains_log_incoming():
    db: yavin.db.YavinDatabase = flask.g.db
    log.debug(f"json: {flask.request.json}")
    auth_phrase: str = flask.request.json["auth-phrase"]
    if auth_phrase.lower() == settings.admin_auth_phrase:
        log.debug("Authorization accepted")
        log_text = flask.request.json["log-text"]
        db.captains_log_insert(log_text)
        return "Log recorded."
    return "Authorization failure."


@app.post("/captains-log/update")
@permission_required("captains-log")
def captains_log_update():
    db: yavin.db.YavinDatabase = flask.g.db
    log_text = flask.request.form.get("log_text")
    db.captains_log_update(flask.request.form.get("id"), log_text)
    return flask.redirect(flask.url_for("captains_log"))


@app.get("/dashboard-card/balances")
def dashboard_card_balances():
    accounts_count = flask.g.db.balances_accounts_count()
    text = f"Accounts: {accounts_count}"
    return yavin.components.dashboard_card_balances(text)


@app.get("/dashboard-card/billboard")
def dashboard_card_billboard():
    latest = flask.g.db.billboard_get_latest()
    if latest is None:
        text = "Unknown"
    else:
        text = f"{latest.get('title')} by {latest.get('artist')}"
    return yavin.components.dashboard_card_billboard(text)


@app.get("/dashboard-card/captains-log")
def dashboard_card_captains_log():
    return yavin.components.dashboard_card_captains_log()


@app.get("/dashboard-card/electricity")
def dashboard_card_electricity():
    return yavin.components.dashboard_card_electricity()


@app.get("/dashboard-card/expenses")
def dashboard_card_expenses():
    return yavin.components.dashboard_card_expenses()


@app.get("/dashboard-card/jar")
def dashboard_card_jar():
    return yavin.components.dashboard_card_jar()


@app.get("/dashboard-card/library")
def dashboard_card_library():
    return yavin.components.dashboard_card_library()


@app.get("/dashboard-card/movie-night")
def dashboard_card_movie_night():
    db: yavin.db.YavinDatabase = flask.g.db
    next_pick = db.movie_people_next_pick()
    if next_pick is None:
        next_pick_person = "Unknown"
    else:
        next_pick_person = next_pick.get("person")
    return yavin.components.dashboard_card_movie_night(next_pick_person)


@app.get("/dashboard-card/phone")
def dashboard_card_phone():
    return yavin.components.dashboard_card_phone()


@app.get("/dashboard-card/tithing")
def dashboard_card_tithing():
    return yavin.components.dashboard_card_tithing()


@app.get("/dashboard-card/weight")
def dashboard_card_weight():
    return yavin.components.dashboard_card_weight()


@app.get("/electricity")
@permission_required("electricity")
def electricity():
    db: yavin.db.YavinDatabase = flask.g.db
    flask.g.records = db.electricity_list()
    return yavin.components.electricity()


@app.post("/electricity/add")
@permission_required("electricity")
def electricity_add():
    db: yavin.db.YavinDatabase = flask.g.db
    bill_date = yavin.util.str_to_date(flask.request.form.get("bill_date"))
    kwh = int(flask.request.form.get("kwh"))
    charge = decimal.Decimal(flask.request.form.get("charge"))
    bill = decimal.Decimal(flask.request.form.get("bill"))
    db.electricity_insert(bill_date, kwh, charge, bill)
    return flask.redirect(flask.url_for("electricity"))


@app.get("/expenses")
@permission_required("expenses")
def expenses():
    ex_db_path = flask.g.app_settings.get("expenses_db")
    if ex_db_path is None:
        return flask.redirect(flask.url_for("app_settings"))
    ex_db = yavin.db.ExpensesDatabase(flask.g.app_settings.get("expenses_db"))
    try:
        start_date = yavin.util.str_to_date(flask.request.values.get("start_date"))
    except (TypeError, ValueError):
        start_date = None
    try:
        end_date = yavin.util.str_to_date(flask.request.values.get("end_date"))
    except (TypeError, ValueError):
        end_date = None
    if start_date is None:
        if end_date is None:
            start_date = yavin.util.today().replace(day=1)
            end_date = yavin.util.today()
            log.debug(f"No dates provided, using {start_date} to {end_date}")
        else:
            start_date = yavin.util.add_days(end_date, -30)
            log.debug(f"Only end_date provided, using {start_date} to {end_date}")
    else:
        if end_date is None:
            end_date = yavin.util.add_days(start_date, 30)
            log.debug(f"Only start_date provided, using {start_date} to {end_date}")
        elif start_date > end_date:
            start_date, end_date = end_date, start_date
            log.debug(f"Dates are out of order, using {start_date} to {end_date}")
        else:
            log.debug(f"Both dates provided, using {start_date} to {end_date}")
    flask.g.start_date = start_date
    flask.g.end_date = end_date
    flask.g.expenses = ex_db.get_expenses(
        "Root Account:Expenses%", start_date, end_date
    )
    flask.g.total = sum([e["amount"] for e in flask.g.expenses], 0)
    return yavin.components.expenses()


@app.get("/jar")
@permission_required("jar")
def jar():
    db: yavin.db.YavinDatabase = flask.g.db
    flask.g.today = yavin.util.today()
    flask.g.days_since_last = db.jar_entries_days_since_last()
    app.logger.debug(f"Days since last jar entry: {flask.g.days_since_last}")
    flask.g.jar_entries = db.jar_entries_list()
    return yavin.components.jar()


@app.post("/jar/add")
@permission_required("jar")
def jar_add():
    db: yavin.db.YavinDatabase = flask.g.db
    entry_date = yavin.util.str_to_date(flask.request.form.get("entry_date"))
    log.info(f"Adding new jar entry for {entry_date}")
    db.jar_entries_insert(entry_date)
    return flask.redirect(flask.url_for("jar"))


@app.post("/jar/rows")
@permission_required("jar")
def jar_rows():
    db: yavin.db.YavinDatabase = flask.g.db
    flask.g.page = int(flask.request.values.get("page", 1))
    flask.g.rows = db.jar_entries_list(flask.g.page)
    return yavin.components.jar_rows()


@app.get("/library")
@permission_required("library")
def library():
    db: yavin.db.YavinDatabase = flask.g.db
    flask.g.library_books = db.library_books_list()
    return yavin.components.library()


@app.get("/library/accounts")
@permission_required("library")
def library_accounts():
    db: yavin.db.YavinDatabase = flask.g.db
    flask.g.library_credentials = db.library_credentials_list()
    return yavin.components.library_accounts()


@app.post("/library/accounts/add")
@permission_required("library")
def library_accounts_add():
    db: yavin.db.YavinDatabase = flask.g.db
    params = {
        "display_name": flask.request.form.get("display_name"),
        "library": flask.request.form.get("library"),
        "library_type": flask.request.form.get("library_type"),
        "username": flask.request.form.get("username"),
        "password": flask.request.form.get("password"),
    }
    db.library_credentials_insert(params)
    yavin.tasks.scheduler.add_job(yavin.tasks.library_sync)
    return flask.redirect(flask.url_for("library_accounts"))


@app.post("/library/accounts/delete")
@permission_required("library")
def library_accounts_delete():
    db: yavin.db.YavinDatabase = flask.g.db
    db.library_credentials_delete(flask.request.form)
    yavin.tasks.scheduler.add_job(yavin.tasks.library_sync)
    return flask.redirect(flask.url_for("library_accounts"))


@app.get("/library/notify-now")
@permission_required("library")
def library_notify_now():
    log.info("Got library notification request")
    yavin.tasks.scheduler.add_job(yavin.tasks.library_notify)
    return flask.redirect(flask.url_for("library"))


@app.get("/library/sync-now")
@permission_required("library")
def library_sync_now():
    log.info("Got library sync request")
    yavin.tasks.scheduler.add_job(yavin.tasks.library_sync)
    return flask.redirect(flask.url_for("library"))


@app.get("/movie-night")
@permission_required("movie-night")
def movie_night():
    db: yavin.db.YavinDatabase = flask.g.db
    flask.g.people = db.movie_people_list()
    flask.g.picks = db.movie_picks_list()
    flask.g.today = yavin.util.today()
    return flask.render_template("movie-night.html")


@app.post("/movie-night/add-person")
@permission_required("movie-night")
def movie_night_add_person():
    db: yavin.db.YavinDatabase = flask.g.db
    params = {"person": flask.request.form.get("person")}
    db.movie_people_insert(params)
    return flask.redirect(flask.url_for("movie_night"))


@app.post("/movie-night/add-pick")
@permission_required("movie-night")
def movie_night_add_pick():
    db: yavin.db.YavinDatabase = flask.g.db
    params = {
        "pick_date": flask.request.form.get("pick_date"),
        "person_id": flask.request.form.get("person_id"),
        "pick_text": flask.request.form.get("pick_text"),
        "pick_url": flask.request.form.get("pick_url"),
    }
    log.debug(params)
    db.movie_picks_insert(params)
    return flask.redirect(flask.url_for("movie_night"))


@app.post("/movie-night/delete-pick")
@permission_required("movie-night")
def movie_night_delete_pick():
    db: yavin.db.YavinDatabase = flask.g.db
    params = {"id": flask.request.form.get("id")}
    db.movie_picks_delete(params)
    return flask.redirect(flask.url_for("movie_night"))


@app.post("/movie-night/edit-pick")
@permission_required("movie-night")
def movie_night_edit_pick():
    db: yavin.db.YavinDatabase = flask.g.db
    params = {
        "id": flask.request.form.get("id"),
        "pick_date": flask.request.form.get("pick_date"),
        "person_id": flask.request.form.get("person_id"),
        "pick_text": flask.request.form.get("pick_text"),
        "pick_url": flask.request.form.get("pick_url"),
    }
    db.movie_picks_update(params)
    return flask.redirect(flask.url_for("movie_night"))


@app.get("/phone")
@permission_required("phone")
def phone():
    db: yavin.db.YavinDatabase = flask.g.db
    flask.g.records = db.phone_usage_list()
    return yavin.components.phone()


@app.post("/phone/add")
@permission_required("phone")
def phone_add():
    db: yavin.db.YavinDatabase = flask.g.db
    kwargs = {
        "start_date": datetime.date.fromisoformat(
            flask.request.values.get("start-date")
        ),
        "end_date": datetime.date.fromisoformat(flask.request.values.get("end-date")),
        "minutes": int(flask.request.values.get("minutes")),
        "messages": int(flask.request.values.get("messages")),
        "megabytes": int(flask.request.values.get("megabytes")),
    }
    db.phone_usage_insert(**kwargs)
    return flask.redirect(flask.url_for("phone"))


@app.get("/tithing")
@permission_required("tithing")
def tithing():
    db: yavin.db.YavinDatabase = flask.g.db
    flask.g.tithing_owed = db.tithing_get_current_owed()
    flask.g.transactions = db.tithing_income_list_unpaid()
    return yavin.components.tithing()


@app.post("/tithing/income/add")
@permission_required("tithing")
def tithing_income_add():
    db: yavin.db.YavinDatabase = flask.g.db
    date = datetime.datetime.strptime(flask.request.values.get("tx-date"), "%Y-%m-%d")
    amount = decimal.Decimal(flask.request.values.get("tx-value"))
    description = flask.request.values.get("tx-description")
    db.tithing_income_insert(date, amount, description)
    return flask.redirect(flask.url_for("tithing"))


@app.post("/tithing/income/paid")
@permission_required("tithing")
def tithing_income_paid():
    db: yavin.db.YavinDatabase = flask.g.db
    db.tithing_income_mark_paid()
    return flask.redirect(flask.url_for("tithing"))


@app.get("/user-permissions")
@permission_required("admin")
def user_permissions():
    flask.g.users = flask.g.db.user_permissions_list()
    return yavin.components.user_permissions()


@app.get("/weight")
@permission_required("weight")
def weight():
    db: yavin.db.YavinDatabase = flask.g.db
    flask.g.today = yavin.util.today()
    flask.g.default_weight = db.weight_entries_get_most_recent()
    flask.g.weight_entries = db.weight_entries_list()
    return yavin.components.weight()


@app.post("/weight/add")
@permission_required("weight")
def weight_add():
    db: yavin.db.YavinDatabase = flask.g.db
    entry_date = yavin.util.str_to_date(flask.request.form.get("entry_date"))
    current = db.weight_entries_get_for_date(entry_date)
    if current is None:
        entry_weight = flask.request.form.get("weight")
        log.info(f"Adding new weight entry for {entry_date}: {entry_weight} lbs")
        db.weight_entries_insert(entry_date, decimal.Decimal(entry_weight))
    else:
        flask.flash(
            f"There is already a weight entry for {entry_date}.", "alert-danger"
        )
    return flask.redirect(flask.url_for("weight"))


@app.get("/authorize")
def authorize():
    for key, value in flask.request.values.items():
        log.debug(f"{key}: {value}")
    if flask.session.get("state") != flask.request.values.get("state"):
        return "State mismatch", 401
    discovery_document = httpx.get(settings.openid_discovery_document).json()
    token_endpoint = discovery_document.get("token_endpoint")
    data = {
        "code": flask.request.values.get("code"),
        "client_id": settings.openid_client_id,
        "client_secret": settings.openid_client_secret,
        "redirect_uri": flask.url_for("authorize", _external=True),
        "grant_type": "authorization_code",
    }
    resp = httpx.post(token_endpoint, data=data).json()
    id_token = resp.get("id_token")
    algorithms = discovery_document.get("id_token_signing_alg_values_supported")
    claim = jwt.decode(
        id_token, options={"verify_signature": False}, algorithms=algorithms
    )
    flask.session["email"] = claim.get("email")
    return flask.redirect(flask.url_for("index"))


@app.get("/sign-in")
def sign_in():
    state = str(uuid.uuid4())
    flask.session["state"] = state
    redirect_uri = flask.url_for("authorize", _external=True)
    query = {
        "client_id": settings.openid_client_id,
        "response_type": "code",
        "scope": "openid email profile",
        "redirect_uri": redirect_uri,
        "state": state,
    }
    discovery_document = httpx.get(settings.openid_discovery_document).json()
    auth_endpoint = discovery_document.get("authorization_endpoint")
    auth_url = f"{auth_endpoint}?{urllib.parse.urlencode(query)}"
    return flask.redirect(auth_url, 307)


@app.get("/sign-out")
def sign_out():
    flask.session.pop("email", None)
    return flask.redirect(flask.url_for("index"))


def main():
    log.info(f"Welcome to Yavin {__version__}")
    if settings.dsn is None:
        log.critical(
            "Missing environment variable DSN; I cannot start without a database"
        )
    else:
        db = yavin.db.YavinDatabase(settings.dsn)
        db.migrate()

        if settings.admin_email:
            db.user_permissions_add(settings.admin_email, "admin")

        yavin.tasks.scheduler.start()
        yavin.tasks.scheduler.add_job(
            yavin.tasks.billboard_number_one_fetch,
            "interval",
            hours=24,
            start_date=yavin.util.in_two_minutes(),
        )
        yavin.tasks.scheduler.add_job(
            yavin.tasks.library_sync,
            "interval",
            hours=6,
            start_date=yavin.util.in_two_minutes(),
        )
        yavin.tasks.scheduler.add_job(
            yavin.tasks.library_notify, "cron", day="*", hour="3"
        )

        waitress.serve(
            app,
            port=settings.port,
            threads=settings.web_server_threads,
            url_scheme=settings.scheme,
            ident=None,
        )
