import signal
import sys
import types

import notch


def handle_sigterm(_signal: int, _frame: types.FrameType | None) -> None:
    sys.exit()


def main() -> None:
    # Imported lazily so other console scripts (e.g. `playlist`) don't pull in
    # the Flask app and its database connection.
    from . import app

    notch.configure()
    signal.signal(signal.SIGTERM, handle_sigterm)
    app.main()


if __name__ == "__main__":
    main()
