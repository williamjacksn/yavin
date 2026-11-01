import os
import tempfile
import unittest
import uuid
from unittest.mock import MagicMock, patch

with (
    tempfile.TemporaryDirectory() as directory,
    patch.dict(os.environ, {"DATABASE": os.path.join(directory, "test.db")}),
):
    from yavin.app import app


class MigrateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = MagicMock()
        self.db.settings_list.return_value = {}
        self.sqlite = MagicMock()
        for patcher in (
            patch("yavin.db.YavinDatabase", return_value=self.db),
            patch("yavin.db.app_sqlite.connection_get", self.sqlite.connection_get),
            patch("yavin.db.app_sqlite.migrate", self.sqlite.migrate),
            patch("yavin.db.app_sqlite.reset_data", self.sqlite.reset_data),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        app.config.update(TESTING=True, SECRET_KEY=uuid.uuid4().hex)
        self.client = app.test_client()

    def test_admins_can_export_to_sqlite(self) -> None:
        self.db.user_permissions_get.return_value = ["admin"]
        response = self.client.get("/migrate")
        self.assertEqual(response.status_code, 302)
        self.sqlite.migrate.assert_called_once()
        self.sqlite.reset_data.assert_called_once()

    def test_everyone_else_is_turned_away_before_anything_is_written(self) -> None:
        for permissions in ([], ["dreamlight", "jar", "tello"]):
            with self.subTest(permissions=permissions):
                self.db.user_permissions_get.return_value = permissions
                response = self.client.get("/migrate")
                self.assertIn(b"Not authorized", response.data)
        self.sqlite.connection_get.assert_not_called()
        self.sqlite.reset_data.assert_not_called()


if __name__ == "__main__":
    unittest.main()
