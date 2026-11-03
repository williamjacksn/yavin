import os
import sqlite3
import tempfile
import unittest
import uuid
from unittest.mock import patch

import lxml.html
from flask.sessions import SecureCookieSessionInterface

with (
    tempfile.TemporaryDirectory() as directory,
    patch.dict(os.environ, {"DATABASE": os.path.join(directory, "test.db")}),
):
    from yavin.app import app

from yavin.db import app_sqlite
from yavin.db.app_sqlite import YavinSqliteDatabase

ADMIN = "admin@example.com"
PLAYER = "player@example.com"
DOWNLOAD = "/download-database"


class DownloadDatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = directory.name
        path = os.path.join(self.directory, "yavin.db")
        app_sqlite.init(path)
        db = YavinSqliteDatabase(path)
        self.addCleanup(db.close)
        db.user_permissions_set(ADMIN, ["admin"])
        db.user_permissions_set(PLAYER, ["dreamlight"])
        # Each request opens its own connection to the test database
        patcher = patch(
            "yavin.db.YavinSqliteDatabase", lambda _: YavinSqliteDatabase(path)
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        app.config.update(TESTING=True, SECRET_KEY=uuid.uuid4().hex)
        self.client = app.test_client()

    def sign_in(self, email: str) -> None:
        serializer = SecureCookieSessionInterface().get_signing_serializer(app)
        if serializer is None:
            self.fail("The app has no secret key for signing sessions")
        self.client.set_cookie(
            app.config["SESSION_COOKIE_NAME"], serializer.dumps({"email": email})
        )

    def test_only_admins_see_the_link_in_the_user_menu(self) -> None:
        link = "//div[contains(@class, 'dropdown-menu')]/a[text()='Download database']"
        for email, expected in ((ADMIN, [DOWNLOAD]), (PLAYER, [])):
            with self.subTest(email=email):
                self.sign_in(email)
                document = lxml.html.fromstring(self.client.get("/").data)
                self.assertEqual(document.xpath(f"{link}/@href"), expected)

    def test_admins_download_a_copy_with_every_change(self) -> None:
        self.sign_in(ADMIN)
        with patch("yavin.util.today", return_value="2026-11-02"):
            response = self.client.get(DOWNLOAD)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["Content-Disposition"],
            "attachment; filename=yavin-2026-11-02.db",
        )
        copy = os.path.join(self.directory, "copy.db")
        with open(copy, "wb") as f:
            f.write(response.data)
        con = sqlite3.connect(copy)
        self.addCleanup(con.close)
        rows = con.execute("select email from user_permissions order by email")
        self.assertEqual(rows.fetchall(), [(ADMIN,), (PLAYER,)])

    def test_everyone_else_is_turned_away(self) -> None:
        self.sign_in(PLAYER)
        response = self.client.get(DOWNLOAD)
        self.assertIn(b"Not authorized", response.data)
        self.assertNotIn("Content-Disposition", response.headers)


if __name__ == "__main__":
    unittest.main()
