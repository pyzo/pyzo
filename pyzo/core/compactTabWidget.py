# -*- coding: utf-8 -*-
# Copyright (C) 2016, the Pyzo development team
#
# Pyzo is distributed under the terms of the (new) BSD License.
# The full license can be found in 'license.txt'.

""" compact tab widget class

See docs of the tab widget.

"""

from pyzolib.qt import QtCore, QtGui
import sys

if sys.version_info[0] < 3:
    str = unicode
    ELLIPSIS = unichr(8230)
else:
    ELLIPSIS = chr(8230)

# Constants for the alignments of tabs
MIN_NAME_WIDTH = 4
MAX_NAME_WIDTH = 64


## Define style sheet for the tabs

STYLESHEET = """
QTabWidget::pane { /* The tab widget frame */
    border-top: 0px solid #A09B90;
}

QTabWidget::tab-bar {
    left: 0px; /* move to the right by x px */
}


/* Style the tab using the tab sub-control. Note that
 it reads QTabBar _not_ QTabWidget */
QTabBar::tab {
    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                stop: 0.0 rgba(220,220,220,128), 
                stop: 0.4 rgba(200,200,200,128), 
                stop: 1.0 rgba(100,100,100,128) );
    border: 1px solid #A09B90;
    border-bottom-color: #DAD5CC; /* same as the pane color */
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    min-width: 5ex;
    padding-bottom: PADDING_BOTTOMpx;
    padding-top: PADDING_TOPpx;
    padding-left: PADDING_LEFTpx;
    padding-right: PADDING_RIGHTpx;
    margin-right: -1px; /* "combine" borders */
}
QTabBar::tab:last {    
    margin-right: 0px;
}

/* Style the selected tab, hoovered tab, and other tabs. */
QTabBar::tab:hover {
    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                stop: 0.0 rgba(245,250,255,128), 
                stop: 0.4 rgba(210,210,210,128), 
                stop: 1.0 rgba(200,200,200,128) );
}
QTabBar::tab:selected {
    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                stop: 0.0 rgba(0,0,128,128), 
                stop: 0.12 rgba(0,0,128,128), 
                stop: 0.120001 rgba(245,250,255,128), 
                stop: 0.4 rgba(210,210,210,128), 
                stop: 1.0 rgba(200,200,200,128) );
}

QTabBar::tab:selected {     
    border-width: 1px;
    border-bottom-width: 0px;
    border-top-left-radius: 5px;
    border-top-right-radius: 5px;    
    border-color: #333;
}

QTabBar::tab:!selected {
    margin-top: 3px; /* make non-selected tabs look smaller */
}

"""

## Define tab widget class

class TabData:
    """ To keep track of real names of the tabs, but also keep supporting
    tabData.
    """
    def __init__(self, name):
        self.name = name
        self.data = None


