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
to move them to a (different) project.

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
when it is busy, IEP itself stays responsonsive, which allows you
to keep coding or even run code in another shell. 

We get back to the different shell configurations later in this 
tutorial.

"""

## Running code
"""
IEP supports several ways to run source code in the editor. (see
also Menu > Run).

  * Run selected lines. If a line is partially selected, the whole
    line is executed. If there is no selection, IEP will run the
    current line.
    
  * Run cell. A cell is everything between two commands starting
    with '##', such as the headings in this tutorial. Try running
    the code at the bottom of this cell!

  * Run file. This runs all the code in the current file.
  
  * Run project main file. Runs the code in the current project's
    main file.

Additionally, one can run the current file or the current project's
main file as a script. This will first restart the shell to provide
a clean environment. The shell is also initialized differently, see
below.

Done on shell startup in INTERACTIVE MODE:
  * sys.argv = []
  * sys.path is prepended with an empty string (current working directory)
  * The working dir is set to the "Initial directory" of the shell config.
  * The PYTHONSTARTUP script is run.

Done on shell startup in SCRIPT MODE:
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
advanced/specific stuff, you can use the logger tool.

All actions in the menu can be run quicker by defining a shortcut for it
via the shortcut editor: Menu > Settings > Change shortcuts.
  
"""

## Shell configurations

## Debugging

## The different tools
