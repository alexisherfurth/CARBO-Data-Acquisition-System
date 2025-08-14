#!/usr/bin/env python3


# Configures apache for use with pyhkweb

import os
import sys
import datetime

# Find out what system this is
if len(sys.argv) < 2 or not os.path.exists(sys.argv[1]):
	print('Execute as:\n  sudo ./conf_apache.py CONFIGFILE\nwhere CONFIGFILE is a path to a valid pyhkweb config file (see the config directory)')
	exit()

if input("Warning!  This will disable any current apache sites (it will remove everything from sites-enabled).  Type 'yes' and hit enter to continue.\n") != 'yes':
	print("Quitting")
	exit() 

conf_file = os.path.realpath(sys.argv[1])
mypath = os.path.realpath(__file__)
pyhkweb_dir = os.path.dirname(mypath)
common_dir = os.path.join(os.path.dirname(pyhkweb_dir), 'common')
user = os.getenv('SUDO_USER')

print("Using config file path:", conf_file)
print("Using pyhkweb directory:", pyhkweb_dir)
print("Using common directory:", common_dir)
print("Using user/group:", user)

le_path = '/etc/letsencrypt/live/'
use_ssl = False
if os.path.exists(le_path):
	# Get a list of the directories in the Let's Encrypt folder
	certs = [d for d in os.listdir(le_path) if os.path.isdir(os.path.join(le_path, d))]
	if len(certs) < 1:
		print("letsencrypt is installed, but no certs are found.  Not using SSL.")
	else:
		domain_name = certs[0]
		cert_dir = os.path.join(le_path, certs[0])
		print("Using letsencrypt certs in " + cert_dir + " for domain " + domain_name)
		cert_fullchain = os.path.join(cert_dir, 'fullchain.pem')
		cert_privkey = os.path.join(cert_dir, 'privkey.pem')
		use_ssl = True
else:
	print("letsencrypt was not found, so we can't use SSL.  ###HIGHLY RECOMMENDED### to install and run certbot.")
	
date_str = str(datetime.datetime.now())

apache_conf_file = '/etc/apache2/sites-available/000-pyhkweb.conf'
apache_en_file = '/etc/apache2/sites-enabled/000-pyhkweb.conf'
apache_en_dir = os.path.dirname(apache_en_file)
wsgi_file = '/usr/share/pyhk/pyhkweb.wsgi'
wsgi_dir = os.path.dirname(wsgi_file)

apache_conf_body = """
	WSGIDaemonProcess pyhkweb user=%s group=%s threads=5
	WSGIScriptAlias / %s
	<Location />
		AuthType Basic
		AuthName "Restricted Content"
		AuthUserFile /etc/apache2/.htpasswd
		Require valid-user
	</Location>
	<Directory %s>
		WSGIProcessGroup pyhkweb
		WSGIApplicationGroup %%{GLOBAL}
		Require all granted
		WSGIScriptReloading On
	</Directory>
""" % (user, user, wsgi_file, wsgi_dir)
	
if use_ssl:
	apache_conf_txt = """
	# Generated automatically %s
	<VirtualHost *:80>
		RewriteEngine on
		RewriteRule ^ https://%%{SERVER_NAME}%%{REQUEST_URI} [END,QSA,R=permanent]
	</VirtualHost>
	<VirtualHost *:443>
		%s
		SSLCertificateFile %s
		SSLCertificateKeyFile %s
		Include /etc/letsencrypt/options-ssl-apache.conf
		ServerName %s
	</VirtualHost>
	""" % (date_str, apache_conf_body, cert_fullchain, cert_privkey, domain_name)
else:
	apache_conf_txt = """
	# Generated automatically %s
	<VirtualHost *:80>
		%s
	</VirtualHost>
	""" % (date_str, apache_conf_body)

wsgi_txt = """
# Generated automatically %s
import sys
sys.path.insert(0,'%s')
sys.path.insert(0,'%s')
from pyhkweb import app_factory
application = app_factory('%s')
""" % (date_str, pyhkweb_dir, common_dir, conf_file)

try:
	with open(apache_conf_file, 'w') as f:
		f.write(apache_conf_txt)
	print("Wrote " + apache_conf_file)
except IOError:
	print("Failed to write to " + apache_conf_file + ", did you run this command with sudo?  Is apache installed?")
	exit()

try:
	for fname in os.listdir(apache_en_dir):
		fpath = os.path.join(apache_en_dir, fname)
		os.remove(fpath)
		print("Removed " + fpath)
	os.symlink(apache_conf_file, apache_en_file)
	print("Linked " + apache_en_file)
except IOError:
	print("Failed to create symlink " + apache_en_file + ", did you run this command with sudo?")
	exit()
	
try:
	if not os.path.isdir(wsgi_dir):
		os.makedirs(wsgi_dir)
	with open(wsgi_file, 'w') as f:
		f.write(wsgi_txt)
	print("Wrote " + wsgi_file)
except IOError:
	print("Failed to write to " + wsgi_file + ", did you run this command with sudo?")
	exit()

print("Enabling apache mods...")
os.system('a2enmod ssl')
os.system('a2enmod rewrite')
print("Restarting apache...")
os.system('service apache2 restart')
print("Done!")
