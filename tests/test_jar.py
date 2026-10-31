import datetime as dt
import os
import tempfile
import unittest
import uuid
from collections import Counter
from unittest.mock import MagicMock, patch

import lxml.html

with (
    tempfile.TemporaryDirectory() as directory,
    patch.dict(os.environ, {"DATABASE": os.path.join(directory, "test.db")}),
):
    from yavin.app import app

from yavin import jar

D = dt.date
TODAY = D(2026, 10, 31)


class JarStatsTests(unittest.TestCase):
    def test_gaps_count_days_between_distinct_entry_dates(self) -> None:
        dates = [D(2026, 1, 1), D(2026, 1, 11), D(2026, 1, 11), D(2026, 3, 2)]
        stats = jar.stats(dates, TODAY)
        self.assertEqual(stats.entries, 4)
        self.assertEqual(stats.entries_this_year, 4)
        self.assertEqual(stats.longest_gap, 50)
        self.assertEqual(stats.average_gap, 30)
        self.assertEqual(stats.days_since_last, (TODAY - D(2026, 3, 2)).days)
        # The current gap (243 days) is longer than any past gap
        self.assertTrue(stats.is_record)

    def test_entries_this_year_only_counts_this_year(self) -> None:
        stats = jar.stats([D(2025, 12, 30), D(2026, 1, 2), D(2026, 10, 30)], TODAY)
        self.assertEqual((stats.entries, stats.entries_this_year), (3, 2))
        self.assertEqual(stats.days_since_last, 1)
        self.assertFalse(stats.is_record)

    def test_empty_single_and_future_entries(self) -> None:
        empty = jar.stats([], TODAY)
        self.assertEqual(
            (empty.entries, empty.days_since_last, empty.longest_gap), (0, None, None)
        )
        self.assertFalse(empty.is_record)
        single = jar.stats([D(2026, 10, 1)], TODAY)
        self.assertEqual((single.days_since_last, single.average_gap), (30, None))
        self.assertFalse(single.is_record)
        self.assertEqual(jar.stats([D(2026, 11, 5)], TODAY).days_since_last, 0)

    def test_years_run_from_the_first_entry_through_this_year(self) -> None:
        self.assertEqual(
            jar.years([D(2024, 6, 1), D(2026, 1, 1)], TODAY), [2024, 2025, 2026]
        )
        self.assertEqual(jar.years([], TODAY), [2026])


class JarCalendarTests(unittest.TestCase):
    def month(
        self, year: int, month: int, dates: list[dt.date]
    ) -> lxml.html.HtmlElement:
        html = str(jar.month(year, month, Counter(dates), TODAY))
        return lxml.html.fragment_fromstring(html)

    def days(self, table: lxml.html.HtmlElement) -> dict[str, lxml.html.HtmlElement]:
        """Day cells by their date, from the cell's title."""
        return {td.get("title").split(":")[0]: td for td in table.xpath("//td[@title]")}

    def assert_classes(self, cell: lxml.html.HtmlElement, *classes: str) -> None:
        """The day's colored box has every class in classes."""
        (box,) = cell.xpath("div")
        for expected in classes:
            for name in expected.split():
                self.assertIn(name, box.classes)

    def test_one_cell_per_day_shaded_by_entry_count(self) -> None:
        table = self.month(2026, 2, [D(2026, 2, 3), D(2026, 2, 14), D(2026, 2, 14)])
        self.assertEqual(table.tag, "table")
        self.assertFalse(table.xpath("//*[@style]"))
        days = self.days(table)
        self.assertEqual(len(days), 28)
        self.assert_classes(days["Tue Feb 3, 2026"], jar.ONE_ENTRY)
        self.assert_classes(days["Sat Feb 14, 2026"], jar.MORE_ENTRIES)
        self.assert_classes(days["Sun Feb 1, 2026"], jar.NO_ENTRY)
        self.assertEqual(
            days["Sat Feb 14, 2026"].get("title"), "Sat Feb 14, 2026: 2 entries"
        )
        self.assertEqual(
            days["Sun Feb 1, 2026"].get("title"), "Sun Feb 1, 2026: no entries"
        )
        # Screen readers hear the count after the day number
        self.assertEqual(days["Sat Feb 14, 2026"].text_content(), "14, 2 entries")
        self.assertEqual(days["Sun Feb 1, 2026"].text_content(), "1")
        caption = table.xpath("//caption//span/text()")
        self.assertEqual(caption, ["February", "3 entries"])

    def test_weeks_start_on_sunday(self) -> None:
        table = self.month(2026, 10, [])
        self.assertEqual(
            table.xpath("//thead//abbr/@title"),
            [
                "Sunday",
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
            ],
        )
        # October 1, 2026 is a Thursday, so the first week starts with four blanks
        first_week = table.xpath("//tbody/tr[1]/td")
        self.assertEqual(
            [td.text_content() for td in first_week], ["", "", "", "", "1", "2", "3"]
        )
        self.assertEqual(len(table.xpath("//tbody/tr")), 5)

    def test_today_is_outlined_and_future_days_are_not_shaded(self) -> None:
        october = self.days(self.month(2026, 10, [TODAY]))
        self.assert_classes(
            october["Sat Oct 31, 2026"], "small", jar.ONE_ENTRY, jar.TODAY
        )
        self.assert_classes(october["Fri Oct 30, 2026"], jar.NO_ENTRY, jar.BORDER)
        self.assertNotIn(jar.TODAY, october["Fri Oct 30, 2026"].xpath("div")[0].classes)
        future = self.days(self.month(2026, 11, []))["Sun Nov 1, 2026"]
        self.assert_classes(future, jar.FUTURE)
        self.assertFalse(
            [c for c in future.xpath("div")[0].classes if c.startswith("bg-")]
        )


class JarPageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = MagicMock()
        self.db.settings_list.return_value = {}
        self.db.user_permissions_get.return_value = ["jar"]
        self.db.jar_entries_list_all.return_value = [
            {"entry_date": d, "id": i, "paid": False}
            for i, d in enumerate([D(2025, 3, 1), D(2026, 1, 1), D(2026, 1, 21)])
        ]
        for patcher in (
            patch("yavin.db.YavinDatabase", return_value=self.db),
            patch("yavin.util.today", return_value=TODAY),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        app.config.update(TESTING=True, SECRET_KEY=uuid.uuid4().hex)
        self.client = app.test_client()

    def page(self, query: str = "") -> lxml.html.HtmlElement:
        response = self.client.get(f"/jar{query}")
        self.assertEqual(response.status_code, 200)
        return lxml.html.fromstring(response.data)

    def stat(self, document: lxml.html.HtmlElement, label: str) -> str:
        return document.xpath(
            f"string(//div[contains(@class, 'card-body')][div[1]='{label}']/div[2])"
        )

    def test_stats_show_the_current_gap_and_records(self) -> None:
        document = self.page()
        self.assertEqual(self.stat(document, "Days since last entry"), "283")
        self.assertEqual(self.stat(document, "Longest gap"), "306 days")
        self.assertEqual(self.stat(document, "Average gap"), "~163 days")
        self.assertEqual(self.stat(document, "Entries in 2026"), "2")
        self.assertIn("3 all time", document.text_content())
        self.assertNotIn("Longest gap yet", document.text_content())

    def test_calendar_defaults_to_this_year_and_links_to_other_years(self) -> None:
        document = self.page()
        self.assertEqual(
            document.xpath("string(//h2[contains(., 'calendar')])"), "2026 calendar"
        )
        self.assertEqual(len(document.xpath("//table[caption]")), 12)
        self.assertEqual(
            document.xpath("//a[contains(@aria-label, 'Previous year')]/@href"),
            ["/jar?year=2025"],
        )
        self.assertFalse(document.xpath("//a[contains(@aria-label, 'Next year')]"))
        document = self.page("?year=2025")
        self.assertEqual(
            document.xpath("string(//h2[contains(., 'calendar')])"), "2025 calendar"
        )
        self.assertEqual(
            document.xpath("//a[contains(@aria-label, 'Next year')]/@href"),
            ["/jar?year=2026"],
        )
        for query in ("?year=1999", "?year=2027", "?year=soon"):
            with self.subTest(query=query):
                heading = self.page(query).xpath(
                    "string(//h2[contains(., 'calendar')])"
                )
                self.assertEqual(heading, "2026 calendar")

    def test_page_has_no_date_list(self) -> None:
        document = self.page()
        # The only tables are the twelve months of the calendar
        months = [
            t.xpath("string(caption//span[1])") for t in document.xpath("//table")
        ]
        self.assertEqual(months[0], "January")
        self.assertEqual(months[-1], "December")
        self.assertEqual(len(months), 12)
        self.assertNotIn("All entries", document.text_content())
        self.assertEqual(self.client.post("/jar/rows").status_code, 404)

    def test_requires_the_jar_permission(self) -> None:
        self.db.user_permissions_get.return_value = []
        self.assertIn(b"Not authorized", self.client.get("/jar").data)
        self.db.jar_entries_list_all.assert_not_called()


if __name__ == "__main__":
    unittest.main()
