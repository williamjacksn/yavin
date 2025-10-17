import signal
import sys
import types

import notch

from . import app


def handle_sigterm(_signal: int, _frame: types.FrameType) -> None:
    sys.exit()


def main() -> None:
    notch.configure()
    signal.signal(signal.SIGTERM, handle_sigterm)
    app.main()


if __name__ == "__main__":
    main()
