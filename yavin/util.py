import datetime
import zoneinfo


def add_days(d: datetime.date, days: int) -> datetime.date:
    return d + datetime.timedelta(days=days)


def clean_datetime(d: datetime.datetime) -> str:
    return d.strftime("%Y-%m-%d %H:%M")


def in_two_minutes() -> datetime.datetime:
    return datetime.datetime.now() + datetime.timedelta(minutes=2)


def str_to_date(d: str) -> datetime.date:
    return datetime.datetime.strptime(d, "%Y-%m-%d").date()


def today() -> datetime.date:
    return (
        datetime.datetime.now(tz=datetime.timezone.utc)
        .astimezone(tz=zoneinfo.ZoneInfo("America/Chicago"))
        .date()
    )
