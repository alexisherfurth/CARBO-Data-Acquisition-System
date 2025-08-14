'''
Handles loading hardware config files
'''

import logging
import importlib
import json5
import sys

# Each entry is (module_name, class_name) for the device object.  All
# classes should be children of the Instrument class.  Keys define the
# name used in the hardware config file.
valid_devices = {
    "ls224": (".instruments.gpib.lakeshore_224", "LakeShore224Interface"),
    "ls336": (".instruments.gpib.lakeshore_336", "SerialLakeshore336"),
    "mks_pressure": (".instruments.gpib.mks_pressure", "MKSADS1115Pressure"),
    "thermocouple": (".instruments.gpib.thermocouple", "ThermocoupleMAX31856"),
    "thales_xpcde4865": (".instruments.gpib.thales_XPCDE4865", "ThalesXPCDE4865"),
}

# Each entry is (module_name, class_name) for the logger object.  All
# classes should be children of the Logger class. Keys define the
# name used in the hardware config file.
valid_loggers = {
    "syncframelog": (".loggers.sync_frame_logger", "SyncFrameLogger"),
}

# Define valid subdevices (add more as needed)
valid_subdevices = {
    # Add subdevice mappings here if you have any
    # Example: "ls336": {"heater": (".instruments.gpib.heater", "HeaterClass")}
}

# Load all of the instruments (and loggers) specified in a given config
# file.  Returns two lists, one of instruments and one of loggers.
# Note that the loggers here are extra user-specified global loggers,
# the per-sensor default loggers are not included here.
def load_instruments(fname):
	
	instruments = []
	loggers = []
	
	logging.info("Loading instruments from config file: " + str(fname))
	
	with open(fname, 'r') as f:
		try:
			config = json5.load(f, allow_duplicate_keys=False)	
		except ValueError as e:
			logging.error("JSON5 Error: " + str(e).replace("<string>:", "Line "))
			sys.exit("Error while reading the hardware config file!  Note that the JSON5 error printed above may not be the root cause of your syntax error, it may simply be a symptom.  Please check that your file is valid JSON5 data (valid JSON data is also valid JSON5 data, see json5.org).  Online JSON5 validators can be very helpful here (e.g. https://jsonformatter.org/json5-validator).   Note most validators will show one error at a time, and you may have multiple.")
		
	for c in config:
		
		if 'type' not in c:
			sys.exit("Error loading a device from the config file, type is missing")
		
		subdevices = []
		c_type = c.pop('type')
		
		if c_type in list(valid_loggers.keys()):
			
			is_logger = True
			module_name, class_name = valid_loggers[c_type]
			
		elif c_type in list(valid_devices.keys()):
			
			is_logger = False
			module_name, class_name = valid_devices[c_type]
			
			# Remove the subdevices key so it is not passed to the device
			if 'subdevices' in c:
				subdevices = c.pop('subdevices')
				
		else:
			sys.exit("Error loading a device from the config file, bad type: " + c_type)
				
		# Load the device
		DeviceClass = get_class(module_name, class_name)
		device_obj = DeviceClass(**c)
		
		if is_logger:
			
			logging.info("Loaded global logger " + class_name)
			loggers.append(device_obj)
		
		else:
		
			instruments.append(device_obj)
			
			# Some devices have subdevices, load these as well			
			for d in subdevices:
				
				if 'type' not in d:
					sys.exit("Error loading subdevice, type is missing")
				
				d_type = d.pop('type')
				
				# Warn people still using old config syntax that things
				# have changed
				if d_type in ['agilent_e364xa','agilent_e363xa']:
					sys.exit("Please specify the full version number for GPIB controlled Agilent power supplies in your config file (ex: agilent_e3641a)")
				
				if d_type not in list(valid_subdevices[c_type].keys()):
					sys.exit("Error loading subdevice, bad type: " + d_type)
					
				# Load the subdevice
				module_name, class_name = valid_subdevices[c_type][d_type]
				SubDeviceClass = get_class(module_name, class_name)
				subdevice_obj = SubDeviceClass(device_obj, **d)
				instruments.append(subdevice_obj)

	return instruments, loggers

def get_class(module_name, class_name):
    """
    Dynamically import a module and return the specified class.
    
    Args:
        module_name: The module path (e.g., ".instruments.gpib.lakeshore_224")
        class_name: The class name to import (e.g., "LakeShore224Interface")
    
    Returns:
        The imported class object
    """
    try:
        # Import the module relative to pyhkdlib package
        module = importlib.import_module(module_name, package='pyhkdlib')
        return getattr(module, class_name)
    except ImportError as e:
        sys.exit(f"Error importing module {module_name}: {e}")
    except AttributeError as e:
        sys.exit(f"Error finding class {class_name} in module {module_name}: {e}")
