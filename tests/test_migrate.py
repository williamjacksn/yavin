import datetime as dt
import decimal
import os
import tempfile
import unittest

from yavin.db import app_sqlite
from yavin.db.app_sqlite import YavinSqliteDatabase

D = dt.date
Dec = decimal.Decimal


class StartupTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = os.path.join(directory.name, "yavin.db")

    def open(self) -> YavinSqliteDatabase:
        db = YavinSqliteDatabase(self.path)
        self.addCleanup(db.close)
        return db

    def test_first_start_creates_an_empty_database(self) -> None:
        app_sqlite.init(self.path)
        con = app_sqlite.connection_get(self.path)
        self.addCleanup(con.close)
        self.assertEqual(app_sqlite.get_schema_version(con), 1)
        self.assertEqual(self.open().settings_list(), {})

    def test_later_starts_keep_the_data(self) -> None:
        app_sqlite.init(self.path)
        db = self.open()
        db.weight_entries_insert(D(2026, 10, 2), Dec("179.9"))
        db.close()
        app_sqlite.init(self.path)
        self.assertEqual(
            self.open().weight_entries_list_all(),
            [{"entry_date": D(2026, 10, 2), "weight": Dec("179.9")}],
        )


if __name__ == "__main__":
    unittest.main()
