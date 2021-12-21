import os
import sys

this_dir = os.path.abspath(os.path.dirname(__file__)) + "/"
frozen_dir = os.path.join(this_dir, "dist", "pyzo")

if sys.platform.startswith("win"):
    exe = os.path.join(frozen_dir, "pyzo.exe")
elif sys.platform.startswith("darwin"):
    exe = os.path.join(frozen_dir, "pyzo.app", "Contents", "MacOS", "pyzo")
else:
    exe = os.path.join(frozen_dir, "pyzo")

os.execv(exe, ["--test"])
