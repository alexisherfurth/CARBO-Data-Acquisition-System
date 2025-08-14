
'''
A collection of unit conversion functions
'''
import math
import logging

# Chosen base units
unit_symbol_default = {
	'temperature': 'K',
	'voltage': 'V',
	'resistance': 'Ohms',
	'current': 'A',
	'currentramp': 'A/s',
	'power': 'W',
	'state': '',
	'bfield': 'T',
	'pressure': 'Torr',
	'relhumidity': '%',
	'energy': 'J',
	'frequency': 'Hz',
	'time': 's',
	'number': '',
	'adu': '',
	'dac': '',
	'fraction'	: '',
	'angle': 'deg',
	'position': 'm',
	'percentage': '%'
}

# Generate units for first derivatives of base units
for key, val in unit_symbol_default.copy().items():
	if val == '':
		dval = '1/s'
	else:
		dval = val + '/s'
	unit_symbol_default[key + 'deriv'] = dval

# Short(ish) and unique representation of the unit
unit_id_short = { 
	'temperature': 'Temperature',
	'voltage': 'Voltage',
	'resistance': 'R',
	'current': 'I',
	'currentramp': 'dI/dt',
	'power': 'Power',
	'state': 'State',
	'bfield': 'B',
	'pressure': 'Pressure',
	'relhumidity': 'RH',
	'energy': 'E',
	'frequency': 'f',
	'time': 't',
	'number': 'Num',
	'adu': 'ADU',
	'dac': 'DAC',
	'fraction'	: 'Fraction',
	'angle': 'Angle',
	'position': 'x',
	'percentage': '%'
}
	
# Generate representations for first derivatives of base units
for key, val in unit_id_short.copy().items():
	unit_id_short[key + 'deriv'] = 'd' + val + '/dt'
	
# Axis labels with default units
unit_labels_full = unit_id_short.copy()
for k,v in unit_id_short.items():
	u = unit_symbol_default.get(k)
	if u:
		unit_labels_full[k] += ' [' + u + ']' 
	
##### Temperature #####

def C2K(val):
	return val + 273.15

def K2C(val):
	return val - 273.15

def K2F(val):
	return val * 1.8 - 459.67
	
def F2K(val):
	return (val + 459.67) / 1.8

##### Pressure #####

def mbar2Torr(val):
	return val * 0.7500616827
	
def Torr2mbar(val):
	return val * 1.3332236842

def Torr2psi(val):
	return val * 0.01934
	
# Torr/sec to mTorr/day
def Torrps2mTorrpday(val):
	return val * (1000 * 24 * 60 * 60)

##### Energy #####

# watt hour to joules
def Whr2J(val):
	return val * 3600.0
	
def J2Whr(val):
	return val / 3600.0
	
