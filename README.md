# Pyzo - The Interactive editor for scientific Python

[![PyPI Version](https://img.shields.io/pypi/v/pyzo.svg)](https://pypi.python.org/pypi/pyzo/)
[![CI](https://github.com/pyzo/pyzo/actions/workflows/ci.yml/badge.svg)](https://github.com/pyzo/pyzo/actions/workflows/ci.yml)

Website: [pyzo.org](https://pyzo.org)


### Description

Pyzo is a cross-platform Python IDE focused on
interactivity and introspection, which makes it very suitable for
scientific computing. Its practical design is aimed at simplicity and
efficiency.

It consists of two main components, the editor and the shell, and uses
a set of pluggable tools to help the programmer in various ways. Some
example tools are source structure, file browser, interactive help,
workspace ...

Pyzo is written in (pure) Python 3 and uses the Qt GUI toolkit. Binaries
are provided for all major operating systems. After installing Pyzo, it
can be used to execute code on any Python version available on your
system (Python 2.7 - 3.x, including PyPy).


### Installation


#### Running Pyzo from pre-built binaries

We provide [binaries](https://github.com/pyzo/pyzo/releases) for Windows, Linux and MacOS.  
Linux users are recommended to run Pyzo from source because of possible Qt library incompatibilities.

#### Running Pyzo from source

To run Pyzo from source, you need a Python interpreter with one of the following Qt bindings:  
PySide2, PySide6, PyQt5, PyQt6.  
If you do not have such a Qt wrapper then install one from https://pypi.org
via the Python package manager, e.g.:  
`python3 -m pip install pyside6`

Linux users might do this via their Linux package manager, e.g.:  
`sudo apt-get install python3-pyqt5`

Download the source code archive from the [releases page](https://github.com/pyzo/pyzo/releases) or the
[newest development version](https://github.com/pyzo/pyzo/archive/refs/heads/main.zip) and extract the
contents into a folder.  
Pyzo can then be run from source by executing
the [pyzolauncher.py](https://github.com/pyzo/pyzo/blob/main/pyzolauncher.py) script inside that folder,
for example:  
`python3 /path/to/pyzo-source/pyzolauncher.py`

To use a specific Qt wrapper, set the environment variable `QT_API` to the name of the wrapper package,
e.g. `pyqt6`.  
Linux users can add Pyzo to the desktop environment by copying and customizing the
[desktop-file](https://github.com/pyzo/pyzo/blob/main/pyzo/resources/org.pyzo.Pyzo.desktop).

#### Running Pyzo as a module

Running Pyzo as a Python module is similar to running Pyzo from source, as described in the
previous chapter.  
Instead of downloading the source code archive from GitHub, it can be installed from https://pypi.org
via the Python package manager, e.g.:  
`python3 -m pip install pyzo`

To run Pyzo, execute:  
`python3 -m pyzo`

#### Building your own binary executable of Pyzo

If you prefer a binary version of Pyzo instead of running Pyzo directly from source or downloading a release then you can
build your own Pyzo executable:  
Download the [source code](https://github.com/pyzo/pyzo/archive/refs/heads/main.zip) and follow the
instructions in the comment block on top of [pyzo_freeze.py](https://github.com/pyzo/pyzo/blob/main/freeze/pyzo_freeze.py).
Basically, this is just  
`pip install --upgrade pip pyside6 pyinstaller dialite` and executing pyzo_freeze.py.


### License

Pyzo is free and open source, licensed under the 2-clause BSD.


### Contributions

If you want to help out, create an issue or pull request on GitHub.


### More information

* main website: https://pyzo.org
* code repository: https://github.com/pyzo/pyzo
* issues: https://github.com/pyzo/pyzo/issues
* questions: https://github.com/pyzo/pyzo/discussions
