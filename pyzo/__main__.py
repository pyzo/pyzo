#!/usr/bin/env python3
"""
Pyzo __main__ module

This module enables starting Pyzo via either "python3 -m pyzo" or
"python3 path/to/pyzo".
"""

import os
import sys


# Very probably run as a script, either the package or the __main__
# directly. Add parent directory to sys.path and try again.
this_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.split(this_dir)[0])

import pyzo


def main():
    # Must have a function main here, as the entry-point to this module
    pyzo.start()


if __name__ == "__main__":
    main()
