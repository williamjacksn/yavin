import datetime as dt
import decimal
import json
import os
import tempfile
import unittest
import uuid
from unittest.mock import patch

from yavin.db import app_sqlite
from yavin.db.app import BillboardRow, UserPermissions
from yavin.db.app_sqlite import YavinSqliteDatabase

D = dt.date
Dec = decimal.Decimal


class SqliteDatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = os.path.join(directory.name, "yavin.db")
        app_sqlite.connection_init(path)
        con = app_sqlite.connection_get(path)
        app_sqlite.migrate(con)
        con.close()
        self.db = YavinSqliteDatabase(path)
        self.addCleanup(self.db.close)
        today = patch("yavin.util.today", return_value=D(2026, 10, 31))
        today.start()
        self.addCleanup(today.stop)

    def test_values_come_back_as_python_types(self) -> None:
        self.db.callings_insert(
            {
                "ward": "Maple",
                "calling": "Clerk",
                "sustained_at": D(2023, 2, 5),
                "set_apart_at": None,
                "released_at": None,
            }
        )
        (calling,) = self.db.callings_list()
        self.assertIsInstance(calling["id"], uuid.UUID)
        self.assertEqual(calling["sustained_at"], D(2023, 2, 5))
        self.assertIsNone(calling["set_apart_at"])
        self.assertEqual(self.db.callings_get(calling["id"]), calling)
        self.assertIsNone(self.db.callings_get(uuid.uuid4()))

        self.db.billboard_insert("Artist", "Song")
        latest = self.db.billboard_get_latest()
        self.assertIsInstance(latest, BillboardRow)
        self.assertEqual(latest.fetched_at.tzinfo, dt.UTC)

    def test_decimals_keep_their_exact_digits(self) -> None:
        for day, weight in ((1, "185.0"), (2, "184.20")):
            self.db.weight_entries_insert(D(2026, 10, day), Dec(weight))
        weights = [str(w["weight"]) for w in self.db.weight_entries_list()]
        self.assertEqual(weights, ["184.20", "185.0"])
        # A second entry for the same day is ignored
        self.db.weight_entries_insert(D(2026, 10, 2), Dec("150"))
        self.assertEqual(
            self.db.weight_entries_get_most_recent(),
            {"entry_date": D(2026, 10, 2), "weight": Dec("184.20")},
        )

    def test_balances_add_up_exactly(self) -> None:
        account = uuid.uuid4()
        self.db.u(
            "insert into balances_accounts (id, account_name) values (:id, 'Checking')",
            {"id": account},
        )
        empty = uuid.uuid4()
        self.db.u(
            "insert into balances_accounts (id, account_name) values (:id, 'empty')",
            {"id": empty},
        )
        for value in ("0.10", "0.20", "-0.05"):
            self.db.balances_transactions_add(
                {
                    "account_id": str(account),
                    "tx_date": "2026-10-31",
                    "tx_description": value,
                    "tx_value": value,
                }
            )
        balances = {
            a["account_name"]: a["account_balance"]
            for a in self.db.balances_accounts_list()
        }
        self.assertEqual(balances, {"Checking": Dec("0.25"), "empty": Dec(0)})
        rows = self.db.balances_transactions_list(account)
        self.assertEqual({r["account_balance"] for r in rows}, {Dec("0.25")})
        # An account with no transactions still lists one row, with a zero balance
        (row,) = self.db.balances_transactions_list(empty)
        self.assertIsNone(row["tx_id"])
        self.assertEqual(row["account_balance"], Dec(0))
        self.assertEqual(self.db.balances_accounts_count(), 2)

    def test_tithing_owed_rounds_half_up_to_cents(self) -> None:
        self.db.tithing_income_insert(D(2026, 9, 1), Dec("1000.00"), "Paid")
        self.db.tithing_income_mark_paid()
        self.db.tithing_income_insert(D(2026, 10, 1), Dec("100.05"), "Pay")
        self.assertEqual(self.db.tithing_get_current_owed(), Dec("10.01"))
        (unpaid,) = self.db.tithing_income_list_unpaid()
        self.assertEqual(unpaid["description"], "Pay")
        paid = [r for r in self.db.tithing_income_list_all() if r["tithing_paid"]]
        self.assertEqual(paid[0]["tithing_paid"], D(2026, 10, 31))

    def test_theatre_import_skips_exact_duplicates(self) -> None:
        entry = {
            "performer": "A. Actor",
            "show": "Wicked",
            "first_show": None,
            "last_show": None,
            "performances": None,
            "role": "",
            "company": "",
            "director": "",
        }
        self.db.theatre_save(entry)
        revival = {**entry, "show": "Wicked (revival)", "first_show": D(2024, 1, 2)}
        self.db.theatre_import(json.dumps([entry, revival, revival], default=str))
        shows = sorted(e["show"] for e in self.db.theatre_list())
        self.assertEqual(shows, ["Wicked", "Wicked (revival)"])
        (saved,) = [e for e in self.db.theatre_list() if e["first_show"]]
        self.assertEqual(saved["first_show"], D(2024, 1, 2))

    def test_dreamlight_skills_are_per_user_and_go_with_their_character(self) -> None:
        for kind, name in (("area", "Plaza"), ("universe", "Toy Story")):
            self.db.dreamlight_lookup_save(kind, name)
        self.db.dreamlight_lookup_save("skill", "Mining")
        self.db.dreamlight_lookup_save("skill", "Fishing")
        lookups = {
            k: {e["name"]: e["id"] for e in self.db.dreamlight_lookup_list(k)}
            for k in ("area", "universe", "skill")
        }
        self.db.dreamlight_character_add(
            "Buzz", lookups["area"]["Plaza"], lookups["universe"]["Toy Story"]
        )
        (buzz,) = self.db.dreamlight_characters_list("a@example.com")
        mining, fishing = lookups["skill"]["Mining"], lookups["skill"]["Fishing"]
        self.db.dreamlight_character_skill(buzz["id"], "a@example.com", mining)
        self.db.dreamlight_character_skill(buzz["id"], "a@example.com", fishing)
        self.db.dreamlight_character_skill(buzz["id"], "b@example.com", mining)
        skill = {
            email: self.db.dreamlight_characters_list(email)[0]["skill"]
            for email in ("a@example.com", "b@example.com", "c@example.com")
        }
        self.assertEqual(
            skill,
            {
                "a@example.com": "Fishing",
                "b@example.com": "Mining",
                "c@example.com": None,
            },
        )
        self.assertEqual(self.db.dreamlight_skills_in_use(), {mining, fishing})
        self.db.dreamlight_character_skill(buzz["id"], "b@example.com", None)
        self.assertEqual(self.db.dreamlight_skills_in_use(), {fishing})
        self.db.dreamlight_character_delete(buzz["id"])
        self.assertEqual(self.db.dreamlight_character_skill_list_all(), [])

    def test_dates_from_aggregates_and_today(self) -> None:
        self.assertEqual(self.db.jar_entries_days_since_last(), -1)
        for day in (D(2026, 9, 1), D(2026, 10, 21)):
            self.db.jar_entries_insert(day)
        self.assertEqual(self.db.jar_entries_days_since_last(), 10)
        self.assertEqual([e["id"] for e in self.db.jar_entries_list_all()], [1, 2])
        self.assertEqual({e["paid"] for e in self.db.jar_entries_list_all()}, {False})

        self.db.library_credentials_insert(
            {
                "library": "https://lib.example",
                "username": "u",
                "password": "p",
                "display_name": "Library",
                "library_type": "biblionix",
            }
        )
        (credential,) = self.db.library_credentials_list()
        self.assertEqual(credential["balance"], 0)
        for title, due in (("Late", D(2026, 10, 30)), ("Today", D(2026, 10, 31))):
            self.db.library_books_insert(
                {
                    "credential_id": credential["id"],
                    "title": title,
                    "due": due,
                    "renewable": True,
                    "item_id": title,
                    "medium": "book",
                }
            )
        self.assertEqual(
            self.db.library_books_count(), {"books_count": 2, "overdue_count": 1}
        )
        self.assertEqual(
            [b["title"] for b in self.db.library_books_list_due()], ["Late", "Today"]
        )
        self.assertIs(self.db.library_books_list()[0]["renewable"], True)
        self.db.library_books_truncate()
        self.assertEqual(self.db.library_books_count()["books_count"], 0)

    def test_settings_and_permissions_update_in_place(self) -> None:
        self.db.settings_update("smtp_server", "one")
        self.db.settings_update("smtp_server", "two")
        self.assertEqual(self.db.settings_list(), {"smtp_server": "two"})
        self.db.user_permissions_set("b@example.com", ["jar", "admin", "jar"])
        self.db.user_permissions_add("b@example.com", "tello")
        self.db.user_permissions_set("A@example.com", ["theatre"])
        self.assertEqual(
            self.db.user_permissions_list(),
            [
                UserPermissions("A@example.com", "theatre"),
                UserPermissions("b@example.com", "admin jar tello"),
            ],
        )
        self.db.user_permissions_delete("A@example.com")
        self.assertEqual(self.db.user_permissions_get("A@example.com"), [])

    def test_text_sorts_ignore_case(self) -> None:
        for person in ("Will", "ann", "Ben"):
            self.db.movie_people_insert({"person": person})
        people = [p["person"] for p in self.db.movie_people_list()]
        self.assertEqual(people, ["ann", "Ben", "Will"])
        # Nobody has picked yet, so the next pick and the pick order agree
        next_pick = self.db.movie_people_next_pick()
        first = min(self.db.movie_people_list(), key=lambda p: p["pick_order"])
        self.assertEqual(next_pick["id"], first["id"])


if __name__ == "__main__":
    unittest.main()
