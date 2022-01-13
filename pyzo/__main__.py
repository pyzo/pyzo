#!/usr/bin/env python3
"""
Pyzo __main__ module

This module enables starting Pyzo via either "python3 -m pyzo" or
"python3 path/to/pyzo".
"""

import os
import sys
import time
import platform


# Very probably run as a script, either the package or the __main__
# directly. Add parent directory to sys.path and try again.
this_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.split(this_dir)[0])

import pyzo


TESTING = "--test" in sys.argv


def write(*msg):
    print(*msg)
    if os.getenv("PYZO_LOG", ""):
        with open(os.getenv("PYZO_LOG"), "at") as f:
            f.write(" ".join(msg) + "\n")


def main():

    if TESTING:
        dt = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        write(f"Testing Pyzo source ({dt} UTC)")
        write(platform.platform())
        write(sys.version)

    write(f"Pyzo {pyzo.__version__}")
    pyzo.start()
    write("Stopped")  # may be written to log twice because Pyzo defers stdout


if __name__ == "__main__":
    main()
