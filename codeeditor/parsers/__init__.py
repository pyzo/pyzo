# -*- coding: utf-8 -*-
# Copyright (c) 2010, the Codeeditor development team
#
# Codeeditor is distributed under the terms of the (new) BSD License.
# The full license can be found in 'license.txt'.

""" Subpackage parsers

This subpackage contains all the syntax parsers for the
different languages. 

"""


""" CREATING PARSERS

Making a parser requires these things:
  * Place a module in the parsers directory, which has a name 
    ending in "_parser.py"
  * In the module implement one or more classes that inherit
    from ..parsers.Parser (or a derived class), and 
    implement the parseLine method.
  * The module should import all the tokens in whiches to use 
    from ..parsers.tokens. New tokens can also be
    defined by subclassing one of the token classes.
  * In codeeditor/parsers/__init__.py, add the new module to the 
    list of imported parsers.

"""

# Normal imports 
import os, sys
import zipfile
from . import tokens


# Base parser class (needs to be defined before importing parser modules
class Parser(object):
    """ Base parser class. 
    All parsers should inherit from this class.
    """
    _extensions = []
    _keywords = []
    
    
    def parseLine(self, line, previousState=0):
        """ parseLine(line, previousState=0)
        
        The method that should be implemented by the parser. The 
        previousState argument can be used to determine how
        the previous block ended (e.g. for multiline comments). It
        is an integer, the meaning of which is only known to the
        specific parser. 
        
        This method should yield token instances. The last token can
        be a ContinuationToken to specify the previousState for the 
        next block.
        
        """
        raise NotImplementedError()
    
    
    def name(self):
        """ name()
        
        Get the name of the parser.
        
        """
        name = self.__class__.__name__.lower()
        if name.endswith('parser'):
            name = name[:-6]
        return name
    
    
    def __repr__(self):
        """ String representation of the parser. 
        """
        return '<Parser for "%s">' % self.name()
    
    
    def keywords(self):
        """ keywords()
        
        Get a list of keywords valid for this parser.
        
        """
        return self._keywords
    
    
    def filenameExtensions(self):
        """ filenameExtensions()
        
        Get a list of filename extensions for which this parser
        is appropriate.
        
        """
        return self._extensions
    
    
    def getStyleElementDescriptions(cls):
        """ getStyleElementDescriptions()
        
        This method returns a list of the StyleElementDescription 
        instances used by this parser. 
        
        """
        descriptions = {}
        for token in self.getUsedTokens():
            description = token.description()
            descriptions[description.key] = description
        
        return list(descriptions.values())
    
    
    def getUsedTokens(self):
        """ getUsedTokens()
        
        Get a a list of token instances used by this parser.
        
        """
        
        # Get module object of the parser
        try:
            mod = sys.modules[self.__module__]
        except KeyError:
            return []
        
        # Get token classes from module
        tokenClasses = []
        for name in mod.__dict__:
            member = mod.__dict__[name]
            if isinstance(member, type) and \
                                    issubclass(member, tokens.DefaultToken):
                tokenClasses.append(member)
        
        # Return as instances
        return [t() for t in tokenClasses]
    


## Import parsers statically
# We could load the parser dynamically from the source files in the 
# directory, but this takes quite some effort to get righ when apps 
# are frozen. This is doable (I do it in Visvis) but it requires the
# user to specify the parser modules by hand when freezing an app.
#
# In summary: it takes a lot of trouble, which can be avoided by just
# listing all parsers here.
from codeeditor.parsers import (    python_parser, 
                                    stupid_parser, 
                                    c_parser,
                                )


# todo: combine pareser manager with a generic code editor manager?
class ParserManager:
    """ ParserManager
    
    Static class to obtain information about parsers.
    
    """
    
    # Static dict of all parsers
    _parserInstances = {}
    
    
