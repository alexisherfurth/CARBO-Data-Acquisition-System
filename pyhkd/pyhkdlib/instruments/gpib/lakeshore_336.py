'''
Read from a Lakeshore 336
'''

import time
import logging
import serial
import math

from pyhkdlib.sensor import Sensor
from .gpib_instrument import AbstractSCPIInstrument, GPIBSCPIInstrument, SerialSCPIInstrument

from calib.helpers import get_calib

# Control logic shared between the GPIB and Serial interfaces
class AbstractLakeshore336:
	
	NUM_SENSORS = 6
	BOX_TYPE = 'LS336'
	IDN_STR = 'MODEL336'
	
	THERM_IDS = ['A','B','C','D']
	HEATER_IDS = ['I1','I2']
	
	def __init__(self):
		pass	
		
	# Perform the initial config.
	# Overrides AbstractSCPIInstrument.initial_config.
	def initial_config(self):
		
		AbstractSCPIInstrument.initial_config(self)
		
		# ~ for i in range(len(self.HEATER_IDS)):
			
			# ~ # Set the heaters to open loop (manual) mode
			# ~ self.send_packet('OUTMODE %i,3,0,1' % i)
			
			# ~ # Choose the high current range
			# ~ self.send_packet('RANGE %i,3' % i)
			
			# ~ # Max output current range
			# ~ self.send_packet('HTRSET %i,1,4,2.0,1' % i)
			
			# ~ self.send_packet('MOUT %i,20.00' % i)
	
	# Handle thermometer data packets
	def handle_therms(self, response):
		
		if self.verbose_rx:
			logging.debug("LS336 data received: " + response.strip())
		
		try:
			
			response_split = response.rstrip().split(",")
			
			# Make sure we have the right numbers
			if len(response_split) != len(self.THERM_IDS):
				raise ValueError()
			
			# Attempt to extract the values
			extracted_raw = [float(response_split[i]) for i in range(len(self.THERM_IDS))]

		except (TypeError, AttributeError, ValueError):
			
			logging.error("Error loading in Lakshore 336 temperatures (received: %s)" % (repr(response)))				
			return
		
		# Save the values
		for i in range(len(self.THERM_IDS)):
			self.get_sensor(self.THERM_IDS[i], Sensor.TYPE_TEMPERATURE).value = extracted_raw[i]

	# Handle a generic class of single-channel heater parameters
	def handle_heater_val(self, response, index, sensor_type):
			
		if self.verbose_rx:
			logging.debug("LS336 heater %i %s received: %s" % (index, sensor_type, response.strip()))
			
		try:
			val = float(response.strip())
		except (TypeError, AttributeError, ValueError):	
			logging.error("Error loading in Lakshore 336 heater parameter (received: %s)" % (repr(response)))				
			return
		
		self.get_sensor(self.HEATER_IDS[index], sensor_type).value = val

	# Code to run when connected with a period of wait_time.
	# Implements AbstractSCPIInstrument.update_connected
	def update_connected(self):

		# Read all the temperatures in
		self.send_packet('KRDG? 0', resp_callback=self.handle_therms)
		
		for i in range(len(self.HEATER_IDS)):
			
			# Note: the "i=i" in the lamba is to freeze in the current
			# value of i and should not be removed
			
			# Manual output fraction
			resp_callback = (lambda x, i=i: self.handle_heater_val(x, i, Sensor.TYPE_PERCENTAGE))
			self.send_packet('MOUT? %i' % (i+1), resp_callback)
			
			# Output range (off, low, med, high)
			resp_callback = (lambda x, i=i: self.handle_heater_val(x, i, Sensor.TYPE_STATE))
			self.send_packet('RANGE? %i' % (i+1), resp_callback)
			
		# Process targets
		self._process_state_targets()
		self._process_percentage_targets()
	
	# Process output range changes
	def _process_state_targets(self):
		
		for i in range(len(self.HEATER_IDS)):
			
			target = self.get_sensor(self.HEATER_IDS[i], Sensor.TYPE_TARGET_STATE)
			
			if target.value is None or math.isnan(target.value):
				continue
				
			sensor = self.get_sensor(self.HEATER_IDS[i], Sensor.TYPE_STATE)
			
			if target.value != sensor.value:
				params = (i+1, target.value)
				logging.debug("Requesting LS336 Output %i move to range %i" % params)
				self.send_packet('RANGE %i %i' % params)
				target.value = None # Don't maintain if error triggered
		
	# Process output fraction changes
	def _process_percentage_targets(self):
		
		for i in range(len(self.HEATER_IDS)):
			
			target = self.get_sensor(self.HEATER_IDS[i], Sensor.TYPE_TARGET_PERCENTAGE)
			
			if target.value is None or math.isnan(target.value):
				continue
				
			sensor = self.get_sensor(self.HEATER_IDS[i], Sensor.TYPE_PERCENTAGE)
			
			if target.value != sensor.value:
				params = (i+1, target.value)
				logging.debug("Requesting LS336 Output %i move to %i%%" % params)
				self.send_packet('MOUT %i %g' % params)
				target.value = None # Don't maintain if error triggered

class GPIBLakeshore336(AbstractLakeshore336, GPIBSCPIInstrument):
	
	def __init__(self, controller, address, channels=[], wait_time=8, **kwargs):
		
		GPIBSCPIInstrument.__init__(self, controller, address, channels, wait_time = wait_time, **kwargs)
		

class SerialLakeshore336(AbstractLakeshore336, SerialSCPIInstrument):
			
	def __init__(self, port, channels=[], wait_time=8, baudrate=57600, **kwargs):

		SerialSCPIInstrument.__init__(self, 
			port, 
			baudrate = baudrate, 
			bytesize=serial.SEVENBITS, 
			parity=serial.PARITY_ODD, 
			stopbits=serial.STOPBITS_ONE,
			pkt_end = '\r\n',
			pkt_start = None,
			channels = channels,
			wait_time = wait_time,
			**kwargs)
