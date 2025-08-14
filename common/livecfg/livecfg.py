'''
Helper class for managing a json configuration file that can 
be watched and edited by multiple separate processes.  Currently
requires a unix-like system.
'''



import os
import json
import fcntl
import logging
import traceback

from collections import OrderedDict

class FileLock:
	
	def __init__(self, f, write=False):
		self.f = f
		self.write = write

	def __enter__(self):
		
		if self.write:
			# Get a write lock
			logging.debug("Waiting for write lock...")
			fcntl.flock(self.f, fcntl.LOCK_EX)
			logging.debug("Write lock acquired!")
		else:
			# Get a read lock
			logging.debug("Waiting for read lock...")
			fcntl.flock(self.f, fcntl.LOCK_SH)
			logging.debug("Read lock acquired!")
			
	def __exit__(self, type, value, traceback):
		
		# Release the lock
		fcntl.flock(self.f, fcntl.LOCK_UN)
		
		if self.write:
			logging.debug("Write lock released!")
		else:
			logging.debug("Read lock released!")

class LiveCfg:
	
	def __init__(self, fname):
		self._fname = str(fname)
		self._lastmtime = None
	
	# Overwrite the current config file with a serilized version
	# of 'obj'.  This function will block until an exlusive file
	# lock can be obtained.
	def dump(self, obj):
		
		if self._fname is None:
			logging.error("No live config file name specified")
			return
			
		dirname = os.path.abspath(os.path.dirname(self._fname))
		if not os.path.exists(dirname):
			os.makedirs(dirname)
		
		with open(self._fname, 'w') as f:
			with FileLock(f, write=True):
				try:
					json.dump(obj, f, indent=4)
					logging.debug("Updated live config file: " + self._fname)
				except (ValueError, TypeError):
					logging.error(str(traceback.format_exc()).rstrip())
					logging.error("Contained error while saving config file: " + self._fname)
	
	# Load a live config file and returns the results as python objects.
	# Returns None on failure. This function will block until a shared 
	# file lock can be obtained.
	def load(self):
		
		if self._fname is None:
			logging.error("No live config file name specified")
			return None
			
		to_return = None
		
		# Create the file if it doesn't exist
		if not os.path.exists(self._fname):
			with open(self._fname, 'a'):
				pass
		
		with open(self._fname, 'r') as f:
		
			with FileLock(f, write=False):

				self._lastmtime = os.path.getmtime(self._fname)
				
				try:
					to_return = json.load(f, object_pairs_hook=OrderedDict)	
					logging.debug("Loaded live config file: " + self._fname)
				except (ValueError, TypeError):
					to_return = None
					logging.error(str(traceback.format_exc()).rstrip())
					logging.error("Contained error while loading config file: " + str(self._fname))

			return to_return
			
	# Returns True iff the config file was modified since the last
	# time we read it.  
	def wasModified(self):
		
		if self._fname is None:
			logging.error("No live config file name specified")
			return False
		
		if not os.path.exists(self._fname):
			logging.error("Live config file doesn't exist: " + self._fname)
			return False
			
		return (self._lastmtime != os.path.getmtime(self._fname))
