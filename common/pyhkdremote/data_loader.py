'''
A set of functions and classes designed to facilitate loading data
saved by pyhkd
'''



import datetime
import time
import logging
import os
import threading
import urllib.request, urllib.parse, urllib.error
import numpy as np
	
# Returns the lastest (timestamp, value) tuple for a given sensor on the
# given target date. If target_date == None, the function will attempt 
# to return the most recent relevant value by checking today and 
# yesterday, returning (None, None) on failure.
def pyhkd_get_latest(base_folder_location, subfolder_label, value_name, target_date=None, return_as_datetime=True):
	
	if target_date is None:
		
		target_date = datetime.datetime.today()
		ts,val = pyhkd_get_latest(base_folder_location, subfolder_label, value_name, target_date, return_as_datetime)
		
		if ts is None:
			# Try yesterday in case we just passed midnight
			target_date -= datetime.timedelta(days=1)
			ts,val = pyhkd_get_latest(base_folder_location, subfolder_label, value_name, target_date, return_as_datetime)
			
		return (ts,val)
	
	fn = pyhkd_get_filename(base_folder_location, subfolder_label, value_name, target_date)
	line = get_last_line(fn)
	return extract_data(line, return_as_datetime)
	
# Returns a list of values stored on a particular date in a subfolder.
# Returns None if it fails (the subfolder doesnt exist).
# Returns [] if the subfolder exists but is empty.
def pyhkd_get_names(base_folder_location, subfolder_label, target_date):
	
	dirname = pyhkd_get_subfolder(base_folder_location, subfolder_label, target_date)
	
	if (dirname is None) or (not os.path.exists(dirname)):
		return None
	
	l = []
	for f in os.listdir(dirname):
		if f.endswith(".txt"): 
			l.append(urllib.parse.unquote(f[0:-4]))
	l.sort()
	return l
		
	
# Get the subfolder for a particular data and type
def pyhkd_get_subfolder(base_folder_location, subfolder_label, target_date):
	return os.path.join(base_folder_location, 
						"%04d" % target_date.year,
						"%02d" % target_date.month,
						"%02d" % target_date.day,
						urllib.parse.quote(str(subfolder_label)))
						
# Return the file name for a given value
def pyhkd_get_filename(base_folder_location, subfolder_label, value_name, target_date):
	return os.path.join(pyhkd_get_subfolder(base_folder_location, subfolder_label, target_date),
						urllib.parse.quote(str(value_name)) + ".txt")	


# Returns the absolute path of the default live config folder
def pyhkd_get_config_dir():
	file_dir = os.path.dirname(os.path.realpath(__file__))
	pyhk_main_dir = os.path.abspath(os.path.join(file_dir,'..','..'))
	return os.path.join(pyhk_main_dir,'pyhkd','config','autogen')

# A function for getting just the last newline-terminated line of given file.
# Returns '' if the file doesn't exist or if there isn't a newline terminated
# line.
def get_last_line(filename):
	
	filename = str(filename)
	if os.path.exists(filename):
	
		with open(filename, 'rb') as f:

			try:
				# Prepare to read the second to last byte
				f.seek(-1,os.SEEK_END)
			except IOError:
				# There is <= 1 byte in the file.  It is either a newline
				# or it is something that isn't newline terminated, either
				# way the return value is an empty string
				return ''
			
			# Read backwards until we find the terminating newline
			while f.read(1) != b'\n':
				if f.tell() > 1:
					f.seek(-2, os.SEEK_CUR)
				else:
					# We never found it
					return ''
			
			# Make sure there is more file behind the terminating newline
			if f.tell() <= 1:
				return ''
			f.seek(-2, os.SEEK_CUR)
			
			# Read backwards until we find the newline of the line above
			while f.read(1) != b'\n':
				
				if f.tell() > 1:
					f.seek(-2, os.SEEK_CUR)
				else:
					# There is only one line, go to the beginning
					f.seek(0, os.SEEK_SET)
					break
					
			# Read the last line
			return f.readline().decode()
		
	return ''
	
# Extracts data from a log file line.  Returns a (datetime, float) or
# (float, float) if it succeeds, and returns (None, None) otherwise.
def extract_data(line, return_as_datetime = True):
	if line != '' and line != None:
		try:
			line_split = str(line).rstrip().split("\t")
			if return_as_datetime:
				timestamp = datetime.datetime.fromtimestamp(float(line_split[0]))
			else:	
				timestamp = float(line_split[0])
			if line_split[1].lower() in ['none', 'null']:
				value = None
			else:
				value = float(line_split[1])
			return (timestamp, value)
		except (ValueError, IndexError):
			return (None, None)
	return (None, None)

