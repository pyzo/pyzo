# -*- coding: utf-8 -*-
# Copyright (C) 2012, the IEP development team
#
# IEP is distributed under the terms of the (new) BSD License.
# The full license can be found in 'license.txt'.

""" iepwizard module

Implements a wizard to help new users get familiar with IEP.

"""

import os
import iep
from iep.codeeditor.qt import QtCore, QtGui


class IEPWizard(QtGui.QWizard):
    
    def __init__(self, parent):
        QtGui.QWizard.__init__(self, parent)
        
        # Set some appearance stuff
        self.setMinimumSize(600, 500)
        self.setWindowTitle('Getting started with IEP')
        self.setWizardStyle(self.ModernStyle)
        
        # Set logo
        pm = QtGui.QPixmap()
        pm.load(os.path.join(iep.iepDir, 'resources', 'appicons', 'ieplogo48.png'))
        self.setPixmap(self.LogoPixmap, pm)
        
        # Define pages
        klasses = [ IntroWizardPage, 
                    TwocomponentsWizardPage, EditorWizardPage, 
                    ShellWizardPage1, ShellWizardPage2,
                    RuncodeWizardPage1, RuncodeWizardPage2, 
                    ToolsWizardPage1, ToolsWizardPage2,
                    FinalPage]
        
        # Create pages
        self._n = len(klasses)        
        for i, klass in enumerate(klasses):
            self.addPage(klass(self, i))
    
    def show(self, startPage=None):
        """ Show the wizard. If startPage is given, open the Wizard at 
        that page. startPage can be an integer or a string that matches
        the classname of a page.
        """ 
        QtGui.QWizard.show(self)
        
        # Check startpage        
        if isinstance(startPage, int):
            pass
        elif isinstance(startPage, str):
            for i in range(self._n):
                page = self.page(i)
                if page.__class__.__name__.lower() == startPage.lower():
                    startPage = i
                    break
            else:                
                print('IEP wizard: Could not find start page: %r' % startPage)
                startPage = None
        elif startPage is not None:            
            print('IEP wizard: invalid start page: %r' % startPage)
            startPage = None
        
        # Go to start page            
        if startPage is not None:
            for i in range(startPage):
                self.next()


class BaseIEPWizardPage(QtGui.QWizardPage):
    
    _title = 'dummy title'
    _description = 'dummy description'
    _image_filename = ''
    
    def __init__(self, parent, i):
        QtGui.QWizardPage.__init__(self, parent)
        
        # Set title
        n = parent._n - 2 # Dont count the first and last page
        prefix = ''
        if i and i <= n:
            prefix = 'Step %i/%i: ' % (i, n)
        
        # Create label from description
        self.setTitle(prefix + self._title)
        T = self._description.strip()
        self._text_label = QtGui.QLabel(T, self)
        self._text_label.setTextFormat(QtCore.Qt.RichText)
        self._text_label.setWordWrap(True)
        
        # Create label for image
        self._comicLabel = QtGui.QLabel(self)        
        pm = QtGui.QPixmap()
        if 'logo' in self._image_filename:
            pm.load(os.path.join(iep.iepDir, 'resources', 'appicons', self._image_filename))
        elif self._image_filename:
            pm.load(os.path.join(iep.iepDir, 'resources', 'images', self._image_filename))
        self._comicLabel.setPixmap(pm)
        self._comicLabel.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
        
        # Layout
        theLayout = QtGui.QVBoxLayout(self)
        self.setLayout(theLayout)
        #
        theLayout.addWidget(self._text_label)
        theLayout.addStretch()
        theLayout.addWidget(self._comicLabel)
        theLayout.addStretch()


class IntroWizardPage(BaseIEPWizardPage):
    
    _title = 'Welcome to the Interactive Editor for Python!'
    _image_filename = 'ieplogo128.png'
    _description = """
        This wizard helps you get familiarized with the workings of IEP.
        <br/><br/>
        IEP is a cross-platform Python IDE focused on <i>interactivity</i> and
        <i>introspection</i>, which makes it very suitable for scientific computing. 
        Its practical design is aimed at <i>simplicity</i> and <i>efficiency</i>. 
        """
    
    def __init__(self, parent, i):
        BaseIEPWizardPage.__init__(self, parent, i)
        
        # Create label and checkbox
        self._label_info = QtGui.QLabel("This wizard can be opened using 'Help > IEP wizard'", self)
        self._check_show = QtGui.QCheckBox("Show this wizard on startup", self)
        self._check_show.stateChanged.connect(self._setNewUser)
        
        # Init check state
        if iep.config.state.newUser:
            self._check_show.setCheckState(QtCore.Qt.Checked)
        
        # Add to layout
        self.layout().addWidget(self._label_info)
        self.layout().addWidget(self._check_show)
    
    def _setNewUser(self, newUser):
        newUser = bool(newUser)
        self._label_info.setHidden(newUser)
        iep.config.state.newUser = newUser


class TwocomponentsWizardPage(BaseIEPWizardPage):
    
    _title = 'IEP consists of two main components'
    _image_filename = 'iep_two_components.png'
    _description = """
        You can use execute commands directly in the <b>shell</b>,<br/>
        or you can write code in the <b>editor</b> and execute that.
        """


