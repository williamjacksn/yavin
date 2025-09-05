import signal
import sys

import notch

import yavin.app

notch.configure()


def handle_sigterm(_signal, _frame):
    sys.exit()


signal.signal(signal.SIGTERM, handle_sigterm)
yavin.app.main()
