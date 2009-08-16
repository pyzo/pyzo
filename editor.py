""" MODULE EDITOR
Defines the editor to be used in IEP.
"""

from PyQt4 import QtCore, QtGui
from PyQt4 import Qsci
qt = QtGui

from baseTextCtrl import BaseTextCtrl

class IepEditor(BaseTextCtrl):
    pass
    

if __name__=="__main__":
    app = QtGui.QApplication([])
    win = IepEditor(None)
    win.setStyle('.py')
    tmp = "foo(bar)\nfor bar in range(5):\n  print bar\n"
    tmp += "\nclass aap:\n  def monkey(self):\n    pass\n\n"
    win.setText(tmp)    
    win.show()
    app.exec_()