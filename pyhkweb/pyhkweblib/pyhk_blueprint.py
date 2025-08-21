import flask
import logging
import ast
import datetime
import json
import os
import urllib.request, urllib.parse, urllib.error
import requests
import time
import platform
import psutil
import numpy as np

from collections import OrderedDict

from pyhkdremote.data_loader import pyhkd_get_filename, pyhkd_get_latest, pyhkd_get_config_dir, pyhkd_get_names
from pyhkdremote.settings import DATA_LOG_FOLDER
from pyhkdremote.control import pyhkd_set
from livecfg.livecfg import LiveCfg
from .cache import cache
import units.units as units
import gitinfo
from pyhkdlib.instruments.gpib.thales_XPCDE4865 import ThalesXPCDE4865

# Returns the correct function to convert between two units ("K", "C", etc).
# Returns None on failure
def get_unit_func(start, finish):
	funcname = str(start).replace('/','p') + '2' + str(finish).replace('/','p')
	try:
		func = getattr(units, funcname)
		return func
	except AttributeError:
		return None

pyhkpage = flask.Blueprint('pyhkpage', __name__,template_folder='templates')

# Check if a page name is a valid page of the given type.  If so, return 
# it.  If not, return the first such valid page.  If no valid page
# exists, return None.
def find_page_name(cur_page_id, page_config, page_type):

	if cur_page_id is not None:
		if cur_page_id in list(page_config.keys()):
			if page_config[cur_page_id]['page_type'] == page_type:
				return cur_page_id
	
	# We have a bad name, so find the first (in order) valid page name	
	for k in flask.current_app.config['page_ids']:
		if page_config[k]['page_type'] == page_type:
			return k
			
	# No valid pages exist
	return None

# Inject global variables used by all templates
@pyhkpage.context_processor
def inject_settings():
	settings = {
		'page_ids': flask.current_app.config['page_ids'], 
		'maintenance_mode': flask.current_app.config['internal_settings'].get("maintenance_mode", False),
		'site_name': flask.current_app.config['internal_settings'].get("site_name", None),
		'unit_symbol_default': units.unit_symbol_default,
		'unit_id_short': units.unit_id_short
	}
	return settings
    
@pyhkpage.route("/control/pyhkd/", methods=["POST"])
def request_pyhkd_set():
	# pyhkd checks its inputs carefully, no sense repeating that here
	command = flask.request.form.get('command')
	name = flask.request.form.get('name')
	value = flask.request.form.get('value')
	pyhkd_set(command, name, value, retry=False)
	return "Request Sent"

# None for target_date or num_days means to use the current local session value
@pyhkpage.route("/")
@pyhkpage.route("/plot")
@pyhkpage.route("/plot/<cur_page_id>")
@pyhkpage.route("/plot/<cur_page_id>/<int:num_days>/<target_date>")
@pyhkpage.route("/plot/<cur_page_id>/<int:num_days>/<target_date>/")
def plot(cur_page_id=None, target_date=None, num_days=None, plot_mode=0, plot_dt=None):
	
	page_config = flask.current_app.config['page_config']
	cur_page_id = find_page_name(cur_page_id, page_config, page_type='plot')
	
	if cur_page_id is None:
		return "No plot pages exist!", 400
	
	page_title = page_config.get(cur_page_id,{}).get('page_title','Plot')
	plots = page_config[cur_page_id].get("plots", [])
	num_plots = len(plots)
	
	# Build the axis labels
	labels = ['']*num_plots
	unit_labels = ['']*num_plots
	for i in range(num_plots):
		labels[i] = units.unit_id_short.get(plots[i]['subfolder_label'], 'Unknown')
		dflt = units.unit_symbol_default.get(plots[i]['subfolder_label'], '')
		unit_labels[i] = plots[i].get("units", dflt)
		if unit_labels[i]:
			labels[i] += ' [' + unit_labels[i] + ']'
		else:
			unit_labels[i] = 'none' # Value for the url, not shown
		unit_labels[i] = unit_labels[i].replace('/','p')
	
	return flask.render_template("plot.html",   cur_page_id = cur_page_id, 
												page_config = page_config,
												page_title = page_title,
												num_plots = num_plots,
												axis_label = labels,
												target_date = target_date,
												plot_mode = plot_mode,
												plot_dt = plot_dt,
												num_days = num_days,
												unit_labels = unit_labels)

