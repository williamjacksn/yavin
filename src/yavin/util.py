import datetime as dt
import zoneinfo


def add_days(d: dt.date, days: int) -> dt.date:
    return d + dt.timedelta(days=days)


def clean_datetime(d: dt.datetime) -> str:
    return d.strftime("%Y-%m-%d %H:%M")


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
