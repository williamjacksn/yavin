import datetime as dt
import os
import tempfile
import unittest
import uuid
import zoneinfo
from unittest.mock import patch

import flask
import lxml.html
from flask.sessions import SecureCookieSessionInterface

with (
    tempfile.TemporaryDirectory() as directory,
    patch.dict(os.environ, {"DATABASE": os.path.join(directory, "test.db")}),
):
    from yavin.app import app

from yavin import util
from yavin.db import app_sqlite
from yavin.db.app_sqlite import YavinSqliteDatabase

ADMIN = "admin@example.com"
MOMENT = dt.datetime(2026, 7, 4, 17, 30, tzinfo=dt.UTC)


class FormatDatetimeTests(unittest.TestCase):
    def format_with(self, app_settings: dict[str, str]) -> str:
        with app.app_context():
            flask.g.app_settings = app_settings
            return util.format_datetime(MOMENT)

    def test_uses_the_display_time_zone_setting(self) -> None:
        self.assertEqual(
            self.format_with({"display_time_zone": "Asia/Tokyo"}), "2026-07-05 02:30"
        )

    def test_falls_back_to_the_default_time_zone(self) -> None:
        for app_settings in ({}, {"display_time_zone": "Not/A_Zone"}):
            with self.subTest(app_settings=app_settings):
                self.assertEqual(self.format_with(app_settings), "2026-07-04 12:30")

    def test_works_outside_an_app_context(self) -> None:
        self.assertEqual(util.format_datetime(MOMENT), "2026-07-04 12:30")

    def test_accepts_a_custom_format(self) -> None:
        self.assertEqual(util.format_datetime(MOMENT, "%H:%M %Z"), "12:30 CDT")

    def test_rejects_naive_datetimes(self) -> None:
        with self.assertRaises(ValueError):
            util.format_datetime(MOMENT.replace(tzinfo=None))


class TodayTests(unittest.TestCase):
    def test_uses_the_display_time_zone_setting(self) -> None:
        # These zones are 25 hours apart, so their dates always differ
        dates = set()
        for tz_name in ("Pacific/Kiritimati", "Pacific/Pago_Pago"):
            with self.subTest(tz_name=tz_name), app.app_context():
                flask.g.app_settings = {"display_time_zone": tz_name}
                today = util.today()
                expected = dt.datetime.now(zoneinfo.ZoneInfo(tz_name)).date()
                self.assertEqual(today, expected)
                dates.add(today)
        self.assertEqual(len(dates), 2)

    def test_falls_back_to_the_default_time_zone(self) -> None:
        expected = dt.datetime.now(zoneinfo.ZoneInfo("America/Chicago")).date()
        self.assertEqual(util.today(), expected)


