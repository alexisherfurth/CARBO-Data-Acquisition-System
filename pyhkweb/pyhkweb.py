#!/usr/bin/env python3

'''
PyHK Viewer Web Server
'''

import sys
import logging

from pyhkweblib.settings import *
sys.path.append(COMMON_CODE_DIR)

# Configure logging
logging.basicConfig(filename=APP_LOG_FILENAME, format=APP_LOG_FORMAT, level=logging.DEBUG)
logging.info("Starting PyHK Web Viewer " + str(VERSION_STR))
screen_handler = logging.StreamHandler() 
screen_handler.setFormatter(logging.Formatter(APP_LOG_FORMAT))
logging.getLogger().addHandler(screen_handler)  # Print to screen as well

import checkdep # Verifies depenencies, comment out to override

import flask
import datetime
import os
import json5
import werkzeug
import numpy as np

from collections import OrderedDict

from pyhkweblib.cache import cache

# We don't change the secret key each boot so cookies aren't invalidated unexpectly
def load_secret():

	key = ''
	if os.path.exists(SECRET_KEY_FILE):
		with open(SECRET_KEY_FILE, 'rb') as f:
			key = f.read()
	if len(key) != 24:
		logging.info("No valid secret key found, generating new key")
		key = os.urandom(24)
		try:
		    os.remove(SECRET_KEY_FILE)
		except OSError:
		    pass
		with open(SECRET_KEY_FILE, 'wb') as f:
			f.write(key)
	else:
		logging.debug("Loaded existing secret key")

	return key

def app_factory(config_file):

	app = flask.Flask(__name__)
	app.secret_key = load_secret()
	
	# Template file conveniences
	app.jinja_env.line_statement_prefix = '%'
	app.jinja_env.line_comment_prefix = '##'
	app.jinja_env.globals.update(datetime_now=datetime.datetime.now)
	app.jinja_env.globals.update(timedelta=datetime.timedelta)
	app.jinja_env.add_extension('jinja2.ext.do')
	
	# Allow signed ints in urls
	class SignedIntConverter(werkzeug.routing.IntegerConverter):
		regex = r'-?\d+'
	app.url_map.converters['signed_int'] = SignedIntConverter
	
	# Load page config
	with open(config_file, 'r') as f:
		try:
			page_list = json5.load(f, object_pairs_hook=OrderedDict, allow_duplicate_keys=False)	
		except ValueError as e:
			logging.error("JSON5 Error: " + str(e).replace("<string>:", "Line "))
			sys.exit("Error while reading the config file!  Note that the JSON5 error printed above may not be the root cause of your syntax error, it may simply be a symptom.  Please check that your file is valid JSON5 data (valid JSON data is also valid JSON5 data, see json5.org).  Online JSON5 validators can be very helpful here (e.g. https://jsonformatter.org/json5-validator).  Note most validators will show one error at a time, and you may have multiple.")
		
	# Pull out the settings dummy page if present
	settings = {}
	for p in list(page_list):
		if p['page_type'] == 'internal_settings':
			settings.update(p)
			page_list.remove(p)
		elif 'page_title' not in p or 'page_title' not in p:
			page_list.remove(p)
			logging.error("Missing either page_type or page_title for page: " + str(p))
	
	# Force certain page types if the config file doesn't include them
	for forced_type in ['export', 'about']:
		if not np.any([p['page_type'] == forced_type for p in page_list]):
			page_list.append({'page_type': forced_type, 
							  'page_title': forced_type.capitalize()})
	
	# Store remaining page config
	page_ids = [page_list[i]['page_title'].lower().replace(' ','_').replace('/','') for i in range(len(page_list))] # URL friendly IDs
	page_config = {page_ids[i] : page_list[i] for i in range(len(page_list))} 
	app.config['page_ids'] = page_ids
	app.config['page_config'] = page_config
	app.config['internal_settings'] = settings
	
	# Data archive caching
	cache.init_app(app, config={'CACHE_TYPE': 'filesystem', 'CACHE_DIR': CACHE_DIR, 'CACHE_THRESHOLD': 1024, 'CACHE_DEFAULT_TIMEOUT': 60*60*24*30})
	
	# The main app definition lives in pyhk_blueprint
	from pyhkweblib.pyhk_blueprint import pyhkpage
	app.register_blueprint(pyhkpage)

	return app

if __name__ == '__main__':
	
	print("This code is intended to be used with Apache.  See the PyHK documentation for installation instructions.")

	#~ app = app_factory()
	#~ try:
		#~ app.run(host='0.0.0.0', port=443, debug=True, use_debugger=True, use_reloader=False, ssl_context='adhoc')	
		#~ app.run(host='0.0.0.0', port=80, debug=True, use_debugger=True, use_reloader=False)	
	#~ except socket.error:
		#~ print(str(traceback.format_exc()).rstrip())

