# Copy this file and update for your environment
# Before launching the app, set the environment variable YAVIN_SETTINGS_FILE to the path to this file

# One of DEBUG, INFO, WARNING, ERROR, CRITICAL
LOGLEVEL = 'INFO'

# The Google account you will use to log in
ADMIN_EMAIL = 'admin@example.com'

# Create an app password for your Google account at https://myaccount.google.com/apppasswords and put it here
# This is used to send email using the Gmail SMTP server
ADMIN_PASSWORD = 'secret'

# Generate an OAuth 2.0 client ID and secret at https://console.cloud.google.com/apis/credentials
# When setting that up, the authorized redirect URI should be <site_url>/login/google
# e.g. https://yavin.example.com/login/google or http://localhost:8080/login/google
GOOGLE_LOGIN_CLIENT_ID = 'secret'
GOOGLE_LOGIN_CLIENT_SECRET = 'secret'
GOOGLE_LOGIN_REDIRECT_SCHEME = 'http'

# Must be PostgreSQL
DATABASE_URL = 'postgresql://user:password@host:port/database'

# Something random
SECRET_KEY = b'random bytes'

# Base URL of published application
_hostname = 'localhost'
APPLICATION_ROOT = '/'

# Port to listen on
PORT = 8080

# Listen on a Unix socket instead of a port
# If both PORT and UNIX_SOCKET are set, UNIX_SOCKET takes precedence
UNIX_SOCKET = None
# UNIX_SOCKET = '/run/yavin.sock'

# Don't change this, it will be automatically generated from the previous values
if UNIX_SOCKET is None:
    SERVER_NAME = f'{_hostname}:{PORT}'
else:
    SERVER_NAME = _hostname
