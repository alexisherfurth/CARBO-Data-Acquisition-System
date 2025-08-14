'''
This class let you store the current value of a single sensor.  The
values are logged to a file as they are updated.

Usage:
	- Initialize a Sensor
	- Set .value as desired, it will automatically be logged to a file

'''

import logging
import time
import numpy as np
import threading

from .loggers.solo_date_logger import SoloDateLogger
from .settings import DATA_LOG_FOLDER

# Used to store a value
class Sensor(object):
	
	# Regular sensors track the value of an input
	TYPE_UNUSED = 'unused'				# Don't save the results
	TYPE_FLOAT = 'float'				# Generic floating point number
	TYPE_STRING = 'string'				# Generic string
	
	TYPE_TEMPERATURE = 'temperature'   	# in Kelvin
	TYPE_VOLTAGE = 'voltage'	   		# in Volts
	TYPE_RESISTANCE = 'resistance'		# in Ohms
	TYPE_CURRENT = 'current'	  		# in Amps
	TYPE_CURRENTRAMP = 'currentramp'	# in Amps/s
	TYPE_POWER = 'power'		   		# in Watts
	TYPE_STATE = 'state'		   		# no units
	TYPE_BFIELD = 'bfield'		   		# in Tesla
	TYPE_PRESSURE = 'pressure'	   		# in Torr
	TYPE_RELHUMIDITY = 'relhumidity'  	# in %
	TYPE_ENERGY = 'energy'  			# in J
	TYPE_FREQUENCY = 'frequency'	   	# in Hz
	TYPE_TIME = 'time'				   	# in sec
	TYPE_NUMBER = 'number'			   	# no units
	TYPE_ADU = 'adu'			   		# ADU
	TYPE_DAC = 'dac'			   		# DAC
	TYPE_PERCENTAGE = 'percentage'  	# in %
	TYPE_FRACTION = 'fraction'			# no units
	TYPE_ANGLE = 'angle'				# in degrees
	TYPE_POSITION = 'position'			# in meters
	
	# Target sensors track the current requested value of an output
	TYPE_TARGET_VOLTAGE = 'vtarg'		# in Volts
	TYPE_TARGET_POWER = 'ptarg'			# in Watts
	TYPE_TARGET_TEMPERATURE = 'ttarg'	# in Kelvin
	TYPE_TARGET_OUTPUTMODE = 'outputmode'
	TYPE_TARGET_CURRENT = 'itarg'		# in Amps
	TYPE_TARGET_CURRENTRAMP = 'irtarg'	# in Amps/sec
	TYPE_TARGET_STATE = 'starg'	
	TYPE_TARGET_PERCENTAGE = 'percenttarg'	
	
	DERIV_SUFFIX = 'deriv'	
	
	VALID_TARGET_TYPES = [TYPE_TARGET_VOLTAGE, TYPE_TARGET_POWER, TYPE_TARGET_TEMPERATURE, TYPE_TARGET_OUTPUTMODE, TYPE_TARGET_CURRENT, TYPE_TARGET_CURRENTRAMP, TYPE_TARGET_STATE, TYPE_TARGET_PERCENTAGE]
	VALID_NONTARGET_TYPES = [TYPE_UNUSED, TYPE_FLOAT, TYPE_STRING, TYPE_TEMPERATURE, TYPE_VOLTAGE, TYPE_RESISTANCE, TYPE_CURRENT, TYPE_CURRENTRAMP, TYPE_POWER, TYPE_STATE, TYPE_BFIELD, TYPE_PRESSURE, TYPE_RELHUMIDITY, TYPE_ENERGY, TYPE_FREQUENCY, TYPE_TIME, TYPE_NUMBER, TYPE_ADU, TYPE_DAC, TYPE_FRACTION, TYPE_ANGLE, TYPE_POSITION, TYPE_PERCENTAGE]
	VALID_DERIV_TYPES = [name + 'deriv' for name in VALID_NONTARGET_TYPES]
	VALID_TYPES = VALID_TARGET_TYPES + VALID_NONTARGET_TYPES + VALID_DERIV_TYPES
	
	VALID_NOLOG_TYPES = [TYPE_UNUSED]
	
	# Sometimes a physical sensor has multiple outputs (ex: resistance
	# and temperature).  MULTI_TYPE names are use to indicate such
	# objects in config files.  Each output will be a separate instance
	# of the Sensor class - you cannot use a MULTI_TYPE as a Sensor type.
	MULTI_TYPE_HEATER = "heater"
	MULTI_TYPE_HEATER_P = "heater:setp"
	MULTI_TYPE_HEATER_P_I = "heater:setp:imon"
	MULTI_TYPE_HEATER_T_P_I = "heater:setpt:imon"
	MULTI_TYPE_HEATER_I = "heater:imon"
	MULTI_TYPE_IMON = "imon"
	MULTI_TYPE_THERM_DIODE = "thermometer:diode"
	MULTI_TYPE_THERM_DIODE_EXC = "thermometer:diode:exc"
	MULTI_TYPE_THERM_R = "thermometer:resistor"
	MULTI_TYPE_THERM_R_EXC = "thermometer:resistor:exc"
	
	MULTI_TYPE_LIST = 	{
		MULTI_TYPE_HEATER: [TYPE_VOLTAGE, TYPE_TARGET_VOLTAGE, TYPE_TARGET_OUTPUTMODE],
		MULTI_TYPE_HEATER_I: [TYPE_VOLTAGE, TYPE_TARGET_VOLTAGE, TYPE_CURRENT, TYPE_TARGET_OUTPUTMODE],
		MULTI_TYPE_HEATER_P: [TYPE_VOLTAGE, TYPE_POWER, TYPE_TARGET_OUTPUTMODE, TYPE_TARGET_VOLTAGE, TYPE_TARGET_POWER],
		MULTI_TYPE_HEATER_P_I: [TYPE_VOLTAGE, TYPE_CURRENT, TYPE_POWER, TYPE_TARGET_OUTPUTMODE, TYPE_TARGET_VOLTAGE, TYPE_TARGET_POWER],
		MULTI_TYPE_HEATER_T_P_I: [TYPE_VOLTAGE, TYPE_CURRENT, TYPE_POWER, TYPE_TEMPERATURE, TYPE_TARGET_OUTPUTMODE, TYPE_TARGET_VOLTAGE, TYPE_TARGET_POWER, TYPE_TARGET_TEMPERATURE],
		MULTI_TYPE_IMON: [TYPE_VOLTAGE, TYPE_CURRENT],
		MULTI_TYPE_THERM_DIODE: [TYPE_VOLTAGE, TYPE_TEMPERATURE],
		MULTI_TYPE_THERM_DIODE_EXC: [TYPE_VOLTAGE, TYPE_TEMPERATURE, TYPE_CURRENT, TYPE_POWER],
		MULTI_TYPE_THERM_R: [TYPE_RESISTANCE, TYPE_TEMPERATURE],
		MULTI_TYPE_THERM_R_EXC: [TYPE_RESISTANCE, TYPE_TEMPERATURE, TYPE_VOLTAGE, TYPE_CURRENT, TYPE_DAC]
	}
	
	VALID_MULTI_TYPES = list(MULTI_TYPE_LIST.keys())
	
	# Check for accidental type name duplication
	for t in VALID_MULTI_TYPES:
		assert (t not in VALID_TYPES)
	for t in VALID_NONTARGET_TYPES:
		assert (t not in VALID_TARGET_TYPES)
	for t in VALID_DERIV_TYPES:
		assert (t not in VALID_TARGET_TYPES)
				    
	def __init__(self, name = '', sensor_type = TYPE_UNUSED, alias = None, save_deriv = False, downsample = 1, save_fast = False, filt=1.0):
		
		assert(sensor_type in self.VALID_TYPES)
		if save_deriv:
			assert(sensor_type in self.VALID_NONTARGET_TYPES)
		assert(downsample >= 1)
		assert(len(name) > 0)
		assert(filt >= 0 and filt <= 1)
		
		# Don't downsample targets
		if sensor_type in self.VALID_TARGET_TYPES:
			downsample = 1
				
		self._name = name
		self._alias = alias
		self._sensor_type = sensor_type
		self._value = float('NaN')
		self._last_update_time = 0
		self._save_deriv = save_deriv
		self._save_fast = save_fast
		self._filt = filt

		self._last_sync_num = None
		
		self._loggers = []
		
		if self._sensor_type not in self.VALID_NOLOG_TYPES:
			
			# Main output, downsampled data
			self._loggers.append(SoloDateLogger(DATA_LOG_FOLDER, sensor_type, name, alias, downsample))
			
			# Save full speed data if requested
			if self._save_fast and downsample > 1:
				fast_name = name + '.fast'
				fast_alias = None
				if fast_alias is not None:
					fast_alias = str(alias) + '.fast'
				self._loggers.append(SoloDateLogger(DATA_LOG_FOLDER, sensor_type, fast_name, fast_alias, downsample = 1))
				
			
		# Sometimes storing the derivative is useful
		if self._save_deriv:
			self._deriv_sensor = Sensor(name = name,
										alias = alias,
										sensor_type = sensor_type + Sensor.DERIV_SUFFIX, 
										save_deriv = False, 
										downsample = downsample,
										filt = 1.0) # We filter the base value
		else:
			self._deriv_sensor = None
			
		self._update_lock = threading.Lock()

	
	@property
	def name(self):
		return self._name
		
	@property
	def alias(self):
		return self._alias
		
	@property
	def last_update_time(self):
		return self._last_update_time
		
	@property
	def last_sync_num(self):
		return self._last_sync_num
		
	@property
	def sensor_type(self):
		return self._sensor_type

	@property
	def value(self):
		return self._value
	
	@value.setter
	def value(self, val):
		self.set_value(val)
	
	# Add an external logger in addition to any internal ones, but 
	# only if this sensor is supposed to be logged
	def add_logger(self, l):
		with self._update_lock:
			if self._sensor_type not in self.VALID_NOLOG_TYPES:
				self._loggers.append(l)
	
	def set_value(self, val, update_time = None, sync_num = None):
		
		with self._update_lock:

			old_value = self._value
			old_time = self._last_update_time
			
			# Simple exponential moving average
			if (self._filt < 1) and old_value and np.isfinite(old_value):
				val = (1 - self._filt) * old_value + self._filt * val
			
			# Keep the newest value in memory, downsampling occurs
			# at the file logging level if relevant (otherwise the
			# filter would break)
			self._value = val
			
			# If we don't know when this is from, assume it is now
			if update_time is None:
				self._last_update_time = time.time()
			else:
				self._last_update_time = update_time
				
			self._last_sync_num = sync_num
			
			# Save the value
			for l in self._loggers:
				l.log(sensor_name = self._name,
					  sensor_type = self._sensor_type,
					  value = val, 
					  update_time = self._last_update_time, 
					  sync_num = self._last_sync_num)
			
			# Save the derivative.  Note that, as implemented, downsampling
			# can cause you to not save the same times as the regular
			# value, since there is no derivative for the first point.
			# This is probably harmless but causes some confusion so
			# should be looked at again.
			if (self._deriv_sensor is not None) and (old_time > 0) and ((self._last_update_time - old_time) > 0):
				deriv = (self._value - old_value) / (self._last_update_time - old_time)
				self._deriv_sensor.set_value(deriv, update_time, sync_num)
				
