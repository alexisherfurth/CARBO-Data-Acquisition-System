'''
A set of functions to facilitate loading data saved by pyhkfridge
'''



import datetime
import time
import logging
import os
import threading
import urllib.request, urllib.parse, urllib.error

from pyhkfridgeremote.settings import FRIDGE_STATE_BASE_FOLDER

# Return the file name the fridge log
def pyhkfridge_get_log_filename(base_folder_location, target_date, port):
	return os.path.join(base_folder_location, 
						"%04d" % target_date.year,
						"%02d" % target_date.month,
						"%02d" % target_date.day,
						"fridge",
						"log_" + urllib.parse.quote(str(port)) + ".txt")

# Return the folder for the fridge state variable files
def pyhkfridge_get_state_folder(base_folder_location, port):
	return os.path.join(base_folder_location, 'port_' + str(port))

# Return the current value of a fridge state variable
def pyhkfridge_get_state(port, varname, multi_line=False):
	fn = pyhkfridge_get_state_folder(FRIDGE_STATE_BASE_FOLDER, port)
	fn = os.path.join(fn, urllib.parse.quote(varname))
	if os.path.exists(fn):
		with open(fn, 'r') as f:
			if multi_line:
				return f.read()
			else:
				return f.readline()
	return 'Error! File Not Found: %s' % fn
	
# Return the file modification time of a fridge state variable,
# or None if it doesn't exisit
def pyhkfridge_get_state_mtime(port, varname):
	fn = pyhkfridge_get_state_folder(FRIDGE_STATE_BASE_FOLDER, port)
	fn = os.path.join(fn, urllib.parse.quote(varname))
	if os.path.exists(fn):
		return os.path.getmtime(fn)
	return None
	
# Returns the absolute path of the default fridge script folder
def pyhkfridge_get_script_dir():
	pyhk_main_dir = os.path.abspath(os.path.join(__file__,'..','..','..'))
	return os.path.join(pyhk_main_dir,'pyhkfridge','scripts')
