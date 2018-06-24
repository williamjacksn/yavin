import datetime
import email.message
import inspect
import logging
import os
import smtplib
import yavin.db

log = logging.getLogger(__name__)


class Config:
    admin_email: str
    database_url: str
    loglevel: str
    site_url: str
    smtp_host: str
    smtp_password: str


def get_config_from_environment() -> Config:
    config = Config()
    for key in ['ADMIN_EMAIL', 'DATABASE_URL', 'LOGLEVEL', 'SITE_URL', 'SMTP_HOST', 'SMTP_PASSWORD']:
        setattr(config, key.lower(), os.environ.get(key))
    return config


def notify(config: Config):
    log.info('Sending notification email')
    msg = email.message.EmailMessage()
    msg['Subject'] = 'Library alert'
    msg['From'] = config.admin_email
    msg['To'] = config.admin_email
    content = inspect.cleandoc(f'''
        Hello,

        Something is due (or possibly overdue) at the library today.

        {config.site_url}/library

        (This is an automated message.)
    ''')
    msg.set_content(content)
    with smtplib.SMTP_SSL(host=config.smtp_host) as s:
        s.login(user=config.admin_email, password=config.smtp_password)
        s.send_message(msg)


def main():
    config = get_config_from_environment()
    db = yavin.db.YavinDatabase(config.database_url)
    for book in db.get_library_books():
        title = book['title']
        due = book['due']
        log.debug(f'{title} is due on {due}')
        if book['due'] <= datetime.date.today():
            log.debug('** Due today or overdue')
            notify(config)
            break
