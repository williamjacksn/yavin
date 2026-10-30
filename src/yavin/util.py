import datetime as dt
import zoneinfo


def add_days(d: dt.date, days: int) -> dt.date:
    return d + dt.timedelta(days=days)


def clean_datetime(d: dt.datetime) -> str:
    return d.strftime("%Y-%m-%d %H:%M")


def data_amount_gb(amount: str) -> float | None:
    """Convert a data amount like "457.59 MB" to gigabytes, using 1 GB = 1,000 MB.
    Return None if the amount is not a number followed by a known unit."""
    factors = {"KB": 0.000001, "MB": 0.001, "GB": 1, "TB": 1000}
    parts = amount.replace(",", "").split()
    if len(parts) != 2 or parts[1].upper() not in factors:
        return None
    try:
        return float(parts[0]) * factors[parts[1].upper()]
    except ValueError:
        return None


def in_two_minutes() -> dt.datetime:
    return dt.datetime.now(tz=dt.UTC) + dt.timedelta(minutes=2)


def str_to_date(d: str) -> dt.date:
    return dt.date.fromisoformat(d)


def today() -> dt.date:
    return (
        dt.datetime.now(tz=dt.UTC)
        .astimezone(tz=zoneinfo.ZoneInfo("America/Chicago"))
        .date()
    )
