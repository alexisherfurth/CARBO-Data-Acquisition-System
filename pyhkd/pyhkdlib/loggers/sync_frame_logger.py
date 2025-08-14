'''
Logs a specified subset of sensors at each sync number frame
'''

import time
import datetime
import os
import logging
import numpy as np
import gzip
import threading
import glob

from .logger import Logger

class SyncFrameLogger(Logger):
	
	FILE_PREFIX = 'syncframes.'
	FILE_SUFFIX = '.npy'
	
	# channels: 	List of channels, each a dict with a name and a type key/
	#				The order of the list determines the index in the output.
	# num_reported: Number of sensors to report per frame
	# frame_count: 	Number of sync frames per output file
	# buffer_count: Number of output files to buffer before writing to 
	#				disk (to make sure late arrivals are stored properly)
	def __init__(self, base_folder, channels, num_reported=256, frame_count=100, buffer_count=5, max_files=100):
		
		assert (num_reported > 0) and (num_reported == int(num_reported)), "num_reported should be a postive integer for SyncFrameLogger"
		assert len(channels) <= num_reported, "More channels are specified than allowed by num_reported for SyncFrameLogger"
		
		# Make sure the folder exists
		try: 
			os.makedirs(base_folder)
		except OSError:
			if not os.path.isdir(base_folder):
				raise
		
		# Cache the index for each sensor
		self._indexes = {}
		for i in range(len(channels)):
			c = channels[i]
			assert 'type' in c.keys(), "All SyncFrameLogger channels must have a type"
			assert 'name' in c.keys(), "All SyncFrameLogger channels must have a name"
			key = (c['name'],c['type'])
			assert key not in self._indexes.keys(), "Repeated SyncFrameLogger channel: " + str(key)
			self._indexes[key] = i

		self._base_folder = base_folder
		self._lock = threading.Lock()
		
		self._frame_count = frame_count
		self._buffer_count = buffer_count
		self._num_reported = num_reported
		self._max_files = max_files
		
		self._base_sync = None
		self._file_shape = (self._frame_count, self._num_reported)
		self._file_stack = [np.full(self._file_shape, np.nan) for i in range(self._buffer_count)]
		
		self._file_pattern = os.path.join(self._base_folder, self.FILE_PREFIX + "*" + self.FILE_SUFFIX)
		
		# Clear out any old files
		for f in glob.glob(self._file_pattern):
			os.remove(f)

	# Save the oldest buffer to a file, add a new empty buffer. 
	# Assumes the caller holds self._lock
	def _save_oldest(self):
		
		# Save the oldest buffered file
		fname = os.path.join(self._base_folder, self.FILE_PREFIX + str(self._base_sync) + self.FILE_SUFFIX)
		logging.debug("Saving sync frame log for base " + str(self._base_sync))
		np.save(fname, self._file_stack.pop(0))
		self._file_stack.append(np.full(self._file_shape, np.nan))
		self._base_sync += self._frame_count
	
		# Keep only the newest N files
		file_names = glob.glob(self._file_pattern)
		num_remove = len(file_names) - self._max_files
		if num_remove > 0:
			file_ctimes = [os.path.getctime(f) for f in file_names]
			to_remove = np.argsort(file_ctimes)[:num_remove]
			for f in to_remove:
				try:
					os.remove(file_names[f])
				except OSError:
					logging.debug("Failed to delete file " + str(file_names[f]))
					pass
	
	# Return the base sync number which puts the value provided in
	# the newest buffer, or 0 at minimum
	def _compute_base(self, sync_num):
		b = int(((sync_num // self._frame_count) - (self._buffer_count - 1)) * self._frame_count)
		return max(b, 0)
	
	# Implements Logger.log, see base class for argument descriptions
	def log(self, sensor_name, sensor_type, value, update_time, sync_num = None):
		
		# self._indexes is static after __init__() and doesn't need the
		# lock.  Taking the lock now would slow us down on sensors
		# that aren't logged here.
		sen_index = self._indexes.get((sensor_name, sensor_type), None)
		if sen_index is None:
			return		
		
		if sync_num is None:
			logging.warning("Failed to store value without sync number in SyncFrameLogger. Type: " + str(sensor_type) + " Name: " + str(sensor_name))
			return
			
		try:
			value = float(value)
		except:
			logging.warning("SyncFrameLogger failed to save non-float value for sensor " + str((sensor_name, sensor_type)) + ": " + str(value))
			return
			
		with self._lock:
			
			if self._base_sync is None:
				self._base_sync = self._compute_base(sync_num)
			
			delta = (sync_num - self._base_sync)
			
			# Index of the file buffer the sync num appears in.
			# The oldest file buffer is 0, the newest is 
			# self._buffer_count - 1.  The next new one to be added
			# is self._buffer_count.  Anything below 0 is too late to
			# save.
			buf = int(delta // self._frame_count)
			
			# Position offset within the buffer
			pos = int(delta % self._frame_count)
			
			if buf < -10:
				
				logging.info("SyncFrameLogger is rebasing to accomodate a far past sync number from sensor " + str((sensor_name, sensor_type)) + ": " + str(sync_num))
				
				for n in range(self._buffer_count):
					self._save_oldest()
				self._base_sync = self._compute_base(sync_num)
				
			elif buf < 0:
				
				logging.warning("SyncFrameLogger found an skipped a late sync number for sensor " + str((sensor_name, sensor_type)) + ": " + str(sync_num))
				return
				
			elif buf >= self._buffer_count:
				
				# Value is in a future buffer, figure out where
				num_to_flush = buf - self._buffer_count + 1
				
				# Save as many buffers as we need, but cap at saving
				# all of the buffers we have
				for n in range(min(num_to_flush, self._buffer_count)):
					self._save_oldest()
					
				# We flushed everything, rebase at the new sync num
				if num_to_flush > self._buffer_count:
					logging.info("SyncFrameLogger is rebasing to accomodate a far future sync number from sensor " + str((sensor_name, sensor_type)) + ": " + str(sync_num))
					self._base_sync = self._compute_base(sync_num)
				
			# Recompute in case we had to rebase
			buf = int((sync_num - self._base_sync) // self._frame_count)
		
			# Save
			self._file_stack[buf][pos,sen_index] = value
					
