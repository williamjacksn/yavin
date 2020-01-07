import yavin.app
import signal
import sys


def handle_sigterm(_signal, _frame):
    sys.exit()


signal.signal(signal.SIGTERM, handle_sigterm)
yavin.app.main()
