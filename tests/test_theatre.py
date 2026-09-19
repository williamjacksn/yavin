import csv
import io
import os
import tempfile
import unittest
import uuid
from unittest.mock import MagicMock, patch

# App import initializes only SQLite WAL; keep that file outside real app data.
with (
    tempfile.TemporaryDirectory() as directory,
    patch.dict(os.environ, {"DATABASE": os.path.join(directory, "test.db")}),
):
    from yavin.app import app

from yavin.theatre import FIELDS, parse_csv, validate


class TheatreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = MagicMock()
        self.db.settings_list.return_value = {}
        self.db.user_permissions_get.return_value = ["theatre"]
        self.db.theatre_list.return_value = []
        self.patcher = patch("yavin.db.YavinDatabase", return_value=self.db)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        app.config.update(TESTING=True, SECRET_KEY=uuid.uuid4().hex)
        self.client = app.test_client()
        self.entry = dict.fromkeys(FIELDS, "")
        self.entry.update(performer="Alice", show="Example", role="Lead, ensemble")

    def test_add_unknown_dates_and_zero(self) -> None:
        self.entry["performances"] = "0"
        response = self.client.post("/theatre/add", data=self.entry)
        self.assertEqual(response.status_code, 302)
        saved = self.db.theatre_save.call_args.args[0]
        self.assertIsNone(saved["first_show"])
        self.assertEqual(saved["performances"], 0)

    def test_invalid_input_preserved_without_writing(self) -> None:
        for changes in (
            {"performer": " "},
            {"first_show": "2026-02-30"},
            {"first_show": "2026-03-01", "last_show": "2026-02-01"},
            {"performances": "-1"},
            {"performances": "1.5"},
        ):
            with self.subTest(changes=changes):
                response = self.client.post("/theatre/add", data=self.entry | changes)
                self.assertEqual(response.status_code, 400)
                self.assertIn(b"Lead, ensemble", response.data)
        self.db.theatre_save.assert_not_called()

    def test_edit_filter_and_export(self) -> None:
        entry_id = uuid.uuid4()
        self.db.theatre_list.return_value = [validate(self.entry) | {"id": entry_id}]
        self.assertEqual(self.client.get(f"/theatre/{entry_id}/edit").status_code, 200)
        self.assertEqual(self.client.get("/theatre?performer=Nobody").status_code, 200)
        response = self.client.post(f"/theatre/{entry_id}/edit", data=self.entry)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.db.theatre_save.call_args.args[1], entry_id)
        exported = self.client.get("/theatre/export").data.decode()
        self.assertEqual(parse_csv(exported), [validate(self.entry)])
        self.assertEqual(
            self.client.get(f"/theatre/{uuid.uuid4()}/edit").status_code, 404
        )

    def test_import_validates_entire_file(self) -> None:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(FIELDS.values())
        writer.writerow(self.entry.values())
        writer.writerow(["", "Invalid", "", "", "", "", "", ""])
        response = self.client.post(
            "/theatre/import",
            data={"file": (io.BytesIO(output.getvalue().encode()), "input.csv")},
        )
        self.assertEqual(response.status_code, 400)
        self.db.theatre_import.assert_not_called()
        valid = output.getvalue().splitlines(keepends=True)[:2]
        response = self.client.post(
            "/theatre/import",
            data={"file": (io.BytesIO("".join(valid).encode()), "input.csv")},
        )
        self.assertEqual(response.status_code, 302)
        self.db.theatre_import.assert_called_once()

    def test_permissions_cover_all_routes(self) -> None:
        self.db.user_permissions_get.return_value = []
        for path in ("/theatre", "/theatre/export", "/dashboard-card/theatre"):
            self.client.get(path)
        for path in (
            "/theatre/add",
            "/theatre/import",
            f"/theatre/{uuid.uuid4()}/edit",
        ):
            self.client.post(path, data=self.entry)
        self.db.theatre_list.assert_not_called()
        self.db.theatre_save.assert_not_called()
        self.db.theatre_import.assert_not_called()

    def test_text_is_escaped(self) -> None:
        self.db.theatre_list.return_value = [
            validate(self.entry | {"show": "<script>alert(1)</script>"})
            | {"id": uuid.uuid4()}
        ]
        response = self.client.get("/theatre")
        self.assertNotIn(b"<script>alert(1)</script>", response.data)
        self.assertIn(b"&lt;script&gt;", response.data)


if __name__ == "__main__":
    unittest.main()
