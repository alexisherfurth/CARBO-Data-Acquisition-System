import logging
import time
import threading
import traceback
import random

from ..instrument import Instrument
from ..serial_instrument import SerialInstrument
from ..sensor import Sensor

# A set of parent classes for devices controlled with IEEE 488.2 or
# SCPI syntax over either a GPIB bus or RS-232.  Provides GPIB bus 
# instruments access to a "send_packet" function that mimics the one
# provided by SerialInstrument, facilitating code reuse in devices that
# can be used over GPIB or serial.
#
# GPIBSCPIInstrument is for GPIB bus control.
# SerialSCPIInstrument is for RS232 control.
# AbstractSCPIInstrument contains the common logic code.

class AbstractSCPIInstrument:
	
	BOX_TYPE = 'SCPI_GENERIC'
	
	# Time since the ask was added to the queue before declaring it 
	# unanswered.  Note this is much higher than SER_ASK_TIMEOUT
	# because we don't know if the packet sat in the queue for awhile
	# before sending.
	DISCONNECTED_TIMEOUT = 30 # sec
	
	# Time between warnings and IDN re-checks we are disconnected.
	# Note that this request is very likely to time out (which holds
	# up the bus), so we want this to be infrequent.
	RECHECK_TIME = 60 # sec 
	
	# Time to wait before reconfiguring the device after a reconnect
	RECONFIG_PAUSE = 3 # sec
	
	# The name to use when printing errors
	SPECIFIC_DEVICE_ID = 'Unknown Device'
	
	# The string to check for in *IDN? responses
	IDN_STR = 'Unknown'
	
	def __init__(self):
		
		# Protects inner state changes
		self._scpi_inst_lock = threading.Lock()
		
		self._scpi_first_ask = None
		self._scpi_last_ask = None
		self._scpi_last_resp = None
		self._scpi_last_print = 0
		self._scpi_last_responsive = True
		
		self._scpi_need_reconfig = False
		self._scpi_reconfig_time = 0
		self.initial_config()
	
	# Wraps callbacks for "ask" requests to monitor connection status
	def _callback_wrapper(self, resp_callback, data):
		
		data = data.strip()
		if len(data) < 1:
			logging.debug(self.SPECIFIC_DEVICE_ID + " callback wrapper received a zero-length packet")
			return
		
		with self._scpi_inst_lock:
			self._scpi_last_resp = time.time()

		# Don't take the insturment lock into the response callback,
		# we can't assume the user will not call another function
		# that needs the lock.  Don't use any assumtions that require
		# taking the lock into resp_callback.
		try:
			resp_callback(data)
		except:
			logging.error("Contained error in %s callback handler! %s" % (self.SPECIFIC_DEVICE_ID, traceback.format_exc()))
		
	# Returns true if the device is thought to be responding to commands
	@property
	def responsive(self):
		with self._scpi_inst_lock:
			return self._responsive
	
	# Returns true if the device is thought to be connected.
	# Assumes the user already has the instrument lock
	@property
	def _responsive(self):
		
		if not self.connected:
			# Communication controller is offline
			return False
		elif (self._scpi_last_ask is None) or (self._scpi_first_ask is None):
			# We just booted
			return True
		elif (self._scpi_last_resp is None):
			# We have an ask but not a response since boot.  Compare
			# to the first ask, since the last ask keeps updating.
			return ((time.time() - self._scpi_first_ask) < self.DISCONNECTED_TIMEOUT)
		elif (self._scpi_last_resp >= self._scpi_last_ask):
			# We received an answer recently
			return True
		else:
			# Check if the last response was close in time to the
			# last ask
			return ((self._scpi_last_ask - self._scpi_last_resp) < self.DISCONNECTED_TIMEOUT)
	
	# Adds a packet to the transmit queue.  If resp_callback is None,
	# the message will be sent normally (not as an "ask").  If 
	# resp_callback is not None, it must be a function taking a single
	# (string) argument.  The transmit will be treated as an "ask",
	# and the resp_callback will be called with the result.
	def send_packet(self, packet, resp_callback=None):
		
		with self._scpi_inst_lock:
								
			# Wrap the callback so we can monitor connection metrics
			cb = None
			if resp_callback is not None:
				cb = lambda x: self._callback_wrapper(resp_callback, x)
				self._scpi_last_ask = time.time()
				if self._scpi_first_ask is None:
					self._scpi_first_ask = self._scpi_last_ask	
					
			self._raw_send_packet(packet, cb)			
		
	# Request the identity
	def request_identity(self):
		self.send_packet('*IDN?', resp_callback=self.handle_identity)
	
	# Verify the identity
	def handle_identity(self, idn):
		logging.debug("Valid %s identity response: %s" % (self.SPECIFIC_DEVICE_ID, str(idn)))
		if self.IDN_STR not in idn:
			logging.error("%s does not have the expected string %s in its identity (%s)" % (self.SPECIFIC_DEVICE_ID, repr(self.IDN_STR), idn.strip()))
			
	# Perform the initial config after a connection has been established
	# or re-established
	def initial_config(self):

		logging.info("Performing initial configuration for %s" % (self.SPECIFIC_DEVICE_ID))

		self.request_identity()
		
	# Send the GPIB CLS command	
	def send_cls(self):
		self.send_packet('*CLS')
		
	# Code to run with a period of wait_time when connected 
	def update_connected(self):
		pass
	
	# Implements Instrument.update_periodic(), which is mixed in by subclasses
	def update_periodic(self):
		
		request_data = False
		request_idn = False
		send_config = False
		send_cls = False
		
		with self._scpi_inst_lock:
			
			if self._scpi_need_reconfig:
				
				# We are reconnected, send the config
				if (time.time() - self._scpi_reconfig_time > self.RECONFIG_PAUSE):
					send_config = True
					request_data = False
					self._scpi_need_reconfig = False
					
			elif not self._responsive:
				
				# Warn the user we are disconnected.
				# Periodically ask IDN to check for reconnection.
				self._scpi_last_responsive = False
				self._scpi_need_reconfig = False
				if (time.time()-self._scpi_last_print > self.RECHECK_TIME):
					logging.warning(self.SPECIFIC_DEVICE_ID + " appears to be disconnected")
					self._scpi_last_print = time.time()
					request_idn = True
					
			else:
				
				# Check if we reconnected
				if not self._scpi_last_responsive:
					self._scpi_last_responsive = True
					self._scpi_need_reconfig = True
					send_cls = True
					self._scpi_reconfig_time = time.time()
					logging.info(self.SPECIFIC_DEVICE_ID + " reconnected!")
				else:
					request_data = True
					
		# Now without the instrument lock		
		if send_cls:
			self.send_cls()
		if send_config:
			self.initial_config()
		if request_idn:
			self.request_identity()
		if request_data:
			self.update_connected()
	
	# Wrapper to abstract the sending method differences between
	# GPIB-over-serial and direct serial
	def _raw_send_packet(self, packet, resp_callback=None):
		raise NotImplementedError()
	
	# Request and clear the status byte (to immitate serial poll)
	def request_status(self, resp_callback):
		raise NotImplementedError()
		
