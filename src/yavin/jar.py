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


# Day cells in a month grid, in SVG user units
CELL = 10
GAP = 2
STEP = CELL + GAP
HEADER = 10
WEEKDAYS = "SMTWTFS"


def _fill(count: int) -> str:
    if count >= 2:
        return "var(--bs-success-text-emphasis)"
    if count == 1:
        return "var(--bs-success)"
    return "var(--bs-secondary-bg)"


def _plural(count: int) -> str:
    return "1 entry" if count == 1 else f"{count} entries"


def month(
    year: int, month_number: int, counts: Counter[dt.date], today: dt.date
) -> h.Element:
    """One month as a grid of days, with weeks starting on Sunday."""
    weeks = cal.Calendar(firstweekday=6).monthdatescalendar(year, month_number)
    width = 7 * STEP - GAP
    height = HEADER + len(weeks) * STEP - GAP
    name = dt.date(year, month_number, 1).strftime("%B")
    total = sum(
        n for d, n in counts.items() if (d.year, d.month) == (year, month_number)
    )
    cells = []
    for row, week in enumerate(weeks):
        for column, day in enumerate(week):
            if day.month != month_number:
                continue
            count = counts[day]
            label = f"{day:%a %b} {day.day}, {day.year}"
            label += f": {_plural(count)}" if count else ": no entries"
            future = day > today
            cells.append(
                h.rect(
                    x=str(column * STEP),
                    y=str(HEADER + row * STEP),
                    width=str(CELL),
                    height=str(CELL),
                    rx="2",
                    fill="none" if future else _fill(count),
                    stroke=(
                        "var(--bs-body-color)"
                        if day == today
                        else "var(--bs-border-color)"
                        if future
                        else None
                    ),
                    stroke_width="1.5" if day == today else "0.75" if future else None,
                )[h.title[label]]
            )
    return h.figure(".mb-0")[
        h.figcaption(".small.d-flex.justify-content-between")[
            h.span(".fw-semibold")[name],
            h.span(".text-body-secondary")[_plural(total) if total else None],
        ],
        h.svg(
            ".d-block.w-100",
            viewBox=f"0 0 {width} {height}",
            role="img",
            aria_label=f"{name} {year}: {_plural(total)}",
            xmlns="http://www.w3.org/2000/svg",
        )[
            [
                h.text(
                    x=str(i * STEP + CELL / 2),
                    y="7",
                    font_size="6",
                    text_anchor="middle",
                    fill="var(--bs-secondary-color)",
                )[letter]
                for i, letter in enumerate(WEEKDAYS)
            ],
            cells,
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
