# -*- coding: utf-8 -*-
# Copyright (C) 2013, the IEP development team
#
# IEP is distributed under the terms of the (new) BSD License.
# The full license can be found in 'license.txt'.

"""
Tool that can view qt help files via the qthelp engine.

Steps to create qhc (qt help collection) files:

1. Generate qt help files of the project of interest with sphinx:
    $ sphinx-build -b qthelp . build/qthelp
2. compress this help:
    $ qhelpgenerator Python.qhp -o Python.qch
3. Create a qhcp (qt help collection project)
    $ vim collection.qhcp
4. Compile qhcp into qhc (qt help collection)
    $ qhelpcollectiongenerator collection.qhcp -o collection.qhc

"""

from pyzolib.qt import QtCore, QtGui, QtHelp


tool_name = "Assistant"
tool_summary = "Browse qt help documents"


class HelpBrowser(QtGui.QTextBrowser):
    """ Override textbrowser to implement load resource """
    def __init__(self, engine):
        super().__init__()
        self._engine = engine

    def loadResource(self, typ, url):
        if url.scheme() == "qthelp":
            return self._engine.fileData(url)
        else:
            return super().loadResource(typ, url)


class IepAssistant(QtGui.QWidget):
    """
        Show help contents and browse qt help files.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        # TODO: parameterize path:
        self._engine = QtHelp.QHelpEngine("all.qhc")
        self._content = self._engine.contentWidget()
        self._index = self._engine.indexWidget()

        layout = QtGui.QHBoxLayout(self)
        layout.addWidget(self._index)
        layout.addWidget(self._content)

        # Important, call setup data to load the files:
        self._engine.setupData()
        self._helpBrowser = HelpBrowser(self._engine)
        layout.addWidget(self._helpBrowser)
        self._content.linkActivated.connect(self._helpBrowser.setSource)
        self._index.linkActivated.connect(self._helpBrowser.setSource)


if __name__ == '__main__':
    app = QtGui.QApplication([])
    view = IepAssistant()
    view.show()
    app.exec()
