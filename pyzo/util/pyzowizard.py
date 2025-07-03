"""pyzowizard module

Implements a wizard to help new users get familiar with pyzo.

"""

import os
import re

import pyzo
from pyzo.qt import QtCore, QtGui, QtWidgets
from pyzo import translate

from pyzo.util._locale import LANGUAGES, LANGUAGE_SYNONYMS, setLanguage


def retranslate(t):
    """To allow retranslating after selecting the language."""
    if hasattr(t, "original"):
        return translate("wizard", t.original)
    else:
        return t


class PyzoWizard(QtWidgets.QWizard):
    def __init__(self, parent):
        super().__init__(parent)

        # Set some appearance stuff
        self.setMinimumSize(600, 500)
        self.setWindowTitle(translate("wizard", "Getting started with Pyzo"))
        self.setWizardStyle(self.WizardStyle.ModernStyle)
        self.setButtonText(self.WizardButton.CancelButton, "Stop")

        # Set logo
        pm = QtGui.QPixmap()
        pm.load(os.path.join(pyzo.pyzoDir, "resources", "appicons", "pyzologo48.png"))
        self.setPixmap(self.WizardPixmap.LogoPixmap, pm)

        # Define pages
        klasses = [
            IntroWizardPage,
            TwocomponentsWizardPage,
            EditorWizardPage,
            ShellWizardPage1,
            ShellWizardPage2,
            RuncodeWizardPage1,
            RuncodeWizardPage2,
            DebuggingWizardPage1,
            DebuggingWizardPage2,
            ToolsWizardPage1,
            ToolsWizardPage2,
            AdvAutoCompWizardPage,
            MiscellaneousWizardPage,
            FinalPage,
        ]

        # Create pages
        self._n = len(klasses)
        for i, klass in enumerate(klasses):
            self.addPage(klass(self, i))

    def show(self, startPage=None):
        """Show the wizard. If startPage is given, open the Wizard at
        that page. startPage can be an integer or a string that matches
        the classname of a page.
        """
        super().show()

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
                print("Pyzo wizard: Could not find start page: {!r}".format(startPage))
                startPage = None
        elif startPage is not None:
            print("Pyzo wizard: invalid start page: {!r}".format(startPage))
            startPage = None

        # Go to start page
        if startPage is not None:
            for i in range(startPage):
                self.next()


class BasePyzoWizardPage(QtWidgets.QWizardPage):
    _prefix = translate("wizard", "Step")

    _title = "dummy title"
    _descriptions = []
    _image_filename = ""

    def __init__(self, parent, i):
        super().__init__(parent)
        self._i = i

        # Create label for description
        self._text_label = QtWidgets.QLabel(self)
        self._text_label.setTextFormat(QtCore.Qt.TextFormat.RichText)
        self._text_label.setWordWrap(True)
        self._text_label.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
        )

        # Create label for image
        self._comicLabel = QtWidgets.QLabel(self)
        pm = QtGui.QPixmap()
        if "logo" in self._image_filename:
            pm.load(
                os.path.join(
                    pyzo.pyzoDir, "resources", "appicons", self._image_filename
                )
            )
        elif self._image_filename:
            pm.load(
                os.path.join(pyzo.pyzoDir, "resources", "images", self._image_filename)
            )
        self._comicLabel.setPixmap(pm)
        AF = QtCore.Qt.AlignmentFlag
        self._comicLabel.setAlignment(AF.AlignHCenter | AF.AlignVCenter)

        # Layout
        theLayout = QtWidgets.QVBoxLayout(self)
        self.setLayout(theLayout)
        #
        theLayout.addWidget(self._text_label)
        theLayout.addStretch()
        theLayout.addWidget(self._comicLabel)
        theLayout.addStretch()

    def initializePage(self):
        # Get prefix
        i = self._i
        n = self.wizard()._n - 2  # Don't count the first and last page
        prefix = ""
        if i and i <= n:
            prefix = retranslate(self._prefix) + " {}/{}: ".format(i, n)

        # Set title
        self.setTitle(prefix + retranslate(self._title))

        # Parse description
        # Two description units are separated with BR tags
        # Emphasis on words is set to italic tags.
        lines = []
        descriptions = [retranslate(d).strip() for d in self._descriptions]
        for description in descriptions:
            for line in description.splitlines():
                line = line.strip()
                line = re.sub(r"\*(.+?)\*", r"<b>\1</b>", line)
                lines.append(line)
            lines.append("<br /><br />")
        lines = lines[:-1]

        # Set description
        self._text_label.setText("\n".join(lines))


