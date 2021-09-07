# -*- coding: utf-8 -*-
# Copyright (C) 2016, the Pyzo development team
#
# Pyzo is distributed under the terms of the 2-Clause BSD License.
# The full license can be found in 'license.txt'.


import sys, os, code
import pyzo
from pyzo.util.qt import QtCore, QtGui, QtWidgets  # noqa
from pyzo.core.shell import BaseShell
from pyzo.core.pyzoLogging import splitConsole

tool_name = pyzo.translate("pyzoLogger", "Logger")
tool_summary = "Logs messages, warnings and errors within Pyzo."


class PyzoLogger(QtWidgets.QWidget):
    """PyzoLogger

    The main widget for this tool.

    """

    def __init__(self, parent):
        QtWidgets.QWidget.__init__(self, parent)

        # logger widget
        self._logger_shell = PyzoLoggerShell(self)

        # set layout
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addWidget(self._logger_shell, 1)
        # spacing of widgets
        self.layout.setSpacing(0)
        # set margins
        margin = pyzo.config.view.widgetMargin
        self.layout.setContentsMargins(margin, margin, margin, margin)
        self.setLayout(self.layout)

    def updateZoom(self):
        self._logger_shell.setZoom(pyzo.config.view.zoom)

    def updateFont(self):
        self._logger_shell.setFont(pyzo.config.view.fontname)


class PyzoLoggerShell(BaseShell):
    """Shell that logs all messages produced by pyzo. It also
    allows to look inside pyzo, which can be handy for debugging
    and developing.
    """

    def __init__(self, parent):
        BaseShell.__init__(self, parent)

        # Set style to Python, or autocompletion does not work
        self.setParser("python")

        # Change background color to make the logger look different from shell
        # Use color as if all lines are highlighted
        f1 = self.getStyleElementFormat("Editor.text")
        f2 = self.getStyleElementFormat("Editor.Highlight current line")
        newStyle = "back:%s, fore:%s" % (f2.back.name(), f1.fore.name())
        self.setStyle(editor_text=newStyle)

        # Create namespace for logger interpreter
        locals = {"pyzo": pyzo, "sys": sys, "os": os}
        # Include linguist tools
        for name in ["linguist", "lrelease", "lupdate", "lhelp"]:
            locals[name] = getattr(pyzo.util._locale, name)

        # Create interpreter to run code
        self._interpreter = code.InteractiveConsole(locals, "<logger>")

        # Show welcome text
        moreBanner = "This is the Pyzo logger shell."
        self.write(
            "Python %s on %s - %s\n\n" % (sys.version[:5], sys.platform, moreBanner)
        )
        self.write(str(sys.ps1), 2)

        # Split console
        history = splitConsole(self.write, self.writeErr)
        self.write(history)

    def executeCommand(self, command):
        """Execute the command here!"""
        # Use writeErr rather than sys.stdout.write. This prevents
        # the prompts to be logged by the history. Because if they
        # are, the text does not look good due to missing newlines
        # when loading the history.

        # "Echo" stdin
        self.write(command, 1)
        more = self._interpreter.push(command.rstrip("\n"))
        if more:
            self.write(str(sys.ps2), 2)
        else:
            self.write(str(sys.ps1), 2)

    def writeErr(self, msg):
        """This is what the logger uses to write errors."""
        self.write(msg, 0, "#C00")

    # Note that I did not (yet) implement calltips

    def processAutoComp(self, aco):
        """Processes an autocomp request using an AutoCompObject instance."""

        # Try using buffer first
        if aco.tryUsingBuffer():
            return

        # Include buildins?
        if not aco.name:
            command = "__builtins__.keys()"
            try:
                names = eval(command, {}, self._interpreter.locals)
                aco.addNames(names)
            except Exception:
                pass

        # Query list of names
        command = "dir({})".format(aco.name)
        try:
            names = eval(command, {}, self._interpreter.locals)
            aco.addNames(names)
        except Exception:
            pass

        # Done
        aco.finish()
