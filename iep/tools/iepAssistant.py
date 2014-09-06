# -*- coding: utf-8 -*-
# Copyright (C) 2013, the IEP development team
#
# IEP is distributed under the terms of the (new) BSD License.
# The full license can be found in 'license.txt'.

"""
Tool that can view qt help files via the qthelp engine.

Run make_docs.sh from:
https://bitbucket.org/windel/qthelpdocs

Copy the "docs" directory to the iep root!

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
        self._engine = QtHelp.QHelpEngine("docs/docs.qhc")

        # Important, call setup data to load the files:
        self._engine.setupData()

        # The main players:
        self._content = self._engine.contentWidget()
        self._index = self._engine.indexWidget()
        self._helpBrowser = HelpBrowser(self._engine)
        self._searchEngine = self._engine.searchEngine()

        tab = QtGui.QTabWidget()
        tab.addTab(self._index, "Index")
        tab.addTab(self._content, "Contents")

        splitter = QtGui.QSplitter(self)
        splitter.addWidget(tab)
        splitter.addWidget(self._helpBrowser)

        layout = QtGui.QHBoxLayout(self)
        layout.addWidget(splitter)

        # Connect clicks:
        self._content.linkActivated.connect(self._helpBrowser.setSource)
        self._index.linkActivated.connect(self._helpBrowser.setSource)
        self._searchEngine.searchingFinished.connect(self.onSearchFinish)
        self._searchEngine.indexingStarted.connect(self.onIndexingStarted)
        self._searchEngine.indexingFinished.connect(self.onIndexingFinished)

        # Always re-index on startup:
        self._searchEngine.reindexDocumentation()

    def onIndexingStarted(self):
        print('Indexing begun')

    def onIndexingFinished(self):
        print('Indexing done')

    def onSearchFinish(self, hits):
        if hits == 0:
            return
        hits = self._searchEngine.hits(0, hits)
        # Pick first hit, this can be improved..
        self._helpBrowser.setSource(QtCore.QUrl(hits[0][0]))

    def showHelpForTerm(self, name):
        # Create a query:
        query = QtHelp.QHelpSearchQuery(QtHelp.QHelpSearchQuery.DEFAULT, [name])
        self._searchEngine.search([query])

if __name__ == '__main__':
    app = QtGui.QApplication([])
    view = IepAssistant()
    view.showHelpForTerm('numpy.linspace')
    view.show()
    app.exec()
