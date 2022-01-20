import os
import sys
import subprocess


this_dir = os.path.abspath(os.path.dirname(__file__))
dist_dir = os.path.join(this_dir, "dist")

# Get what executable to run
if sys.platform.startswith("win"):
    exe = os.path.join(dist_dir, "pyzo", "pyzo.exe")
elif sys.platform.startswith("darwin"):
    exe = os.path.join(dist_dir, "pyzo.app", "Contents", "MacOS", "pyzo")
else:
    exe = os.path.join(dist_dir, "pyzo", "pyzo")

# Prepare log file
logfilename = os.path.abspath(os.path.join(__file__, "..", "..", "log.txt"))
with open(logfilename, "wt") as f:
    f.write("")

# Run Pyzo
os.environ["PYZO_LOG"] = logfilename
subprocess.run([exe, "--test"], cwd=this_dir)
