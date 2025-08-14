

import os

##### pyhkweb settings #####

VERSION_STR = 'v3.0'
USER_DB_FILENAME = './data/users.pkl'
APP_LOG_FILENAME = '/var/log/pyhk/pyhkweb.log'
APP_LOG_FORMAT = '[%(asctime)s] %(levelname)s: %(message)s'
CACHE_DIR = '/data/hk/webcache'
SECRET_KEY_FILE = '/data/hk/webkey'
COMMON_CODE_DIR = os.path.abspath(os.path.join(__file__,'..','..','..','common'))

# Make sure the folders exists
for f in [CACHE_DIR]:
	try: 
		os.makedirs(f)
	except OSError:
		if not os.path.isdir(f):
			raise