class CompactTabBar(QtGui.QTabBar):
    """ CompactTabBar(parent, *args, padding=(4,4,6,6), preventEqualTexts=True)
    
    Tab bar corresponcing to the CompactTabWidget.
    
    With the "padding" argument the padding of the tabs can be chosen.
    It should be an integer, or a 4 element tuple specifying the padding
    for top, bottom, left, right. When a tab has a button,
    the padding is the space between button and text.
    
    With preventEqualTexts to True, will reduce the amount of eliding if
    two tabs have (partly) the same name, so that they can always be
    distinguished.
    
    """
    
    # Add signal to be notified of double clicks on tabs
    tabDoubleClicked = QtCore.Signal(int)
    barDoubleClicked = QtCore.Signal()
    
    def __init__(self, *args, padding=(4,4,6,6), preventEqualTexts=True):
        QtGui.QTabBar.__init__(self, *args)
        
        # Put tab widget in document mode
        self.setDocumentMode(True)
        
        # Widget needs to draw its background (otherwise Mac has a dark bg)
        self.setDrawBase(False)
        if sys.platform == 'darwin':
            self.setAutoFillBackground(True)
        
        # Set whether we want to prevent eliding for names that start the same.
        self._preventEqualTexts = preventEqualTexts
        
        # Allow moving tabs around
        self.setMovable(True)
        
        # Get padding
        if isinstance(padding, (int, float)):
            padding = padding, padding, padding, padding
        elif isinstance(padding, (tuple, list)):
            pass
        else:
            raise ValueError('Invalid value for padding.')
        
        # Set style sheet
        stylesheet = STYLESHEET
        stylesheet = stylesheet.replace('PADDING_TOP', str(padding[0]))
        stylesheet = stylesheet.replace('PADDING_BOTTOM', str(padding[1]))
        stylesheet = stylesheet.replace('PADDING_LEFT', str(padding[2]))
        stylesheet = stylesheet.replace('PADDING_RIGHT', str(padding[3]))
        self.setStyleSheet(stylesheet)
        
        # We do our own eliding
        self.setElideMode(QtCore.Qt.ElideNone) 
        
        # Make tabs wider if there's plenty space?
        self.setExpanding(False) 
        
        # If there's not enough space, use scroll buttons
        self.setUsesScrollButtons(True) 
        
        # When a tab is removed, select previous
        self.setSelectionBehaviorOnRemove(self.SelectPreviousTab)
        
        # Init alignment parameters
        self._alignWidth = MIN_NAME_WIDTH  # Width in characters
        self._alignWidthIsReducing = False # Whether in process of reducing
        
        # Create timer for aligning
        self._alignTimer = QtCore.QTimer(self)
        self._alignTimer.setInterval(10)
        self._alignTimer.setSingleShot(True)
        self._alignTimer.timeout.connect(self._alignRecursive)
    
    
    def _compactTabBarData(self, i):
        """ _compactTabBarData(i)
        
        Get the underlying tab data for tab i. Only for internal use.
        
        """
        
        # Get current TabData instance
        tabData = QtGui.QTabBar.tabData(self, i)
        if (tabData is not None) and hasattr(tabData, 'toPyObject'):
            tabData = tabData.toPyObject() # Older version of Qt
        
        # If none, make it as good as we can
        if not tabData:
            name = str(QtGui.QTabBar.tabText(self, i))
            tabData = TabData( name )
            QtGui.QTabBar.setTabData(self, i, tabData)
        
        # Done
        return tabData
    
    
    ## Overload a few methods
    
    def mouseDoubleClickEvent(self, event):
        i = self.tabAt(event.pos())
        if i == -1:
            # There was no tab under the cursor
            self.barDoubleClicked.emit()
        else:
            # Tab was double clicked
            self.tabDoubleClicked.emit(i)
    
    
    def setTabData(self, i, data):
        """ setTabData(i, data)
        
        Set the given object at the tab with index 1.
        
        """
        # Get underlying python instance
        tabData = self._compactTabBarData(i)
        
        # Attach given data
        tabData.data = data
    
    
    def tabData(self, i):
        """ tabData(i)
        
        Get the tab data at item i. Always returns a Python object.
        
        """
        
        # Get underlying python instance
        tabData = self._compactTabBarData(i)
        
        # Return stored data
        return tabData.data
    
    
    def setTabText(self, i, text):
        """ setTabText(i, text)
        
        Set the text for tab i.
        
        """
        tabData = self._compactTabBarData(i)
        if text != tabData.name:
            tabData.name = text
            self.alignTabs()
    
    
    def tabText(self, i):
        """ tabText(i)
        
        Get the title of the tab at index i.
        
        """
        tabData = self._compactTabBarData(i)
        return tabData.name
    
    
    ## Overload events and protected functions
    
    def tabInserted(self, i):        
        QtGui.QTabBar.tabInserted(self, i)
        
        # Is called when a tab is inserted
        
        # Get given name and store
        name = str(QtGui.QTabBar.tabText(self, i))
        tabData = TabData(name)
        QtGui.QTabBar.setTabData(self, i, tabData)
        
        # Update
        self.alignTabs()
    
        
    def tabRemoved(self, i):
        QtGui.QTabBar.tabRemoved(self, i)
        
        # Update
        self.alignTabs()
    
        
    def resizeEvent(self, event):
        QtGui.QTabBar.resizeEvent(self, event)
        self.alignTabs()
    
    
    def showEvent(self, event):
        QtGui.QTabBar.showEvent(self, event)
        self.alignTabs()
    
        
    ## For aligning
    
    def alignTabs(self):
        """ alignTabs()
        
        Align the tab items. Their names are ellided if required so that
        all tabs fit on the tab bar if possible. When there is too little
        space, the QTabBar will kick in and draw scroll arrows.
        
        """
        
        # Set name widths correct (in case new names were added)
        self._setMaxWidthOfAllItems()
        
        # Start alignment process
        self._alignWidthIsReducing = False
        self._alignTimer.start()
        
        
    def _alignRecursive(self):
        """ _alignRecursive()
        
        Recursive alignment of the items. The alignment process
        should be initiated from alignTabs().
        
        """
        
        # Only if visible
        if not self.isVisible():
            return
        
        # Get tab bar and number of items
        N = self.count()
        
        # Get right edge of last tab and left edge of corner widget
        pos1 = self.tabRect(0).topLeft()
        pos2 = self.tabRect(N-1).topRight()
        cornerWidget = self.parent().cornerWidget()
        if cornerWidget:
            pos3 = cornerWidget.pos()
        else:
            pos3 = QtCore.QPoint(self.width(), 0)
        x1 = pos1.x()
        x2 = pos2.x()
        x3 = pos3.x()
        alignMargin = x3 - (x2-x1) -3  # Must be positive (has margin)
        
        # Are the tabs too wide?
        if alignMargin < 0:
            # Tabs extend beyond corner widget
            
            # Reduce width then
            self._alignWidth -= 1
            self._alignWidth = max(self._alignWidth, MIN_NAME_WIDTH)
            
            # Apply
            self._setMaxWidthOfAllItems()
            self._alignWidthIsReducing = True
            
            # Try again if there's still room for reduction
            if self._alignWidth > MIN_NAME_WIDTH:
                self._alignTimer.start()
        
        elif alignMargin > 10 and not self._alignWidthIsReducing:
            # Gap between tabs and corner widget is a bit large
            
            # Increase width then
            self._alignWidth += 1
            self._alignWidth = min(self._alignWidth, MAX_NAME_WIDTH)
            
            # Apply
            itemsElided = self._setMaxWidthOfAllItems()
            
            # Try again if there's still room for increment
            if itemsElided and self._alignWidth < MAX_NAME_WIDTH:
                self._alignTimer.start()
                #self._alignTimer.timeout.emit()
        
        else:            
            pass # margin is good
    
    
    def _getAllNames(self):
        """ _getAllNames()
        
        Get a list of all (full) tab names.
        
        """
        return [self._compactTabBarData(i).name for i in range(self.count())]
    
    
    def _setMaxWidthOfAllItems(self):
        """ _setMaxWidthOfAllItems()
        
        Sets the maximum width of all items now, by eliding the names.
        Returns whether any items were elided.
        
        """ 
        
        # Prepare for measuring font sizes
        font = self.font()
        metrics = QtGui.QFontMetrics(font)
        
        # Get whether an item was reduced in size
        itemReduced = False
        
        for i in range(self.count()):
            
            # Get width
            w = self._alignWidth
            
            # Get name
            name = name0 = self._compactTabBarData(i).name
            
            # Check if we can reduce the name size, correct w if necessary
            if ( (w+1) < len(name0) ) and self._preventEqualTexts:
                
                # Increase w untill there are no names that start the same
                allNames = self._getAllNames()
                hasSimilarNames = True
                diff = 2
                w -= 1
                while hasSimilarNames and w < len(name0):
                    w += 1
                    w2 = w - (diff-1)
                    shortName = name[:w2]
                    similarnames = [n for n in allNames if n[:w2]==shortName]
                    hasSimilarNames = len(similarnames)>1
            
            # Check again, with corrected w
            if (w+1) < len(name0):
                name = name[:w] + ELLIPSIS
                itemReduced = True
            
            # Set text now
            QtGui.QTabBar.setTabText(self, i, name)
        
        # Done
        return itemReduced



