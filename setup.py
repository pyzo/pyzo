# -*- coding: utf-8 -*-

""" Setup script for the Pyzo package.
"""


import os
import sys

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


def get_version_and_doc(filename):
    NS = dict(__version__='', __doc__='')
    docStatus = 0  # Not started, in progress, done
    for line in open(filename, 'rb').read().decode().splitlines():
        if line.startswith('__version__'):
            exec(line.strip(), NS, NS)
        elif line.startswith('"""'):
            if docStatus == 0:
                docStatus = 1
                line = line.lstrip('"')
            elif docStatus == 1:
                docStatus = 2
        if docStatus == 1:
            NS['__doc__'] += line.rstrip() + '\n'
    if not NS['__version__']:
        raise RuntimeError('Could not find __version__')
    return NS['__version__'], NS['__doc__']


def package_tree(pkgroot):
    subdirs = [os.path.relpath(i[0], THIS_DIR).replace(os.path.sep, '.')
               for i in os.walk(os.path.join(THIS_DIR, pkgroot))
               if '__init__.py' in i[2]]
    return subdirs


## Define info of this package

THIS_DIR = os.path.dirname(__file__)

name = 'pyzo'
description = 'the Python IDE for scientific computing'

version, doc = get_version_and_doc(os.path.join(THIS_DIR, name, '__init__.py'))


## Setup
setup(
    name = name,
    version = version,
    author = 'Almar Klein',
    author_email = 'almar.klein@gmail.com',
    license = '(new) BSD',

    url = 'http://www.pyzo.org',
    keywords = "Python interactive IDE Qt science computing",
    description = description,
    long_description = doc,

    platforms = 'any',
    provides = ['pyzo'],
    install_requires = [],  # and 'PySide' or 'PySide2' or 'PyQt5' or 'PyQt4'

    packages = package_tree(name),
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
        
    entry_points = {'console_scripts': ['pyzo = pyzo.__main__:main',], },
    )


## Post processing

# Install appdata.xml on Linux if we are installing in the system Python
if sys.platform.startswith('linux') and sys.prefix.startswith('/usr'):
    if len(sys.argv) >= 2 and sys.argv[1] == 'install':
        fname = 'pyzo.appdata.xml'
        filename1 = os.path.join(os.path.dirname(__file__), fname)
        filename2 = os.path.join('/usr/share/metainfo', fname)
        try:
            bb = open(filename1, 'rb').read()
            open(filename2, 'wb').write(bb)
        except PermissionError:
            pass  # No sudo, no need to warn
        except Exception as err:
            print('Could not install %s: %s' % (fname, str(err)))
        else:
            print('Installed %s' % fname)