class IntroWizardPage(BasePyzoWizardPage):
    _title = translate("wizard", "Welcome to the Interactive Editor for Python!")
    _image_filename = "pyzologo128.png"
    _descriptions = [
        translate(
            "wizard",
            """This wizard helps you get familiarized with the workings of Pyzo.""",
        ),
        translate(
            "wizard",
            """Pyzo is a cross-platform Python IDE
        focused on *interactivity* and *introspection*, which makes it
        very suitable for scientific computing. Its practical design
        is aimed at *simplicity* and *efficiency*.""",
        ),
    ]

    def __init__(self, parent, i):
        super().__init__(parent, i)

        # Create label and checkbox
        t1 = translate("wizard", "This wizard can be opened using 'Help > Pyzo wizard'")
        # t2 = translate('wizard', "Show this wizard on startup")
        self._label_info = QtWidgets.QLabel(t1, self)
        # self._check_show = QtWidgets.QCheckBox(t2, self)
        # self._check_show.stateChanged.connect(self._setNewUser)

        # Create language switcher
        self._langLabel = QtWidgets.QLabel(translate("wizard", "Select language"), self)
        #
        self._langBox = QtWidgets.QComboBox(self)
        self._langBox.setEditable(False)
        # Fill
        index, theIndex = -1, -1
        cur = pyzo.config.settings.language
        for lang in sorted(LANGUAGES):
            index += 1
            self._langBox.addItem(lang)
            if lang == LANGUAGE_SYNONYMS.get(cur, cur):
                theIndex = index
        # Set current index
        if theIndex >= 0:
            self._langBox.setCurrentIndex(theIndex)
        # Bind signal
        self._langBox.activated.connect(self.onLanguageChange)

        # Init check state
        # if pyzo.config.state.newUser:
        #    self._check_show.setCheckState(QtCore.Qt.Checked)

        # Create sublayout
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self._langLabel, 0)
        layout.addWidget(self._langBox, 0)
        layout.addStretch(2)
        self.layout().addLayout(layout)

        # Add to layout
        self.layout().addSpacing(10)
        self.layout().addWidget(self._label_info)
        # self.layout().addWidget(self._check_show)

    def _setNewUser(self, newUser):
        newUser = bool(newUser)
        self._label_info.setHidden(newUser)
        pyzo.config.state.newUser = newUser

    def onLanguageChange(self):
        languageName = self._langBox.currentText()
        if pyzo.config.settings.language == languageName:
            return
        # Save new language
        pyzo.config.settings.language = languageName
        setLanguage(pyzo.config.settings.language)
        # Notify user
        text = translate(
            "wizard",
            """
        The language has been changed for this wizard.
        Pyzo needs to restart for the change to take effect application-wide.
        """,
        )
        m = QtWidgets.QMessageBox(self)
        m.setWindowTitle(translate("wizard", "Language changed"))
        m.setText(text)
        m.setIcon(m.Icon.Information)
        m.exec()

        # Get props of current wizard
        geo = self.wizard().geometry()
        parent = self.wizard().parent()
        # Close ourself!
        self.wizard().close()
        # Start new one
        w = PyzoWizard(parent)
        w.setGeometry(geo)
        w.show()


class TwocomponentsWizardPage(BasePyzoWizardPage):
    _title = translate("wizard", "Pyzo consists of two main components")
    _image_filename = "pyzo_two_components.png"
    _descriptions = [
        translate("wizard", "You can execute commands directly in the *shell*,"),
        translate("wizard", "or you can write code in the *editor* and execute that."),
    ]


