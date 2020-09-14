# -*- coding: utf-8 -*-
# Copyright (C) 2012 Almar Klein
# This module is distributed under the terms of the (new) BSD License.

""" Various utilities to modify Dynamic Link libraries.

Needed to build the Pyzo distro, and it's possible that this
functionality is needed to fix extension modules after installation in
a Pyzo distro.

This is a mix of utilities for Windows, Mac and Linux.

"""

import os
import stat
import sys
import subprocess
import time
import re


_COMMAND_TO_SEARCH_PATH = []


def get_command_to_set_search_path():
    """Get the command to change the RPATH of executables and dynamic
    libraries. Returns None if there is no such command or if it
    cannot be found.
    """

    # Check if already computed
    if _COMMAND_TO_SEARCH_PATH:
        return _COMMAND_TO_SEARCH_PATH[0]

    # Get name of the utility
    # In Pyzo it should be present in 'shared'.
    utilCommand = None
    if sys.platform.startswith("win"):
        return
    if sys.platform.startswith("linux"):
        utilname = "patchelf"
    if sys.platform.startswith("darwin"):
        utilname = "install_name_tool"
    if True:
        # Try old Pyzo
        utilCommand = os.path.join(sys.prefix, "shared", utilname)
        if not os.path.isfile(utilCommand):
            utilCommand = utilname
        # Try new Pyzo / anaconda
        utilCommand = os.path.join(sys.prefix, "bin", utilname)
        if not os.path.isfile(utilCommand):
            utilCommand = utilname
        # Test whether it exists
        try:
            subprocess.check_output(["which", utilCommand])
        except Exception:
            raise RuntimeError(
                "Could not get command (%s) to set search path." % utilCommand
            )

    # Store and return
    _COMMAND_TO_SEARCH_PATH.append(utilCommand)
    return utilCommand


def set_search_path(fname, *args):
    """set_search_path(fname, *args)
    For the given library/executable, set the search path to the
    relative paths specified in args.

    For Linux: The RPATH is the path to search for its dependencies.
    http://enchildfone.wordpress.com/2010/03/23/a-description-of-rpath-origin-ld_library_path-and-portable-linux-binaries/

    For Mac: We use the @rpath identifier to get similar behavior to
    Linux. But each dependency must be specified. To realize this, we
    need to check for each dependency whether it is on one of te given
    search paths.

    For Windows: not supported in any way. Windows searches next to the
    library and then in system paths and PATH.

    """

    # Prepare
    args = [arg.lstrip("/") for arg in args if arg]
    args = [arg for arg in args if arg != "."]  # Because we add empty dir anyway
    args.append("")  # make libs search next to themselves
    command = get_command_to_set_search_path()

    if sys.platform.startswith("linux"):
        # Create search path value
        rpath = ":".join(["$ORIGIN/" + arg for arg in args])
        # Modify rpath using a call to patchelf utility
        cmd = [command, "--set-rpath", rpath, fname]
        subprocess.check_call(cmd)
        print("Set RPATH for %r" % os.path.basename(fname))
        # print('Set RPATH for %r: %r' % (os.path.basename(fname), rpath))

    elif sys.platform.startswith("darwin"):
        # ensure write permissions
        mode = os.stat(fname).st_mode
        if not (mode & stat.S_IWUSR):
            os.chmod(fname, mode | stat.S_IWUSR)
        # let the file itself know its place (simpyl on rpath)
        name = os.path.basename(fname)
        subprocess.call(("install_name_tool", "-id", "@rpath/" + name, fname))
        # find the references: call otool -L on the file
        otool = subprocess.Popen(("otool", "-L", fname), stdout=subprocess.PIPE)
        references = otool.stdout.readlines()[1:]

        # Replace each reference
        rereferencedlibs = []
        for reference in references:
            # find the actual referenced file name
            referencedFile = reference.decode().strip().split()[0]
            if referencedFile.startswith("@"):
                continue  # the referencedFile is already a relative path
            # Get lib name
            _, name = os.path.split(referencedFile)
            if name.lower() == "python":
                name = "libpython"  # Rename Python lib on Mac
            # see if we provided the referenced file
            potentiallibs = [
                os.path.join(os.path.dirname(fname), arg, name) for arg in args
            ]
            # if so, change the reference and rpath
            if any([os.path.isfile(p) for p in potentiallibs]):
                subprocess.call(
                    (
                        "install_name_tool",
                        "-change",
                        referencedFile,
                        "@rpath/" + name,
                        fname,
                    )
                )
                for arg in args:
                    mac_add_rpath(fname, "@loader_path/" + arg)
                mac_add_rpath(fname, "@executable_path/")  # use libpython next to exe
                rereferencedlibs.append(name)
        if rereferencedlibs:
            print(
                'Replaced refs for "%s": %s'
                % (os.path.basename(fname), ", ".join(rereferencedlibs))
            )

    elif sys.platform.startswith("win"):
        raise RuntimeError(
            "Windows has no way of setting the search path on a library or exe."
        )
    else:
        raise RuntimeError(
            "Do not know how to set search path of library or exe on %s" % sys.platform
        )


