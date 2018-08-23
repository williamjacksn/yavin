import yavin.yavin
import signal
import sys


def handle_sigterm():
    sys.exit()


signal.signal(signal.SIGTERM, handle_sigterm)
yavin.yavin.main()
