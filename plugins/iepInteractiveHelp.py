import sys, os, time
from PyQt4 import QtCore, QtGui
import iep 

plugin_name = "Interactive Help"
plugin_summary = "Shows help on an object when using up/down in autocomplete."

class IepInteractiveHelp(QtGui.QTextBrowser):
    pass