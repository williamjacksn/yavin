# Yavin

Requires Python 3.6 (because [f-strings][]).

[f-strings]: https://docs.python.org/3.6/reference/lexical_analysis.html#f-strings

Install with `pip`:

    pip install https://github.com/williamjacksn/yavin/archive/master.zip

This will add the `yavin` command to your path.

Copy `example-settings.py` to `settings.py` and edit for your environment. Set the environment variable
`YAVIN_SETTINGS_FILE` to the path to `settings.py`, then launch with `yavin`.

## Docker

1. Copy `example-settings.py` to `settings.py` and edit for your environment; leave `PORT = 8080`
2. Launch with `docker-compose up`
