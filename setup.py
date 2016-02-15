# -*- coding: utf-8 -*-

""" Setup script for the IEP package.
"""


import os
import sys

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


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
    install_requires = [], # and 'PySide' or 'PyQt4'

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

    classifiers = [
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
        
    entry_points = {'console_scripts': ['iep = iep.__main__',], },
    )


# Install appdata.xml on Linux if we are installing in the system Python
if sys.platform.startswith('linux') and sys.prefix.startswith('/usr'):
    if len(sys.argv) >= 2 and sys.argv[1] == 'install':
        fname = 'iep.appdata.xml'
        filename1 = os.path.join(os.path.dirname(__file__), fname)
        filename2 = os.path.join('/usr/share/appdata', fname)
        try:
            bb = open(filename1, 'rb').read()
            open(filename2, 'wb').write(bb)
        except PermissionError:
            pass  # No sudo, no need to warn
        except Exception as err:
            print('Could not install %s: %s' % (fname, str(err)))
        else:
            print('Installed %s' % fname)
