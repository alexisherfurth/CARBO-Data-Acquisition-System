import numpy as np
import os
import importlib
import logging

import units.units as units
from . import temperature
from .temperature import helpers as thelp
from . import pressure

# Creates and returns a calibration function based on a list of values
def load_interp(fn):
	
	assert os.path.exists(fn)
	
	d = np.loadtxt(fn)
	d = d[d[:,0].argsort()] # Sort
	x0, y0 = d[:,0], d[:,1]
	
	logging.debug("Loading interpolation file " + fn)
	
	def f(x):
		return np.interp(x, x0, y0, left=np.nan, right=np.nan)
	
	f.__name__ = fn
	
	return f

# Safety wrapper for calibration functions
def _calib_wrapper(func, val):
	try:
		return func(val)
	except ValueError:
		# Common for out-of-range errors, don't bother reporting
		return 0.0
	except Exception as e:
		logging.error("Contained " + e.__class__.__name__ + " in calib function " + str(func.__name__) + " with argument " + str(val))
		return 0.0

# Try to find a calibration function matching the given name
def get_calib(name, raise_on_fail=True):
		
	# Simple unit conversion
	try:
		loaded_func = getattr(units, name)
		logging.debug("Loaded unit calib function " + name)
		return lambda x: _calib_wrapper(loaded_func, x)
	except AttributeError:
		pass
	
	for mod in [temperature, pressure]:
	
		# Python function
		try:
			pkg = importlib.import_module(mod.__name__ + '.' + name)
			loaded_func = getattr(pkg, name)
			logging.debug("Loaded python calib function " + name)
			return lambda x: _calib_wrapper(loaded_func, x)
		except (ImportError, AttributeError) as e:
			pass
			
		# Interpolation file
		folder = os.path.abspath(os.path.join(mod.__file__, os.pardir)) 
		fn = os.path.join(folder, name + '.interp')
		if os.path.exists(fn):
			logging.debug("Loaded interp calib function " + name)
			interp_func = load_interp(fn) # Do not condense with following line, it re-loads the file each time
			return lambda x: _calib_wrapper(interp_func, x)
			
	# COF file
	folder = os.path.abspath(os.path.join(temperature.__file__, os.pardir)) 
	fn = os.path.join(folder, name + '.cof')
	if os.path.exists(fn):
		logging.debug("Loaded cof calib function " + name)
		return lambda x: _calib_wrapper(thelp.load_cof(fn), x)
		
	if raise_on_fail:
		raise NameError("No calibration file found for " + name)
		
	return None
