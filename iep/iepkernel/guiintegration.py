# -*- coding: utf-8 -*-
# Copyright (C) 2012, the IEP development team
#
# IEP is distributed under the terms of the (new) BSD License.
# The full license can be found in 'license.txt'.

""" 
Module to integrate GUI event loops in the IEP interpreter.

This specifies classes that all have the same interface. Each class
wraps one GUI toolkit.

Support for PyQt4, WxPython, FLTK, GTK, TK.

"""

from iepkernel import printDirect

mainloopWarning = """
Note: not entering main loop. The GUI app is integrated with the IEP event
loop, which means that the function to enter the main loop does not block. 
If your app crashes, this might be because a GUI object goes out of scope 
and is prematurely cleaned up.
""".strip()


class Hijacked_base:
    """ Defines the interface. 
    """
    def processEvents(self):
        raise NotImplemented()


class Hijacked_tk(Hijacked_base):    
    """ Tries to import tkinter and returns a withdrawn tkinter root
    window.  If tkinter is already imported or not available, this
    returns None.  
    Modifies tkinter's mainloop with a dummy so when a module calls
    mainloop, it does not block.
    """    
    def __init__(self):
        
        # Try importing
        import sys
        if sys.version[0] == '3':
            import tkinter
        else:
            import Tkinter as tkinter
        
        # Replace mainloop. Note that a root object obtained with
        # tkinter.Tk() has a mainloop method, which will simply call
        # tkinter.mainloop().
        def dummy_mainloop(*args,**kwargs):
            printDirect(mainloopWarning)
        tkinter.Misc.mainloop = dummy_mainloop
        tkinter.mainloop = dummy_mainloop
                
        # Create tk "main window" that has a Tcl interpreter.
        # Withdraw so it's not shown. This object can be used to
        # process events for any other windows.
        r = tkinter.Tk()
        r.withdraw()
        
        # Store the app instance to process events
        self.app = r
        
        # Notify that we integrated the event loop
        self.app._in_event_loop = 'IEP'
        tkinter._in_event_loop = 'IEP'
    
    def processEvents(self):
        self.app.update()


class Hijacked_fltk(Hijacked_base):
    """ Hijack fltk 1.
    This one is easy. Just call fl.wait(0.0) now and then.
    Note that both tk and fltk try to bind to PyOS_InputHook. Fltk
    will warn about not being able to and Tk does not, so we should
    just hijack (import) fltk first. The hook that they try to fetch
    is not required in IEP, because the IEP interpreter will keep
    all GUI backends updated when idle.
    """
    def __init__(self):
        # Try importing        
        import fltk as fl
        import types
        
        # Replace mainloop with a dummy
        def dummyrun(*args,**kwargs):
            printDirect(mainloopWarning)
        fl.Fl.run = types.MethodType(dummyrun, fl.Fl)
        
        # Store the app instance to process events
        self.app =  fl.Fl   
        
        # Notify that we integrated the event loop
        self.app._in_event_loop = 'IEP'
        fl._in_event_loop = 'IEP'
    
    def processEvents(self):
        self.app.wait(0)


class Hijacked_fltk2(Hijacked_base):
    """ Hijack fltk 2.    
    """
    def __init__(self):
        # Try importing
        import fltk2 as fl        
        
        # Replace mainloop with a dummy
        def dummyrun(*args,**kwargs):
            printDirect(mainloopWarning)    
        fl.run = dummyrun    
        
        # Return the app instance to process events
        self.app = fl
        
        # Notify that we integrated the event loop
        self.app._in_event_loop = 'IEP'
    
    def processEvents(self):
        # is this right?
        self.app.wait(0) 


