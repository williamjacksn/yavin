import logging
import os
import yavin.yavin

logging.basicConfig(format='[%(levelname)s] %(message)s', level=os.environ.get('LOGLEVEL', 'DEBUG'))
yavin.yavin.main()
