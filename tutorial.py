## Introduction
""" 
Welcome to the tutorial for IEP! This tutorial should get you 
familiarized with IEP in just a few minutes. If you feel this tutorial
contains error or lacks some information, please let me know via
almar.klein at gmail dot com.

IEP is a cross-platform Python IDE focused on interactivity and
introspection, which makes it very suitable for scientific computing. 
Its practical design is aimed at simplicity and efficiency. 

IEP consists of two main components, the editor and the shell, and 
uses a set of pluggable tools to help the programmer in various ways. 

"""


## The editor
"""
The editor is where your code is located; it is the central component
of IEP. 

To the left of the editor is a list of open files. The files
can be organized in projects, and are stacked vertically so you can
access your files easily. You can drag files to change their order, or
move them to a (different) project.

Using the right mouse button, files can be created, saved, closed, etc. 

The right mouse button also enables to make a file the MAIN FILE of
a project. This file can be easily recognized by its bold face, and
it enables running the file more easily (as we will see later in this
tutorial).

"""


## The shells
"""
The other main component is the window that holds the shells. When IEP
starts, a default shell is created. You can add more shells that run
simultaneously, and which can be of different Python versions.

It is good to know that the shells run in a sub-process, such that
when it is busy, IEP itself stays responsive, which allows you to 
keep coding and even run code in another shell. 

Another notable feature is that IEP can integrate the event loop of
four different GUI toolkits, thus enabling interactive plotting with
Visvis or Matplotlib. The module of the integrated toolkit is given
an "_integratedEventLoop" attribute, which can be used in scripts to
recognize that an application instance does not have to be created.
  
Via "Shell > Edit shell configurations", you can edit and add shell
configurations. This allows you to for example select the initial
directory, or use a custom PYTHONPATH.

"""


## The tools
"""
Via the "Tools" menu, one can select what tools to use. The tools can
be positioned in any way you want, and can also be un-docked.

Try the "Source Structure" tool to see the outline of this tutorial!

Note that the tools system is designed such that it's quite easy to
create your own tools. Look at the online wiki for more information,
or use one of the existing tools as an example. Also, IEP does not
need to restart to see new tools, or to update existing tools.

"""


## Running code
"""
IEP supports several ways to run source code in the editor. (see
also the "Run" menu).

  * Run selected lines. If a line is partially selected, the whole
    line is executed. If there is no selection, IEP will run the
    current line.
    
  * Run cell. A cell is everything between two commands starting
    with '##', such as the headings in this tutorial. Try running
    the code at the bottom of this cell!

  * Run file. This runs all the code in the current file.
  
  * Run project main file. Runs the code in the current project's
    main file.

Additionally, you can run the current file or the current project's
main file as a script. This will first restart the shell to provide
a clean environment. The shell is also initialized differently, see
below.

Things done on shell startup in INTERACTIVE MODE:
  * sys.argv = []
  * sys.path is prepended with an empty string (current working directory)
  * The working dir is set to the "Initial directory" of the shell config.
  * The PYTHONSTARTUP script is run.

Things done on shell startup in SCRIPT MODE:
  * __file__ = <script_filename>  
  * sys.argv = [ <script_filename> ]  
  * sys.path is prepended with the directory containing the script.
  * The working dir is set to the directory containing the script.  

"""

a = 3
b = 4
print('The answer is ' + str(a+b))


## The menu
"""
Almost all functionality of IEP can be accessed via the menu. For more
advanced/specific stuff, you can use the logger tool (see also 
Settings > Advanced)

All actions in the menu can be accessed via a shortcut. Change the 
shortcuts using the shortcut editor: Menu > Settings > Change shortcuts.
  
"""

  
## Introspection
"""
IEP has strong introspection capabilities. IEP knows about the objects
in the shell, and parses (not runs) the source code in order to detect
the structure of your code. This enables powerful instospection such
as autocompletion, calltips, interactive help and source structure.
  
"""


## Debugging
"""
IEP supports post-mortem debugging, which means that after something 
went wrong, you can inspect the stack trace to find the error.

The easiest way to start debugging is to press the "Post mortem" button
at the upper right corner of the shells.

Once in debug mode, the button becomes expandable, allowing you to
see the stack trace and go to any frame you like. (Starting debug mode
brings you to the bottom frame). Changing a frame will make all objects
in that frame available in the shell. If possible, IEP will also show
the source file belonging to that frame, and select the line where the
error occurred.

Debugging can also be controlled via magic commands, type "?" in the
shell for more information.

Below follows an example that you can run to test the debugging.
  
""" 

import random
someModuleVariable = True

def getNumber():
    return random.choice(range(10))

def foo():
    spam = 'yum'
    egs = 7 
    value = bar()
    
def bar():
    total = 0
    for i1 in range(100):
        i2 = getNumber()
        total += i1/i2    
    return total

foo()

