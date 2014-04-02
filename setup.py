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
    author = 'Almar Klein',
    author_email = 'almar.klein@gmail.com',
    license = '(new) BSD',
    
    url = 'http://www.iep-project.org',
    download_url = 'http://www.iep-project.org/downloads.html',    
    keywords = "Python interactive IDE Qt science",
    description = description,
    long_description = __doc__,
    
    platforms = 'any',
    provides = ['iep'],
    install_requires = ['pyzolib'], # and 'PySide' or 'PyQt4'
    
    packages = ['iep', 'iep.iepcore', 'iep.iepkernel', 'iep.util',
                'iep.tools', 'iep.tools.iepFileBrowser',
                'iep.codeeditor', 'iep.codeeditor.parsers', 'iep.codeeditor.extensions',
                'iep.yoton', 'iep.yoton.channels',
               ],
    package_dir = {'iep': 'iep'},
    package_data = {'iep': ['license.txt', 'contributors.txt', 
                            'resources/*.*', 
                            'resources/icons/*.*', 'resources/appicons/*.*', 
                            'resources/images/*.*', 'resources/fonts/*.*',
                            'resources/translations/*.*']},
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