class CompactTabWidget(QtGui.QTabWidget):
    """ CompactTabWidget(parent, *args, **kwargs)
    
    Implements a tab widget with a tabbar that is in document mode
    and has more compact tabs that conventional tab widgets, so more
    items fit on the same space.

    Further much care is taken to ellide the names in a smart way:
      * All items are allowed the same amount of characters instead of
        that the same amount of characters is removed from all names.
      * If there are two item with the same beginning, it is made
        sure that enough characters are shown such that the names
        can be distinguished.
    
    The kwargs are passed to the tab bar constructor. There are a few 
    keywords arguments to influence the appearance of the tabs. See the 
    CompactTabBar class.
    
    """
    
    def __init__(self, *args, **kwargs):
        QtGui.QTabWidget.__init__(self, *args)
        
        # Set tab bar
        self.setTabBar(CompactTabBar(self, **kwargs))
        
        # Draw tabs at the top by default
        self.setTabPosition(QtGui.QTabWidget.North)
    
    
    def setTabData(self, i, data):
        """ setTabData(i, data)
        
        Set the given object at the tab with index 1.
        
        """
        self.tabBar().setTabData(i, data)
    
    
    def tabData(self, i):
        """ tabData(i)
        
        Get the tab data at item i. Always returns a Python object.
        
        """
        return self.tabBar().tabData(i)
    
    
    def setTabText(self, i, text):
        """ setTabText(i, text)
        
        Set the text for tab i.
        
        """
        self.tabBar().setTabText(i, text)
    
    
    def tabText(self, i):
        """ tabText(i)
        
        Get the title of the tab at index i.
        
        """
        return self.tabBar().tabText(i)
    

if __name__ == '__main__':
    
    w = CompactTabWidget()    
    w.show()
    
    w.addTab(QtGui.QWidget(w), 'aapenootjedopje')
    w.addTab(QtGui.QWidget(w), 'aapenootjedropje')
    w.addTab( QtGui.QWidget(w), 'noot en mies')
    w.addTab( QtGui.QWidget(w), 'boom bijv een iep')
    w.addTab( QtGui.QWidget(w), 'roosemarijnus')
    w.addTab( QtGui.QWidget(w), 'vis')
    w.addTab( QtGui.QWidget(w), 'vuurvuurvuur')
