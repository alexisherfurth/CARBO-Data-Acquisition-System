
Troubleshooting Tips
************************************************************************

-  Log files for the various PyHK subsystems can be found in
   ``/var/log/pyhk/``.

-  If you are getting an Internal Server Error page when attempting to
   access the website, this typically indicates an invalid
   ``pyhkweb`` configuration file or a missing depenedency. Check the
   error messages recorded in ``/var/log/apache2/error.log`` for further
   information.

-  If you can’t reach the website at all (or if you need local access
   and do not have an internet connection), try going to
   http://127.0.0.1 from a web browser on the machine running PyHK. Note
   that if https is enabled (recommended), your web browser will
   complain about security issues; this is expected, since 127.0.0.1 is
   not the name the TLS certificate is assigned to. You must tell the
   browser to ignore or proceed anyway. If you see this security warning
   at your normal subdomain (often \_\_.pyhk.net), your TLS certificate
   has likely expired and should be renewed (see the certbot
   instructions to renew it). If you can access PyHK from
   http://127.0.0.1 on the local machine but not from your subdomain on
   an external machine, check that your subdomain is pointing to your
   current IP address and that there are no firewalls or routers
   blocking port 80 and 443.

-  If ``pyhkd`` or ``pyhkweb`` fails to start, double check your JSON5
   config files. Online JSON5 validators can be very helpful here (as of
   writing, one can be found at
   https://jsonformatter.org/json5-validator). The JSON5 command line
   interface (not installed by default, instructions available at
   `json5.org <json5.org>`__) also contains a syntax validator
   (``json5 -v <file>``). Finally, since valid JSON is always valid
   JSON5, any of the many online plain JSON validators can check for
   common syntax errors if you remove JSON5-specific features (such as
   comments).

-  If you consistently get an error about a serial device being busy,
   and the issue persists after rebooting, it may be that
   ``modemmanager`` is taking control of the device. Try removing it
   (``sudo apt-get purge modemmanager``).

-  If the whole GPIB bus seems to be nonfunctional even after restarting
   PyHK and the Prologix device, it is likely one of the devices on the
   bus is misbehaving (often an Agilent power supply in my experience).
   Stop PyHK and power cycle ALL devices connected to the GPIB bus, then
   restart PyHK. (A script located at ``tools/gpibcheck`` attempts to
   identify if this state has occured, and can only be run if
   ``pyhkd`` is stopped.)

-  The GPIB standard places limitations on how many devices can be
   powered off while connected to the bus. It is best for all connected
   devices to be powered on, even if you don’t communicate with them or
   indicate their presence to PyHK.

-  If a particular GPIB device does not respond, verify the GPIB address
   is correct and that the GPIB cable is good. A script located at
   ``tools/gpibcheck`` will print all of the identity strings for
   devices on a working bus (and can only be run if ``pyhkd`` is
   stopped).
