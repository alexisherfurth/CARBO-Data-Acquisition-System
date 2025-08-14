'''
A set of functions to facilitate commanding pyhkfridge from an external
application
'''



import socket
import urllib.request, urllib.parse, urllib.error
import logging
import psutil

from pyhkfridgeremote.settings import PYHKFRIDGE_PROCNAME, PYHKFRIDGE_IP, PYHKFRIDGE_BASE_PORT, PYHKFRIDGE_MAX_PORT
from packetcomm.packetcomm import send_single_packet

# Get a list of active listening UDP ports for all pyhkfridge instances
# on this machine
def pyhkfridge_get_active_ports():
	
	active = []
	for proc in psutil.process_iter():
		if proc.name() == PYHKFRIDGE_PROCNAME:
			for c in proc.connections():
				if c.type == socket.SOCK_STREAM:
					ip, port = c.laddr
					if (port >= PYHKFRIDGE_BASE_PORT) and (port <= PYHKFRIDGE_MAX_PORT):
						active.append(port)	
	active.sort()
	return active

# Tell pyhkfridge to load a new script
# port: port of pyhkfridge instance you want to target
# filename: new script
# retry: do not return until the packet is sent successfully
# Returns True on success or False on failure.
def pyhkfridge_load(port, filename, retry=True):
	fn = urllib.parse.quote(filename)
	logging.info('Requesting script load from pyhkfridge: ' + fn)
	data = 'load,' + fn
	return send_single_packet(PYHKFRIDGE_IP, port, data, retry)

# Tell pyhkfridge to reload the config file
# port: port of pyhkfridge instance you want to target
# retry: do not return until the packet is sent successfully
# Returns True on success or False on failure.
def pyhkfridge_reload_conf(port, retry=True):
	logging.info('Requesting reload_conf from pyhkfridge')
	data = 'reload_conf'
	return send_single_packet(PYHKFRIDGE_IP, port, data, retry)

# Tell pyhkfridge to start
# port: port of pyhkfridge instance you want to target
# retry: do not return until the packet is sent successfully
# Returns True on success or False on failure.
def pyhkfridge_start(port, retry=True):
	logging.info('Requesting start from pyhkfridge')
	data = 'start'
	return send_single_packet(PYHKFRIDGE_IP, port, data, retry)
	
# Tell pyhkfridge to stop
# port: port of pyhkfridge instance you want to target
# retry: do not return until the packet is sent successfully
# Returns True on success or False on failure.
def pyhkfridge_stop(port, retry=True):
	logging.info('Requesting stop from pyhkfridge')
	data = 'stop'
	return send_single_packet(PYHKFRIDGE_IP, port, data, retry)

# Tell pyhkfridge to skip a step
# port: port of pyhkfridge instance you want to target
# retry: do not return until the packet is sent successfully
# Returns True on success or False on failure.
def pyhkfridge_skip(port, retry=True):
	logging.info('Requesting skip from pyhkfridge')
	data = 'skip'
	return send_single_packet(PYHKFRIDGE_IP, port, data, retry)
	
# Tell pyhkfridge to turn autorun on
# port: port of pyhkfridge instance you want to target
# retry: do not return until the packet is sent successfully
# Returns True on success or False on failure.
def pyhkfridge_auto_on(port, retry=True):
	logging.info('Requesting auto_on from pyhkfridge')
	data = 'auto_on'
	return send_single_packet(PYHKFRIDGE_IP, port, data, retry)
	
# Tell pyhkfridge to turn autorun off
# port: port of pyhkfridge instance you want to target
# retry: do not return until the packet is sent successfully
# Returns True on success or False on failure.
def pyhkfridge_auto_off(port, retry=True):
	logging.info('Requesting auto_off from pyhkfridge')
	data = 'auto_off'
	return send_single_packet(PYHKFRIDGE_IP, port, data, retry)

# Tell pyhkfridge the new autorun time
# port: port of pyhkfridge instance you want to target
# hour: hour of time to start (24 hour time)
# minute: minute of time to start
# retry: do not return until the packet is sent successfully
# Returns True on success or False on failure.
def pyhkfridge_auto_time(port, hour, minute, retry=True):
	logging.info('Requesting autorun time from pyhkfridge: ' + str(hour) + ',' + str(minute))
	data = 'auto_time,' + str(hour) + ',' + str(minute)
	return send_single_packet(PYHKFRIDGE_IP, port, data, retry)