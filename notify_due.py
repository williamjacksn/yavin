import logging
import os
import yavin.notify

logging.basicConfig(format='[%(levelname)s] %(message)s', level=os.environ.get('LOGLEVEL', 'DEBUG'))
yavin.notify.main()