#     @classmethod
#     def collecrParsersDynamically(cls):
#         """ insert the function is this module's namespace.
#         """
#         
#         # Get the path of this subpackage
#         path = __file__
#         path = os.path.dirname( os.path.abspath(path) )
#         
#         # Determine if we're in a zipfile
#         i = path.find('.zip')
#         if i>0:
#             # get list of files from zipfile
#             path = path[:i+4]
#             z = zipfile.ZipFile(path)
#             files = [os.path.split(i)[-1] for i in z.namelist() 
#                         if 'codeeditor' in i and 'parsers' in i]
#         else:
#             # get list of files from file system
#             files = os.listdir(path)
#         
#         # Extract all parsers
#         parserModules = []
#         for file in files:            
#             
#             # Only python files
#             if file.endswith('.pyc'):
#                 if file[:-1] in files:
#                     continue # Only try import once
#             elif not file.endswith('.py'):
#                 continue    
#             # Only syntax files
#             if '_parser.' not in file:
#                 continue
#             
#             # Import module
#             fullfile = os.path.join(path, file)
#             modname = os.path.splitext(file)[0]
#             print('modname', modname)
#             mod = __import__("codeeditor.parsers."+modname, fromlist=[modname])
#             parserModules.append(mod)
#         
#         print(parserModules)
    

    
    @classmethod
    def collectParsers(cls):
        """ collectParsers()
        
        Collect all parser classes. This function is called on startup.
        
        """
        
        # Prepare (use a set to prevent duplicates)
        foundParsers = set()
        G = globals()
        ModuleClass = os.__class__
        
        # Collect parser classes
        for module_name in G:
            # Check if it is indeed a module, and if it has the right name
            if not isinstance(G[module_name], ModuleClass):
                continue
            if not module_name.endswith('_parser'):
                continue
            # Collect all valid classes from the module
            moduleDict = G[module_name].__dict__
            for name_in_module in moduleDict:
                ob = moduleDict[name_in_module]                    
                if isinstance(ob, type) and issubclass(ob, Parser):
                    foundParsers.add(ob)
        
        # Put in list with the parser names as keys
        parserInstances = {}
        for parserClass in foundParsers:
            name = parserClass.__name__
            if name.endswith('Parser') and len(name)>6:
                
                # Get parser identifier name
                name = name[:-6].lower()
                
                # Try instantiating the parser
                try:
                    parserInstances[name] = parserClass()
                except Exception:
                    # We cannot get the exception object in a Python2/Python3
                    # compatible way
                    print('Could not instantiate parser "%s".'%name)
        
        # Store
        cls._parserInstances = parserInstances
    
    
    @classmethod
    def getParserNames(cls):
        """ getParserNames()
        
        Get a list of all available parsers.
        
        """
        return list(cls._parserInstances.keys())
    
    
    @classmethod
    def getParserByName(cls, parserName):
        """ getParserByName(parserName)
        
        Get the parser object corresponding to the given name.
        If no parser is known by the given name, a warning message
        is printed and None is returned.
        
        """
        
        # Case insensitive
        parserName = parserName.lower()
        
        # Return instantiated parser object.
        if parserName in cls._parserInstances:
            return cls._parserInstances[parserName]
        else:
            print('Warning: no parser known by the name "%s".'%parserName)
            print('I know these: ', cls._parserInstances.keys())
            return None
    
    
    @classmethod
    def getStyleElementDescriptionsForAllParsers(cls):
        """ getStyleElementDescriptionsForAllParsers()
        
        Get all style element descriptions corresponding to 
        the tokens of all parsers.
        
        """
        descriptions = {}
        for parser in cls._parserInstances.values():
            for token in parser.getUsedTokens():
                description = token.description()
                descriptions[description.key] = description
        
        return list(descriptions.values())
    
    
    # todo: define common extension in parsers
    def suggestParserForGivenExtension(self, ext):
        pass
    
    def registerExtension(self, ext, parserName):
        pass


try:
    ParserManager.collectParsers()
except Exception:
    print('Error collecting parsers')
