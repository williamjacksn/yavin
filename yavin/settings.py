import os


class Settings:
    admin_auth_phrase: str
    admin_email: str
    admin_password: str
    application_root: str
    debug_layout: bool
    dsn: str
    log_format: str
    log_level: str
    openid_client_id: str
    openid_client_secret: str
    openid_discovery_document: str
    permanent_sessions: bool
    port: int
    scheme: str
    secret_key: str
    server_name: str
    version: str
    web_server_threads: int

    def __init__(self):
        """Instantiating a Settings object will automatically read the following environment variables:

        ADMIN_AUTH_PHRASE, ADMIN_EMAIL, ADMIN_PASSWORD, APP_VERSION, APPLICATION_ROOT, DEBUG_LAYOUT, DSN, LOG_FORMAT,
        LOG_LEVEL, OPENID_CLIENT_ID, OPENID_CLIENT_SECRET, OPENID_DISCOVERY_DOCUMENT, PERMANENT_SESSIONS, PORT, SCHEME,
        SECRET_KEY, SERVER_NAME, WEB_SERVER_THREADS

        Some variables have defaults if they are not found in the environment:

        APPLICATION_ROOT="/"
        DEBUG_LAYOUT="False"
        LOG_FORMAT="%(levelname)s [%(name)s] %(message)s"
        LOG_LEVEL="INFO"
        OPENID_DISCOVERY_DOCUMENT="https://accounts.google.com/.well-known/openid-configuration"
        PERMANENT_SESSIONS="False"
        PORT="8080"
        SCHEME="http"
        SERVER_NAME="localhost:8080"
        WEB_SERVER_THREADS="4"
        """

        _true_values = ('true', '1', 'yes', 'on')
        self.admin_auth_phrase = os.getenv('ADMIN_AUTH_PHRASE', '').lower()
        self.admin_email = os.getenv('ADMIN_EMAIL')
        self.admin_password = os.getenv('ADMIN_PASSWORD')
        self.application_root = os.getenv('APPLICATION_ROOT', '/')
        self.debug_layout = os.getenv('DEBUG_LAYOUT', 'false').lower() in _true_values
        self.dsn = os.getenv('DSN')
        self.log_format = os.getenv('LOG_FORMAT', '%(levelname)s [%(name)s] %(message)s')
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        self.openid_client_id = os.getenv('OPENID_CLIENT_ID')
        self.openid_client_secret = os.getenv('OPENID_CLIENT_SECRET')
        self.openid_discovery_document = os.getenv('OPENID_DISCOVERY_DOCUMENT',
                                                   'https://accounts.google.com/.well-known/openid-configuration')
        self.permanent_sessions = os.getenv('PERMANENT_SESSIONS', 'false').lower() in _true_values
        self.port = int(os.getenv('PORT', '8080'))
        self.scheme = os.getenv('SCHEME', 'http').lower()
        self.secret_key = os.getenv('SECRET_KEY')
        self.server_name = os.getenv('SERVER_NAME', 'localhost:8080')
        self.version = os.getenv('APP_VERSION', 'unknown')
        self.web_server_threads = int(os.getenv('WEB_SERVER_THREADS', '4'))
