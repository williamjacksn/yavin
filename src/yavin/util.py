import datetime as dt
import zoneinfo

import flask

DEFAULT_DISPLAY_TIME_ZONE = "America/Chicago"


def add_days(d: dt.date, days: int) -> dt.date:
    return d + dt.timedelta(days=days)


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


def display_time_zone_name() -> str:
    """Return the display time zone name from the app settings loaded for the current
    request. Fall back to the default if the setting is missing or invalid, or if
    there is no app context."""
    tz_name = None
    if flask.has_app_context():
        app_settings: dict[str, str] = flask.g.get("app_settings", {})
        tz_name = app_settings.get("display_time_zone")
    return valid_time_zone_name(tz_name)


def display_time_zone() -> zoneinfo.ZoneInfo:
    return zoneinfo.ZoneInfo(display_time_zone_name())


def format_datetime(d: dt.datetime, fmt: str = "%Y-%m-%d %H:%M") -> str:
    """Convert an aware datetime to the display time zone and format it.
    Raise ValueError if the datetime is naive."""
    if d.utcoffset() is None:
        msg = f"Expected an aware datetime, got naive {d!r}"
        raise ValueError(msg)
    return d.astimezone(display_time_zone()).strftime(fmt)


def in_two_minutes() -> dt.datetime:
    return dt.datetime.now(tz=dt.UTC) + dt.timedelta(minutes=2)


def is_valid_time_zone(tz_name: str) -> bool:
    return tz_name in zoneinfo.available_timezones()


def str_to_date(d: str) -> dt.date:
    return dt.date.fromisoformat(d)


def today(tz: zoneinfo.ZoneInfo | None = None) -> dt.date:
    """Return the current date in the given time zone, or in the display time zone
    if no time zone is given."""
    return dt.datetime.now(tz=tz or display_time_zone()).date()


def valid_time_zone_name(tz_name: str | None) -> str:
    """Return tz_name if it is a valid time zone name, otherwise the default."""
    if tz_name is None or not is_valid_time_zone(tz_name):
        return DEFAULT_DISPLAY_TIME_ZONE
    return tz_name