class SignedInAdminTestCase(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = os.path.join(directory.name, "yavin.db")
        app_sqlite.init(self.path)
        db = YavinSqliteDatabase(self.path)
        self.addCleanup(db.close)
        db.user_permissions_set(ADMIN, ["admin", "billboard", "tello"])
        self.db = db
        for target, new in (
            ("yavin.db.YavinSqliteDatabase", lambda _: YavinSqliteDatabase(self.path)),
            ("yavin.app._manage_scheduled_tasks", lambda _: None),
        ):
            patcher = patch(target, new)
            patcher.start()
            self.addCleanup(patcher.stop)
        app.config.update(TESTING=True, SECRET_KEY=uuid.uuid4().hex)
        self.client = app.test_client()
        serializer = SecureCookieSessionInterface().get_signing_serializer(app)
        if serializer is None:
            self.fail("The app has no secret key for signing sessions")
        self.client.set_cookie(
            app.config["SESSION_COOKIE_NAME"], serializer.dumps({"email": ADMIN})
        )


class DisplayTimeZoneSettingTests(SignedInAdminTestCase):
    def selected_time_zone(self) -> list[str]:
        document = lxml.html.fromstring(self.client.get("/app-settings").data)
        return document.xpath(
            "//select[@name='display_time_zone']/option[@selected]/@value"
        )

    def save(self, tz_name: str) -> None:
        self.client.post("/app-settings/update", data={"display_time_zone": tz_name})

    def test_form_selects_the_default_time_zone(self) -> None:
        self.assertEqual(self.selected_time_zone(), ["America/Chicago"])

    def test_saving_a_valid_time_zone(self) -> None:
        self.save("Europe/London")
        self.assertEqual(self.db.settings_list()["display_time_zone"], "Europe/London")
        self.assertEqual(self.selected_time_zone(), ["Europe/London"])

    def test_saving_an_invalid_time_zone_keeps_the_old_one(self) -> None:
        self.save("Europe/London")
        self.save("Not/A_Zone")
        self.assertEqual(self.db.settings_list()["display_time_zone"], "Europe/London")


class DisplayedTimesTests(SignedInAdminTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.db.settings_update("display_time_zone", "Asia/Tokyo")
        self.db.u(
            """
                insert into billboard_number_one (artist, fetched_at, id, title)
                values ('Artist', :fetched_at, :id, 'Title')
            """,
            {"fetched_at": MOMENT, "id": uuid.uuid4()},
        )
        self.db.tello_balances_insert(
            {
                "allowance": "5 GB",
                "fetched_at": MOMENT,
                "line": "Phone",
                "percentage_available": 50,
                "remaining": "2.5 GB",
                "renewal_date": None,
                "subscription_id": "sub-1",
            }
        )

    def text(self, url: str) -> str:
        return lxml.html.fromstring(self.client.get(url).data).text_content()

    def test_billboard_last_fetched(self) -> None:
        self.assertIn("Last fetched: 2026-07-05 02:30 JST", self.text("/billboard"))

    def test_tello_last_fetched(self) -> None:
        self.assertIn("Last fetched: 2026-07-05 02:30 JST", self.text("/tello"))

    def test_tello_line_history(self) -> None:
        self.assertIn("2026-07-05 02:30 JST", self.text("/tello/sub-1"))

    def test_tello_chart_tooltip(self) -> None:
        svg = self.client.get("/tello/sub-1/svg").data.decode()
        self.assertIn("2026-07-05: 2.50 GB", svg)


# Zones 25 hours apart, so their dates always differ
EARLY_ZONE = "Pacific/Kiritimati"
LATE_ZONE = "Pacific/Pago_Pago"


class DatabaseTimeZoneTests(unittest.TestCase):
    """The database reads the display time zone from its own settings table, so
    scheduled tasks that run outside a request use the stored setting too."""

    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = os.path.join(directory.name, "yavin.db")
        app_sqlite.init(path)
        self.db = YavinSqliteDatabase(path)
        self.addCleanup(self.db.close)

    def test_display_time_zone(self) -> None:
        for stored, expected in (
            (None, "America/Chicago"),
            ("Not/A_Zone", "America/Chicago"),
            ("Asia/Tokyo", "Asia/Tokyo"),
        ):
            with self.subTest(stored=stored):
                if stored is None:
                    self.db.settings_delete("display_time_zone")
                else:
                    self.db.settings_update("display_time_zone", stored)
                self.assertEqual(self.db.display_time_zone().key, expected)

    def test_today_uses_the_stored_time_zone(self) -> None:
        for tz_name in (EARLY_ZONE, LATE_ZONE):
            with self.subTest(tz_name=tz_name):
                self.db.settings_update("display_time_zone", tz_name)
                expected = dt.datetime.now(zoneinfo.ZoneInfo(tz_name)).date()
                self.assertEqual(self.db.today(), expected)

    def test_due_library_books_use_the_stored_time_zone(self) -> None:
        self.db.library_credentials_insert(
            {
                "display_name": "Library",
                "library": "https://library.example.com",
                "library_type": "biblionix",
                "password": "",
                "username": "",
            }
        )
        credential_id = self.db.library_credentials_list()[0]["id"]
        due = dt.datetime.now(zoneinfo.ZoneInfo(EARLY_ZONE)).date()
        self.db.library_books_insert(
            {
                "credential_id": credential_id,
                "due": due,
                "item_id": "1",
                "medium": "Book",
                "renewable": True,
                "title": "Title",
            }
        )
        for tz_name, expected in ((EARLY_ZONE, ["Title"]), (LATE_ZONE, [])):
            with self.subTest(tz_name=tz_name):
                self.db.settings_update("display_time_zone", tz_name)
                titles = [b["title"] for b in self.db.library_books_list_due()]
                self.assertEqual(titles, expected)


if __name__ == "__main__":
    unittest.main()
