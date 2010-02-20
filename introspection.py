""" Module introspection
Provides introspection functionality to IEP.

There are two sources of introspection information. The first is the
source file; the currently active file is parsed to obtain the names
of classes, fuctions, methods and class attributes. The second is the
currently active shell; members of objects (dir) are queried, function
signatures obtained, and documentation on objects is compiled.

The collected information is used in several ways:
  * For autocompletion (shell + file info)
  * For showing the signature of a function (shell + file? info)
  * For providing interactive help (shell info)
  * For providing the structure of the source (file info)
  
Requests for the autocompletion and signature should react relatively 
quick (as the user types), and it should be able to cancel them. 
For the other two usages, this is less important.

"""

import time
import threading
from PyQt4 import QtCore, QtGui

import iep


## blabla

def doAutocomplete(editor, objectName, partialMemberName):
    
#     # Get editor
#     editor = iep.editors.getCurrentEditor()
#     if not editor:
#         return
    
    # Create introspection object
    ob = IntrospectAutocomplete(editor, objectName, partialMemberName)
    
    # process it
    shellQuerier.postAutocompletion(ob)


def doSignature(objectName, partialMemberName):
    pass

def doDocs(objectName):
    pass

# 
# def getMembers(responseFunc, objectName, partialMemberName):
#     pass
# 
# def getSignature(responseFunc, objectName):
#     pass
# 
# def getDocs(responseFunc, objectName):
#     pass
# 
# def getSourceStructure(responseFunc):
#     pass


## The classes and functions to get that information


# todo: emit signal when new result is available
# if the code for parsing the file is large, put in seperate module.
class SourceParser(threading.Thread):
    """ Parsing sourcecode in a separate thread, this class obtains
    the introspection informarion from the first source.
    """
    
    def __init__(self):
        threading.Thread.__init__(self)
        
        # Reference to text to parse
        self._text = ''
        
        # Flag to indicate new text
        self._gotNewText = False
        
        # The resulting structure
        self._result = None
    
    
    def parseThis(self, text):
        """ parseThis(text)
        Give the parser new text to parse.
        If the parser is busy parsing text, it will stop doing that
        and start a new with the most recent version of the text. 
        """
        self._text = text
        self._gotNewText = True
    
    
    def getStructure(self):
        """ getStructure()
        Get the structure that was obtained by parsing the text.
        """
        return self._result
    
    
    def run(self):
        """ run()
        This is the main loop.
        """
        pass
    
    
    def _parseThis(self, text):
        """ _parseThis(text)
        This function will actually parse the given text, and is called
        from the mainloop when appropriate. The resulting structure is
        stored in self._result.
        """
        pass
    


class IntrospectionClass:
    pass

class IntrospectAutocomplete(IntrospectionClass):
    
    def __init__(self, editor, objectName, partialMemberName):
        self._editor = editor
        self._objectName = objectName
        self._partialMemberName = partialMemberName
    
    def getRequestString(self):
        return "EVAL ' '.join(dir({}))".format(self._objectName)
    
    def process(self, response):
        
        # First see if this is still the right editor (can also be a shell)
#         editor = iep.editors.getCurrentEditor()
        editor = iep.shells.getCurrentShell()
        if editor is not self._editor:
            return
        
        # Show list
        iep.callLater(editor.autoCompShow, 0, response)
    

# class RequestMembers(RequestClass):
#     def __init__(self, responseFunc, objectName, partialName):
#         RequestClass.__init__(self, RequestClass)
#         self._objectName = objectName
#         self._partialName = partialName
# 
# class RequestDocs(RequestClass):
#     def __init__(self, responseFunc, objectName):
#         pass
# 
# class RequestSignature(RequestClass):
#     def __init__(self, responseFunc, objectName):
#         pass
# 

# todo: Can a request be represented as a single string (to send to the shell)
# Each type of request should be singleton: a new request posted when not
# responded yet, will replace that request. Member request have priority
# over signature requests, which have priority over docs requests.

# todo: maybe this class should be in the shell module?
# class ShellQuerier(QtCore.QThread):
class ShellQuerier(threading.Thread):
    """ Thread that obtains introspection information from the second 
    source of information, by communicating with the remote process of
    the shell.
    """
    
    def __init__(self):
        threading.Thread.__init__(self, name='shellQuerier')
#         QtCore.QThread.__init__(self)
        
        # Requests to process
        self._requestAutocomp = None
        self._requestSignature = None
        self._requestDocs = None
        
        # Flag to remember what was processed
        self._requestType = 0
        
        self.daemon = True
    
    
    def _processMemberRequest(self, request):
        req, resp = self._getChannels()
    
    
    def postAutocompletion(self, request):
        """ postMemberRequest(request)
        Post a request for information.
        """ 
        self._requestAutocomp = request
    
    
    def postSignature(self, request):
        """ postMemberRequest(request)
        Post a request for information.
        """  
        self._requestSignature = request
    
    
    def postInteractiveDocs(self, request):
        """ postMemberRequest(request)
        Post a request for information.
        """ 
        self._requestDocs = request
    
    
    def run(self):
        """ run() 
        The mainloop.
        """
        time.sleep(1)
        
        while True:
            
            # Sleep for a bit
            time.sleep(0.05)
            
            # Check for a request
            if self._requestAutocomp:
                request = self._requestAutocomp
                result = self._processRequest(request)
                if result:
                    if request is self._requestAutocomp:
                        # Process
                        request.process(result)
                        # The request was processed
                        self._requestAutocomp = None
                    else:
                        pass # We'll process the new version next round
    
    
    def _processRequest(self, request):
        
        # Get reference of currenly active shell
        shell = iep.shells.getCurrentShell()
        
        # If there is no active shell, we cannot do introspection
        if shell:
            
            # Get channels
            req = shell._request
            resp = shell._response
            
            # Flush response queue so we're in sync                    
            resp.read()
            
            # Send request and wait for response
            request = request.getRequestString()
            if request:
                req.write(request)
                result = resp.readOne(True) # Block: wait for response
                if result != '<error>':
                    return result
        
        # If not returned nicely, disable
        self._requestAutocomp = None
        self._requestSignature = None
        self._requestDocs = None
        return None


shellQuerier = ShellQuerier()
shellQuerier.start()


