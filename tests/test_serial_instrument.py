#!/usr/bin/env python3

import unittest
import sys
import os
import logging
import time
import threading

basepath = os.path.abspath(os.path.join(__file__,'..','..'))
sys.path.append(os.path.join(basepath, 'pyhkd'))
sys.path.append(os.path.join(basepath, 'common'))

from pyhkdlib.settings import APP_LOG_FORMAT
from pyhkdlib.instruments.serial_instrument import SerialInstrument

class SampleInstument(SerialInstrument):
	
	def __init__(self, *args, **kwargs):
		SerialInstrument.__init__(self, verbose_rx=True, *args, **kwargs)
		self._last_packet = None
		self._num_rx = 0
		self._lock = threading.Lock()
		
	def handle_packet(self, packet):
		with self._lock:
			logging.info("Instrument handle_packet: " + str(packet))
			self._last_packet = packet
			self._num_rx += 1
			if self._first_packet is None:
				self._first_packet = packet
	
	def reset_rx(self):
		with self._lock:
			self._last_packet = None
			self._first_packet = None
			self._num_rx = 0
			
	@property
	def num_rx(self):
		with self._lock:
			return self._num_rx
			
	@property
	def last_packet(self):
		with self._lock:
			return self._last_packet
			
	@property
	def first_packet(self):
		with self._lock:
			return self._first_packet
			

# Get the expected packet given the start and end of line values
def get_full_packet(sol, pkt, eol):
	
	if not isinstance(pkt, str):
		pkt = pkt.decode()
	if not isinstance(eol, str):
		eol = eol.decode()

	expect = pkt + eol 
	
	if sol is not None:
	
		if not isinstance(sol, str):
			sol = sol.decode()
		
		expect = sol + expect
		
	return expect
		
class TestSerialInstrument(unittest.TestCase):
	
	# Run once
	@classmethod
	def setUpClass(cls):
		
		cls.eol_list = ['\n', 'sjsasf492', '\r\n', '\u1F600', b'\n', ';\n']
		cls.sol_list = [None, None, None, None, 'asdjhad', b'#']
		cls.f_master = []
		cls.f_slave = []
		cls.inst = []
		
		# Create a set of virtual serial ports (the other end is a file
		# descriptor we can read/write).  Create several instruments
		# with different parameters.
		for i in range(len(cls.eol_list)):
			eol = cls.eol_list[i]
			sol = cls.sol_list[i]
			m, s = os.openpty()
			cls.f_master.append(m)
			cls.f_slave.append(s)
			cls.inst.append(SampleInstument(port=os.ttyname(s), baudrate=9600, pkt_start=sol, pkt_end=eol))
		
		cls.pkts = ['testing 1 2 3', 'blah\n\n\n\n', ' ', '', '\u1F601 test', b'testing 1 2 3', b'']
		cls.pkts_simple = ['aaa','b',' dff ']
				
	# Run once
	@classmethod
	def tearDownClass(cls):
		#~ cls.inst_m.close()
		#~ cls.inst_s.close()
		#~ os.close(cls.f_master)
		#~ os.close(cls.f_slave)
		pass
		
	# Run per test
	def setUp(self):
		pass
	
	# Run per test
	def tearDown(self):
		pass
	
	# Test packet receiving
	def test_receive(self):
		
		for pkt in self.pkts:
			for i in range(len(self.eol_list)):
				
				self.inst[i].reset_rx()
				
				assert self.inst[i].connected
								
				sol = self.sol_list[i]
				eol = self.eol_list[i]
				to_send = get_full_packet(sol, pkt, eol).encode()
				nsent = os.write(self.f_master[i], to_send)
				
				logging.debug("Packet: " + repr(pkt) + " EOL: " + repr(eol) +  "  SOL: " + repr(sol))
				
				if hasattr(pkt, 'decode'):
					pkt = pkt.decode()
				if hasattr(eol, 'decode'):
					eol = eol.decode()
				
				expect_first = pkt.split(eol)[0]
				
				expect_last = None
				if sol is not None:
					expect_last = pkt.split(eol)[0]
				
				assert nsent == len(to_send)

				# Wait for the receive
				start = time.time()
				while (self.inst[i].num_rx < 1):
					if time.time() - start > 0.1:
						break 

				self.assertEqual(self.inst[i].first_packet, expect_first)
				if expect_last is not None:
					self.assertEqual(self.inst[i].last_packet, expect_last)
	
	# Test packet sending
	def test_send(self):
		
		for pkt in self.pkts:
			for i in range(len(self.eol_list)):
				
				self.inst[i].send_packet(pkt)
				
				# Wait for the send
				start = time.time()
				while (self.inst[i].tx_buf_len > 0):
					if time.time() - start > 0.1:
						break 

				# Read in the other end of the virtual serial port
				ret = os.read(self.f_master[i], 1000).decode()

				expect = get_full_packet(self.sol_list[i], pkt, self.eol_list[i])					
				self.assertEqual(ret, expect)
	

	def callback(self, askid, pkt):
		logging.info("Callback " + str(askid) + " " + str(pkt))
		with self.results_lock:
			self.results[askid] = pkt
	
	# Test asks
	def test_ask(self):		
		
		for i in range(len(self.eol_list)):
			
			self.inst[i].reset_rx()
			
			self.results_lock = threading.Lock()
			self.results = {}
			
			for j in range(len(self.pkts_simple)):
				self.inst[i].send_packet(self.pkts_simple[j], resp_callback=lambda x, jj=j:self.callback(jj,x))
			
			for j in range(len(self.pkts_simple)):
				
				# Block and wait for a message.  Reads only one at a time
				# if the ask-respond timing is working correctly
				ret = os.read(self.f_master[i], 1000).decode()
				
				# Make sure the question was right
				expect = get_full_packet(self.sol_list[i], self.pkts_simple[j], self.eol_list[i])
				self.assertEqual(ret, expect)
				
				# Respond
				pkt = 'resp%i' % j
				to_send = get_full_packet(self.sol_list[i], pkt, self.eol_list[i]).encode()
				nsent = os.write(self.f_master[i], to_send)
				
			# Give the final rx time to process
			time.sleep(0.1)
					
			with self.results_lock:
				for j in range(len(self.pkts_simple)):	
					pkt = 'resp%i' % j
					self.assertEqual(pkt, self.results.get(j))



if __name__ == '__main__':
	logging.basicConfig(format=APP_LOG_FORMAT, level=logging.DEBUG)
	unittest.main()
