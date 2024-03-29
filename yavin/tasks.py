import apscheduler.schedulers.background
import email.message
import email.utils
import flask
import logging
import lxml.html
import requests
import requests.utils
import smtplib
import xml.etree.ElementTree
import yavin.db
import yavin.settings
import yavin.util

log = logging.getLogger(__name__)
scheduler = apscheduler.schedulers.background.BackgroundScheduler()


def library_notify(app: flask.Flask):
    log.info('Checking for due library items')
    settings = yavin.settings.Settings()
    db = yavin.db.YavinDatabase(settings.dsn)
    app_settings = db.settings_list()
    due_books = db.library_books_list_due()
    if due_books:
        log.info('Sending notification email')
        with app.app_context():
            msg = email.message.EmailMessage()
            msg['Message-ID'] = email.utils.make_msgid()
            msg['Date'] = email.utils.formatdate()
            msg['Subject'] = 'Library alert'
            msg['From'] = app_settings.get('smtp_from_address')
            msg['To'] = settings.admin_email
            content = flask.render_template('email-library-item-due.html', due_books=due_books)
            msg.set_content(content, subtype='html')
            with smtplib.SMTP_SSL(host=app_settings.get('smtp_server')) as s:
                s.login(user=app_settings.get('smtp_username'), password=app_settings.get('smtp_password'))
                s.send_message(msg)
    else:
        log.info('No due library items found')


def library_renew(item_id: str):
    settings = yavin.settings.Settings()
    db = yavin.db.YavinDatabase(settings.dsn)
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
    login_et = xml.etree.ElementTree.XML(login.text)
    session_key = login_et.get('session')
    account_url = f'https://{lib_url}.biblionix.com/catalog/ajax_backend/account.xml.pl'
    account_data = {'session': session_key}
    s.post(url=account_url, data=account_data)
    requests.utils.add_dict_to_cookiejar(s.cookies, {'session': session_key})
    renew_url = f'https://{lib_url}.biblionix.com/catalog/ajax_backend/account_command.xml.pl'
    renew_data = {'command': 'renew', 'checkout': item_id}
    renew = s.post(url=renew_url, data=renew_data)
    log.debug(renew.text)
    renew_et = xml.etree.ElementTree.XML(renew.text)
    if renew_et.get('success') == '1':
        item = renew_et.find('item')
        new_due = yavin.util.clean_due_date(item.get('due'))
        db.library_books_update({'due': new_due, 'item_id': item_id})


def library_sync():
    log.info('Syncing library data')
    settings = yavin.settings.Settings()
    db = yavin.db.YavinDatabase(settings.dsn)
    db.library_books_truncate()
    for lib_cred in db.library_credentials_list():
        lib_type = lib_cred.get('library_type')
        display_name = lib_cred.get('display_name')
        log.info(f'Syncing library data for {display_name}')
        if lib_type == 'biblionix':
            library_sync_biblionix(lib_cred, db)
        elif lib_type == 'bibliocommons':
            library_sync_bibliocommons(lib_cred, db)
        else:
            log.warning(f'Library type {lib_type} is not implemented yet')


def library_sync_bibliocommons(lib_data: dict, db: yavin.db.YavinDatabase):
    lib_url = lib_data.get('library')
    s = requests.Session()
    login_page = s.get(f'https://{lib_url}.bibliocommons.com/user/login', params={'destination': 'x'})
    login_page.raise_for_status()
    doc = lxml.html.document_fromstring(login_page.content)
    auth_token_el = doc.cssselect('input[name="authenticity_token"]')[0]
    auth_token = auth_token_el.value
    data = {
        'authenticity_token': auth_token,
        'name': lib_data.get('username'),
        'user_pin': lib_data.get('password'),
    }
    login_action = s.post(f'https://{lib_url}.bibliocommons.com/user/login', data=data)
    login_action.raise_for_status()
    log.debug(f'Cookies: {s.cookies}')
    session_id = s.cookies.get('session_id')
    access_token = s.cookies.get('bc_access_token')
    account_id_guess = int(session_id.split('-')[-1]) + 1
    checkouts_url = f'https://gateway.bibliocommons.com/v2/libraries/{lib_url}/checkouts'
    params = {
        'accountId': account_id_guess
    }
    headers = {
        'X-Access-Token': access_token,
        'X-Session-Id': session_id,
    }
    checkouts = s.get(checkouts_url, headers=headers, params=params)
    checkouts.raise_for_status()
    response = checkouts.json()
    log.debug(response)
    for item in response.get('entities', {}).get('checkouts', {}).values():
        params = {
            'credential_id': lib_data.get('id'),
            'due': item.get('dueDate'),
            'item_id': '',
            'medium': '',
            'renewable': False,
            'title': item.get('bibTitle'),
        }
        db.library_books_insert(params)


def library_sync_biblionix(lib_data: dict, db: yavin.db.YavinDatabase):
    lib_url = lib_data.get('library')
    s = requests.Session()
    login_url = f'https://{lib_url}.biblionix.com/catalog/ajax_backend/login.xml.pl'
    login_data = {
        'username': lib_data.get('username'),
        'password': lib_data.get('password'),
    }
    login = s.post(url=login_url, data=login_data)
    log.info(f'Received {len(login.content)} bytes from {login_url}')
    log.debug(login.text)
    login_et = xml.etree.ElementTree.XML(login.text)
    session_key = login_et.get('session')
    account_url = f'https://{lib_url}.biblionix.com/catalog/ajax_backend/account.xml.pl'
    account_data = {'session': session_key}
    account = s.post(url=account_url, data=account_data)
    log.info(f'Received {len(account.content)} bytes from {account_url}')
    log.debug(account.text)
    account_et = xml.etree.ElementTree.XML(account.text)
    cred_id = lib_data.get('id')
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
