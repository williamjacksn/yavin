import yavin.yavin
import signal
import sys


def handle_sigterm(_signal, _frame):
    sys.exit()


signal.signal(signal.SIGTERM, handle_sigterm)
yavin.yavin.main()
