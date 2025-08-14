import os
import logging
import time
import serial
import math
import threading
import traceback

from ..sensor import Sensor
from ..instruments.instrument import Instrument

# An instrument communicating over serial.  Uses two threads for serial
# TX and RX outside of the normal Instrument.update cadence.
#
# Instrument.update can be used by subclasses to request new data.  
# SerialInstrument.handle_packet handles incoming data without being
# 		limited to the Instrument.update cadence.
# SerialInstrument.send_packet adds new packets to the transmit queue,
# 		which is also not limited to the Instrument.update cadence.
#
# Any function or property beginning with an underscore should be 
# considered an internal function which may change between versions
# without notice.
#
# Public interface functions:
# 	send_packet
# 	close
# 	rx_settings
# 	purge_tx_buf
# 	purge_rx_buf
# 	purge_bufs
# Functions to be implemented by subclasses:
# 	on_reconnect (optional)
#	handle_packet
# Public interface properties:
# 	connected
#	tx_buf_len
#	ask_waiting
#
class SerialInstrument(Instrument):

	# The read timeout should be large enough to prevent CPU hogging
	# but small enough to keep packet latency low (you might
	# need to wait for the timeout if serial messages are rare)
	SER_READ_BATCH = 1024 # bytes
	SER_READ_TIMEOUT = 0.01 # seconds
	SER_PACKET_TIMEOUT = 1 # seconds before flushing an incomplete packet
	SER_RECONNECT_TIME = 5 # seconds
	SER_RX_PAUSE = 0.001 # seconds to pause between empty receives
	SER_TX_PAUSE = 0.05 # seconds to pause between sends
	SER_TX_TIMEOUT = 20 # seconds before dropping TX packets
	SER_ASK_TIMEOUT = 2 # second to wait to start or fail an "ask"

	# pkt_end: marks the end of a packet
	# pkt_start: marks the start of a packet, or None to start immediately after pkt_end
	def __init__(self, port, baudrate, pkt_end = '\n', pkt_start = None, 
				 bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, 
				 stopbits=serial.STOPBITS_ONE, return_bytes=False, 
				 fixed_rx_size=None, **kwargs):
				
		logging.debug("Requesting baudrate of " + str(baudrate) + " for port " + str(port))
		
		if hasattr(pkt_start, 'encode'):
			pkt_start = pkt_start.encode()
		if hasattr(pkt_end, 'encode'):
			pkt_end = pkt_end.encode()
		
		if 'ttyUSB' in port or 'ttyACM' in port:
			logging.warning("It looks like you are using a generic serial port name (%s).  This may change when disconnected or when the computer reboots.  It is highly recommended that you define a fixed name for this port (see help-setup.txt)." % (port,))
		
		if pkt_start is not None and len(pkt_start) == 0:
			pkt_start = None
		
		self._port = port
		self._baudrate = baudrate
		self._bytesize = bytesize
		self._parity = parity
		self._stopbits = stopbits
		self._pkt_start = pkt_start
		self._pkt_end = pkt_end
		self._return_bytes = return_bytes
		self._fixed_rx_size = fixed_rx_size
		self._tx_buf = []	
		self._pkts_to_process = []	
		self._last_reconnect_try = 0
		self._last_rx_time = 0
		
		self._ser = None
		self._ser_lock = threading.Lock()
		self._tx_lock = threading.Lock()
		self._rx_lock = threading.Lock()
		self._pktproc_lock = threading.Lock()

		self._rx_reset()
						
		self._thread_rx = threading.Thread(target = self._loop_ser_rx, name="Serial RX (%s)" % (self._port,))
		self._thread_tx = threading.Thread(target = self._loop_ser_tx, name="Serial TX (%s)" % (self._port,))
		self._thread_pktproc = threading.Thread(target = self._loop_ser_pktproc, name="Serial Packet Process (%s)" % (self._port,))
		
		# Don't let the threads keep the program alive
		self._thread_rx.daemon = True
		self._thread_tx.daemon = True
		
		Instrument.__init__(self, **kwargs)
		
		self._ser_reconnect()
		
		self._threads_running = True 
		self._thread_rx.start()
		self._thread_tx.start()
		self._thread_pktproc.start()
		
	def __del__(self):
		try:
			self.close()		
		except:
			# We are dying anyway, lets not pollute the terminal
			# with errors that confuse people
			pass
			
	# Shut down the serial port and RX/TX threads
	def close(self):
		
		logging.debug("Shutting down serial communication on port " + str(self._port))
		
		self._threads_running = False
		
		self._thread_rx.join()
		self._thread_tx.join()
		self._thread_pktproc.join()
		
		with self._ser_lock:
			if self._ser is not None:
				self._ser.close()
		
		logging.debug("Serial communication was shut down on port " + str(self._port))
		
	# Returns true if the serial device is thought to be connected.
	@property
	def connected(self):
		with self._ser_lock:
			return (self._ser is not None)
	
	# Re-open the serial port, return True if it works
	def _ser_reconnect(self):
		
		with self._ser_lock:
			
			# Make sure we aren't already connected
			if self._ser is not None:
				return True
			
			# Make sure we don't try too often
			if (time.time() - self._last_reconnect_try) < self.SER_RECONNECT_TIME:
				return False
			
			self._last_reconnect_try = time.time()
			
			try:
				self._ser = serial.Serial(
					port=self._port, 
					baudrate=self._baudrate, 
					timeout=self.SER_READ_TIMEOUT,
					bytesize=self._bytesize,
					parity=self._parity,
					stopbits=self._stopbits,
					write_timeout=0, # Non-blocking write
				)
			except serial.SerialException:
				self._ser = None
				if self.verbose_fail:
					logging.error("Error while opening serial communication (port %s)." % (self._port))
				return False
			
			logging.debug("Serial communication opened successfully (port %s)." % (self._port))
			
			with self._rx_lock:
				self._rx_reset()

		self.on_reconnect()
		
		return True	

	# Called whenever a successful serial connection is opened or re-opened
	def on_reconnect(self):
		pass
	
	# Run forever, handles packet handler processing without bogging
	# down the RX thread.
	def _loop_ser_pktproc(self):	
									
		while (self._threads_running):
			
			# Grab one packet but give up the lock quickly
			with self._pktproc_lock:
				if len(self._pkts_to_process) < 1:
					packet = None
				else:
					ask_callback, packet = self._pkts_to_process.pop(0)
					if len(self._pkts_to_process) > 100:
						logging.warning("Packet rx pile-up detected (%i packets, port %s)" % (len(self._pkts_to_process), self._port))
			
			# Rate limit, but only if we run out of packets
			if packet is None:
				time.sleep(self.SER_RX_PAUSE) 
				continue
						
			# Try to call the relevant handler
			try:
				if ask_callback is None:
					self.handle_packet(packet)
				else:
					ask_callback(packet)
			except:
				txt_ask = ''
				if ask_callback is not None:
					txt_ask = " (in 'ask' handler %s)" % str(ask_callback)
				logging.error("Contained serial packet handler error (port %s)%s. %s" % (self._port, txt_ask, traceback.format_exc()))
				
	# Run forever, handles serial RX
	def _loop_ser_rx(self):	
									
		while (self._threads_running):
			
			# Rate limit
			time.sleep(self.SER_RX_PAUSE)
			
			# Check connection
			if not self.connected:
				self._ser_reconnect()
				continue
				
			with self._rx_lock:
				
				# Flush stale partial packets or asks
				if len(self._rx_buf) > 0:
					if (time.time() - self._last_rx_time) > self.SER_PACKET_TIMEOUT:
						logging.error("Flushing stale incomplete serial packet received on port %s.  RX buffer: %s" % (self._port, str(self._rx_buf)))
						self._rx_reset()			
				if self._ask_callback is not None:
					if (time.time() - self._last_ask_time) > self.SER_ASK_TIMEOUT:
						#~ logging.error("Flushing stale 'ask' (no response) on port %s.  RX buffer: %s" % (self._port, str(self._rx_buf)))
						self._rx_reset()			

				# Read new data
				with self._ser_lock:
					new_data = b''
					try:
						# Block for the timeout period waiting for new bytes.
						new_data = self._ser.read(self.SER_READ_BATCH)
					except serial.SerialException:
						self._ser = None
						if self.verbose_fail:
							logging.error("Lost serial communication (port %s)." % (self._port))
						continue
				
				if len(new_data) < 1:
					continue
					
				self._last_rx_time = time.time()
				
				if self.verbose_rx and self.verbose_raw:
					if self._return_bytes:
						rx_repr = ":".join("{:02x}".format(c) for c in new_data)
					else:
						rx_repr = repr(new_data)
					logging.debug("Raw serial data recieved (port %s): %s" % (self._port, rx_repr))
					
				# Extract packets
				for c in new_data:
					self._rx_new_char(c)
	
	# Process a single newly received character.  Assumed the rx lock
	# is already held.
	def _rx_new_char(self, c):
				
		# Start immediately if there is no start marker
		if not self._pkt_started and self._pkt_start is None:
			self._pkt_started = True
						
		if not self._pkt_started:
			
			# Look for the start
			if c == self._pkt_start[self._next_start_pos]:
				self._next_start_pos += 1
				if self._next_start_pos >= len(self._pkt_start):
					self._pkt_started = True
					self._next_start_pos = 0
					#~ logging.debug("Serial message started")
			else:
				# Restart the start sequence (if len > 1)
				self._next_start_pos = 0
			
		else:
			
			self._rx_buf.append(c)
			
			# Check for the whole ending string
			end_found = (self._pkt_end is not None) and self._rx_buf.endswith(self._pkt_end)
			end_forced = (self._fixed_rx_size is not None) and (len(self._rx_buf) >= self._fixed_rx_size)
			
			if end_found or end_forced:
				
				# Finished packet, snip off end marker
				packet = self._rx_buf
				if end_found:
					packet = packet[:-len(self._pkt_end)]
				
				if not self._return_bytes:
					try:
						packet = packet.decode()
					except UnicodeDecodeError:
						logging.debug("Failed to decode unicode serial packet (port %s), should return_bytes be enabled for this hardware?" % (self._port,))
						self._rx_reset()
						return
				
				# Call the handler in a separate process so we don't
				# bog down this thread and drop incomming data
				with self._pktproc_lock:
					self._pkts_to_process.append((self._ask_callback, packet))
						
				self._rx_reset()
			
			elif self._pkt_start is not None and self._rx_buf.endswith(self._pkt_start):
				
				# We got a packet mid packet!  Start over.
				logging.error("New serial packet detected mid-packet, flushing old data (port %s): %s" % (self._port, repr(self._rx_buf)))
				self._rx_reset()
				self._pkt_started = True
	
	# Run forever, handles serial TX.  For normal messages, these
	# are sent blindly (regardless of the state of the RX thread)
	# at some metered rate (set by self.SER_TX_PAUSE).  If the message
	# is an "ask", then a callback function was included with the 
	# packet.  An "ask" allows one to communicate with devices where
	# the interpretation of the received packets depends on the context
	# of the last transmitted message.  For example, GPIB devices work
	# in a question->answer paradigm that requires keeping track of 
	# responses to specific commands.  In some cases this can be avoided
	# by only asking one question repeatedly (ex: 'SRDG?' on a LS218),
	# and for performance reasons that usage is preferred when relevant.
	# However, some devices require multiple commands (ex: 'VOLT?' and
	# 'MEAS:CURR?' on an AgilentE36XXA).  While the AgilentE36XXA could
	# be handled by adding another question with known output (such as
	# '*IDN?') and using this to identify the "phase" of the received
	# data, a dedicated "ask" mode is added for better generality.
	# When an "ask" is next in the TX buffer, it waits for the RX buffer
	# to empty.	
	def _loop_ser_tx(self):	
		
		while (self._threads_running):
			
			# Slow down to prevent overloading the instrument and 
			# hogging all of the CPU time
			time.sleep(self.SER_TX_PAUSE)	
			
			# Check for stale packets (to prevent build-up if we disconnected).
			# Note we need this to run even if disconnected, so it is
			# before the connection check.
			with self._tx_lock:
				for (pkt,t,cb) in list(self._tx_buf):
					if (time.time() - t) > self.SER_TX_TIMEOUT:
						self._tx_buf.remove((pkt,t,cb))
						hex_repr = ":".join("{:02x}".format(c) for c in pkt)
						if self.verbose_tx:
							logging.debug("Dropping stale packet from serial tx queue (port %s): %s" % (self._port, hex_repr))
							logging.debug("Serial tx queue size (port %s): %i" % (self._port, len(self._tx_buf)))
			
			# Check connection
			if not self.connected:
				self._ser_reconnect()
				continue
			
			with self._tx_lock:

				if len(self._tx_buf) < 1:
					continue
					
				if len(self._tx_buf) > 100:
					logging.warning("The serial packet transmit buffer for port %s has grown to size %i" % (self._port, len(self._tx_buf)))
				
				# Send the next packet
				#~ logging.debug("Serial TX buf: " + str(self._tx_buf))
				to_send, t, resp_callback = self._tx_buf.pop(0)
				
				if to_send is None:
					continue

			# Wait for any existing "ask"s to either send or time out.
			# It is ok to lose the rx/serial lock after this, since
			# only this thread can add an "ask" (the rx thread can
			# only finish or timeout/remove an ask)
			while (True):
				
				with self._rx_lock:
					if self._ask_callback == None:
						break
				
				# Rate limit
				time.sleep(self.SER_RX_PAUSE) 
				
				# Don't get trapped here on shutdown
				if not self._threads_running:
					return
					
			# Check if this new packet is an "ask"
			if resp_callback is not None:
				
				# Wait for an empty RX buffer before starting an "ask"
				start_time = time.time()
				while True:
					
					with self._rx_lock, self._ser_lock:
						if self._ser.in_waiting == 0 and len(self._rx_buf) == 0:
							self._ask_callback = resp_callback
							self._last_ask_time = time.time()
							self._ser_send_packet_now(to_send)
							#~ logging.debug("Serial 'ask' initialized (port %s)" % (self._port))
							break
							
					if (time.time() - start_time) > self.SER_ASK_TIMEOUT:
						logging.error("Serial 'ask' failed, timeout reached when waiting for an empty RX buffer (port %s)" % (self._port))
						break
					
					# Rate limit
					time.sleep(self.SER_RX_PAUSE) 
					
					# Don't get trapped here on shutdown
					if not self._threads_running:
						return
			
			else:
				
				# Normal send
				with self._ser_lock:
					self._ser_send_packet_now(to_send)

	
	# Return the number of packets waiting to send
	@property
	def tx_buf_len(self):
		with self._tx_lock:
			return len(self._tx_buf)
	
	# Return true if an "ask" is in progress
	@property
	def ask_waiting(self):
		with self._rx_lock:
			return (self._ask_callback is not None)
				
	# Change the packet rx settings live (for poorly behaved packet structures)
	def rx_settings(self, pkt_end = '\n', pkt_start = None, return_bytes=False, fixed_rx_size=None):
		
		logging.debug("Serial RX settings have been changed on port " + str(self._port))
		
		if hasattr(pkt_start, 'encode'):
			pkt_start = pkt_start.encode()
		if hasattr(pkt_end, 'encode'):
			pkt_end = pkt_end.encode()
			
		with self._rx_lock:
			self._pkt_start = pkt_start
			self._pkt_end = pkt_end
			self._return_bytes = return_bytes
			self._fixed_rx_size = fixed_rx_size
			self._rx_reset()
	
	# Re-initialize the packet RX buffer.  Assumes the user already
	# has _rx_lock.
	def _rx_reset(self):
		self._ask_callback = None
		self._rx_buf = bytearray()
		self._pkt_started = False
		self._next_start_pos = 0
		self._last_ask_time = 0
			
	# Adds a packet to the transmit queue.  If resp_callback is None,
	# the message will be sent normally (not as an "ask").  If 
	# resp_callback is not None, it must be a function taking a single
	# (string) argument.  The transmit will be treated as an "ask",
	# and the resp_callback will be called with the result.  
	# See _loop_ser_tx() for more info on how an "ask" works. 
	def send_packet(self, packet, resp_callback=None):
		
		if hasattr(packet, 'encode'):
			packet = packet.encode()
			
		with self._tx_lock:				
			self._tx_buf.append((packet, time.time(), resp_callback))
		
		if self.verbose_tx:	
			logging.debug("Added packet to serial TX queue (port %s)" % (self._port))
		
	# Implement in subclass.  Called with each new received message.
	def handle_packet(self, packet):
		raise NotImplemented()
	
	# Try sending a serial packet now (no queue).  Returns True on success.
	# Assumes the user has the serial lock already.
	def _ser_send_packet_now(self, packet):
		
		if hasattr(packet, 'encode'):
			# Encode with utf-8 in case non-ascii was sent.  Normal
			# ascii will not be affected by this. 
			packet = packet.encode()
		
		if self._pkt_end is not None:
			packet = packet + self._pkt_end
		if self._pkt_start is not None:
			packet = self._pkt_start + packet
			
		if self.verbose_tx and self.verbose_raw:
			hex_repr = ":".join("{:02x}".format(c) for c in packet)
			logging.debug("Sending serial packet (port %s): %s" % (self._port, hex_repr))
				
		try:
			self._ser.write(packet) # write_timeout=0, so not blocking
			# ~ self._ser.flush() # Not necessary, sometimes harmful?
			return True
		except serial.SerialException:
			self._ser = None
			if self.verbose_fail:
				logging.error("Failed sending serial data (port %s)." % (self._port))
			return False

	# Empty the transmit buffer
	def purge_tx_buf(self):
		with self._tx_lock:
			self._tx_buf = []	
			
	# Empty the receive buffer
	def purge_rx_buf(self):
		with self._rx_lock:
			self._rx_reset()
	
	# Empty the transmit and receive buffers
	def purge_bufs(self):
		self.purge_tx_buf()
		self.purge_rx_buf()
			
