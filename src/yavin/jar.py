"""Jar history: gap statistics and a calendar of entry dates."""

import calendar as cal
import dataclasses
import datetime as dt
import itertools
from collections import Counter

import htpy as h


@dataclasses.dataclass
class JarStats:
    entries: int
    entries_this_year: int
    days_since_last: int | None
    longest_gap: int | None
    average_gap: float | None

    @property
    def is_record(self) -> bool:
        """The current gap is longer than any gap between past entries."""
        return (
            self.days_since_last is not None
            and self.longest_gap is not None
            and self.days_since_last > self.longest_gap
        )


def stats(dates: list[dt.date], today: dt.date) -> JarStats:
    """Gaps are the days between consecutive entry dates. Several entries on one
    day count as one date when measuring gaps."""
    distinct = sorted(set(dates))
    gaps = [(b - a).days for a, b in itertools.pairwise(distinct)]
    return JarStats(
        entries=len(dates),
        entries_this_year=sum(1 for d in dates if d.year == today.year),
        days_since_last=max(0, (today - distinct[-1]).days) if distinct else None,
        longest_gap=max(gaps) if gaps else None,
        average_gap=sum(gaps) / len(gaps) if gaps else None,
    )


def years(dates: list[dt.date], today: dt.date) -> list[int]:
    """Years the calendar can show: from the first entry through this year."""
    first = min(dates).year if dates else today.year
    return list(range(min(first, today.year), today.year + 1))


WEEKDAYS = (
    "Sunday",
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
)

# Bootstrap classes for a day by its number of entries, light to dark. The legend
# uses the same classes.
NO_ENTRY = "bg-body-secondary text-body-secondary"
ONE_ENTRY = "bg-success bg-opacity-50 text-success-emphasis"
MORE_ENTRIES = "bg-success text-white"
FUTURE = "text-body-tertiary"
# Every day has a border so the white one spaces the cells and today's dark one
# outlines it without changing its size
BORDER = "border-white"
TODAY = "border-dark"


def cell_classes(count: int) -> str:
    if count >= 2:
        return MORE_ENTRIES
    if count == 1:
        return ONE_ENTRY
    return NO_ENTRY


def _plural(count: int) -> str:
    return "1 entry" if count == 1 else f"{count} entries"


def _day(day: dt.date, count: int, today: dt.date) -> h.Element:
    label = f"{day:%a %b} {day.day}, {day.year}: "
    label += _plural(count) if count else "no entries"
    colors = FUTURE if day > today else cell_classes(count)
    border = TODAY if day == today else BORDER
    return h.td(".p-0", title=label)[
        h.div(class_=f"small border border-2 rounded-1 {border} {colors}")[
            day.day,
            h.span(".visually-hidden")[f", {_plural(count)}"] if count else None,
        ]
    ]


def month(
    year: int, month_number: int, counts: Counter[dt.date], today: dt.date
) -> h.Element:
    """One month as a calendar table, with weeks starting on Sunday."""
    weeks = cal.Calendar(firstweekday=6).monthdatescalendar(year, month_number)
    name = dt.date(year, month_number, 1).strftime("%B")
    total = sum(
        n for d, n in counts.items() if (d.year, d.month) == (year, month_number)
    )
    return h.table(".caption-top.w-100.mb-0.text-center.small")[
        # A flex caption stops being a caption, so the layout is on a div inside
        h.caption(".pt-0.pb-1.text-body")[
            h.div(".d-flex.justify-content-between")[
                h.span(".fw-semibold")[name],
                h.span(".text-body-secondary")[_plural(total) if total else None],
            ]
        ],
        h.thead[
            h.tr[
                (
                    h.th(".fw-normal.text-body-secondary", scope="col")[
                        h.abbr(".text-decoration-none", title=weekday)[weekday[0]]
                    ]
                    for weekday in WEEKDAYS
                )
            ]
        ],
        h.tbody[
            (
                h.tr[
                    (
                        _day(day, counts[day], today)
                        if day.month == month_number
                        else h.td
                        for day in week
                    )
                ]
                for week in weeks
            )
        ],
    ]


def year_calendar(dates: list[dt.date], year: int, today: dt.date) -> h.Element:
    counts = Counter(dates)
    return h.div(".row.g-3")[
        [
            h.div(".col-6.col-sm-4.col-md-3.col-xl-2")[month(year, m, counts, today)]
            for m in range(1, 13)
        ]
    ]
