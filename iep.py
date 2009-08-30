#   $Author: almar $
#   $Date: 2008-09-30 10:26:38 +0200 (Tue, 30 Sep 2008) $
#   $Rev: 557 $
#
#   Copyright 2008 Almar Klein
#
#   This file is part of IEP.
#    
#   IEP is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
# 
#   IEP is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
# 
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

""" IEP - Interactive Editor for Python
This is the main module, where I define some stuff to be used in the other
modules.

"""

import os, os.path

# import ssdf or the suplied copy if not available
try:
    import ssdf
except ImportError:
    # if strux not available, use the copy we included with IEP
    import ssdf_copy as ssdf

# get the path where IEP is located
path = __file__
path = os.path.dirname( os.path.abspath(path) )


## the configuration stuff...

# create strux in module namespace
config = ssdf.new()

def loadConfig():
    """Load configurations, create if doesn't exist!"""
    filename = os.path.join(path,"config.ssdf")
    if os.path.isfile(filename):
        # load file        
        tmp = ssdf.load(os.path.join(path,"config.ssdf"))
        for key in tmp:
            config[key] = tmp[key]
    else:
        # create file
        config.Clear()
        # todo: if not available produce new file also for styles and keymaps
        config.editorState = ''
        
        config.layout = ssdf.new()
        config.layout.left = 110
        config.layout.top = 50
        config.layout.heigth = 700
        config.layout.width = 900
        config.layout.maximized = 0
        config.layout.splitter0 = 600
        config.layout.splitter1 = 400
        config.layout.splitter2 = 400          
        config.layout.pluginsLocation = "right"
        config.layout.shellsLocation = "bottom"
        
        config.plugins = ssdf.new()
        config.plugins.top = []
        config.plugins.bottom = []
        
        
def saveConfig():
    """Store configurations"""
    ssdf.save( os.path.join(path,"config.xml"), config )

# load on import
loadConfig()


## Some functions...

def startIep():
    """ RUN IEP 
    """        
    from main import MainWindow
    from PyQt4 import QtCore, QtGui
    app = QtGui.QApplication([])
    frame=MainWindow()
    app.exec_()
    
    
def normalizeLineEndings(text):
    """ normalize text, following Python styles.
    Convert all line endings to the \\n (LF) style.    
    """ 
    # line endings
    text = text.replace("\r\n","\n")
    text = text.replace("\r","\n")    
    # done
    return text


def GetMainFrame(window):
    """ Get the main frame, giving a window that's in it.
    Can be used by windows to find the main frame, and
    via it, can interact with other windows.
    """
    try:
        while True:
            parent = window.parent()
            if parent is None:
                return window
            else:
                window = parent
    except:    
        raise Exception("Cannot find the main window!")

    
if __name__ == "__main__":
    startIep()
    
