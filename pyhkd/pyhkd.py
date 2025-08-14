#!/usr/bin/env python3

'''
This script is the main extry point to pyhkd.  Execute it with no 
arguments to print the help.
'''

import sys
import logging
import os

from pyhkdlib.settings import *
sys.path.append(COMMON_CODE_DIR)

# Configure logging
log_filename = os.environ.get("PYHKD_LOG", "/tmp/pyhkd.log")
logging.basicConfig(filename=log_filename, format=APP_LOG_FORMAT, level=logging.DEBUG)
screen_handler = logging.StreamHandler() 
screen_handler.setFormatter(logging.Formatter(APP_LOG_FORMAT))
logging.getLogger().addHandler(screen_handler)  # Print to screen as well
logging.info("Starting pyhkd " + VERSION_STR)

import checkdep # Verifies depenencies, comment out to override

import os
import socket
import importlib
import argparse
import subprocess
import setproctitle
import psutil
import time

from pyhkdlib.data_acq import DataAcqController
from pyhkdlib.instruments.instrument_loader import load_instruments

service_name = 'pyhkd.service'
service_fname = '/lib/systemd/system/' + service_name
service_text = '''
[Unit]
Description=pyhkd
After=multi-user.target

[Service]
User=%s
Group=%s
Type=idle
ExecStart=/home/carbo/myenv/bin/python3 %s %s

[Install]
WantedBy=multi-user.target
'''
			

if __name__ == '__main__':
	
	setproctitle.setproctitle(PYHKD_PROCNAME)
	
	# Command line arguments
	parser = argparse.ArgumentParser(
		formatter_class=argparse.RawDescriptionHelpFormatter,
		description='PyHK data acquisition script.', 
		epilog='Example (TIME):  ./pyhkd.py ./config/hw_time.json5\nExample (Shortkeck):  ./pyhkd.py ./config/hw_sk.json5\n ')
	parser.add_argument('configfile', type=str, help='The hardware config file, normally located at ./config/hw_CRYOSTAT.json5.')
	parser.add_argument('--install', action='store_true', help='Install pyhkd as a systemd service that starts automatically at boot (run as root).')
	
	# They really should pass at least one argument.  If not, show the help.
	if len(sys.argv) <= 1: 
		parser.print_help()
		exit()
		
	args = parser.parse_args()
	
	if not os.path.exists(args.configfile):
		print("Config file '" + str(args.configfile) + "' cannot be found")
		exit()
	
	if args.install:
		
		print('Installing pyhkd systemd service (run as root)...')
				
		if os.path.exists(service_fname):
			os.remove(service_fname)
		
		user = os.environ["SUDO_USER"]
		with open(service_fname, "wt") as f:
			f.write(service_text % (user, user, os.path.abspath(__file__), os.path.abspath(args.configfile)))
		
		os.chmod(service_fname, 0o644)
		subprocess.call(['systemctl daemon-reload && systemctl enable ' + service_name + ' && systemctl restart ' + service_name], shell=True)
		
		print('Installation complete.  Check the log feed with pyhk/tools/log_pyhkd.  Note that you may need to give yourself journal permissions and logout:\n    sudo usermod -a -G systemd-journal USERNAME')
		
		exit()
	
	# Shame the user for running on a crappy machine, but allow it
	n_cpu = psutil.cpu_count()
	total_ram = psutil.virtual_memory().total / 1024**3 # GB
	if n_cpu < 4 or total_ram < 15:
		logging.warning("The computer you are running this on seems rather feeble (%i CPU cores, %0.1f GB RAM).  Be aware of other processes that might bog down the machine and harm performance, especially web browsers." % (n_cpu, total_ram))
		time.sleep(2) # Give them time to see it and feel the shame
	
	# Initialize the data acq process
	instruments, loggers = load_instruments(args.configfile)
	data_acq = DataAcqController(instruments, loggers)

	# Start the data acquisition loop
	data_acq.main_loop()
		
	logging.info("Exiting")
