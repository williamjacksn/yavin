import os


class Settings:
    admin_auth_phrase: str
    admin_email: str
    debug_layout: bool
    dsn: str
    expenses_db: str
    openid_client_id: str
    openid_client_secret: str
    openid_discovery_document: str
    port: int
    scheme: str
    secret_key: str
    server_name: str
    web_server_threads: int

    def __init__(self):
        """Instantiating a Settings object will automatically read the following environment variables:

        ADMIN_AUTH_PHRASE, ADMIN_EMAIL, DEBUG_LAYOUT, DSN, EXPENSES_DB, OPENID_CLIENT_ID, OPENID_CLIENT_SECRET,
        OPENID_DISCOVERY_DOCUMENT, PORT, SCHEME, SECRET_KEY, SERVER_NAME, WEB_SERVER_THREADS

        Some variables have defaults if they are not found in the environment:

        DEBUG_LAYOUT="False"
        PORT="8080"
        SCHEME="http"
        SERVER_NAME="localhost:8080"
        WEB_SERVER_THREADS="4"
        """

        _true_values = ('true', '1', 'yes', 'on')
        self.admin_auth_phrase = os.getenv('ADMIN_AUTH_PHRASE', '').lower()
        self.admin_email = os.getenv('ADMIN_EMAIL')
        self.debug_layout = os.getenv('DEBUG_LAYOUT', 'false').lower() in _true_values
        self.dsn = os.getenv('DSN')
        self.expenses_db = os.getenv('EXPENSES_DB')
        self.openid_client_id = os.getenv('OPENID_CLIENT_ID')
        self.openid_client_secret = os.getenv('OPENID_CLIENT_SECRET')
        self.openid_discovery_document = os.getenv('OPENID_DISCOVERY_DOCUMENT')
        self.port = int(os.getenv('PORT', '8080'))
        self.scheme = os.getenv('SCHEME', 'http').lower()
        self.secret_key = os.getenv('SECRET_KEY')
        self.server_name = os.getenv('SERVER_NAME', 'localhost:8080')
        self.web_server_threads = int(os.getenv('WEB_SERVER_THREADS', '4'))
