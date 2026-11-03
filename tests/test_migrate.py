import datetime as dt
import decimal
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from yavin.db import app_sqlite
from yavin.db.app_sqlite import YavinSqliteDatabase

D = dt.date
Dec = decimal.Decimal


class StartupMigrationTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = os.path.join(directory.name, "yavin.db")
        # MagicMock list methods return nothing, so only these tables have rows
        self.pg = MagicMock()
        self.pg.settings_list.return_value = {"scheduled_tasks_enabled": "true"}
        self.pg.weight_entries_list_all.return_value = [
            {"entry_date": D(2026, 10, 1), "weight": Dec("180.4")}
        ]
        self.postgres = MagicMock(return_value=self.pg)
        patcher = patch("yavin.db.app_sqlite.YavinDatabase", self.postgres)
        patcher.start()
        self.addCleanup(patcher.stop)

    def open(self) -> YavinSqliteDatabase:
        db = YavinSqliteDatabase(self.path)
        self.addCleanup(db.close)
        return db

    def schema_version(self) -> int:
        con = app_sqlite.connection_get(self.path)
        try:
            return app_sqlite.get_schema_version(con)
        finally:
            con.close()

    def test_first_start_copies_everything_from_postgres(self) -> None:
        app_sqlite.init(self.path, "postgres://db", "admin@example.com")
        self.postgres.assert_called_once_with("postgres://db")
        self.pg.migrate.assert_called_once_with(admin_email="admin@example.com")
        db = self.open()
        self.assertEqual(db.settings_list(), {"scheduled_tasks_enabled": "true"})
        self.assertEqual(
            db.weight_entries_list_all(),
            [{"entry_date": D(2026, 10, 1), "weight": Dec("180.4")}],
        )
        self.assertFalse(os.path.exists(f"{self.path}.tmp"))

    def test_later_starts_keep_sqlite_data_and_leave_postgres_alone(self) -> None:
        app_sqlite.init(self.path, "postgres://db")
        db = self.open()
        db.weight_entries_insert(D(2026, 10, 2), Dec("179.9"))
        db.close()
        self.postgres.reset_mock()
        app_sqlite.init(self.path, "postgres://db")
        self.postgres.assert_not_called()
        self.assertEqual(len(self.open().weight_entries_list_all()), 2)

    def test_without_a_dsn_the_database_starts_empty(self) -> None:
        app_sqlite.init(self.path)
        self.postgres.assert_not_called()
        self.assertEqual(self.schema_version(), 1)
        self.assertEqual(self.open().settings_list(), {})

    def test_a_failed_copy_leaves_nothing_behind_and_is_retried(self) -> None:
        self.pg.hymns_list.side_effect = RuntimeError("connection lost")
        with self.assertRaises(RuntimeError):
            app_sqlite.init(self.path, "postgres://db")
        self.assertEqual(self.schema_version(), 0)
        self.pg.hymns_list.side_effect = None
        app_sqlite.init(self.path, "postgres://db")
        self.assertEqual(len(self.open().weight_entries_list_all()), 1)


if __name__ == "__main__":
    unittest.main()