class Hijacked_qt(Hijacked_base):
    """ Common functionality for pyqt and pyside
    """
    
    def __init__(self):
        import types
        
        # Try importing qt        
        QtGui, QtCore = self.importCoreAndGui()
        
        # Store the real application class
        if not hasattr(QtGui, 'real_QApplication'):
            QtGui.real_QApplication = QtGui.QApplication
        
        class QApplication_hijacked(QtGui.QApplication):
            """ QApplication_hijacked(*args, **kwargs)
            
            Hijacked QApplication class. This class has a __new__() 
            method that always returns the global application 
            instance, i.e. QtGui.qApp.
            
            The QtGui.qApp instance is an instance of the original
            QtGui.QApplication, but with its __init__() and exec_() 
            methods replaced.
            
            You can subclass this class; the global application instance
            will be given the methods and attributes so it will behave 
            like the subclass.
            
            """
            
            def __new__(cls, *args, **kwargs):
                
                # Get the singleton application instance
                theApp = QApplication_hijacked.instance()
                
                # Instantiate an original QApplication instance if we need to
                if theApp is None:
                    theApp = QtGui.real_QApplication(*args, **kwargs)
                    QtGui.qApp = theApp
                
                # Add attributes of cls to the instance to make it
                # behave as if it were an instance of that class
                for key in dir(cls):
                    # Skip all magic methods except __init__
                    if key.startswith('__') and key != '__init__':
                        continue
                    # Skip attributes that we already have
                    val = getattr(cls, key)
                    if hasattr(theApp.__class__, key):
                        if hash(val) == hash(getattr(theApp.__class__, key)):
                            continue
                    # Make method?
                    if hasattr(val, '__call__'):
                        if hasattr(val, 'im_func'):
                            val = val.im_func # Python 2.x
                        val = types.MethodType(val, theApp.__class__)
                    # Set attribute on app instance (not the class!)
                    try:
                        setattr(theApp, key, val)
                    except Exception:
                        pass # tough luck
                
                # Call init function (in case the user overloaded it)
                theApp.__init__(*args, **kwargs)
                
                # Return global app object (modified to the users needs)
                return theApp
            
            def __init__(self, *args, **kwargs):
               pass
            
            def exec_(self, *args, **kwargs):
                """ This function does nothing, except printing a
                warning message. The point is that a Qt App can crash
                quite hard if an object goes out of scope, and the error
                is not obvious.
                """
                printDirect(mainloopWarning)
        
        
        # Instantiate application object 
        self.app = QApplication_hijacked([''])
        
        # Replace app class
        QtGui.QApplication = QApplication_hijacked
        
        # Notify that we integrated the event loop
        self.app._in_event_loop = 'IEP'
        QtGui._in_event_loop = 'IEP'
    
    
    def processEvents(self):
        self.app.flush()
        self.app.processEvents()


class Hijacked_qt_old(Hijacked_base):
    """ Common functionality for pyqt and pyside
    """
    
    def __init__(self):
        # Try importing qt        
        QtGui, QtCore = self.importCoreAndGui()
        
        # Function to get members for a class, taking base classes into account
        def collectClassMembers(cls, D):
            for k in cls.__dict__: 
                if not k.startswith('_'):
                    D[k] = cls.__dict__[k]
            for b in cls.__bases__:
                collectClassMembers(b, D)
            return D
        
        # Store the real application instance
        if not hasattr(QtGui, 'real_QApplication'):
            QtGui.real_QApplication = QtGui.QApplication
        
        # Meta class that injects all member of the original QApplication 
        # in the QHijackedApp class (and its derivatives).
        class QApplicationMetaClass(type):
            def __new__(meta, name, bases, dct):
                # Collect all members of class, take inheritance into account
                dict1 = dct.copy()
                for b in bases:
                    collectClassMembers(b, dict1)
                # Dict used to update members
                dict2 = collectClassMembers(QtGui.real_QApplication, {})
                # Update members
                for key in dict2:
                    if key not in dict1:
                        dct[key] = dict2[key]
                # Create class and return
                klass = type.__new__(meta, name, bases, dct)
                return klass
        
        QHijackedApp_base = QApplicationMetaClass('QHijackedApp_base', (object,), {})
        class QHijackedApp(QHijackedApp_base):
            """ This is an iep-hijacked Qt application. You can subclass from
            this class and instantiate as many instances as you wish.
            This class is essentially an empty class, with all members
            of the real QApplication injected in it.
            """
            __metaclass__ = QApplicationMetaClass
            def __init__(self, *args, **kwargs):
                pass
            def exec_(self, *args, **kwargs):
                printDirect(mainloopWarning)
        
        # Instantiate QApplication and store
        app = QtGui.QApplication.instance()
        if app is None:
            app = QtGui.QApplication([''])
        QtGui.qApp = self.app = app
        
        # Replace app class
        QtGui.QApplication = QHijackedApp
        
        # Notify that we integrated the event loop
        self.app._in_event_loop = 'IEP'
        QtGui._in_event_loop = 'IEP'
    
    
    def processEvents(self):
        self.app.flush()
        self.app.processEvents()


