
Installation
************************************************************************

System Requirements
========================================================================

This software has been tested on Ubuntu 16.04/18.04 with Python 3.5/3.6.
Python 2.7 is no longer supported; Python 3.4 and below have not been
tested. Windows has not been tested and is not supported at this time.
Other versions of Linux should work fine, but these instructions are
written with Ubunutu in mind. Hardware requirements vary depending on
what else will be running on the computer in question (web browsers are
expecially resource-intensive); generally I would recommend the
equivalent of an Intel i5 or better with at least 16 GB of RAM unless
you are running a dedicated headless system.

Installation Procedure
========================================================================

#. Install the following prerequisite system packages with
   ``sudo apt install``:

   ``git python3-pip python3-matplotlib ccze apache2 apache2-utils libapache2-mod-wsgi-py3``

#. Install the following prerequisite Python packages with ``pip3``
   (either in a Python ``virtualenv`` or with ``sudo pip3 install`` to
   install them globally):

   ``numpy~=1.16 scipy~=1.3 setproctitle~=1.1.9 psutil~=5.6 flask~=1.0 markupsafe==2.0.1 flask-caching~=1.7 pyserial~=3.0 requests~=2.22 JSON5~=0.8 paho-mqtt~=1.5``

#. Clone the master branch of the PyHK repository into a local
   directory. Running the following from the home directory will create
   a folder ``~/pyhk`` with the PyHK code.

   ``git clone https://bitbucket.org/jhunacek/pyhk.git``
   
   (Note: If you are instead upgrading an existing repository from PyHK 2.1 or earlier, make sure to delete the legacy folder ``pyhk/pyhkd/data_acq`` afterwards to prevent an ``ImportError``.)

#. Make sure the user you intend to use is a member of the group
   ``dialout``. This allows you to access serial commumnication without
   running PyHK as root. If the output of the command ``groups`` does
   not include the group ``dialout``, then add it as follows (you will
   need to log out/in afterwards for it to take effect):

   ``sudo adduser $USER dialout``

#. Create the folders /data/hk/ and /var/log/pyhk and make sure that the
   user has write permission.

   ``sudo mkdir /data /data/hk /var/log/pyhk``

   ``sudo chown $USER:$USER /data/hk /var/log/pyhk``

#. If you plan to use any USB serial devices (including the yellow
   Prologix GPIB-USB adapter), the port name applied by the kernel (such
   as ``/dev/ttyUSB0``) may change when rebooting the system or when
   disconnecting and reconnecting devices. To prevent this from causing
   confusion, you will want to instruct the kernel to apply a fixed name
   (of your choice) whenever it sees your specific device connected.

   a. Run ``sudo lsusb -v`` and find the section pertaining to the
      serial device you wish you apply a fixed name to. Comparing the
      output before and after plugging in the device may assist in
      locating the relevant section.

   #. Look for a minimal set of defining characteristics the kernel can
      use to identify your device. For example, the Prologix GPIB-USB
      adapter can be identified with ``idVendor`` (always ``0x0403``),
      ``idProduct`` (always ``0x6001``), and ``iSerial`` (unique per
      device, of the form ``PXHB40P8``). For most USB serial devices
      these are the three attributes you will want to specify. Note that
      some models of USB-RS232 adapter do not have individually-unique
      serial numbers. This is problematic, as the kernel will be unable
      to differentiate between devices. The CHIPI-X10 from FTDI is known
      to have unique serial numbers and is recommended.

   #. Create one file ``/etc/udev/rules.d/serial.rules`` for your all of
      your naming rules (older installations of PyHK may have called
      this file ``prologix.rules`` instead). Each rule corresponds to
      one device you wish to name and should be on a separate line (rule
      examples may be presented on multiple lines below, but should each
      be written as a single line in your rules file). Example rules for
      some common devices are shown below. Be sure to substitute in your
      serial number when relevant, and change the string in the
      ``SYMLINK`` option to name you wish to apply. Be sure to provide
      unique names for each device. Some devices will also require
      ``KERNEL=="ttyACM*"`` instead of ``KERNEL=="ttyUSB*"`` (you can tell
      by checking the default name created in ``/dev/`` when plugging it
      in).

      -  | Prologix GPIB-USB adapter:
         | ``SUBSYSTEMS=="usb", KERNEL=="ttyUSB*", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="6001", ATTRS{serial}=="PXHB40P8", SYMLINK+="ttyPrologix"``

      -  | CHIPI-X10 RS232-USB adapter:
         | ``SUBSYSTEMS=="usb", KERNEL=="ttyUSB*", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="6015", ATTRS{serial}=="FTXOV0NS", SYMLINK+="ttyPTC"``

      -  | Teensy 3.6 / HKMB:
         | ``SUBSYSTEMS=="usb", KERNEL=="ttyACM*", ATTRS{idVendor}=="16c0", ATTRS{idProduct}=="0483", ATTRS{serial}=="2380370", SYMLINK+="ttyHKMBv1Box0"``

      -  | Arduino Uno:
         | ``SUBSYSTEMS=="usb", KERNEL=="ttyACM*", ATTRS{idVendor}=="2341", ATTRS{idProduct}=="0043", ATTRS{serial}=="5573641324835131D281", SYMLINK+="ttyArduino"``

   #. Reload and apply the new naming rules

      ``sudo udevadm control --reload-rules``

      ``sudo udevadm trigger``

   #. Make sure your devices are plugged in and that the new names exist
      (``/dev/ttyPrologix``, etc.). If they don’t appear, check your
      rules try again.

