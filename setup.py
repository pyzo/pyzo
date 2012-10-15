# -*- coding: utf-8 -*-
import os
from distutils.core import setup

""" Setup script for the IEP package.

What it tries to achieve: copy the iep directory to the install dir.
"""

name = 'iep'
description = 'the interactive editor for Python'

# Get version and docstring
__version__ = None
__doc__ = ''
docStatus = 0 # Not started, in progress, done
initFile = os.path.join(os.path.dirname(__file__), 'iep', '__init__.py')
for line in open(initFile).readlines():
    if (line.startswith('__version__')):
        exec(line.strip())
    elif line.startswith('"""'):
        if docStatus == 0:
            docStatus = 1
            line = line.lstrip('"')
        elif docStatus == 1:
            docStatus = 2
    if docStatus == 1:
        __doc__ += line


setup(
    name = name,
    version = __version__,
    author = 'Science Applied',
    author_email = 'a.klein@science-applied.nl',
    license = '(new) BSD',
    
    url = 'http://code.google.com/p/iep/',
    download_url = 'http://code.google.com/p/iep/downloads/list',    
    keywords = "Python interactive IDE Qt science",
    description = description,
    long_description = __doc__,
    
    platforms = 'any',
    provides = ['iep'],
    #install_requires = ['pyzolib', 'PySide' or 'PyQt4'],
    
    packages = ['iep', 'iep.iepcore', 'iep.iepkernel', 'iep.tools', 
                'iep.codeeditor', 'iep.codeeditor.parsers', 'iep.codeeditor.extensions',
                'iep.yoton', 'iep.yoton.channels',  'iep.yoton.tests',
               ],
    package_dir = {'iep': 'iep'},
    package_data = {'iep': [ 'license.txt', 'resources/*.*', 'resources/icons/*.*']},
    zip_safe = False,
    
    classifiers=[
          'Development Status :: 5 - Production/Stable',
          'Intended Audience :: Science/Research',
          'Intended Audience :: Education',
          'Intended Audience :: Developers',
          'Topic :: Scientific/Engineering',
          'Topic :: Software Development',
          'License :: OSI Approved :: BSD License',
          'Operating System :: MacOS :: MacOS X',
          'Operating System :: Microsoft :: Windows',
          'Operating System :: POSIX',
          'Programming Language :: Python :: 3',
          ],
    )
