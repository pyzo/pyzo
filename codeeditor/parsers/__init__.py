# -*- coding: utf-8 -*-
# Copyright (c) 2010, the Codeeditor development team
#
# Codeeditor is distributed under the terms of the (new) BSD License.
# The full license can be found in 'license.txt'.

""" This subpackage contains all the syntax parsers for the
different languages. These are dynamically loaded by this __init__ 
module.
"""

# todo: dynamically load tokenizeLine functions
# todo: way to link style with all tokens, tokens depend on language partly
# todo: way to introduce keywords

import os

from codeeditor.parsers.python_syntax import tokenizeLinePython
from codeeditor.parsers.stupid_syntax import tokenizeLineStupid
from codeeditor.parsers import how_to_call_this
from codeeditor.parsers.how_to_call_this import *


# 
# def _insertFunctions():
#     """ insert the parsers is this module's namespace.
#     """
#     
#     # see which files we have
#     path = __file__
#     path = os.path.dirname( os.path.abspath(path) )
#     
#     # determine if we're in a zipfile
#     i = path.find('.zip')
#     if i>0:
#         # get list of files from zipfile
#         path = path[:i+4]
#         import zipfile
#         z = zipfile.ZipFile(path)
#         files = [os.path.split(i)[1] for i in z.namelist() 
#                     if i.startswith('visvis') and i.count('functions')]
#     else:
#         # get list of files from file system
#         files = os.listdir(path)
#     
#     # extract all functions
#     names = []
#     for file in files:
#         # not this file
#         if file.startswith('__'):
#             continue
#         # only python files
#         if file.endswith('.pyc'):
#             if file[:-1] in files:
#                 continue # only try import once
#         elif not file.endswith('.py'):
#             continue    
#         # build names
#         fullfile = os.path.join(path, file)
#         funname = os.path.splitext(file)[0]
#         # import module
#         mod = __import__("visvis.functions."+funname, fromlist=[funname])
#         if not hasattr(mod,funname):
#             print "module %s does not have a function with the same name!" % (
#                 funname)
#         else:
#             # insert into THIS namespace
#             g = globals()
#             g[funname] = mod.__dict__[funname]
#             names.append(funname)
#     
#     return names
# 
# 
# # do it and clean up
# _functionNames = _insertFunctions()