# A class for loading live file data and passing it to
# a callback function as the data is written
class DataLoader(object):
	
	# base_folder_location: base folder for HK data storage
	# subfolder_label: subfolder used for value_names
	# value_names: list of names you want to monitor
	# callback: a function that is passed any data loaded by load_**
	# 			Must accept three arguments:
	# 			  index: the index for the value name this corresponds to
	# 			  t_data: a list of datetimes
	# 			  y_data: a list of floats (same length as t_data)	
	def __init__(self, base_folder_location, subfolder_label, value_names, callback):
		
		self._base_folder_location = base_folder_location
		self._subfolder_label = subfolder_label
		self._value_names = value_names
		self._callback = callback
		
		self._live_update_thread = None
		self._live_update_lock = threading.Lock()
		self._live_update_running = False 
		
		self._NUM_VALUES = len(value_names)
		self._files = [None]*len(value_names)
		self._open_current_files()
			
	# Loads and sends all data from date_start to now (inclusive)
	# and sends any new data added from a separate thread.  If 
	# updates are currently being send from a previous load_***_live
	# call, stop them.
	def load_archived_live(self, date_start):
		self.stop_live()
		self._send_archived(date_start,  datetime.date.today())
		self._send_live()
		
	# Loads and sends all data from date_start to date_stop (inclusive).
	# If updates are currently being send from a previous load_***_live
	# call, stop them.
	def load_archived(self, date_start, date_stop):
		self.stop_live()
		self._send_archived(date_start, date_stop)
		
	# Sends any new data added from a separate thread.  If 
	# updates are currently being send from a previous load_***_live
	# call, stop them.
	def load_live(self):
		self.stop_live()
		self._send_live()
	
	# If updates are currently being send from a previous load_***_live
	# call, stop them.
	def stop_live(self):
		
		# Ask the thread to stop
		#logging.debug("Waiting for thread lock...")
		with self._live_update_lock:
			if self._live_update_running == True:
				self._live_update_running = False
		
		# Wait for it to finish
		#logging.debug("Waiting to join thread...")
		if self._live_update_thread != None:
			self._live_update_thread.join()
			self._live_update_thread = None
	
	# Update the current open files for everything we are watching
	def _open_current_files(self):
		d = datetime.date.today()
		self._current_filenames = [pyhkd_get_filename(self._base_folder_location, self._subfolder_label, vn, d) for vn in self._value_names]
		self._last_filename_update = d
		
		for i in range(len(self._files)):
			self._open_file(i)
	
	# Open self._current_filenames[index].  Returns True if it succeeds,
	# False otherwise.
	def _open_file(self, index):
		if self._files[index] != None:
			self._files[index].close()
		if os.path.exists(self._current_filenames[index]):
			self._files[index] = open(self._current_filenames[index], 'r')
			#logging.debug("Data logger opening file " + str(self._current_filenames[index]))
			return True
		else:
			self._files[index] = None
			return False
				
	# Send a multiple day's worth of data for each value
	def _send_archived(self, date_start, date_end):
		date_to_send = date_start
		while (date_to_send <= date_end):
			self._send_archived_single(date_to_send)
			date_to_send += datetime.timedelta(days=1)
		
	# Send a single day's worth of data for each value
	def _send_archived_single(self, date_to_send):
		
		for i in range(self._NUM_VALUES):

			fn = pyhkd_get_filename(self._base_folder_location, self._subfolder_label, self._value_names[i], date_to_send)
			
			if os.path.exists(fn):
				
				logging.info("Loading log file " + str(fn))
				try:
					data_t_float, data_y = np.loadtxt(fn, unpack=True, ndmin=2)
					data_t = [datetime.datetime.fromtimestamp(data_t_float[j]) for j in range(len(data_t_float))]
					self._callback(i, data_t, data_y.tolist())
				except (ValueError, TypeError):
					logging.error('Unabled to extract data from file ' + str(fn) + ' (could be empty?)')
		
		
	# Starts a new thread on the live file monitoring.  Only sends
	# new data, no exisiting data.
	def _send_live(self):
		
		self.stop_live()
		with self._live_update_lock:
			self._live_update_thread = threading.Thread(target = self._live_update_mainloop, name="Live File Mon")
			self._live_update_thread.daemon = True # Don't let this thread keep the program alive
			self._live_update_running = True 
			self._live_update_thread.start()
		
		
	# Main loop for live file monitoring.  Dies when _live_update_running = false.
	def _live_update_mainloop(self):
		
		logging.debug("Live update loop starting in thread " + str(threading.current_thread().ident))	
		
		with self._live_update_lock:
			
			# Check if the day changed
			if (datetime.date.today() != self._last_filename_update):
				self._open_current_files()
				
			# Move to the end of the file so we only send new data
			for i in range(self._NUM_VALUES):
				if self._files[i] is not None:
					self._files[i].seek(0,os.SEEK_END)
		
		while True:
			
			with self._live_update_lock:
				
				if not self._live_update_running:
					break
				
				# Check if the day changed
				if (datetime.date.today() != self._last_filename_update):
					self._open_current_files()
					
				anything_read = False
					
				# Check for updates
				for i in range(self._NUM_VALUES):
					
					if not self._live_update_running:
						anything_read = True
						break
					
					if self._files[i] is None:
						# Try to load it again in case it wasn't
						# there before
						if not self._open_file(i):
							# Give up
							continue
					
					line = self._files[i].readline()
					
					if line != '':
						timestamp, value = extract_data(line)
						
						if (timestamp is not None) and (value is not None):
							self._callback(i, [timestamp], [value])
							anything_read = True
						else:
							logging.error("Error reading line in file " + str(self._current_filenames[i]))				
						
			# Let's not spin our wheels, wait for some new data
			if not anything_read:
				time.sleep(0.3)
	
		logging.debug("Live update loop stopping in thread " + str(threading.current_thread().ident))
		
