import email.message
import email.utils
import logging
import smtplib

import apscheduler.schedulers.background
import bibliocommons
import biblionix
import httpx

import yavin.billboard
import yavin.components
import yavin.db
import yavin.settings
import yavin.util

log = logging.getLogger(__name__)
scheduler = apscheduler.schedulers.background.BackgroundScheduler()


def _notify(subject: str, body: str) -> None:
    settings = yavin.settings.Settings()
    db = yavin.db.YavinDatabase(settings.dsn)
    app_settings = db.settings_list()
    msg = email.message.EmailMessage()
    msg["Message-ID"] = email.utils.make_msgid()
    msg["Date"] = email.utils.formatdate()
    msg["Subject"] = subject
    msg["From"] = app_settings.get("smtp_from_address", "")
    msg["To"] = settings.admin_email
    msg.set_content(body, subtype="html")
    with smtplib.SMTP_SSL(host=app_settings.get("smtp_server", "")) as s:
        s.login(
            user=app_settings.get("smtp_username", ""),
            password=app_settings.get("smtp_password", ""),
        )
        s.send_message(msg)


def billboard_number_one_fetch() -> None:
    song = yavin.billboard.fetch_number_one()

    settings = yavin.settings.Settings()
    db = yavin.db.YavinDatabase(settings.dsn)
    latest = db.billboard_get_latest()
    if latest and song == (latest.get("artist"), latest.get("title")):
        db.billboard_update_fetched_at(latest.get("id"))
    else:
        db.billboard_insert(song.artist, song.title)
        subject = "New Billboard Hot 100 #1"
        _notify(subject, yavin.components.email_billboard(song.title, song.artist))


def library_notify() -> None:
    log.info("Checking for due library items")
    settings = yavin.settings.Settings()
    db = yavin.db.YavinDatabase(settings.dsn)
    due_books = db.library_books_list_due()
    if due_books:
        log.info("Sending notification email")
        subject = "Library alert"
        _notify(subject, yavin.components.email_library_item_due(due_books))
    else:
        log.info("No due library items found")


def library_sync() -> None:
    log.info("Syncing library data")
    settings = yavin.settings.Settings()
    db = yavin.db.YavinDatabase(settings.dsn)
    db.library_books_truncate()
    for lib_cred in db.library_credentials_list():
        lib_type = lib_cred.get("library_type")
        display_name = lib_cred.get("display_name")
        log.info(f"Syncing library data for {display_name}")
        try:
            if lib_type == "biblionix":
                library_sync_biblionix(lib_cred, db)
            elif lib_type == "bibliocommons":
                library_sync_bibliocommons(lib_cred, db)
            else:
                log.warning(f"Library type {lib_type} is not implemented yet")
        except httpx.ReadTimeout:
            log.error(f"Library sync timed out for {display_name}")


def library_sync_bibliocommons(
    lib_data: yavin.db.app.LibraryCredential, db: yavin.db.YavinDatabase
) -> None:
    lib_url = lib_data.get("library")
    bc = bibliocommons.BiblioCommonsClient(lib_url)
    bc.authenticate(lib_data.get("username"), lib_data.get("password"))
    for item in bc.loans:
        if item.subtitle:
            title = f"{item.title} / {item.subtitle}"
        else:
            title = item.title
        params = {
            "credential_id": lib_data.get("id"),
            "due": item.due,
            "item_id": item.item_id,
            "medium": item.medium,
            "renewable": item.renewable,
            "title": title,
        }
        db.library_books_insert(params)


def library_sync_biblionix(
    lib_data: yavin.db.app.LibraryCredential, db: yavin.db.YavinDatabase
) -> None:
    lib_url = lib_data.get("library")
    bc = biblionix.BiblionixClient(lib_url)
    bc.authenticate(lib_data.get("username"), lib_data.get("password"))
    for item in bc.loans:
        params = {
            "credential_id": lib_data.get("id"),
            "due": item.due,
            "item_id": item.item_id,
            "medium": item.medium,
            "renewable": item.renewable,
            "title": item.title,
        }
        db.library_books_insert(params)