@pyhkpage.route("/plot/<cur_page_id>/<int:num_days>/<target_date>/compare")
@pyhkpage.route("/plot/<cur_page_id>/<int:num_days>/<target_date>/compare/<signed_int:plot_dt>sec")
def plot_compare(cur_page_id, target_date, num_days, plot_dt=None, plot_mode=1):
	return plot(cur_page_id=cur_page_id, target_date=target_date, num_days=num_days, plot_mode=plot_mode, plot_dt=plot_dt)
																				
valid_generic_pages = ["tables", "export", "panel", "thales", "safety_dashboard", "ls224"]
@pyhkpage.route("/<page_type>")
@pyhkpage.route("/<page_type>/<cur_page_id>")
def generic_page(page_type, cur_page_id=None):
	if page_type not in valid_generic_pages:
		return "Invalid page type!", 400
	page_config = flask.current_app.config['page_config']
	cur_page_id = find_page_name(cur_page_id, page_config, page_type=page_type)
	if cur_page_id is None:
		return "No " + page_type + " pages exist!", 400
	page_title = page_config.get(cur_page_id,{}).get('page_title', page_type.capitalize())
	return flask.render_template(page_type + ".html",cur_page_id = cur_page_id, 
												page_config = page_config,
												page_title = page_title,
												axis_labels = units.unit_labels_full)
							
# value_names should be given as repr(list) for passing to ast.literal_eval.
@pyhkpage.route("/data/current/<subfolder_label>/<units_name>/<value_names>.json")
@pyhkpage.route("/data/current/<subfolder_label>/default/<value_names>.json")
def get_data_current(subfolder_label, value_names, units_name='default'):

	# Try to load the unit conversion function
	dflt = units.unit_symbol_default.get(subfolder_label)
	conv_func = None
	#logging.debug("Requested units: " + str(units_name) + " (" + str(subfolder_label) + ")")
	if units_name not in ['default', dflt]:
		conv_func = get_unit_func(dflt, units_name)
		logging.debug("Attempting to load unit conversion from " + str(dflt) + " to " + str(units_name) + ". Found: " + str(conv_func))
	
	# Data comes in as repr(actual_list), so we need to convert it.
	# ast.literal_eval is safe with untrusted strings.
	try:
		value_names = ast.literal_eval(value_names)
	except:
		logging.error("Bad value names passed to get_data_current: " + str(value_names))
		return "", 400
		
	results = OrderedDict()
	for n in value_names:
		ts, v = pyhkd_get_latest(DATA_LOG_FOLDER, subfolder_label, n, return_as_datetime = False)
		if ts is not None:
			
			if v is not None:
				
				if conv_func is not None:
					v = conv_func(v)
				
				# NaN isn't allowed in strict json, was causing some issues.
				# None converts to null and is allowed.
				if not np.isfinite(v):
					v = None
				
			results[n] = (int(1000*ts), v)
			
	return json.dumps(results)
		
	
# Load a day's worth of archived data for a list of sensors, downsampling
# each sensor as needed.  target_date is a string of the form YYYYMMDD.
# value_names should be given as repr(list) for passing to ast.literal_eval.
# max_points_each is max reported points for all days for one value_name.
# Currently each day for each value_name will be downsampled to
# max_points_each/num_days points, but this may change in the future.
PLOTMODE_NORMAL = 0
PLOTMODE_LIVECOMPARE = 1
PLOTMODE_FASTDATA = 2
VALID_PLOTMODES = [PLOTMODE_NORMAL, PLOTMODE_LIVECOMPARE, PLOTMODE_FASTDATA]

