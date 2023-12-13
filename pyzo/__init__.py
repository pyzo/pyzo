#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2016, the Pyzo development team
#
# Pyzo is distributed under the terms of the 2-Clause BSD License.
# The full license can be found in 'license.txt'.

"""
Pyzo is a cross-platform Python IDE focused on
interactivity and introspection, which makes it very suitable for
scientific computing. Its practical design is aimed at simplicity and
efficiency.

Pyzo is written in Python 3 and Qt. Binaries are available for Windows,
Linux, and Mac. For questions, there is a discussion group.

**Two components + tools**


Pyzo consists of two main components, the editor and the shell, and uses
a set of pluggable tools to help the programmer in various ways. Some
example tools are source structure, project manager, interactive help,
and workspace.

**Some key features**


* Powerful *introspection* (autocompletion, calltips, interactive help)
* Allows various ways to *run code interactively* or to run a file as a script.
* The shells runs in a *subprocess* and can therefore be interrupted or killed.
* *Multiple shells* can be used at the same time, and can be of different
  Python versions (from v2.4 to 3.x, including pypy)
* Support for using several *GUI toolkits* interactively:
  asyncio, PySide, PySide2, PyQt4, PyQt5, wx, fltk, GTK, Tk, Tornado.
* Run IPython shell or native shell.
* *Full Unicode support* in both editor and shell.
* Various handy *tools*, plus the ability to make your own.
* Matlab-style *cell notation* to mark code sections (by starting a line
  with '##').

"""

# Set version number
__version__ = "4.14.4"

import sys

# Check Python version
if sys.version_info < (3, 6):
    raise RuntimeError("Pyzo requires Python 3.6+ to run.")


def start():
    """Start Pyzo."""
    from ._start import start

    start()
