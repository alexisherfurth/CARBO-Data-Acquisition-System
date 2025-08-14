
# Checks dependencies needed for PyHK and warns the user if something
# is missing or is too old.  The goal is to find problems and provide
# useful feedback before things start failing in ways that are not
# obvious to people.  This is more restrictive than I think we should
# be philosophically (it would be nice to try using unexpected versions
# of things in case things work), but in practice demanding certain
# version ranges greatly reduces support load for me.  End users that 
# have problems or cannot install the requested versions of packages and
# make changes to this file are asked to please contact Jon Hunacek with 
# details of their use case so it can be accommodated in future updates.

import sys
import logging

if sys.version_info.major != 3:
    sys.exit("This software is only supported on Python 3 (see help-setup.txt)")
if sys.version_info.minor < 5:
    logging.warning("This software is expecting Python 3.5+, but version %i.%i was detected.  The software is attempting to run anyway, but if you run into issues your first step should be to update to the most current stable version of Python 3.x." % (sys.version_info.major, sys.version_info.minor))

import platform

if platform.system() != 'Linux':
	logging.warning("WARNING: You seem to be running this software on something other than Linux.  While in principle this should work, it is not tested or supported so you are on your own.  As a first step, make you have updated settings files with proper paths for your OS if it does not use Unix style paths.")

# Check for the "serial" package, which is available in pip and 
# conflicts with the much more popular "pyserial" package (which is
# imported as "serial").  This causes a lot of confusion for people,
# and the developer of "serial" really needs to rename their package.
try:
	import serial.abc # Sub-module in serial but not pyserial
	sys.exit("It appears you have serial installed, which conflicts with the required package pyserial.  Please remove serial and install pyserial.  (see help-setup.txt)")
except ImportError: # Also catches subclass ModuleNotFoundError
	# The offending package isn't present, good
	pass

import importlib

# Minimum verison allowed for each required module. "None" checks the  
# module exists, but does not check versions.
min_vers = {'flask':[1,0], 'psutil':[5,6],	'setproctitle': [1,1,9], 
			'requests':[2,22], 'serial':[3,4], 'flask_caching':[1,7], 
			'scipy':[1,3], 'numpy':[1,16], 'json5':[0,8],
			'paho.mqtt':[1,5]
			}

# Maximum verison allowed for each required module. Default values are 
# computed for things not listed.
max_vers = {} 

# A mapping between module name and the pip package name for those
# where the two names are not identical
package_names = {
	'serial':'pyserial', 
	'flask_caching':'flask-caching',
	'paho.mqtt': 'paho-mqtt'
}

def verstr(v):
	return ".".join([str(x) for x in v])

for modname, min_ver in min_vers.items():
	
	if modname not in max_vers:
		# Default max version allows only the last specified version
		# value to change (1.1.34: <1.2.0, 0.1: <1.0, etc).
		if min_ver is not None:
			max_ver = list(min_ver)
			max_ver[-1] = 0
			max_ver[-2] += 1
			max_vers[modname] = max_ver
		else:
			max_ver = None
	else:
		max_ver = max_vers[modname]
	
	found_ver = None
	try:
		# Attempt to import the module and check its version
		m = importlib.import_module(modname)
		if min_ver is not None or max_ver is not None:
			try: 
				cur_ver_str = m.__version__
			except AttributeError:
				# At least one module (json5) uses VERSION instead of
				# __version__, which is less than ideal
				cur_ver_str = m.VERSION			
			found_ver = [int(j) for j in cur_ver_str.split('.')]
			if min_ver is not None:
				assert found_ver >= min_ver
			if max_ver is not None:
				assert found_ver < max_ver
	except:
		minstr = ''
		maxstr = ''
		foundstr = ''
		if min_ver is not None:
			minstr = " >=%s" % verstr(min_ver)
		if max_ver is not None:
			maxstr = " <%s" % verstr(max_ver)
		if found_ver is not None:
			foundstr = " (found %s)" % verstr(found_ver)
		name = package_names.get(modname, modname) # Rename if needed
		sys.exit("Please install %s%s%s%s (see the documentation for current package requirements)" % (name,minstr,maxstr,foundstr))

