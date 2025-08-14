'''
A mixin for Instrument subclasses that contains settings and functions
common to all classes that contain setable voltages.  Such classes
should have sensors of the type Sensor.TYPE_TARGET_VOLTAGE

Usage:
	- Inherit in an Instrument subclass
	- Call VoltageOutputMixin.__init__ in the subclass's __init__

'''

import logging
import math
import numpy as np

from pyhkdlib.sensor import Sensor

class VoltageOutputMixin:
	
	OUTPUT_MODE_VOLTAGE = 0
	OUTPUT_MODE_POWER = 1
	OUTPUT_MODE_TEMPERATURE = 2
	VALID_OUTPUT_MODES = [OUTPUT_MODE_VOLTAGE, OUTPUT_MODE_POWER, OUTPUT_MODE_TEMPERATURE]
	
	# This can be overridden if your HW has better/worse precision
	ACCEPTABLE_VOLTAGE_ERROR = 0.001
	
	# 'max_voltages'  The absolute maximum possible output of any channel
	# 		(list or dict, ID indexed)
	# 'can_set_power' is True if you can set this output to a given power in W,
	# 		else False.
	# 'can_set_temperature' is True if you can PID this output to a given 
	#		temperature
	def __init__(self, default_max_voltage=10, default_min_voltage=0, can_set_power=False, max_voltages=None, min_voltages=None, can_set_temperature=False):

		if max_voltages is None:
			self.max_voltages = {sid: default_max_voltage for sid in self.sensor_ids}
		else:
			self.max_voltages = max_voltages
		
		if min_voltages is None:
			self.min_voltages = {sid: default_min_voltage for sid in self.sensor_ids}
		else:
			self.min_voltages = min_voltages
			
		self.can_set_power = can_set_power
		self.can_set_temperature = can_set_temperature
		self.has_output_mode = (self.can_set_power or self.can_set_temperature)
	
	# Sets the voltage of 'chan_id' to 'value'.  Must be implemented
	# by subclasses.
	def set_voltage(self, chan_id, value):
		raise NotImplementedError()
		
	# Sets the voltage of 'chan_id' to 'value'.  Must be implemented
	# by subclasses.
	def set_temperature(self, chan_id, value):
		raise NotImplementedError()
		
	# Take a power target given in W and return the needed voltage for
	# 'chan_id'.  May be re-implemented by subclasses that use powers.
	def power_to_voltage(self, chan_id, power):
		
		chan = self.get_channel(chan_id)
		
		if chan is None:
			return 0
			
		r_heater = chan.get("r_heater", None)
		r_total = chan.get("r_total", None)
		
		if (r_heater is None) or (r_total is None):
			return 0
		
		try:
			v = math.sqrt(float(power) * float(r_total)**2 / float(r_heater))
		except (ValueError, TypeError) as e:
			v = 0
			
		return v
		
	# Take a voltage target return the needed power in W for
	# 'chan_id'.  May be re-implemented by subclasses that use powers.
	def voltage_to_power(self, chan_id, voltage):
		
		chan = self.get_channel(chan_id)
		
		if chan is None:
			return 0
			
		r_heater = chan.get("r_heater", None)
		r_total = chan.get("r_total", None)
		
		if (r_heater is None) or (r_total is None):
			return 0
		
		try:
			p = (float(voltage)**2 / float(r_total)**2) * float(r_heater)
		except (ValueError, TypeError) as e:
			p = 0
			
		return p
	
	# Checks targets for all setable voltages and changed outputs as
	# needed.  Call in the instrument update loop.  Returns True if
	# any new voltages were applied, False otherwise.
	def process_voltage_targets(self):
		
		any_set = False
		
		for c_id in self.sensor_ids:
			
			# Look for setable voltages
			sen_t = self.get_sensor(c_id, Sensor.TYPE_TARGET_VOLTAGE, none_on_fail = True)
			if sen_t is None:
				continue
				
			# Current voltage reported by the device
			cur_v = self.get_sensor(c_id, Sensor.TYPE_VOLTAGE).value
			
			if self.can_set_temperature:
				cur_t = self.get_sensor(c_id, Sensor.TYPE_TEMPERATURE).value
			
			mode = self._fix_and_return_mode(c_id)

			if (mode == self.OUTPUT_MODE_POWER) and not self.can_set_power:
				mode = self.OUTPUT_MODE_VOLTAGE
			
			if (mode == self.OUTPUT_MODE_TEMPERATURE) and not self.can_set_temperature:
				mode = self.OUTPUT_MODE_VOLTAGE
			
			if mode == self.OUTPUT_MODE_POWER:
				
				ptarg = self._fix_and_return_ptarg(c_id)
				if ptarg is None:
					continue				
				vtarg = self.power_to_voltage(c_id, ptarg)
				
			elif mode == self.OUTPUT_MODE_TEMPERATURE:
				
				vtarg = None
				ttarg = self._fix_and_return_ttarg(c_id)
				if ttarg is None:
					continue	
					
				if cur_t != ttarg:
					self.set_temperature(c_id, ttarg)
					
			else:
				
				vtarg = self._fix_and_return_vtarg(c_id)
					
			# Clear out conflicting targets
			if self.can_set_temperature:
				sen_tt = self.get_sensor(c_id, Sensor.TYPE_TARGET_TEMPERATURE)
				sen_vt = self.get_sensor(c_id, Sensor.TYPE_TARGET_VOLTAGE)
				if mode != self.OUTPUT_MODE_TEMPERATURE:
					if sen_tt.value is not None:
						sen_tt.value = None
						self.set_temperature(c_id, None)
				else:
					if sen_vt.value is not None:
						sen_vt.value = None
					
			if vtarg is None:
				continue	
			
			if (cur_v is None) or (not np.isfinite(cur_v)) or (abs(cur_v - vtarg) > self.ACCEPTABLE_VOLTAGE_ERROR):
				self.set_voltage(c_id, vtarg)
				any_set = True
		
		return any_set
					
	# Checks the voltage target and fixes it if it is improper or out
	# of range.  The final value is returned, or None if there isn't one.
	def _fix_and_return_vtarg(self, chan_id):

		target_sensor = self.get_sensor(chan_id, Sensor.TYPE_TARGET_VOLTAGE, none_on_fail = True)
		max_out = self.max_voltages[chan_id]
		min_out = self.min_voltages[chan_id]
		
		if target_sensor is None:
			logging.warning("VoltageOutputMixin tried to find a voltage target, but channel " + str(chan_id) + " has no voltage target sensor")
			return None
			
		voltage_target = target_sensor.value
		
		if (voltage_target is None) or math.isnan(voltage_target):
			return None
				
		# Make sure the voltage target is a number
		try:
			voltage_target = float(voltage_target)
		except ValueError:
			target_sensor.value = None
			return None
			
		# Check if this voltage target is out of bounds
		if voltage_target < min_out:
			logging.warning("Invalid voltage target " + str(voltage_target) + " for " + str(chan_id) + ", set to " + str(min_out) + "V")
			voltage_target = min_out
			target_sensor.value = min_out
		elif voltage_target > max_out:
			logging.warning("Invalid voltage target " + str(voltage_target) + " for " + str(chan_id) + ", set to " + str(max_out) + "V")
			voltage_target = max_out
			target_sensor.value = max_out
			
		return voltage_target
		
			
	# Checks the power target and fixes it if it is improper or out
	# of range.  The final value is returned, or None if there isn't one.
	def _fix_and_return_ptarg(self, chan_id):

		target_sensor = self.get_sensor(chan_id, Sensor.TYPE_TARGET_POWER, none_on_fail = True)
		
		if target_sensor is None:
			logging.warning("VoltageOutputMixin tried to find a power target, but channel " + str(chan_id) + " has no power target sensor")
			return None
			
		power_target = target_sensor.value

		if (power_target is None) or math.isnan(power_target):
			return None
			
		# Make sure we can set by power
		if not self.can_set_power:
			logging.warning("Power target attempted for an output which can't use power targets.")
			target_sensor.value = None
			return None	
				
		# Make sure the power target is a number
		try:
			power_target = float(power_target)
		except ValueError:
			target_sensor.value = None
			return None
			
		# Check if this power target is out of bounds
		if power_target < 0:
			logging.warning("Invalid power target " + str(power_target) + " for " + str(chan_id) + ", set to 0")
			power_target = 0.0
			target_sensor.value = 0.0
			
		return power_target
		
	# Checks the temperature target and fixes it if it is improper or out
	# of range.  The final value is returned, or None if there isn't one.
	def _fix_and_return_ttarg(self, chan_id):

		target_sensor = self.get_sensor(chan_id, Sensor.TYPE_TARGET_TEMPERATURE, none_on_fail = True)
		
		if target_sensor is None:
			logging.warning("VoltageOutputMixin tried to find a temperature target, but channel " + str(chan_id) + " has no temperature target sensor")
			return None
			
		temperature_target = target_sensor.value

		if (temperature_target is None) or math.isnan(temperature_target):
			return None
			
		# Make sure we can set by temperature
		if not self.can_set_temperature:
			logging.warning("Power target attempted for an output which can't use temperature targets.")
			target_sensor.value = None
			return None	
				
		# Make sure the temperature target is a number
		try:
			temperature_target = float(temperature_target)
		except ValueError:
			target_sensor.value = None
			return None
			
		# Check if this temperature target is out of bounds
		if temperature_target < 0 or temperature_target > 350:
			logging.warning("Invalid temperature target " + str(temperature_target) + " for " + str(chan_id))
			temperature_target = None
			target_sensor.value = None
			
		return temperature_target
		
	# Checks the output and fixes it if it is improper.  The final value is returned.
	def _fix_and_return_mode(self, chan_id):
		
		if not self.has_output_mode:
			return self.OUTPUT_MODE_VOLTAGE

		target_sensor = self.get_sensor(chan_id, Sensor.TYPE_TARGET_OUTPUTMODE, none_on_fail = True)
		
		if target_sensor is None:
			logging.warning("VoltageOutputMixin tried to find a output mode target, but channel " + str(chan_id) + " has no output mode target sensor")
			return None
			
		output_mode = target_sensor.value
		
		if (output_mode not in self.VALID_OUTPUT_MODES) or \
		   ((output_mode == self.OUTPUT_MODE_POWER) and (not self.can_set_power)) or \
		   ((output_mode == self.OUTPUT_MODE_TEMPERATURE) and (not self.can_set_temperature)):
			
			if not math.isnan(output_mode):
				logging.warning("Invalid output mode " + str(output_mode) + " detected for channel ID " + str(chan_id))
			
			output_mode = self.OUTPUT_MODE_VOLTAGE
			target_sensor.value = output_mode
			
		return output_mode
		
	
			
