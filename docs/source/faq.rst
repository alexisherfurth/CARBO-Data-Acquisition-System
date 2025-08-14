
Frequently Asked Questions
************************************************************************

Something has failed, what should I do?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Start by reading through the Troubleshooting section of this document to
see if anything is relevant to your issue.

I need a new feature or device to be added to PyHK, what should I do?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Start by reading through the Extension section of this document to see
if there is a simple way to accomplish your goal.

How do I integrate my own scripts into PyHK?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

There are two main avenues for custom scripts running on the same
computer as PyHK. If you want to have your script managed from
``pyhkweb``, then you can implement it as a fridge script in
``pyhkfridge`` (note that a fridge script can do just about anything
you can do in Python, the name is historical). If you instead want a
stand-alone script to read values or send commands to PyHK, then you can
call ``tools/pyhkcmd`` from your script or from the command line.

Does PyHK support the National Instruments GPIB-USB adapters?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Not at this time. Proprietary drivers are required, and at last check
the Linux support from NI is poor. The Prologix GPIB-USB devices are
much easier for me to support (and cheaper!).

How do I make sure serial devices use the same name each time they are plugged in?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you plan to use any USB serial devices (including the yellow Prologix
GPIB-USB adapter), the port name applied by the kernel (such as
``/dev/ttyUSB0``) may change when rebooting the system or when
disconnecting and reconnecting devices. To prevent this from causing
confusion, you will want to instruct the kernel to apply a fixed name
(of your choice) whenever it sees your specific device connected.
Instructions for this can be found in Sec. [sec:install].

How do I rename an old thermometer?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This is not currently supported, but may be in the future.

Why do I need to enter the thermometer name in both the pyhkd and pyhkweb config files?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This setup allows one to organize plots in ``pyhkweb`` in ways that do
not match the hardware organization in ``pyhkd``. While for simple
systems the two files tend to feel redundant, more complex setups
require this flexibility.

Why is JSON5 used for some configuration files?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Plain JSON continues to be supported for all PyHK configuration files,
but for human-edited files JSON5 is recommended. It allows for
human-friendly features such as comments, and is more forgiving toward
syntax errors that don’t impact meaning. Internal configuation files not
intended for human use remain in plain JSON for speed and simplicity.


