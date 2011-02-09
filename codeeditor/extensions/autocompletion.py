"""
Code editor extensions that provides autocompleter functionality
"""


from PyQt4 import QtGui,QtCore
from PyQt4.QtCore import Qt

import keyword

# todo: use keywords from the parser
class AutoCompletion(object):
    def __init__(self,*args, **kwds):
        super(AutoCompletion, self).__init__(*args, **kwds)
        # Autocompleter
        self.__completerModel=QtGui.QStringListModel(keyword.kwlist)
        self.__completer=QtGui.QCompleter(self.__completerModel, self)
        self.__completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.__completer.setWidget(self)
        self.__completerNames=[]
        self.__recentCompletions=[] #List of recently selected completions
        
        # Text position corresponding to first charcter of the word being completed
        self.__autocompleteStart=None
        
        #Connect signals
        self.connect(self.__completer,QtCore.SIGNAL("activated(QString)"),self.onAutoComplete)
    
    ## Properties
    def recentCompletionsList(self):
        """ 
        The list of recent auto-completions. This property may be set to a
        list that is shared among several editors, in order to share the notion
        of recent auto-completions
        """
        return self.__recentCompletions
    
    def setRecentCompletionsList(self,value):
        self.__recentCompletions = value
    
    def completer(self):
        return self.__completer
        

    ## Autocompletion
    def autocompleteShow(self,offset = 0,names = None):
        """
        Pop-up the autocompleter (if not already visible) and position it at current
        cursor position minus offset. If names is given and not None, it is set
        as the list of possible completions.
        """
        #Pop-up the autocompleteList
        startcursor=self.textCursor()
        startcursor.movePosition(startcursor.Left, n=offset)
        
        if not self.autocompleteActive() or \
            startcursor.position() != self.__autocompleteStart:

            self.__autocompleteStart=startcursor.position()

            #Popup the autocompleter. Don't use .complete() since we want to
            #position the popup manually
            self.__positionAutocompleter()
            self.__updateAutocompleterPrefix()
            self.__completer.popup().show()
        

        if names is not None:
            #TODO: a more intelligent implementation that adds new items and removes
            #old ones
            if names != self.__completerNames:
                self.__completerModel.setStringList(names)
                self.__completerNames = names

        self.__updateAutocompleterPrefix()
    def autocompleteAccept(self):
        pass
    def autocompleteCancel(self):
        self.__completer.popup().hide()
        self.__autocompleteStart = None
        
    def onAutoComplete(self,text):
        #Select the text from autocompleteStart until the current cursor
        cursor=self.textCursor()
        cursor.setPosition(self.__autocompleteStart,cursor.KeepAnchor)
        #Replace it with the selected text 
        cursor.insertText(text)
        self.__autocompleteStart=None
        self.autocompleteCancel() #Reset the completer
        
        #Update the recent completions list
        if text in self.__recentCompletions:
            self.__recentCompletions.remove(text)
        self.__recentCompletions.append(text)
        
    def autocompleteActive(self):
        """ Returns whether an autocompletion list is currently shown. 
        """
        return self.__autocompleteStart is not None
    
        
    def __positionAutocompleter(self):
        """Move the autocompleter list to a proper position"""
        #Find the start of the autocompletion and move the completer popup there
        cur=self.textCursor()
        cur.setPosition(self.__autocompleteStart)
        position = self.cursorRect(cur).bottomLeft() + \
            self.viewport().pos() #self.geometry().topLeft() +
        self.__completer.popup().move(self.mapToGlobal(position))
        
        #Set size
        geometry = self.__completer.popup().geometry()
        geometry.setWidth(200)
        geometry.setHeight(100)
        self.__completer.popup().setGeometry(geometry)
    
    def __updateAutocompleterPrefix(self):
        """
        Find the autocompletion prefix (the part of the word that has been 
        entered) and send it to the completer
        """
        prefix=self.toPlainText()[self.__autocompleteStart:
        self.textCursor().position()]

        self.__completer.setCompletionPrefix(prefix)
        model = self.__completer.completionModel()
        if model.rowCount():
            #Iterate over the matches, find the one that was most recently used
            #print (self._recentCompletions)
            recentFound = -1
            recentFoundRow = 0 #If no recent match, just select the first match
            
            for row in range(model.rowCount()):
                data = model.data(model.index(row,0),self.__completer.completionRole())
                if not data in self.__recentCompletions:
                    continue
                
                index = self.__recentCompletions.index(data)
                if index > recentFound: #Later in the list = more recent
                    recentFound, recentFoundRow = index, row

            
            self.__completer.popup().setCurrentIndex(model.index(recentFoundRow,0));

                
        else:
            #No match, just hide
            self.autocompleteCancel()
    
    def keyPressEvent(self, event):
        key = event.key()
        modifiers = event.modifiers()
        if key == Qt.Key_Escape and modifiers == Qt.NoModifier and \
                self.autocompleteActive():
            self.autocompleteCancel()
            return #Consume the key
        
        if key == Qt.Key_Tab and modifiers == Qt.NoModifier:
            if self.autocompleteActive():
                #Let the completer handle this one!
                event.ignore()
                return #Don't call the super() keyPressEvent
        
        #Allowed keys that do not close the autocompleteList:
        # alphanumeric and _ ans shift
        # Backspace (until start of autocomplete word)
        if self.autocompleteActive() and \
            not event.text().isalnum() and event.text != '_' and \
            key != Qt.Key_Shift and not (
            (key==Qt.Key_Backspace) and self.textCursor().position()>self.__autocompleteStart):
            self.autocompleteCancel()
        
        # Apply the key that was pressed
        super(AutoCompletion, self).keyPressEvent(event)
        
        if self.autocompleteActive():
            #While we type, the start of the autocompletion may move due to line
            #wrapping, so reposition after every key stroke
            self.__positionAutocompleter()
            self.__updateAutocompleterPrefix()
