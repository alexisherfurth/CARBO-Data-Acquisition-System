import os

##### pyhkd settings #####

VERSION_STR = 'v3.0'
DATA_LOG_FOLDER = '/data/hk'
APP_LOG_BASE_FOLDER = '/var/log/pyhk'
APP_LOG_FILENAME = 'pyhkd.log'
APP_LOG_FORMAT = '[%(asctime)s] %(levelname)s: %(message)s'
RECV_PORT = 7945
PYHKD_PROCNAME = 'pyhkd'
COMMON_CODE_DIR = os.path.abspath(os.path.join(__file__,'..','..','..','common'))

# Make sure the folders exists
for f in [DATA_LOG_FOLDER, APP_LOG_BASE_FOLDER]:
	try: 
		os.makedirs(f)
	except OSError:
		if not os.path.isdir(f):
			raise
