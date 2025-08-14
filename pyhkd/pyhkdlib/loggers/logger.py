'''
Logger base class
'''

class Logger():
	
	# value:		The current value to save. This is typically a 
	#				floating point number, but that is not guaranteed.
	#				Strings, NaNs, None, etc are valid inputs.		 
	# update_time:	The floating point number of seconds since the 
	#				epoch (such as time.time()) corresponding to the
	#				best guess for then the data was taken.  This
	#				may or may not be equal to the arrival time.
	# sensor_name:	A string containing the name of the sensor
	# sensor_type:	A string containing a valid sensor type
	# sync_num:		An optional integer frame number corresponding to
	#				some global or external time base.  Mapping from
	#				sync_num to update_time should not be assumed to
	#				be linear or even monotonic.
	
	def log(self, sensor_name, sensor_type, value, update_time, sync_num = None):
		raise NotImplementedError()
		
