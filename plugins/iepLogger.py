import sys, os, code
from PyQt4 import QtCore, QtGui
import iep
from iepLogging import LoggerShell

plugin_name = "Logger"
plugin_summary = "Logs messaged, warnings and errors within IEP"
 
# This tool simply wraps the LoggerShell in dockable widget.
# I could define the logger shell here, but I chose to make
# a module logging.py because there needs to be other functionality
# defined that cannot be implemented in a tool module. That given,
# I think it makes more sense to define the Logger shell in that
# module also and simply make it available through here.

class IepLogger(LoggerShell):
    pass
