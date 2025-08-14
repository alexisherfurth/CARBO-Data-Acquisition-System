'''
Main controller and packet server for the data acquistion system
'''

import time
import logging
import socket
import threading
import urllib.request, urllib.parse, urllib.error
import numpy as np

from .sensor import Sensor
from .instruments.voltage_output_mixin import VoltageOutputMixin
from pyhkdlib.settings import RECV_PORT
from packetcomm.packetcomm import PacketServer

class DataAcqController(PacketServer):
	
	COMMAND_SET_VOLTAGE = 'vset'
	COMMAND_SET_POWER = 'pset'
	COMMAND_SET_CURRENT = 'iset'
	COMMAND_SET_CURRENTRAMP = 'irset'
	COMMAND_SET_STATE = 'sset'
	COMMAND_SET_TEMPERATURE = 'tset'
	COMMAND_SET_PERCENTAGE = 'perset'
	VALID_COMMANDS = [COMMAND_SET_VOLTAGE, COMMAND_SET_POWER, COMMAND_SET_CURRENT, COMMAND_SET_CURRENTRAMP, COMMAND_SET_STATE, COMMAND_SET_TEMPERATURE, COMMAND_SET_PERCENTAGE]
	
	# 'instruments' is a list of instruments used by the data acq system
	# 'loggers' is a list of extra global loggers used in addition to
	#			the per-channel logger in the Sensor class
	def __init__ (self, instruments, loggers):
		
		self.instruments = instruments
		
		self._action_lock = threading.Lock()
		
		self.targets = {k:{} for k in Sensor.VALID_TARGET_TYPES}

		# Let the instruments have access to the targets and any 
		# global loggers
		for inst in self.instruments:
			inst.connect_targets(self.targets)
			for l in loggers:
				inst.add_logger(l)		
			
		# Bound to localhost so external commands are not accepted
		PacketServer.__init__(self, "localhost", RECV_PORT)

	# Main data acq loop
	def main_loop(self):
		
		logging.info("Starting main data loop")
		
		try:

			# Loop all of the instruments forever
			while True:
				for inst in self.instruments:
					with self._action_lock:
						start_time = time.time()
						inst.update()
						dt = time.time() - start_time
						if dt > 0.3:
							logging.warning("Instrument of type " + str(inst.BOX_TYPE) + " held the update loop for %0.1f sec!  Should it have its own thread?" % dt)
				# Don't loop faster than 200 Hz to prevent CPU hogging
				time.sleep(0.005)
				
		except KeyboardInterrupt:
			pass
		
		logging.info("Main data loop closing...")
		
		with self._action_lock:
			for inst in self.instruments:
				inst.close()				
		
		logging.info("Main data loop closed")
		
	def _safe_set_target(self, name, target_type, value):
		if name in self.targets[target_type]:
			self.targets[target_type][name].value = value
			# ~ print(target_type, name, value, self.targets[target_type][name].value)
		else:
			logging.error("Can't set " + str(target_type) + ", name doesn't exist: " + str(name))

	# Handle incomming packets (from packet server thread)
	def handle_packet(self, data):
		with self._action_lock:
			self._handle_packet_helper(data)
	
	def _handle_packet_helper(self, data):
							
		try:
			command_split = data.rstrip().split(",")
			
			# Make sure we have the right number
			if len(command_split) != 3:
				raise ValueError("Wrong number of values")
			
			# Attempt to extract the values
			command = str(command_split[0])
			name = urllib.parse.unquote(command_split[1])
			value = float(command_split[2])
			
			if not np.isfinite(value):
				 raise ValueError("Non-finite Value")
			
			if command not in self.VALID_COMMANDS:
				raise ValueError("Bad Command")
			
		except (TypeError, AttributeError, ValueError):
			logging.error("Invalid packet: " + str(data))	
			return
			
		# Handle the command
		logging.info("Valid command: " + str(data))	
		if command == self.COMMAND_SET_VOLTAGE:
			self._safe_set_target(name, Sensor.TYPE_TARGET_VOLTAGE, value)
			self._safe_set_target(name, Sensor.TYPE_TARGET_OUTPUTMODE, VoltageOutputMixin.OUTPUT_MODE_VOLTAGE)
		elif command == self.COMMAND_SET_POWER:
			self._safe_set_target(name, Sensor.TYPE_TARGET_POWER, value)
			self._safe_set_target(name, Sensor.TYPE_TARGET_OUTPUTMODE, VoltageOutputMixin.OUTPUT_MODE_POWER)
		elif command == self.COMMAND_SET_TEMPERATURE:
			self._safe_set_target(name, Sensor.TYPE_TARGET_TEMPERATURE, value)
			self._safe_set_target(name, Sensor.TYPE_TARGET_OUTPUTMODE, VoltageOutputMixin.OUTPUT_MODE_TEMPERATURE)
		elif command == self.COMMAND_SET_CURRENT:
			self._safe_set_target(name, Sensor.TYPE_TARGET_CURRENT, value)
		elif command == self.COMMAND_SET_CURRENTRAMP:
			self._safe_set_target(name, Sensor.TYPE_TARGET_CURRENTRAMP, value)
		elif command == self.COMMAND_SET_STATE:
			self._safe_set_target(name, Sensor.TYPE_TARGET_STATE, value)
		elif command == self.COMMAND_SET_PERCENTAGE:
			self._safe_set_target(name, Sensor.TYPE_TARGET_PERCENTAGE, value)

