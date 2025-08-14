'''
A set of functions used to command pyhkd from external applications
'''



import urllib.request, urllib.parse, urllib.error
import logging

from pyhkdremote.settings import PYHKD_IP, PYHKD_PORT
from packetcomm.packetcomm import send_single_packet

# Tell pyhkd to set a value.
# command: command string to send
# name: name of the current to change
# value: value to request
# retry: do not return until the packet is sent successfully
# Returns True on success or False on failure.
def pyhkd_set(command, name, value, retry=True):
	
	# Validation is done server-side, no sense repeating it here
	n = urllib.parse.quote(name)
	v = str(value)
	logging.debug('Requesting value set from pyhkd: ' + command + ', ' + n + ', ' + v)
	
	data = command + ',' + n + ',' + v
	
	return send_single_packet(PYHKD_IP, PYHKD_PORT, data, retry)

# Tell pyhkd to set a specific value.
# name: name of the item to change
# value: value to request
# retry: do not return until the packet is sent successfully
# Returns True on success or False on failure.
def pyhkd_set_voltage(name, value, retry=True): return pyhkd_set('vset', name, value, retry)
def pyhkd_set_power(name, value, retry=True): return pyhkd_set('pset', name, value, retry)
def pyhkd_set_temperature(name, value, retry=True): return pyhkd_set('tset', name, value, retry)
def pyhkd_set_current(name, value, retry=True): return pyhkd_set('iset', name, value, retry)
def pyhkd_set_currentramp(name, value, retry=True): return pyhkd_set('irset', name, value, retry)
def pyhkd_set_state(name, value, retry=True): return pyhkd_set('sset', name, value, retry)