MAX_TOTAL_POINTS = 30000
PLOT_URL = "/data/archive/<target_date>/mode<int:plot_mode>/<signed_int:plot_dt>sec/<int:num_days>/<subfolder_label>/<units_name>/<value_names>.csv"
@pyhkpage.route(PLOT_URL)
@pyhkpage.route(PLOT_URL.replace("<target_date>", "today"))
def get_data_archive(subfolder_label, value_names, units_name='default', target_date = None, num_days = 1, plot_mode = PLOTMODE_NORMAL, 
	plot_dt = 0, max_points_each = 5000):
	
	logging.debug("Data archive requested")
	
	if target_date is None:
		target_date = datetime.date.today()
	else:
		try:
			target_date = datetime.datetime.strptime(target_date, '%Y%m%d').date()
		except ValueError:
			logging.error("Bad target date passed to get_data_archive: " + str(target_date))
			return "", 400

	if plot_mode not in VALID_PLOTMODES:
		plot_mode = PLOTMODE_NORMAL
		
	try:
		num_days = int(num_days)
	except:
		logging.error("Bad day count passed to get_data_archive: " + str(num_days))
		return "", 400
	
	# Restrict the date range
	num_days = np.clip(num_days, 1, 14)

	# Data comes in as repr(actual_list), so we need to convert it.
	# ast.literal_eval is safe with untrusted strings.
	try:
		value_names = ast.literal_eval(value_names) 
		if not isinstance(value_names, list):
			value_names = [value_names]
	except:
		logging.error("Bad value names passed to get_data_archive: " + str(value_names))
		return "", 400
		
	# Set harsher point count limits for very busy plots
	max_points_each = min(max_points_each, int(MAX_TOTAL_POINTS / len(value_names)))
	
	# Set harsher point count limits for very busy plots
	max_points_each = min(max_points_each, int(MAX_TOTAL_POINTS / len(value_names)))
	
	# We can't use the cached function for today or the future, both
	# to prevent incomplete data loads and to keep it from caching
	# for a day that isn't complete. 
	if target_date < datetime.date.today() and plot_mode == PLOTMODE_NORMAL:
		return get_data_archive_helper(subfolder_label, value_names, 
					target_date, num_days, max_points_each, units_name, 
					plot_mode=0, plot_dt=0)
	else:
		logging.debug("Skipping data archive cache, date isn't in the past")
		return get_data_archive_helper.uncached(subfolder_label, value_names, 
					target_date, num_days, max_points_each, units_name, 
					plot_mode, plot_dt)


