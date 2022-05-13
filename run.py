import notch
import signal
import sys
import yavin.app

log = notch.make_log('yavin-entrypoint')

def handle_sigterm(_signal, _frame):
    sys.exit()


signal.signal(signal.SIGTERM, handle_sigterm)
yavin.app.main()
