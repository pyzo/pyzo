# -*- coding: utf-8 -*-

""" Setup script for the Pyzo package.
"""


import os
import sys

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


name = 'pyzo'
description = 'the interactive editor for Python'


# Get version and docstring
__version__ = None
__doc__ = ''
docStatus = 0 # Not started, in progress, done
initFile = os.path.join(os.path.dirname(__file__), 'pyzo', '__init__.py')
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

    url = 'http://www.pyzo.org',
    download_url = 'http://www.pyzo.org/downloads.html',
    keywords = "Python interactive IDE Qt science",
    description = description,
    long_description = __doc__,

    platforms = 'any',
    provides = ['pyzo'],
    install_requires = [], # and 'PySide' or 'PyQt4'

    packages = ['pyzo', 'pyzo.core', 'pyzo.pyzokernel', 'pyzo.util',
                'pyzo.tools', 'pyzo.tools.pyzoFileBrowser',
                'pyzo.codeeditor', 'pyzo.codeeditor.parsers', 'pyzo.codeeditor.extensions',
                'pyzo.yoton', 'pyzo.yoton.channels',
               ],
    package_dir = {'pyzo': 'pyzo'},
    package_data = {'pyzo': ['license.txt', 'contributors.txt',
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
        
    entry_points = {'console_scripts': ['pyzo = pyzo.__main__',], },
    )


# Install appdata.xml on Linux if we are installing in the system Python
if sys.platform.startswith('linux') and sys.prefix.startswith('/usr'):
    if len(sys.argv) >= 2 and sys.argv[1] == 'install':
        fname = 'pyzo.appdata.xml'
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