# Device on a GPIB bus			
class GPIBSCPIInstrument(AbstractSCPIInstrument, Instrument):
	
	# "controller" should be a Prologix object (or equivalent).
	def __init__(self, controller, address, channels=[], wait_time=10, **kwargs):
		
		assert address in range(31), "Invalid GPIB address: " + repr(address)
		
		# Inherit from the controller
		for key in ['verbose_fail', 'verbose_rx', 'verbose_tx', 'verbose_raw']:
			if key not in kwargs.keys():
				kwargs[key] = getattr(controller, key)
		
		self._gpib_controller = controller
		self._gpib_address = address
		self.SPECIFIC_DEVICE_ID = "GPIB device (address %i, type %s)" % (self._gpib_address, self.BOX_TYPE)
		
		Instrument.__init__(self, channels, wait_time=wait_time, **kwargs)
		AbstractSCPIInstrument.__init__(self)
		
		# Add a random phase to the readout timing so we spread out
		# the load on the bus a little bit
		self.last_update_time += random.random() * wait_time
	
	@property
	def connected(self):
		return self._gpib_controller.connected
	
	# Send via the controller, which needs an address
	def _raw_send_packet(self, packet, resp_callback=None):
		self._gpib_controller.addr_send_packet(self._gpib_address, packet, resp_callback)
	
	# Use the serial poll functionality so the instrument doesn't need
	# to parse the request (it is handled in the interface chip)
	def request_status(self, resp_callback):
		
		with self._scpi_inst_lock:
								
			# Wrap the callback so we can monitor connection metrics
			cb = lambda x: self._callback_wrapper(resp_callback, x)
			self._scpi_last_ask = time.time()
			if self._scpi_first_ask is None:
				self._scpi_first_ask = self._scpi_last_ask	
					
			self._gpib_controller.serial_poll(self._gpib_address, cb)		
	
	def request_read(self, resp_callback):
		self._gpib_controller.addr_read(self._gpib_address, resp_callback)
		
# Device connected via RS232 but commanded with GPIB syntax
class SerialSCPIInstrument(AbstractSCPIInstrument, SerialInstrument):
	
	def __init__(self, port, channels=[], wait_time=10, baudrate=9600, pkt_end='\r\n', **kwargs):
		
		self.SPECIFIC_DEVICE_ID = "Serial device (port %s, type %s)" % (port, self.BOX_TYPE)

		SerialInstrument.__init__(self, 
			port, 
			baudrate = baudrate, 
			pkt_end = pkt_end,
			channels = channels,
			wait_time = wait_time,
			**kwargs)
			
		AbstractSCPIInstrument.__init__(self)

	# Send directly
	def _raw_send_packet(self, packet, resp_callback=None):
		SerialInstrument.send_packet(self, packet, resp_callback)

	# Request and clear the status byte (to immitate serial poll)
	def request_status(self, resp_callback):
		self.send_packet('*STB?\n*CLS', resp_callback)
	
	# This packet scheme (reading later after writing) is not currently
	# supported for pure serial devices, since you don't have to ask
	# them to read
	def request_read(self, resp_callback):
		raise NotImplementedError
