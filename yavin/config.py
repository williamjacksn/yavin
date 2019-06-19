import os
import pathlib


class Config:
    admin_auth_phrase: str
    admin_email: str
    admin_password: str
    application_root: str
    dsn: str
    google_login_client_id: str
    google_login_client_secret: str
    log_format: str
    log_level: str
    openid_discovery_document: str
    permanent_sessions: bool
    port: int
    scheme: str
    secret_key: str
    server_name: str

    def __init__(self):
        """Instantiating a Config object will automatically read the following environment variables:

        ADMIN_AUTH_PHRASE, ADMIN_EMAIL, ADMIN_PASSWORD, APPLICATION_ROOT, DSN, GOOGLE_LOGIN_CLIENT_ID,
        GOOGLE_LOGIN_CLIENT_SECRET, LOG_FORMAT, LOG_LEVEL, OPENID_DISCOVERY_DOCUMENT, PERMANENT_SESSIONS, PORT, SCHEME,
        SECRET_KEY, SERVER_NAME

        Some variables have defaults if they are not found in the environment:

        APPLICATION_ROOT=/
        LOG_FORMAT="%(levelname)s [%(name)s] %(message)s"
        LOG_LEVEL=DEBUG
        OPENID_DISCOVERY_DOCUMENT="https://accounts.google.com/.well-known/openid-configuration"
        PERMANENT_SESSIONS=False
        PORT=8080
        SCHEME=http
        SERVER_NAME=localhost:8080"""

        self.admin_auth_phrase = os.getenv('ADMIN_AUTH_PHRASE', '').lower()
        self.admin_email = os.getenv('ADMIN_EMAIL')
        self.admin_password = os.getenv('ADMIN_PASSWORD')
        self.application_root = os.getenv('APPLICATION_ROOT', '/')
        self.dsn = os.getenv('DSN')
        self.google_login_client_id = os.getenv('GOOGLE_LOGIN_CLIENT_ID')
        self.google_login_client_secret = os.getenv('GOOGLE_LOGIN_CLIENT_SECRET')
        self.log_format = os.getenv('LOG_FORMAT', '%(levelname)s [%(name)s] %(message)s')
        self.log_level = os.getenv('LOG_LEVEL', 'DEBUG')
        self.openid_discovery_document = os.getenv('OPENID_DISCOVERY_DOCUMENT',
                                                   'https://accounts.google.com/.well-known/openid-configuration')
        self.permanent_sessions = (os.getenv('PERMANENT_SESSIONS', 'False') == 'True')
        self.port = int(os.getenv('PORT', '8080'))
        self.scheme = os.getenv('SCHEME', 'http').lower()
        self.secret_key = os.getenv('SECRET_KEY')
        self.server_name = os.getenv('SERVER_NAME', 'localhost:8080')

    @property
    def version(self) -> str:
        """Read version from Dockerfile"""
        dockerfile = pathlib.Path(__file__).resolve().parent.parent / 'Dockerfile'
        with open(dockerfile) as f:
            for line in f:
                if 'org.opencontainers.image.version' in line:
                    return line.strip().split('=', maxsplit=1)[1]
        return 'unknown'