#. Set up your domain name (``time.pyhk.net``, ``mycryostat.com``, etc.) and make sure Apache is working
   with it. If you skip this step, you will only be able to access
   ``pyhkweb`` on the local machine (at http://127.0.0.1, which may
   require bypassing a browser security warning caused by the lack of a
   name/certificate).

   #. If you would like a domain name, contact Jon Hunacek. Otherwise,
      any domain or subdomain name can be used. Be sure you set up
      dynamic IP updating if you do not have a static IP. There are
      several free services that will provide you with a subdomain name
      and instructions for automatically updating the IP.

   #. Uncomment and edit the ``ServerName`` line in ``/etc/apache2/sites-enabled/000-default.conf`` to match your new
      domain name, and reboot Apache

      (``sudo service apache2 restart``)

   #. Go to your domain name in a web browser (both locally and on a
      remote machine). You should see the default Apache splash screen.
      If you don’t, stop, something is wrong; check that you are not
      behind a firewall or a router that is blocking port 80 (HTTP) or
      443 (HTTPS).

   #. Use ``certbot`` to generate a free TLS certificate for your domain
      name. This allows for encryption when accessing the PyHK web
      interface and is **strongly** recommended (it protects the
      password you enter). The cerbot website provides instructions for
      your operating system.

      Ubuntu 18.04:
      https://certbot.eff.org/lets-encrypt/ubuntubionic-apache

      Ubuntu 16.04:
      https://certbot.eff.org/lets-encrypt/ubuntuxenial-apache

      Follow all of the ``certbot`` installation instructions (it should
      have you run something like ``sudo certbot --apache`` at some
      point). Check the output, make sure everything succeeded.

#. Create an Apache password file for the web viewer with the username
   you wish to use when logging into the website (it does not need to
   match your system username).

   ``sudo htpasswd -c /etc/apache2/.htpasswd DESIRED_USERNAME``

   Additional users can be added now (or later) as follows:

   ``sudo htpasswd /etc/apache2/.htpasswd another_user``

#. At this point you will need a both a ``pyhkd`` and a
   ``pyhkweb`` config file. Instructions for creating these config
   files are provided in the Configuration section. If your system
   resembles an existing system saved in the public repo you can start
   with copies of those config files and proceed (config files can
   always be updated later).

#. Configure Apache to run ``pyhkweb`` and to redirect non-encrypted
   ``http`` traffic to the equivalent ``https`` domain. You will need
   your system-specific ``pyhkweb`` config file here. From the
   ``pyhk/pyhkweb`` directory, invoke ``conf_apache.py`` as follows and
   follow the prompts:

   ``sudo ./conf_apache.py ./config/MY_CONFIG.json5``

#. (Optional, Recommended) Add the PyHK ``tools`` folder to the global
   path so the included helper scripts (including ``pyhkcmd``) can be
   executed from anywhere. This can be accomplished by added a line to
   the end of ``~/.profile`` of the form below. Be sure to replace
   ``/home/myusername/pyhk/tools`` with the proper folder path for your
   system. You will need to log out for your changes to take effect.

   ``PATH=$PATH:/home/myusername/pyhk/tools``

#. (Optional, Recommended) Instead of running ``pyhkd`` or
   ``pyhkfridge`` locally in a terminal, you can choose to install them
   as ``systemd`` services (on ``systemd`` based operating systems).
   This allows them to start automatically at system boot and to be
   stopped/restarted remotely (over SSH) without needing to to run them
   in ``screen`` (or equivalent).

   #. From the ``pyhk/pyhkd`` directory, invoke ``pyhkd.py`` with your
      system-specfic config file and the ``--install`` flag. Note that
      ``sudo`` is required here to install the system service;
      ``pyhkd`` will be executed as a non-root user.

      ``sudo ./pyhkd.py ./config/MY_CONFIG.json5 --install``

   #. Make sure pyhkfridge will runs successfully from your current
      user account. From the ``pyhk/pyhkfridge`` directory, run:
      
      ``./pyhkfridge.py``
      
      Then, from the ``pyhk/pyhkfridge`` directory, invoke ``pyhkfridge.py``
      with the ``--install`` flag. In this context, ``NUMBER_INSTANCES``
      should be an integer number of independent
      ``pyhkfridge`` instances to run (4 is a good number). Note that
      ``sudo`` is required here to install the system service;
      ``pyhkfridge`` will be executed as a non-root user.

      ``sudo ./pyhkfridge.py -n NUMBER_INSTANCES --install``

   #. Make sure your user has permission to view the system service
      journal:

      ``sudo usermod -a -G systemd-journal $USER``

      You may need to reboot afterwards.

   #. The logs generated by ``pyhkd`` and ``pyhkfridge`` can now be
      monitored (locally or remotely) with the log scripts in the
      ``pyhk/tools`` folder. When needed, ``pyhkd`` and
      ``pyhkfridge`` can be restarted/stopped/started/disabled with
      commands of the form ``sudo systemctl restart pyhkd.service``.

#. If you chose not to install ``pyhkd`` or ``pyhkfridge`` as system
   services, they can be manually invoked from the ``pyhk/pyhkd`` and
   ``pyhk/pyhkfridge`` folders respectively as follows. Root privileges
   (``sudo``) are not needed or recommended for either. In this context,
   ``NUMBER_INSTANCES`` should be an integer number of independent
   ``pyhkfridge`` instances to run (4 is a good number).

   ``./pyhkd.py ./config/MY_CONFIG.json5``

   ``./pyhkfridge.py -n NUMBER_INSTANCES``
