import signal
import sys
import types

import notch

import yavin.app

notch.configure()


def handle_sigterm(_signal: int, _frame: types.FrameType) -> None:
    sys.exit()


signal.signal(signal.SIGTERM, handle_sigterm)
yavin.app.main()
