'''
This is a common base class for instruments that have some number
of sensors.

Usage:
	- Inherit from Instrument
	- Redefine NUM_SENSORS, BOX_NAME
	- Implement update()
	- All sensor names must be globally unique
'''

import numpy as np
import time
import sys
import logging

from ..sensor import Sensor
from calib.helpers import get_calib
import units.units as units
		
class Instrument:
	
	NUM_SENSORS = 0
	BOX_TYPE = 'GENERIC'	
	
	VALID_CHAN_KEYS = ['calib_func','name','type','alias','id','save_deriv','save_fast','downsample','r_total','r_heater','current_limit','output_range','filter']
	REQUIRED_CHAN_KEYS = ['name']
				
	# 'channels'				A list (length NUM_SENSORS) of dicts, one per sensor.  Stores per-channel
	#							constant data.  Must include a "name" field with a globally unique name.
	# 'default_sensor_type' 	A single Sensor.TYPE_??? to use as the default if "type" isn't specified in channels.

	# 'default_calib_func'		Default raw conversion function to use if "calib_func" isn't in channels
	# 'default_downsample'		Number of real samples to buffer and combine into one actual update. 
	#							If raw sensors are used, those are what are buffered.  1 means no buffer,
	#							all new values should be reported individually.
	def __init__(self, channels=[], default_sensor_type = Sensor.TYPE_UNUSED, 
		default_calib_func = (lambda x: 0), default_downsample = 1, 
		default_save_deriv = False, default_save_fast = False,
		verbose_rx=False, verbose_tx=False, verbose_fail=True,
		verbose_raw=False, wait_time=10):
		
		assert isinstance(channels, list), "The 'channels' input should be a list (instrument type: %s)" % self.BOX_TYPE
		assert (len(channels) == self.NUM_SENSORS), "The number of channels specified does not match expectectations for this instrument (instrument type: %s)" % self.BOX_TYPE
		
		assert isinstance(verbose_fail, bool), "verbose_fail should be a boolean value (not a string or number)"
		assert isinstance(verbose_rx, bool), "verbose_rx should be a boolean value (not a string or number)"
		assert isinstance(verbose_tx, bool), "verbose_tx should be a boolean value (not a string or number)"
		assert isinstance(verbose_raw, bool), "verbose_raw should be a boolean value (not a string or number)"
		
		assert (np.isfinite(wait_time) and wait_time >= 0), "wait_time should be a positive number"

		self.verbose_fail = verbose_fail
		self.verbose_rx = verbose_rx
		self.verbose_tx = verbose_tx
		self.verbose_raw = verbose_raw
		
		self.wait_time = wait_time
		
		self._default_downsample = default_downsample
		self._default_calib_func = default_calib_func
		self._default_save_deriv = default_save_deriv
		self._default_save_fast = default_save_fast
		self._default_sensor_type = default_sensor_type
		
		# A dict of channel configurations, indexed by channel ID
		# (which can be a number or a string).  
		# Access with get_channel()
		self._channels = {}

		# A dict of sensors indexed by (chan_id, sensor_type)	
		# Access with get_sensor()
		self._sensors = {}
		
		self.sensor_ids = []
		
		# Name indexed
		self.lookup_id = {}
		self.lookup_typelist = {}
		
		id_all = True
		id_none = True
		
		for ci in range(len(channels)):
			
			chan = channels[ci]
			
			# Verify we have the keys needed
			for kn in self.REQUIRED_CHAN_KEYS:
				if kn not in chan.keys():
					sys.exit('The channel key "%s" is required but not found in the following channel definition: %s' % (kn, str(chan)))
			
			c_name = chan['name']
			c_types = chan.get('type', default_sensor_type)
			c_alias = chan.get('alias', None)
			c_id = chan.get('id', None)
			c_save_deriv = chan.get('save_deriv', default_save_deriv)
			c_save_fast = chan.get('save_fast', default_save_fast)
			c_ds = chan.get('downsample', default_downsample)
			c_filt = chan.get('filter', 1.0)
			
			try:
				c_filt = float(c_filt)
				assert (c_filt >= 0 and c_filt <= 1.0)
			except:
				sys.exit("The channel parameter 'filter' must be a value in the range [0,1].  See the documentation for details.")
			
			# Default to using the position index
			if c_id is None:
				c_id = ci
				id_all = False
			else:
				id_none = False
			
			if 'type_raw' in list(chan.keys()):
				sys.exit("type_raw has been removed.  Multi-types such as thermometer-resistor replace this functionality.  See the documentation for details.")
			if 'type_deriv' in list(chan.keys()):
				sys.exit("type_deriv has been removed.  Use the save_deriv boolean flag instead.  See the documentation for details.")
				
			# Check for extra keys (likely typos the user isn't aware of)
			for k in list(chan.keys()):
				if k not in self.VALID_CHAN_KEYS:
					sys.exit("Invalid key '%s' specified for channel '%s'." % (k, c_name))
			
			if c_id in self.sensor_ids:
				sys.exit("Duplicate channel ID " + str(c_id) + " found in config for instrument of type " + str(self.BOX_TYPE) + ".  Sensors with multiple types should specify either a list of types or a multi-type designator.  See the documentation for details.")
				
			self.sensor_ids.append(c_id)

			# Check if this is high level shortcut type
			if c_types in Sensor.VALID_MULTI_TYPES:
				c_types = Sensor.MULTI_TYPE_LIST[c_types]

			# Check if the channel only has one data type
			if not isinstance(c_types, list):
				c_types = [c_types]
			
			if len(c_types) < 1:
				sys.exit("No type or default_type found for channel '%s'" % (c_name))
			
			# Save for later use
			chan['types_processed'] = c_types
			
			for c_type in c_types:
			
				if c_type not in Sensor.VALID_TYPES:
					sys.exit("Bad sensor type: " + str(c_type))
					
				sen = Sensor(c_name, c_type, alias=c_alias, downsample=c_ds, save_fast=c_save_fast, save_deriv=c_save_deriv, filt=c_filt)
				
				self._sensors[(c_id, c_type)] = sen
			
			c_calib = chan.get('calib_func', None)
				
			if c_calib is None or c_calib == "default" or c_calib == "":
				# Nothing specified
				chan['calib_func'] = default_calib_func
			elif callable(c_calib):
				# It is already a function
				pass
			else:
				# Try to find the function by name.
				loaded_func = get_calib(c_calib, raise_on_fail=True)
					
				chan['calib_func'] = loaded_func
			
			self._channels[c_id] = chan
			
			self.lookup_id[c_name] = c_id
			self.lookup_typelist[c_name] = c_types
		
		assert (id_all or id_none), "Channel IDs must be provided for either all channels or no channels within an instrument (type %s)" % self.BOX_TYPE
		
		# Read-in timing
		self.last_update_time = time.time()
		
	# Shut down any relevant resources
	def close(self):
		pass
		
	@property
	def default_downsample(self):
		return self._default_downsample
		
	# Return the channel configuration
	def get_channel(self, chan_id):
		return self._channels.get(chan_id, None)
		
	# Return a list of the processed basic types in a channel
	def get_channel_types(self, chan_id):
		return self.get_channel(chan_id)['types_processed']
	
	# Return the calibration function for a given channel
	def get_calib_func(self, chan_id):

		chan = self.get_channel(chan_id)
		
		if chan is None:
			return self._default_calib_func
			
		return chan.get('calib_func', self._default_calib_func)
	
	# Return the sensor of a given type from the given channel.
	# This is the preferred way to access sensor objects.
	def get_sensor(self, chan_id, chan_type, none_on_fail = False):
		
		s = self._sensors.get((chan_id, chan_type), None)
		
		if not none_on_fail:
			
			if s is None:
				# Instruments may expect a sensor object at a given name
				# that has been disabled in the config file.  Check for 
				# this case so we don't warn the user about an error.
				s = self._sensors.get((chan_id, Sensor.TYPE_UNUSED), None)
			
			# Check again
			if s is None:
				# The sensor *still* isn't there, so give an error message.
				# Return a dummy sensor so ignorant function calls work.
				s = Sensor(name="Missing Sensor") 
				logging.error("Sensor not found: id " + str(chan_id) + ", channel type " + str(chan_type) + ", box type " + str(self.BOX_TYPE) + " (valid keys: " + str(self._sensors.keys()) + ")")
				
		return s
		
	# Runs frequent instrument updates.
	# Typically called many times a second, but not guarenteed to
	# be called at a constant frequency. This function is not allowed 
	# to block for more than a fraction of a second.
	def update(self):
		
		# The default implementation is to occasionally call
		# update_periodic() with a period of wait_time.  Note
		# that subclasses that override update() will not 
		# automatically have access to update_periodic().
		if ((time.time() - self.last_update_time) < self.wait_time):
			return
		self.last_update_time = time.time()
		self.update_periodic()
	
	
	# Runs periodic instrument updates (with a period of wait_time).
	# This function is not allowed to block for more than a fraction of
	# a second.
	def update_periodic(self):
		pass
		
	# 'targets' is a set of target request dictionaries.  For example,
	# if your instrument had the ability to set a voltage, this
	# function would need to save a reference to the voltage target
	# dictionary so it can check for voltage target changes. Here
	# we save a reference to the shared targets dictionary and
	# create all the target tracking sensors we need for this 
	# instrument
	def connect_targets(self, targets):

		self.targets = targets
		
		# Register and target tracking sensors into the global
		# target dictionary
		for _, s in self._sensors.items():
			if s.sensor_type in Sensor.VALID_TARGET_TYPES:
				self.targets[s.sensor_type][s.name] = s
				if s.alias is not None:
					self.targets[s.sensor_type][s.alias] = s
					
	# Add an external logger to all sensors in addition to the internal ones
	def add_logger(self, l):
		for s in list(self._sensors.values()):
			s.add_logger(l)
