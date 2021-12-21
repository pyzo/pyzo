import os
import sys
import subprocess

this_dir = os.path.abspath(os.path.dirname(__file__)) + "/"
dist_dir = os.path.join(this_dir, "dist")

# Get what executable to run
if sys.platform.startswith("win"):
    exe = os.path.join(dist_dir, "pyzo", "pyzo.exe")
elif sys.platform.startswith("darwin"):
    exe = os.path.join(dist_dir, "pyzo.app", "Contents", "MacOS", "pyzo")
else:
    exe = os.path.join(dist_dir, "pyzo", "pyzo")

# Prepare log file
logfile = os.path.join(this_dir, "log.txt")
with open(logfile, "wt") as f:
    f.write("")

# Run Pyzo
os.environ["PYZO_LOG"] = logfile
subprocess.run([exe, "--test"])

# Process log
print("=" * 80)
with open(logfile, "rt") as f:
    log = f.read()
os.remove(logfile)
print(log)
if log.strip().endswith("Stopped"):
    sys.exit(0)
else:
    sys.exit("Unsuccessful Pyzo test run")
