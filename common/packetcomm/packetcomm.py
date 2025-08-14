
import sys
import socket
import logging
import time
import threading

# Connects to the server, sends a packet, and disconnects.  If "retry"
# is True, the function will keep resending and not return for up to
# "max_retries" tries if the sending is not successful. If "max_retries" 
# is +inf, this function never returns until sending succeeds. The 
# 'delim' is added to the front and back of all sent packets. Returns 
# True is sent successfully, otherwise False.
def send_single_packet(host, port, data, retry=True, delim=b'\n', max_retries=100):
	
	if isinstance(data, str):
		data = data.encode()
	
	data = delim + data + delim # Delim in front helps mitigate partial previous packets
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	
	num_tries = 0
	while True:
		
		try:
			s.connect((host, port))
		except socket.error:
			logging.error("Cannot connect to server at %s:%s" % (host, port))
			if retry:
				s.close()
				time.sleep(.5)
				continue
			else:
				s.close()
				return False
		
		send_successful = False
		
		try:
			if s.sendall(data) is None:
				send_successful = True
		except socket.error:
			logging.error("Error sending data to server at %s:%s" % (host, port))
		
		s.close()
		
		if send_successful:
			logging.debug("Packet sent to %s:%s" % (str(host), str(port)))
			return True
		elif num_tries < max_retries:
			logging.error("Packet failed to send to %s:%s, auto retrying" % (str(host), str(port)))
			time.sleep(.1)
			num_tries += 1
			continue
		else:
			logging.error("Packet failed to send to %s:%s" % (str(host), str(port)))
			return False

class PacketServer(object):
	
	PACKET_DELIM = b'\n'
	
	def __init__(self, host, port):
		
		self._socket_host = host
		self._socket_port = port
		self._thread_rx = None
		
		logging.info("Listening for packets at %s:%s" % (host, port))
		self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		
		success = False
		for nretry in range(5):
			try:
				self._socket.bind((host, port))
				self._socket.listen(5)
				self._socket.settimeout(0.01)
				success = True
				break
			except OSError:
				logging.error("Failed to bind/listen on port " + str(port) + ", retrying...")
				time.sleep(1)
		
		if not success:
			sys.exit("Failed to bind/listen on port " + str(port) + ", is another copy of the software already running?")
			
		self._active_connections = []
		self._packet_buffers = {}
		
		self._thread_rx = threading.Thread(target = self._packet_server_loop, name="Packet Server")
		
		# Don't let the threads keep the program alive
		self._thread_rx.daemon = True
		
		# Start the packet listening server
		self._threads_running = True 
		self._thread_rx.start()
	
	def __del__(self):
		
		self._threads_running = False
		
		if self._thread_rx is not None:
			self._thread_rx.join()
	
	# Called with each new packet that is received.  Override this function.
	def handle_packet(self, data):
		logging.error("Packet handler not implemented! Received: " + str(data))
	
	# Infinite loop that handles packets. Calls self.handle_packet
	# with each new packet.
	def _packet_server_loop(self):
		
		logging.info("Starting packet server loop")
		
		while self._threads_running:
	
			try:
				conn, addr = self._socket.accept()
				conn.settimeout(0.01)
				self._active_connections.append(conn)
				self._packet_buffers[conn] = b''
				logging.debug('Connection from ' + str(addr) + ', now have ' + str(len(self._active_connections)) + ' open connections')
			except socket.timeout:
				# No new connections
				pass

			for c in self._active_connections:
				try:
					logging.debug("Checking for data...")
					data = c.recv(2048)
					
					#~ logging.debug("Raw packet data received: " + str(data))
					
					# A receive of 0 length signifies a closed socket
					if len(data) == 0:
						c.close()
						self._active_connections.remove(c)
						self._packet_buffers.pop(c, None)
						logging.debug('Socket closed, now have ' + str(len(self._active_connections)) + ' open connections')
						continue
						
					dbuf = self._packet_buffers[c] + data
					dbuf_split = dbuf.split(self.PACKET_DELIM)
			
					if dbuf[-1] == self.PACKET_DELIM:
						# The buffer is full of complete packets
						packets = dbuf_split
						self._packet_buffers[c] = b''
					else:
						# The last packet is incomplete
						packets = dbuf_split[:-1]
						self._packet_buffers[c] = dbuf_split[-1]
						#~ logging.debug("Incomplete packet received, waiting for the rest")
					
					for p in packets:
						if len(p) != 0:
							self.handle_packet(p.decode())
					
				except socket.timeout:
					# No new data
					logging.debug("Socket data timeout")
					pass
		
		logging.info("Packet server loop dying")
					
if __name__ == "__main__":
	
	print("Packet communication testing")
	
	import threading
	
	server = PacketServer("localhost", 12345)
	server_thread = threading.Thread(target = server.packet_server_loop, name = "Server Loop")
	server_thread.daemon = True # Don't let this keep the program alive
	server_thread.start()
	
	while (True):
		send_single_packet("localhost", 12345, "The time is %s" % (time.time(),))
		time.sleep(.5)