class EditorWizardPage(BasePyzoWizardPage):
    _title = translate("wizard", "The editor is where you write your code")
    _image_filename = "pyzo_editor.png"
    _descriptions = [
        translate(
            "wizard",
            """In the *editor*, each open file is represented as a tab. By
        right-clicking on a tab, files can be run, saved, closed, etc.""",
        ),
        translate(
            "wizard",
            """The right mouse button also enables one to make a file the
        *main file* of a project. This file can be recognized by its star
        symbol, and it enables running the file more easily.""",
        ),
    ]


class ShellWizardPage1(BasePyzoWizardPage):
    _title = translate("wizard", "The shell is where your code gets executed")
    _image_filename = "pyzo_shell1.png"
    _descriptions = [
        translate(
            "wizard",
            """When Pyzo starts, a default *shell* is created. You can add more
        shells that run simultaneously, and which may be of different
        Python versions.""",
        ),
        translate(
            "wizard",
            """Shells run in a sub-process, such that when it is busy, Pyzo
        itself stays responsive, allowing you to keep coding and even
        run code in another shell.""",
        ),
    ]


class ShellWizardPage2(BasePyzoWizardPage):
    _title = translate("wizard", "Configuring shells")
    _image_filename = "pyzo_shell2.png"
    _descriptions = [
        translate(
            "wizard",
            """Pyzo can integrate the event loop of five different *GUI toolkits*,
        thus enabling interactive plotting with e.g. Visvis or Matplotlib.""",
        ),
        translate(
            "wizard",
            """Via 'Shell > Edit shell configurations', you can edit and add
        *shell configurations*. This allows you to for example select the
        initial directory, or use a custom Pythonpath.""",
        ),
    ]


class RuncodeWizardPage1(BasePyzoWizardPage):
    _title = translate("wizard", "Running code")
    _image_filename = "pyzo_run1.png"
    _descriptions = [
        translate(
            "wizard",
            "Pyzo supports several ways to run source code in the editor. (see the 'Run' menu).",
        ),
        translate(
            "wizard",
            """*Execute selection:* if there is no selected text, the current line
        is executed; if the selection is on a single line, the selection
        is evaluated; if the selection spans multiple lines, Pyzo will
        run the (complete) selected lines.""",
        ),
        translate(
            "wizard",
            """*Execute line and print result:* execute the editor's current line
        in the shell and print the result
        <br />
        e.g.: line "<code>y = myfunc(x)</code>" will be executed as "<code>y = myfunc(x); y</code>" """,
        ),
        translate(
            "wizard",
            "*Execute cell:* a cell is everything between two lines starting with '##'.",
        ),
        translate("wizard", "*Execute file:* run all the code in the current file."),
        translate(
            "wizard",
            "*Execute main file:* run the code in the current main file.",
        ),
    ]


class RuncodeWizardPage2(BasePyzoWizardPage):
    _title = translate("wizard", "Interactive mode vs running as script")
    _image_filename = ""
    _descriptions = [
        translate(
            "wizard",
            """You can run the current file or the main file normally, or as a script.
        When run as script, the file is saved first. Then the shell is restarted to provide
        a clean environment before executing the file.
        The shell is also initialized differently so that it closely resembles a normal
        script execution.""",
        ),
        translate(
            "wizard",
            """In *interactive mode*, <code>sys.path[0]</code> is an empty string (i.e. the current dir),
        <code>sys.argv</code> is set to <code>['']</code> and <code>__file__</code> is not defined.""",
        ),
        translate(
            "wizard",
            """As a substitute for the undefined <code>__file__</code>, you can insert and run
            something like""",
        ),
        """<code>import os, inspect<br />
        __file__ = inspect.getfile(inspect.currentframe())<br />
        __this_dir__ = os.path.abspath(os.path.dirname(__file__))
        </code>""",
        translate(
            "wizard",
            """to get it.""",
        ),
        translate(
            "wizard",
            """In *script mode*, <code>__file__</code> and <code>sys.argv[0]</code> are set
            to the script's filename, <code>sys.path[0]</code> and the working dir are set
            to the directory containing the script.""",
        ),
    ]


