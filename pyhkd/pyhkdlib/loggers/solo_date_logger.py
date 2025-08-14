'''
Logs values for a single sensor in a date-based folder structure
'''

import time
import urllib.request, urllib.parse, urllib.error
import datetime
import os
import logging
import numpy as np

try:
	from numpy import nanmedian
except ImportError:
	# Older version
	from scipy.stats import nanmedian

from .logger import Logger

class SoloDateLogger(Logger):

	# base_folder: location of the date-sorted log structure
	# sensor_type: string name of the sensor type (used for folder names)
	def __init__(self, base_folder, sensor_type, sensor_name, alias = None, downsample = 1):
		
		assert downsample >= 1, "The downsample value must be >=1 samples, was given " + str(downsample)
		assert int(downsample) == downsample, "The downsample factor should be an integer number of samples, was given " + str(downsample)

		self._sensor_type = sensor_type
		self._sensor_name = sensor_name
		self._base_folder = base_folder
		self._fileobj = None
		
		self._downsample = int(downsample)
		self._buffer = [0]*self._downsample
		self._next_buf = 0
		
		# Switch to the median if we have enough values (to exclude
		# large outliers)
		if self._downsample < 6:
			self._ds_func = np.nanmean
		else:
			self._ds_func = nanmedian
			
		# Escape special chars
		self._esc_sensor_type = urllib.parse.quote(str(sensor_type))
		self._esc_sensor_name = urllib.parse.quote(str(sensor_name))
		if alias is not None:
			self._alias = urllib.parse.quote(str(alias))
		else:
			self._alias = None
			
		self._open_current_file()
	
	def __del__(self):
					
		if self._fileobj is not None:
			self._fileobj.close()
			
	def _open_current_file(self):
		
		d = datetime.date.today()
		self._last_filename_update = d
		
		self._filedir = os.path.join(self._base_folder, 
									 "%04d" % d.year,
									 "%02d" % d.month,
									 "%02d" % d.day,
									 self._esc_sensor_type)
		
		try:
			os.makedirs(self._filedir)
		except OSError:
			pass
		
		self._filename = os.path.join(self._filedir,
									  self._esc_sensor_name + ".txt")
									 
		if self._fileobj is not None:
			self._fileobj.close()
		
		try:
			# Open in text mode with line buffering
			self._fileobj = open(self._filename, 'a', buffering=1)
			logging.info("Opening log file: " + self._filename)
		except OSError:
			self._fileobj = None
			logging.info("Failed to open log file: " + self._filename)
		
		if self._alias is not None:
			self._filename_alias = os.path.join(self._filedir, self._alias + ".txt")
			try:
				os.symlink(self._esc_sensor_name + ".txt", self._filename_alias)
			except OSError:
				pass

	# Implements Logger.log, see base class for argument descriptions
	def log(self, sensor_name, sensor_type, value, update_time, sync_num = None):
		
		# This logger only deals with a single sensor, so make sure
		# it isn't being used globally.  The name may have an extension
		# (e.g. ".fast"), so allow some freedom there.
		assert self._sensor_name.startswith(sensor_name) and (sensor_type == self._sensor_type), "SoloDateLogger was provided data for (%s, %s), but it is expecting only (%s, %s)" % (sensor_name, sensor_type, self._sensor_name, self._sensor_type)
		
		# "None" causes some issues with numpy functions
		if value is None:
			value = np.nan
		
		# Downsample if need be
		if self._downsample > 1:
			
			self._buffer[self._next_buf] = value
			self._next_buf += 1
			
			if self._next_buf >= self._downsample:
				
				# Full buffer, compute value and process with this
				# update time and sync number
				self._next_buf = 0
				try:
					value = self._ds_func(self._buffer)
				except:
					logging.error("Failed on buffer " + repr(self._buffer))

			else:
				# Not a full buffer, don't record the data yet
				return

		# Make sure we don't need to open a new file
		if self._last_filename_update != datetime.date.today() or self._fileobj is None:
			self._open_current_file()
		
		to_write = '%.3f\t' % (update_time,)
		
		try:
			to_write += '%0.8g' % value
		except TypeError:
			to_write += str(value)
		
		if sync_num is not None:
			to_write += '\t%i' % (sync_num,)	
			
		to_write += '\n'
		
		if self._fileobj is not None:
			self._fileobj.write(to_write)