class EditorWizardPage(BaseIEPWizardPage):
    
    _title = 'The editor is where you write your code'
    _image_filename = 'iep_editor.png'
    _description = """
        In the editor, each open file is represented as a tab. By
        right-clicking on a tab, files can be run, saved, closed, etc.
        <br/><br/> 
        The right mouse button also enables one to make a file the <b>main
        file</b> of a project. This file can be recognized by its star
        symbol, and it enables running the file more easily.
        """


class ShellWizardPage1(BaseIEPWizardPage):
    
    _title = 'The shell is where your code gets executed'
    _image_filename = 'iep_shell1.png'
    _description = """
        When IEP starts, a default shell is created. You can add more
        shells that run simultaneously, and which may be of different
        Python versions. 
        <br/><br/> 
        Shells run in a sub-process, such
        that when it is busy, IEP itself stays responsive, allowing you
        to keep coding and even run code in another shell.
        """


class ShellWizardPage2(BaseIEPWizardPage):
    
    _title = 'Configuring shells'
    _image_filename = 'iep_shell2.png'
    _description = """
        IEP can integrate the event loop of five different GUI toolkits,
        thus enabling interactive plotting with e.g., Visvis or
        Matplotlib.
        <br/><br/>
        Via <i>Shell > Edit shell configurations</i>, you can edit and add
        shell configurations. This allows you to for example select the
        initial directory, or use a custom PYTHONPATH.
        """


class RuncodeWizardPage1(BaseIEPWizardPage):
    
    _title = 'Running code'
    _image_filename = 'iep_run1.png'
    _description = """
        IEP supports several ways to run source code in the editor. (see the "Run" menu).
        <ul>
        <li><b>Run selection:</b> if there is no selected text, the
            current line is executed; if the selection is on a single
            line, the selection is evaluated; if the selection spans
            multiple lines, IEP will run the the (complete) selected
            lines.
            </li>
        <li><b>Run cell:</b> a cell is everything between two commands starting
            with '##'.</li> 
        <li><b>Run file:</b> this runs all the code in the current file.  </li>
        <li><b>Run project main file:</b> runs the code in the current project's
            main file. </li>
        </ul> 
        """


class RuncodeWizardPage2(BaseIEPWizardPage):
    
    _title = 'Interactive mode vs running as script'
    _image_filename = ''
    _description = """
        Additionally, you can run the current file or the current project's
        main file as a script. This will first restart the shell to provide
        a clean environment. The shell is also initialized differently:
        <br/><br/>
        Things done on shell startup in <b>interactive mode</b>:
        <ul>
        <li>sys.argv = ['']</li>
        <li>sys.path is prepended with an empty string (current working directory)</li>
        <li>The working dir is set to the "Initial directory" of the shell config</li>
        <li>The PYTHONSTARTUP script is run</li>
        </ul>
        
        Things done on shell startup in <b>script mode</b>:
        <ul>
        <li>__file__ = <i>script_filename</i></li>
        <li>sys.argv = [ <i>script_filename</i> ]</li>
        <li>sys.path is prepended with the directory containing the script</li>
        <li>The working dir is set to the directory containing the script</li> 
        </ul>
        Depending on the settings of the <i>Project mananger</i>, the current project
        directory may also be inserted in sys.path.
        """


class ToolsWizardPage1(BaseIEPWizardPage):
    
    _title = 'Tools for your convenience'
    _image_filename = 'iep_tools1.png'
    _description = """
        Via the <i>Tools menu</i>, one can select which tools to use. The tools can
        be positioned in any way you want, and can also be un-docked.
        <br/><br/>
        Note that the tools system is designed such that it's easy to
        create your own tools. Look at the online wiki for more information,
        or use one of the existing tools as an example. 
        """


class ToolsWizardPage2(BaseIEPWizardPage):
    
    _title = 'Recommended tools'
    _image_filename = 'iep_tools2.png'
    _description = """
        We especially recommend the following tools:
        <ul>
        <li>
        The <b>Source structure tool</b> gives an outline of the source code.
        </li>
        <li>
        The <b>Project manager tool</b> helps keep an overview of
        all files in a directory. To manage your projects,
        click the button with the wrench icon.
        </li>        
        </ul>
        """


class FinalPage(BaseIEPWizardPage):
    
    _title = 'Get coding!'
    _image_filename = 'ieplogo128.png'
    _description = """
        This concludes the IEP wizard.
        Now, get coding and have fun!
        <br/><br/>
        - The IEP development team
        """


# def smooth_images():
#     """ This was used to create the images from their raw versions.
#     """
#     
#     import os
#     import visvis as vv
#     import scipy as sp
#     import scipy.ndimage
#     for fname in os.listdir('images'):
#         im = vv.imread(os.path.join('images', fname))
#         for i in range(im.shape[2]):
#             im[:,:,i] = sp.ndimage.gaussian_filter(im[:,:,i], 0.7)
#         #fname = fname.replace('.png', '.jpg')
#         print(fname)
#         vv.imwrite(fname, im[::2,::2,:])


if __name__ == '__main__':
    w = IEPWizard(None)    
    w.show()
    