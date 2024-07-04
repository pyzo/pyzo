import os
import re
import sys
import zipfile
import tarfile
import platform
import subprocess


this_dir = os.path.abspath(os.path.dirname(__file__)) + "/"
dist_dir = this_dir + "dist/"


with open(
    os.path.join(this_dir, "..", "pyzo", "__init__.py"), "rt", encoding="utf-8"
) as fh:
    __version__ = re.search(r"__version__ = \"(.*?)\"", fh.read()).group(1)

bitness = "32" if sys.maxsize <= 2**32 else "64"

osname = os.getenv("PYZO_OSNAME", "")
if osname:
    pass
elif sys.platform.startswith("linux"):
    osname = "linux_" + platform.machine()
elif sys.platform.startswith("win"):
    osname = f"win{bitness}"
elif sys.platform.startswith("darwin"):
    osname = "macos_" + platform.machine()
else:
    raise RuntimeError("Unknown platform")

basename = f"pyzo-{__version__}-{osname}"


## Utils


def package_tar_gz():
    print("Packing up into tar.gz ...")

    oridir = os.getcwd()
    os.chdir(dist_dir)
    try:
        with tarfile.open(basename + ".tar.gz", "w|gz") as tf:
            tf.add("pyzo", arcname="pyzo")
    finally:
        os.chdir(oridir)


def package_zip():
    print("Packing up into zip ...")

    dirname1 = "pyzo.app" if sys.platform.startswith("darwin") else "pyzo"
    dirname2 = dirname1

    zf = zipfile.ZipFile(
        os.path.join(dist_dir, basename + ".zip"), "w", compression=zipfile.ZIP_DEFLATED
    )
    with zf:
        for root, dirs, files in os.walk(os.path.join(dist_dir, dirname1)):
            for fname in files:
                filename1 = os.path.join(root, fname)
                filename2 = os.path.relpath(filename1, os.path.join(dist_dir, dirname1))
                filename2 = os.path.join(dirname2, filename2)
                zf.write(filename1, filename2)


def package_inno_installer():
    print("Packing up into exe installer (via Inno Setup) ...")

    exes = [
        r"c:\Program Files (x86)\Inno Setup 5\ISCC.exe",
        r"c:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    ]
    for exe in exes:
        if os.path.isfile(exe):
            break
    else:
        raise RuntimeError("Could not find Inno Setup exe")

    # Set inno file
    innoFile1 = os.path.join(this_dir, "installerBuilderScript.iss")
    innoFile2 = os.path.join(this_dir, "installerBuilderScript2.iss")
    with open(innoFile1, "rb") as f:
        text = f.read().decode()
    text = text.replace("X.Y.Z", __version__).replace("64", bitness)
    if bitness == "32":
        text = text.replace("ArchitecturesInstallIn64BitMode = x64", "")
    with open(innoFile2, "wb") as f:
        f.write(text.encode())
    try:
        subprocess.check_call([exe, "/Qp", innoFile2], cwd=dist_dir)
    finally:
        os.remove(innoFile2)


def package_dmg():
    print("Packing up into DMG ...")

    app_dir = "pyzo.app"
    dmg_file = basename + ".dmg"

    cmd = ["hdiutil", "create"]
    cmd.extend(["-srcfolder", app_dir])
    cmd.extend(["-volname", "pyzo"])
    cmd.extend(["-format", "UDZO"])
    cmd.extend(["-fs", "HFSX"])
    # cmd.extend(["-uid", "99"])  # who ever is mounting
    # cmd.extend(["-gid", "99"])  # who ever is mounting
    cmd.extend(["-mode", "555"])  # readonly
    cmd.append("-noscrub")
    cmd.append(dmg_file)

    try:
        subprocess.check_output(cmd, cwd=dist_dir, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as err:
        print(err.output.decode())  # hopefully helpful
        raise err


## Build


if sys.platform.startswith("linux"):
    package_zip()
    package_tar_gz()

if sys.platform.startswith("win"):
    package_zip()
    if bitness == "64":
        # Note: for some reason the 32bit installer is broken. Ah well, the zip works.
        package_inno_installer()

if sys.platform.startswith("darwin"):
    package_zip()
    package_dmg()