# Cached helper function doing the data loading/processing for
# get_data_archive.  Assumed inputs are already verified and transformed 
# to their proper types - value_names is a list, target_date is a 
# datetime.date, num_days is a postive integer.
@cache.memoize()
def get_data_archive_helper(subfolder_label, value_names, target_date, 
	num_days, max_points_each, units_name, plot_mode, plot_dt):
		
	# Override, doesn't make sense to load multiple days for fast mode
	if plot_mode == PLOTMODE_FASTDATA:
		num_days = 1

	start_time = time.time()
		
	# Allocate the same number of points per day.
	max_points_each /= num_days
	
	dates_archive = [target_date - datetime.timedelta(days=n) for n in range(num_days)]
	dates_live = [datetime.date.today() - datetime.timedelta(days=n) for n in range(num_days)]
	num_names = len(value_names)
	num_files = num_names * num_days
	data = []
	
	logging.info("Loading " + str(num_files) + " archived files from " + str(target_date))
	
	# Try to load the unit conversion function
	dflt = units.unit_symbol_default.get(subfolder_label)
	conv_func = None
	logging.debug("Requested units: " + str(units_name) + " (" + str(subfolder_label) + ")")
	if units_name not in ['default', dflt]:
		conv_func = get_unit_func(dflt, units_name)
		logging.debug("Attempting to load unit conversion from " + str(dflt) + " to " + str(units_name) + ". Found: " + str(conv_func))
	
	# We need to time shift the archived data to overplot it with live data if relevant
	dates_list = [dates_archive]
	timeshift_ms_list = [0]
	num_entries = num_names
	if plot_mode == PLOTMODE_LIVECOMPARE:
		num_entries = 2 * num_names
		dates_list = [dates_live, dates_archive]
		timeshift_ms_list = [0, plot_dt * 1000 + ((datetime.date.today() - target_date).days) * 24 * 3600 * 1000]

	logging.debug("Using plot mode " + str(plot_mode))
	
	for iii in range(len(dates_list)):
		dates = dates_list[iii]
		timeshift_ms = timeshift_ms_list[iii]
		for vi in range(num_names):
			for d in dates:
				filename = pyhkd_get_filename(DATA_LOG_FOLDER, subfolder_label, value_names[vi], d) 
				if os.path.exists(filename):	
					with open(filename, 'r') as fhandle:
			
						lines = fhandle.read().split('\n')
						nlines = len(lines)
						
						# Check if we should be downsampling or returning
						# the newest data.  Either way, we need to limit
						# to at most max_points_each points.
						downsample = max(1, nlines // max_points_each)
						startline = 0
						if (plot_mode == PLOTMODE_FASTDATA) and downsample > 1:
							downsample = 1
							startline = int(nlines - max_points_each)
							logging.debug("Returning only the latest points for %s on %s" % (value_names[vi], d))
							
						if downsample > 1:
							logging.debug("Downsampling %s on %s by a factor of %i" % (value_names[vi], d, downsample))
			
						for l in range(startline, nlines):
				
							if (l % downsample) != 0:
								continue

							lines[l] = lines[l].split('\t')
				
							# Each line should have at least 2 fields, but
							# can possibly have more (sync num)
							if len(lines[l]) < 2:
								lines[l] = None
								print("Bad line: " + str(lines[l]))
								continue
					
							try:
								if conv_func is not None:
									lines[l][1] = "%0.5g" % (conv_func(float(lines[l][1])))
					
								# Insert null values for the other curves at this timestamp
								lines[l][0] = int(1000*float(lines[l][0])) + timeshift_ms
								vis = vi + iii*num_names
								lines[l][1] = ','*vis + lines[l][1] + ','*(num_entries-(vis+1))
							except:
								lines[l] = None
								print("Bad line: " + str(lines[l]))
								continue
					
							data.append(lines[l])
				else:
					#logging.debug("File doesn't exist: " + str(filenames[f]))
					pass
	
	load_time = time.time()
	
	data.sort()
	
	sort_time = time.time()
	
	# Merge entries with identical timestamps (prevents viewer issues
	# on the client side)
	i = 0
	while i < len(data)-1:
		if data[i][0] == data[i+1][0]:
			a1 = data[i][1].split(',')
			a2 = data[i+1][1].split(',')
			for j in range(len(a1)):
				a1[j] = a1[j] or a2[j]
			data[i][1] = ','.join(a1)
			data.pop(i+1)
		else:
			i += 1
			
	merge_time = time.time()
	
	#~ result_js = "data=[[\"Date\",\"" + '\",\"'.join(value_names) + '\"],'
	result_csv = ''
	for d in data:
		if d is not None:
			result_csv +=  str(d[0]) + ',' + d[1] + '\n'
			
	end_time = time.time()
	
	logging.debug("Data archive request serviced for %i day(s) of %i sensors, max %i points per sensor per day. %i ms to load, %i ms to sort, %i ms to merge, %i ms to form output." % (num_days, len(value_names), max_points_each, 1000*(load_time-start_time), 1000*(sort_time-load_time), 1000*(merge_time-sort_time), 1000*(end_time-merge_time)))
	
	return result_csv

												
@pyhkpage.route("/about")
def about():
	page_config = flask.current_app.config['page_config']
	cur_page_id = find_page_name(None, page_config, page_type='about')
	page_title = page_config.get(cur_page_id,{}).get('page_title','About')
	
	load = psutil.getloadavg()
	ram = psutil.virtual_memory()
	
	kwargs = {
		'cur_page_id': cur_page_id,
		'page_config': page_config,
		'page_title': page_title,
		'boot_git_branch': gitinfo.BOOT_GIT_BRANCH,
		'boot_git_date': gitinfo.BOOT_GIT_DATE,
		'boot_git_commit': gitinfo.BOOT_GIT_COMMIT,
		'server_hostname': platform.node(),
		'server_platform': platform.platform(),
		'server_pyver': platform.python_version(),
		'server_ncpu': psutil.cpu_count(),
		'server_load1': load[0],
		'server_load5': load[1],
		'server_load15': load[2],
		'server_ramtot': ram.total / 1024**3,
		'server_ramused': (ram.total-ram.available) / 1024**3,
	}
	
	return flask.render_template("about.html", **kwargs)		

@pyhkpage.route("/data/export/<subfolder_label>/<date_start>/<date_stop>/names")
def get_export_names(subfolder_label, date_start, date_stop):
	
	try:
		date_start = datetime.datetime.strptime(date_start, '%Y%m%d')
		date_stop = datetime.datetime.strptime(date_stop, '%Y%m%d')
	except ValueError:
		logging.error("Bad target dates passed to get_export_names: " + str(date_start) + " " + str(date_stop))
		return "", 400
		
	if date_stop < date_start:
		logging.error("Bad date order passed to get_export_names: " + str(date_start) + " " + str(date_stop))
		return "", 400
	
	names_all = set()
	d = date_start
	while d <= date_stop:
		names_day = pyhkd_get_names(DATA_LOG_FOLDER, subfolder_label, d)	
		if names_day is not None:
			for n in names_day:
				names_all.add(n)
		d += datetime.timedelta(days=1)
	names_all = list(names_all)	
	names_all.sort()
	
	txt = ''
	for n in names_all:
		# Handle '#' differently because it has special meaning in urls
		txt += "<option value='%s'>%s</option><br>" % (n.replace('#','%23'),n)
		 
	return txt
	
@pyhkpage.route("/data/export/<subfolder_label>/<date_start>/<date_stop>/<value_name>.txt")
def get_export_data(subfolder_label, date_start, date_stop, value_name):

	output_filename = "pyhk_export_%s_%s_%s_%s.txt" % (subfolder_label, urllib.parse.quote_plus(value_name), date_start, date_stop)

	try:
		date_start = datetime.datetime.strptime(date_start, '%Y%m%d')
		date_stop = datetime.datetime.strptime(date_stop, '%Y%m%d')
	except ValueError:
		logging.error("Bad target dates passed to get_export_data: " + str(date_start) + " " + str(date_stop))
		return "", 400
		
	if date_stop < date_start:
		logging.error("Bad date order passed to get_export_data: " + str(date_start) + " " + str(date_stop))
		return "", 400

	txt = ''
	d = date_start
	while (d <= date_stop):
		input_filename = pyhkd_get_filename(DATA_LOG_FOLDER, subfolder_label, value_name, d)			
		if os.path.exists(input_filename):
			with open(input_filename, 'r') as fin:
				txt += fin.read()
		d += datetime.timedelta(days=1)

	response = flask.make_response(txt)

	# Tell the browser to download the file, not show it
	response.headers["Content-Disposition"] = "attachment; filename=%s" % (output_filename,)

	return response	


# Load and return the objects in a live config file
def get_live_config(fname):
	
	cfg = []
	cf = None

	if fname is not None:
		fname = os.path.join(pyhkd_get_config_dir(), fname)
		if os.path.exists(fname):
			cf = LiveCfg(fname)
			cfg = cf.load()
	
	if not isinstance(cfg, list):
		cfg = []
	
	return cfg, cf
											

# Thales control routes
thales = ThalesXPCDE4865(port='/dev/ttyUSB0')

@pyhkpage.route("/control/thales/connect", methods=["POST"])
def thales_connect():
    try:
        thales.connect()
        return "Connected"
    except Exception as e:
        return f"Connect failed: {e}"

@pyhkpage.route("/control/thales/disconnect", methods=["POST"])
def thales_disconnect():
    try:
        thales.disconnect()
        return "Disconnected"
    except Exception as e:
        return f"Disconnect failed: {e}"

@pyhkpage.route("/control/thales/set_frequency", methods=["POST"])
def thales_set_frequency():
    freq = flask.request.json.get("frequency")
    try:
        thales.set_frequency(float(freq))
        return f"Frequency set to {freq} Hz"
    except Exception as e:
        return f"Set frequency failed: {e}"

@pyhkpage.route("/control/thales/read_frequency", methods=["POST"])
def thales_read_frequency():
    try:
        freq = thales.read_frequency()
        return str(freq)
    except Exception as e:
        return f"Read frequency failed: {e}"

@pyhkpage.route("/control/thales/update_mode", methods=["POST"])
def thales_update_mode():
    mode = flask.request.json.get("mode")
    temp = flask.request.json.get("temp")
    volt = flask.request.json.get("volt")
    max_volt = flask.request.json.get("maxVolt")
    
    logging.info(f"Update mode request: mode={mode}, temp={temp}, volt={volt}, maxVolt={max_volt}")
    
    try:
        if mode == "temp":
            max_voltage = None
            if max_volt and float(max_volt) > 0:
                max_voltage = float(max_volt)
                if max_voltage > 28:
                    max_voltage = 28
                    logging.warning(f"Max voltage {max_volt}V exceeds limit, capped at 28V")
            
            # Call the temperature control method
            actual_voltage = thales.set_temperature(float(temp), max_voltage)
            
            response = f"Started automatic temperature control: target={temp}K"
            if max_voltage:
                response += f", max voltage={max_voltage}V"
            response += f", actual voltage set: {actual_voltage:.2f}V"
            return response
        else:
            # Use manual voltage mode
            voltage_to_set = float(volt)
            if voltage_to_set > 28:
                voltage_to_set = 28
                logging.warning(f"Voltage {volt}V exceeds limit, capped at 28V")
            
            actual_voltage = thales.set_voltage(voltage_to_set)
            return f"Set manual voltage to {actual_voltage:.2f}V"
    except Exception as e:
        logging.error(f"Update mode failed: {e}")
        return f"Update mode failed: {e}"

@pyhkpage.route("/control/thales/stop_temperature_control", methods=["POST"])
def thales_stop_temperature_control():
    """Stop automatic temperature control"""
    try:
        thales.stop_automatic_temperature_control()
        return "Automatic temperature control stopped"
    except Exception as e:
        return f"Stop temperature control failed: {e}"

@pyhkpage.route("/control/thales/temperature_control_status", methods=["POST"])
def thales_temperature_control_status():
    """Get temperature control status"""
    try:
        status = thales.get_temperature_control_status()
        return json.dumps(status)
    except Exception as e:
        return f"Get status failed: {e}"

@pyhkpage.route("/control/thales/read_temperature", methods=["POST"])
def thales_read_temperature():
    try:
        temp = thales.read_temperature()
        return str(temp)
    except Exception as e:
        return f"Read temperature failed: {e}"

@pyhkpage.route("/control/thales/read_voltage", methods=["POST"])
def thales_read_voltage():
    try:
        voltage = thales.read_voltage()
        return str(voltage)
    except Exception as e:
        return f"Read voltage failed: {e}"

@pyhkpage.route("/control/thales/start", methods=["POST"])
def thales_start():
    try:
        thales.enable(True)
        return "Cryocooler started"
    except Exception as e:
        return f"Start failed: {e}"

@pyhkpage.route("/control/thales/stop", methods=["POST"])
def thales_stop():
    try:
        thales.enable(False)
        return "Cryocooler stopped"
    except Exception as e:
        return f"Stop failed: {e}"

@pyhkpage.route("/control/thales/apply_slow_start", methods=["POST"])
def thales_apply_slow_start():
    try:
        params = flask.request.json
        thales.apply_slow_start(
            ssf=float(params.get('ssf', 100)),
            ss1=float(params.get('ss1', 5)),
            ss2=float(params.get('ss2', 60)),
            ss3=float(params.get('ss3', 81)),
            sv1=float(params.get('sv1', 920)),
            sv2=float(params.get('sv2', 1040))
        )
        return "Slow start parameters applied"
    except Exception as e:
        return f"Apply slow start failed: {e}"

@pyhkpage.route("/control/thales/end_slow_start", methods=["POST"])
def thales_end_slow_start():
    try:
        thales.end_slow_start()
        return "Slow start sequence ended"
    except Exception as e:
        return f"End slow start failed: {e}"

@pyhkpage.route("/control/thales/set_pid_gains", methods=["POST"])
def thales_set_pid_gains():
    try:
        kp = float(flask.request.json.get("kp", 1.0))
        ki = float(flask.request.json.get("ki", 0.1))
        thales.set_pid_gains(kp, ki)
        return f"PID gains set: Kp={kp:.2f}, Ki={ki:.2f}"
    except Exception as e:
        return f"Set PID gains failed: {e}"

@pyhkpage.route("/control/thales/read_pid_gains", methods=["POST"])
def thales_read_pid_gains():
    try:
        kp, ki = thales.read_pid_gains()
        return json.dumps({"kp": kp, "ki": ki})
    except Exception as e:
        return f"Read PID gains failed: {e}"

@pyhkpage.route("/control/thales/set_ready_window", methods=["POST"])
def thales_set_ready_window():
    try:
        window = float(flask.request.json.get("window", 10.0))
        thales.set_ready_window(window)
        return f"Ready window set to {window:.2f} mV"
    except Exception as e:
        return f"Set ready window failed: {e}"