def mac_add_rpath(fname, rpath):
    """mac_add_rpath(fname, rpath)
    Set the rpath for a Mac library or executble. If the rpath is already
    registered, it is ignored.
    """
    cmd = ["install_name_tool", "-add_rpath", rpath, fname]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    while p.poll() is None:
        time.sleep(0.01)
    if p.returncode:
        msg = p.stdout.read().decode("utf-8")
        if "would duplicate path" in msg:
            pass  # Ignore t
        else:
            raise RuntimeError("Could not set rpath: " + msg)


def remove_CRT_dependencies(dirname, recurse=True):
    """remove_CRT_dependencies(path, recurse=True)
    Check all .dll and .pyd files in the given directory (and its
    subdirectories if recurse is True), removing the dependency on the
    Windows C runtime from the embedded manifest.
    """
    dllExt = [".dll", ".pyd"]
    for entry in os.listdir(dirname):
        p = os.path.join(dirname, entry)
        if recurse and os.path.isdir(p):
            remove_CRT_dependencies(p, recurse)
        elif os.path.isfile(p) and os.path.splitext(p)[1].lower() in dllExt:
            remove_CRT_dependency(p)


def remove_CRT_dependency(filename):
    """remove_CRT_dependency(filename)
    Modify the embedded manifest of a Windows dll (or pyd file),
    such that it no longer depends on the Windows C runtime.
    In effect, the dll will fall back to using the C runtime that
    the executable depends on (and has loaded in memory).

    This function is not necessary for dll's and pyd's that come with
    Python, because these are build without the CRT dependencies for a
    while. However, some third party packages (e.g. PySide) do have
    these dependencies, and they need to be removed in order to work
    on a system that does not have the C-runtime installed.

    Based on this diff by C. Gohlke:
    http://bugs.python.org/file15113/msvc9compiler_stripruntimes_regexp2.diff
    See discussion at: http://bugs.python.org/issue4120

    """
    if "QtCore" in filename:
        1 / 0

    # Read the whole file
    with open(filename, "rb") as f:
        try:
            bb = f.read()
        except IOError:
            # raise IOError('Could not read %s'%filename)
            print("Warning: could not read %s" % filename)
            return

    # Remove assemblyIdentity tag
    # This code is different from that in python's distutils/msvc9compiler.py
    # by removing re.DOTALL and replaceing the second DOT with "(.|\n|\r)",
    # which means that the first DOT cannot contain newlines. Would we not do
    # this, the match is too greedy (and causes tk85.dll to break).
    pattern = (
        r"""<assemblyIdentity.*?name=("|')Microsoft\."""
        r"""VC\d{2}\.CRT("|')(.|\n|\r)*?(/>|</assemblyIdentity>)"""
    )
    pattern = re.compile(pattern.encode("ascii"))
    bb, hasMatch = _replacePatternWithSpaces(pattern, bb)
    if hasMatch:
        # Remove dependentAssembly tag if it's empty
        pattern = "<dependentAssembly>\s*</dependentAssembly>".encode("ascii")
        bb, hasMatch = _replacePatternWithSpaces(pattern, bb)
        # Write back
        with open(filename, "wb") as f:
            f.write(bb)
        print("Removed embedded MSVCR dependency for: %s" % filename)


def _replacePatternWithSpaces(pattern, bb):
    match = re.search(pattern, bb)
    if match is not None:
        L = match.end() - match.start()
        bb = re.sub(pattern, b" " * L, bb)
        return bb, True
    else:
        return bb, False
