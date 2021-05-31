import logging
from email.message import EmailMessage
from smtplib import SMTP_SSL
from xml.etree import ElementTree

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, render_template, url_for
import requests
import requests.utils

from yavin.db import YavinDatabase
from yavin.settings import Settings
from yavin.util import clean_due_date, today

log = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def library_notify(app: Flask):
    log.info('Checking for due library items')
    settings = Settings()
    db = YavinDatabase(settings.dsn)
    with app.app_context():
        lib_url = url_for('library')
    log.debug(f'url for library: {lib_url}')
    for book in db.library_books_list():
        title = book.get('title')
        due = book.get('due')
        log.debug(f'{title} is due on {due}')
        if due <= today():
            log.info(f'** {title} is due today or overdue')
            log.info('Sending notification email')
            msg = EmailMessage()
            msg['Subject'] = 'Library alert'
            msg['From'] = settings.admin_email
            msg['To'] = settings.admin_email
            content = render_template('email-library-item-due.jinja2', lib_url=lib_url)
            msg.set_content(content)
            with SMTP_SSL(host='smtp.gmail.com') as s:
                s.login(user=settings.admin_email, password=settings.admin_password)
                s.send_message(msg)
            break


def library_renew(item_id: str):
    settings = Settings()
    db = YavinDatabase(settings.dsn)
    log.info(f'Attempting to renew item {item_id}')
    lib_cred = db.library_credentials_get({'item_id': item_id})
    lib_url = lib_cred.get('library')
    s = requests.Session()
    login_url = f'https://{lib_url}.biblionix.com/catalog/ajax_backend/login.xml.pl'
    login_data = {
        'username': lib_cred.get('username'),
        'password': lib_cred.get('password'),
    }
    login = s.post(url=login_url, data=login_data)
    login_et = ElementTree.XML(login.text)
    session_key = login_et.get('session')
    account_url = f'https://{lib_url}.biblionix.com/catalog/ajax_backend/account.xml.pl'
    account_data = {'session': session_key}
    s.post(url=account_url, data=account_data)
    requests.utils.add_dict_to_cookiejar(s.cookies, {'session': session_key})
    renew_url = f'https://{lib_url}.biblionix.com/catalog/ajax_backend/account_command.xml.pl'
    renew_data = {'command': 'renew', 'checkout': item_id}
    renew = s.post(url=renew_url, data=renew_data)
    log.debug(renew.text)
    renew_et = ElementTree.XML(renew.text)
    if renew_et.get('success') == '1':
        item = renew_et.find('item')
        new_due = clean_due_date(item.get('due'))
        db.library_books_update({'due': new_due, 'item_id': item_id})


def library_sync():
    log.info('Syncing library data')
    settings = Settings()
    db = YavinDatabase(settings.dsn)
    db.library_books_truncate()
    for lib_cred in db.library_credentials_list():
        cred_id = lib_cred.get('id')
        display_name = lib_cred.get('display_name')
        log.info(f'Syncing library data for {display_name}')
        lib_url = lib_cred.get('library')
        s = requests.Session()
        login_url = f'https://{lib_url}.biblionix.com/catalog/ajax_backend/login.xml.pl'
        login_data = {
            'username': lib_cred.get('username'),
            'password': lib_cred.get('password'),
        }
        login = s.post(url=login_url, data=login_data)
        log.info(f'Received {len(login.content)} bytes from {login_url}')
        log.debug(login.text)
        login_et = ElementTree.XML(login.text)
        session_key = login_et.get('session')
        account_url = f'https://{lib_url}.biblionix.com/catalog/ajax_backend/account.xml.pl'
        account_data = {'session': session_key}
        account = s.post(url=account_url, data=account_data)
        log.info(f'Received {len(account.content)} bytes from {account_url}')
        log.debug(account.text)
        account_et = ElementTree.XML(account.text)
        db.library_credentials_update({
            'id': cred_id,
            'balance': 0
        })
        for alert in account_et.findall('alerts'):
            if alert.get('balance'):
                db.library_credentials_update({
                    'id': cred_id,
                    'balance': int(alert.get('balance'))
                })
        for item in account_et.findall('item'):
            params = {
                'credential_id': cred_id,
                'title': item.get('title').replace('\xad', ''),
                'due': item.get('due_raw'),
                'renewable': item.get('renewable') == '1',
                'item_id': item.get('id'),
                'medium': item.get('medium').replace('\xad', '')
            }
            db.library_books_insert(params)
