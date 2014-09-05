
import unittest
from pyzolib.qt import QtCore, QtGui, QtNetwork
from iep.iepcore.main import MainWindow


class FirstTestCase(unittest.TestCase):
    def test1(self):
        app = QtGui.QApplication([])
        MainWindow()


