
Overview
************************************************************************

PyHK is a suite of Python software developed to collect, store, and view cryogenic
housekeeping data and to control heaters and fridges. It is developed
with the intention of being flexible and extensible, allowing differing
hardware configurations to be managed by the same platform. Versions of
the code have been in use since 2014, and it is still in active
development. PyHK is made of several separate packages, of which the
main few are described below.

-  ``pyhkd`` is the main instrument control sofware, which runs
   indefinitely collecting data and storing it to files ``/data/hk``. It
   is designed to run in the background as a system service, but can
   also be explicitly executed in a terminal. ``pyhkd`` listens for
   command packets and execute valid requests (setting a voltage, etc.)

-  ``pyhkweb`` is a web viewer that is used in conjunction with Apache.
   It is the primary method for monitoring and controlling housekeeping
   and fridge scripts, even on the local machine. Once installed it is
   started automatically by Apache as needed, you never need to run
   pyhkweb.py yourself. You should have a DNS name (typically
   \_\_.pyhk.net) assigned to your machine, and you use that name to
   access the website. If you are running in a situation with no
   internet access, you can still access pyhkweb locally at
   http://127.0.0.1.

-  ``pyhkfridge`` is responsible for the fridge cycle and other related
   scripts (like automated G measurement or heating the pumps during
   cooldown). It watches the files in ``/data/hk`` for changes and
   issues commands to ``pyhkd`` via sockets. An arbitrary number of
   instances of ``pyhkfridge`` can be run simultaneously.
   ``pyhkfridge`` is designed to run in the background as a system
   service and controlled via ``pyhkweb``.

-  ``pyhkcmd`` (still in development) is a command line interface
   script for PyHK. While ``pyhkfridge`` is the preferred method for
   writing scripts the read or write PyHK data (due to its integeration
   with ``pyhkweb``), ``pyhkcmd`` may be easier to integrate into
   exisiting workflows.