class DebuggingWizardPage1(BasePyzoWizardPage):
    _title = translate("wizard", "Debugging code and execution control (1/2)")
    _image_filename = ""
    _descriptions = [
        translate(
            "wizard",
            """To stop the execution of code (in an infinite loop or when calculations
        take longer than expected, use the flash symbol, or select "Interrupt" from the
        "Shell" menu. This will raise an exception, and you can postmortem-debug after
        that.""",
        ),
        translate(
            "wizard",
            """Via *Postmortem* debugging, you can inspect the values of objects after
        code execution was stopped by an unhandled exception. By switching stack frames,
        you can see local variables in different layers of nested function calls.
        Continuing execution is not possible in postmortem, though.""",
        ),
        translate(
            "wizard",
            """The *Pause* debug action (in the "Shell" menu or shell toolbar) makes it
        possible to pause execution and activate the debug mode, and then continue, stop
        or pause again the execution.""",
        ),
        translate(
            "wizard",
            """While in *debug mode*, there are many possibilities:
        <ul>
        <li>objects can be inspected and modified</li>
        <li>stack frames can be switched (to go to different levels of nested function calls)
        <li>custom code can be executed in the shell (also whole scripts)</li>
        <li>code execution can be stepped</li>
        <li>the pointer to the next line to execute can be changed via the "Debug jump" action,
        for example to skip lines or repeat previously executed lines (some limitations
        apply, though)</li>
        </ul>
        When continuing execution (and thus leaving debug mode), breakpoints will be updated
        (see next page).""",
        ),
    ]


class DebuggingWizardPage2(BasePyzoWizardPage):
    _title = translate("wizard", "Debugging code and execution control (2/2)")
    _image_filename = ""
    _descriptions = [
        translate(
            "wizard",
            """While the debug mode is active, the gui event loop of the Python interpreter
        in the shell is normally not periodically called anymore. This means that, for example,
        matplotlib figures will be frozen as if the program would have crashed.
        By setting the environment variable <code>PYZO_PROCESS_EVENTS_WHILE_DEBUGGING=1</code>
        in the "environ" field of the shell configuration, the gui event loop will be processed
        even while debug mode is active. Matplotlib figures can then also be interacted with
        normally while code execution is paused.""",
        ),
        translate(
            "wizard",
            """To (repeatedly) pause at specific code lines and enter debug mode, set a
        *breakpoint* there, via "Toggle breakpoint" from the "Edit" menu or by clicking in
        the bar to the right of the line number. Only a full circle is a breakpoint, whereas
        a half circle represents a disabled breakpoint that can be used as a navigation point
        (via "Jump to previous/next breakpoint" from the menu).
        Breakpoints are only updated (i.e. synchronized with the debugger) when the user
        gives the command to execute code or when continuing execution while in debug mode.
        When executing code that has code parts still running via the event loop after
        execution has finished, for example GUI applications with PySide6, a simple way
        to update breakpoints is to just press RETURN in the idle command prompt of the shell.
        Another way to update breakpoints would be to pause execution and continue it.
        Note that, when there are breakpoints set (and synchronized), execution becomes much
        slower than without breakpoints.""",
        ),
        translate(
            "wizard",
            """Instead of a breakpoint or pause action, code execution can also be paused
        by executing the function *<code>breakpoint()</code>* in the Python code. This will
        enter debug mode the same way. Compared to normal breakpoints, there is no
        performance penalty, but with the disadvantage, that these hard-coded breakpoint
        functions cannot be disabled while the script is executed.""",
        ),
    ]


class ToolsWizardPage1(BasePyzoWizardPage):
    _title = translate("wizard", "Tools for your convenience")
    _image_filename = "pyzo_tools1.png"
    _descriptions = [
        translate(
            "wizard",
            """Via the *Tools menu*, one can select which tools to use. The tools can
        be positioned in any way you want, and can also be un-docked.""",
        ),
        translate(
            "wizard",
            """Note that the tools system is designed such that it's easy to
        create your own tools. Look at the example tools for more information,
        or use one of the existing tools as a more advanced example.""",
        ),
        os.path.join(pyzo.pyzoDir, "resources", "tool_examples"),
        os.path.join(pyzo.pyzoDir, "tools"),
        "https://github.com/pyzo/pyzo/blob/main/pyzo/resources/tool_examples",
        "https://github.com/pyzo/pyzo/blob/main/pyzo/tools/",
    ]


