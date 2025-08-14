
Extension
************************************************************************

This section serves as a launching point for adding support for new
devices to PyHK. Note that program logic (acting on sensor values)
should probably be implemented in ``pyhkfridge`` or via ``pyhkcmd.py``,
this section is for adding new data sources. Before attempting to extend
PyHK, consider whether your goal can be accomplished with existing
systems:

-  PyHK can subscribe to messages from a MQTT broker. Many existing
   tools/systems work with MQTT already, and MQTT messages can be
   accepted from remote computers.

-  (TODO) PyHK can watch for changes in simple text files, so writing a
   small independent script to periodically write data to a text file
   may be the easiest way to integrate new devices without working
   directly with PyHK source code.
   
(TODO) Document internal program structure