class Hijacked_pyqt4(Hijacked_qt):
    """ Hijack the PyQt4 mainloop.
    """
    
    def importCoreAndGui(self):
        # Try importing qt        
        import PyQt4
        from PyQt4 import QtGui, QtCore
        return QtGui, QtCore
    
    
class Hijacked_pyside(Hijacked_qt):
    """ Hijack the PySide mainloop.
    """
    
    def importCoreAndGui(self):
        # Try importing qt        
        import PySide
        from PySide import QtGui, QtCore
        return QtGui, QtCore


class Hijacked_wx(Hijacked_base):
    """ Hijack the wxWidgets mainloop.    
    """ 
    
    def __init__(self):
        
        # Try importing
        try:
            import wx
        except ImportError:            
            # For very old versions of WX
            import wxPython as wx
        
        # Create dummy mainloop to replace original mainloop
        def dummy_mainloop(*args, **kw):
            printDirect(mainloopWarning)
        
        # Depending on version, replace mainloop
        ver = wx.__version__
        orig_mainloop = None
        if ver[:3] >= '2.5':
            if hasattr(wx, '_core_'): core = getattr(wx, '_core_')
            elif hasattr(wx, '_core'): core = getattr(wx, '_core')
            else: raise ImportError
            orig_mainloop = core.PyApp_MainLoop
            core.PyApp_MainLoop = dummy_mainloop
        elif ver[:3] == '2.4':
            orig_mainloop = wx.wxc.wxPyApp_MainLoop
            wx.wxc.wxPyApp_MainLoop = dummy_mainloop
        else:
            # Unable to find either wxPython version 2.4 or >= 2.5."
            raise ImportError
        
        # Store package wx
        self.wx = wx
        
        # Get and store the app instance to process events 
        app = wx.GetApp()
        if app is None:
            app = wx.App(False)
        self.app = app
        
        # Notify that we integrated the event loop
        self.app._in_event_loop = 'IEP'
        wx._in_event_loop = 'IEP'
    
    def processEvents(self):
        wx = self.wx
        
        # This bit is really needed        
        old = wx.EventLoop.GetActive()                       
        eventLoop = wx.EventLoop()
        wx.EventLoop.SetActive(eventLoop)                        
        while eventLoop.Pending():
            eventLoop.Dispatch()
        
        # Process and reset
        self.app.ProcessIdle() # otherwise frames do not close
        wx.EventLoop.SetActive(old)   


class Hijacked_gtk(Hijacked_base):
    """ Modifies pyGTK's mainloop with a dummy so user code does not
    block IPython.  processing events is done using the module'
    main_iteration function.
    """
    def __init__(self):
        # Try importing gtk
        import gtk
        
        # Replace mainloop with a dummy
        def dummy_mainloop(*args, **kwargs):
            printDirect(mainloopWarning)        
        gtk.mainloop = dummy_mainloop
        gtk.main = dummy_mainloop
        
        # Replace main_quit with a dummy too
        def dummy_quit(*args, **kwargs):
            pass        
        gtk.main_quit = dummy_quit
        gtk.mainquit = dummy_quit
        
        # Make sure main_iteration exists even on older versions
        if not hasattr(gtk, 'main_iteration'):
            gtk.main_iteration = gtk.mainiteration
        
        # Store 'app object'
        self.app = gtk
        
        # Notify that we integrated the event loop
        self.app._in_event_loop = 'IEP'
    
    def processEvents(self):
        gtk = self.app
        while gtk.events_pending():            
            gtk.main_iteration(False)