class ToolsWizardPage2(BasePyzoWizardPage):
    _title = translate("wizard", "Recommended tools")
    _image_filename = "pyzo_tools2.png"
    _descriptions = [
        translate("wizard", """We especially recommend the following tools:"""),
        translate(
            "wizard",
            """The *Source structure* tool gives an outline of the source code.""",
        ),
        translate(
            "wizard",
            """The *File browser* tool helps keeping an overview of all files
            in a directory and allows for searching text across multiple files.
            To manage your bookmarks, click the star icon.""",
        ),
        translate(
            "wizard",
            """The *Interactive help* tool shows you the documentation of objects,
            automatically when browsing the autocompletion list,
            or manually by selecting an expression and clicking "Help" in the context menu.""",
        ),
        translate(
            "wizard",
            """The *Editor list* tool is convenient when having more than just
            a few editor tabs open at the same time.""",
        ),
    ]


class AdvAutoCompWizardPage(BasePyzoWizardPage):
    _title = translate("wizard", "Advanced Autocompletion and Calltips")
    _image_filename = ""
    _descriptions = [
        translate(
            "wizard",
            """Auto completion for attributes and calltips can also be used for complex
        expressions that include function calls and indexing.<br />
        <br />
        For example:<br />
        <br />
        Type "<code>locals().</code>" (with the dot at the end) and press Ctrl+Space. This will evaluate
        <code>locals()</code> and assign the result to <code>__pyzo__autocomp</code> in the
        local scope. Then auto-completion continues and displays the list widget with the
        attributes.<br />
        <br />
        Type "<code>locals()[</code>" (with the open bracket at the end) and press Ctrl+Space.
        This will evaluate <code>locals()</code> and assign the result to
        <code>__pyzo__autocomp</code> in the local scope. Then auto-completion continues
        and displays the list widget with the keys.<br />
        <br />
        Type "<code>locals().get(</code>" (with the open parenthesis at the end) and press
        Ctrl+Space. This will evaluate <code>locals()</code> and assign the result to
        <code>__pyzo__calltip</code> in the local scope. Then auto-completion continues
        and displays the calltip for <code>dict.get(...)</code>.<br />
        <br />
        The Ctrl+Space hot key can also be pressed while having already entered some characters
        of the attribute, key or arguments, in case the autocompletion list widget resp. calltip
        should be shown again after having cancelled it.""",
        ),
    ]


class MiscellaneousWizardPage(BasePyzoWizardPage):
    _title = translate("wizard", "Miscellaneous tips and tricks")
    _image_filename = ""
    _descriptions = [
        translate(
            "wizard",
            """Press keys Ctrl+Shift+ArrowUp/Down to move the selected lines up/down
        in the editor.<br />
        <br />
        Use magic commands to manage packets, e.g. "pip list" or "pip install numpy".<br />
        <br />
        When there is a printed stack trace in Python shell (usually the red error text),
        double click the *filepath* to open the file at the specific line number.<br />
        <br />
        When dealing with performance critical code, avoid printing too much to the shell
        because stream outputs directed to the Pyzo IDE will slow down the execution.<br />
        <br />
        You can double-click the line number to get an input field for jumping to a
        specific line.<br />
        <br />
        In Pyzo's "About" dialog (Help -> About Pyzo) you can see the folder where Pyzo
        stores the settings.<br />
        <br />
        Pyzo can be configured to be portable, for example to run it from a USB pen-drive
        with encapsulated settings. To enable this, rename the folder "_settings" in Pyzo's
        application folder to "settings".<br />
        <br />
        You can directly modify Pyzo's source code even in the binary distribution because
        the binary is just a Python-Interpreter that runs the Python source code in the
        installation directory. See the "About Pyzo" dialog for the code location.""",
        ),
    ]


class FinalPage(BasePyzoWizardPage):
    _title = translate("wizard", "Get coding!")
    _image_filename = "pyzologo128.png"
    _descriptions = [
        translate(
            "wizard",
            """This concludes the Pyzo wizard. Now, get coding and have fun!""",
        ),
    ]


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


if __name__ == "__main__":
    w = PyzoWizard(None)
    w.show()
