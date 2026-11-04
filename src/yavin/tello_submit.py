"""Collect Tello Mobile balances and submit them to Yavin.

Run this tool on another machine (for example, a home computer on a daily schedule).
It reads the following environment variables:

TELLO_USERNAME, TELLO_PASSWORD: Tello Mobile account credentials
TELLO_COOKIE_FILE: file for saving the Tello Mobile login session (optional)
YAVIN_URL: base URL of the Yavin server, for example https://yavin.example.com
YAVIN_AUTH_PHRASE: the ADMIN_AUTH_PHRASE configured on the Yavin server

When a cookie file is given, a saved Tello Mobile session is reused and credentials are
only needed if that session has expired. Missing Tello Mobile credentials are requested
through terminal prompts when possible."""

import argparse
import getpass
import logging
import os
import sys

import certifi
import httpx2
import notch
import tello_usage

notch.configure()
log = logging.getLogger(__name__)


class Args:
    cookie_file: str
    url: str


def parse_args() -> Args:
    parser = argparse.ArgumentParser(
        description="Collect Tello Mobile balances and submit them to Yavin."
    )
    parser.add_argument(
        "--url",
        default=os.getenv("YAVIN_URL", ""),
        help="Base URL of the Yavin server (default: YAVIN_URL)",
    )
    parser.add_argument(
        "--cookie-file",
        default=os.getenv("TELLO_COOKIE_FILE", ""),
        metavar="PATH",
        help="Save the Tello Mobile login session to this file and reuse it on later "
        "runs (default: TELLO_COOKIE_FILE; not saved if unset)",
    )
    return parser.parse_args(namespace=Args())


def _credential(name: str, prompt: str, *, secret: bool = False) -> str:
    value = os.getenv(name, "")
    if not value and sys.stdin.isatty():
        value = getpass.getpass(prompt) if secret else input(prompt)
    if not value:
        log.critical(f"Missing {name}")
        sys.exit(1)
    return value


def collect_balances(cookie_file: str) -> list[dict]:
    """Read balances, reusing the session in cookie_file when it is still valid."""
    username = os.getenv("TELLO_USERNAME") or None
    with tello_usage.TelloClient(cookie_file=cookie_file or None) as client:
        try:
            balances = client.balances(username)
        except tello_usage.TelloLoginRequired:
            if cookie_file:
                log.info("No usable saved Tello Mobile session; logging in")
            username = _credential("TELLO_USERNAME", "Tello Mobile email address: ")
            password = _credential(
                "TELLO_PASSWORD", "Tello Mobile password: ", secret=True
            )
            balances = client.balances(username, password)
    return [
        {
            "allowance": b.allowance,
            "line": b.line,
            "percentage_available": b.percentage_available,
            "remaining": b.remaining,
            "renewal_date": b.renewal_date,
            "subscription_id": b.subscription_id,
        }
        for b in balances
    ]


def submit_balances(url: str, auth_phrase: str, balances: list[dict]) -> int:
    """Send balances to Yavin and return the number of balances it stored."""
    resp = httpx2.post(
        f"{url.rstrip('/')}/tello/incoming",
        json={"balances": balances},
        headers={"Authorization": f"Bearer {auth_phrase}"},
        timeout=30,
        verify=certifi.where(),
    )
    if resp.is_error:
        log.critical(f"Yavin rejected the submission ({resp.status_code}): {resp.text}")
        sys.exit(1)
    return resp.json()["stored"]


def main() -> None:
    args = parse_args()
    if not args.url:
        log.critical("Missing Yavin URL; use --url or set YAVIN_URL")
        sys.exit(1)
    auth_phrase = _credential("YAVIN_AUTH_PHRASE", "Yavin auth phrase: ", secret=True)

    try:
        balances = collect_balances(args.cookie_file)
    except (tello_usage.TelloError, httpx2.HTTPError) as e:
        log.critical(f"Could not read Tello Mobile balances: {e}")
        sys.exit(1)
    log.info(f"Collected {len(balances)} Tello Mobile balances")

    try:
        stored = submit_balances(args.url, auth_phrase, balances)
    except httpx2.HTTPError as e:
        log.critical(f"Could not reach Yavin: {e}")
        sys.exit(1)
    log.info(f"Yavin stored {stored} Tello Mobile balances")


if __name__ == "__main__":
    main()
