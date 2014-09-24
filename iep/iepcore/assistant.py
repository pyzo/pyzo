# -*- coding: utf-8 -*-
# Copyright (C) 2013, the IEP development team
# Author: Windel Bouwman
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
from iep import getResourceDirs
import os


tool_name = "Assistant"
tool_summary = "Browse qt help documents"


class Settings(QtGui.QWidget):
    def __init__(self, engine):
        super().__init__()
        self._engine = engine
        layout = QtGui.QVBoxLayout(self)
        add_button = QtGui.QPushButton("Add")
        del_button = QtGui.QPushButton("Delete")
        add_button.setObjectName('assistant_add_doc_button')
        self._view = QtGui.QListView()
        layout.addWidget(self._view)
        layout2 = QtGui.QHBoxLayout()
        layout2.addWidget(add_button)
        layout2.addWidget(del_button)
        layout.addLayout(layout2)
        self._model = QtGui.QStringListModel()
        self._view.setModel(self._model)

        self._model.setStringList(self._engine.registeredDocumentations())

        add_button.clicked.connect(self.add_doc)
        del_button.clicked.connect(self.del_doc)

    def add_doc(self):
        doc_file = QtGui.QFileDialog.getOpenFileName(
            self,
            "Select a compressed help file",
            filter="Qt compressed help files (*.qch)")
        if isinstance(doc_file, tuple):
            doc = doc[0]
        self.add_doc_do(doc_file)

    def add_doc_do(self, doc_file):
        ok = self._engine.registerDocumentation(doc_file)
        if ok:
            self._model.setStringList(self._engine.registeredDocumentations())
        else:
            QtGui.QMessageBox.critical(self, "Error", "Error loading doc")

    def del_doc(self):
        idx = self._view.currentIndex()
        if idx.isValid():
            doc_file = self._model.data(idx, QtCore.Qt.DisplayRole)
            self.del_doc_do(doc_file)

    def del_doc_do(self, doc_file):
        self._engine.unregisterDocumentation(doc_file)
        self._model.setStringList(self._engine.registeredDocumentations())


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
    def __init__(self, parent=None, collection_filename=None):
        """
            Initializes an assistance instance.
            When collection_file is none, it is determined from the
            appDataDir.
        """
        super().__init__(parent)
        self.setWindowTitle('Help')
        if collection_filename is None:
            # Collection file is stored in iep data dir:
            _, appDataDir = getResourceDirs()
            collection_filename = os.path.join(appDataDir, 'tools', 'docs.qhc')
        self._engine = QtHelp.QHelpEngine(collection_filename)

        # Important, call setup data to load the files:
        self._engine.setupData()

        # The main players:
        self._content = self._engine.contentWidget()
        self._index = self._engine.indexWidget()
        self._indexTab = QtGui.QWidget()
        il = QtGui.QVBoxLayout(self._indexTab)
        filter_text = QtGui.QLineEdit()
        il.addWidget(filter_text)
        il.addWidget(self._index)

        self._helpBrowser = HelpBrowser(self._engine)
        self._searchEngine = self._engine.searchEngine()
        self._settings = Settings(self._engine)

        self._progress = QtGui.QWidget()
        pl = QtGui.QHBoxLayout(self._progress)
        bar = QtGui.QProgressBar()
        bar.setMaximum(0)
        pl.addWidget(QtGui.QLabel('Indexing'))
        pl.addWidget(bar)

        self._searchResultWidget = self._searchEngine.resultWidget()
        self._searchQueryWidget = self._searchEngine.queryWidget()
        self._searchTab = QtGui.QWidget()
        search_layout = QtGui.QVBoxLayout(self._searchTab)
        search_layout.addWidget(self._searchQueryWidget)
        search_layout.addWidget(self._searchResultWidget)

        tab = QtGui.QTabWidget()
        tab.addTab(self._content, "Contents")
        tab.addTab(self._indexTab, "Index")
        tab.addTab(self._searchTab, "Search")
        tab.addTab(self._settings, "Settings")

        splitter = QtGui.QSplitter(self)
        splitter.addWidget(tab)
        splitter.addWidget(self._helpBrowser)

        layout = QtGui.QVBoxLayout(self)
        layout.addWidget(splitter)
        layout.addWidget(self._progress)

        # Connect clicks:
        self._content.linkActivated.connect(self._helpBrowser.setSource)
        self._index.linkActivated.connect(self._helpBrowser.setSource)
        self._searchEngine.searchingFinished.connect(self.onSearchFinish)
        self._searchEngine.indexingStarted.connect(self.onIndexingStarted)
        self._searchEngine.indexingFinished.connect(self.onIndexingFinished)
        filter_text.textChanged.connect(self._index.filterIndices)
        self._searchResultWidget.requestShowLink.connect(self._helpBrowser.setSource)
        self._searchQueryWidget.search.connect(self.goSearch)

        # Always re-index on startup:
        self._searchEngine.reindexDocumentation()

        self._search_term = None

        # Show initial page:
        self.showHelpForTerm('serial')

    def goSearch(self):
        query = self._searchQueryWidget.query()
        self._searchEngine.search(query)

    def onIndexingStarted(self):
        self._progress.show()

    def onIndexingFinished(self):
        self._progress.hide()

    def onSearchFinish(self, hits):
        if hits == 0:
            return
        hits = self._searchEngine.hits(0, hits)
        if not hits:
            return
        if self._search_term is not None:
            for url2, page_title in hits:
                if page_title == self._search_term:
                    url = url2
                    break
            else:
                # Not matching page title, just go for the first hit:
                url, _ = hits[0]
        else:
            # Pick first hit:
            url, _ = hits[0]
        self._helpBrowser.setSource(QtCore.QUrl(url))

    def showHelpForTerm(self, name):
        # Cache for later use:
        self._search_term = name

        # Create a query:
        query = QtHelp.QHelpSearchQuery(QtHelp.QHelpSearchQuery.DEFAULT, [name])
        self._searchEngine.search([query])


if __name__ == '__main__':
    app = QtGui.QApplication([])
    view = IepAssistant()
    view.show()
    app.exec()
