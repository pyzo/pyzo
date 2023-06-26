# -*- coding: utf-8 -*-
# Copyright (c) 2016, Almar Klein, Rob Reilink
#
# This file is distributed under the terms of the 2-Clause BSD License.

import os
import sys
from pyzo.qt import QtCore


def is_frozen():
    """is_frozen()
    Return whether this app is a frozen application (using e.g. cx_freeze).
    """
    return bool(getattr(sys, "frozen", None))


def prepare_appdata_appconfig_dirs():
    """get the directories for Pyzo application data and configuration
    folders are created if not present
    """

    # check for a "settings" folder next to the Pyzo executable or one level above,
    # which is typically used for portable applications
    use_portable_settings = False
    if is_frozen():
        exec_dir = os.path.abspath(os.path.dirname(sys.executable))
        for reldir in ("settings", "../settings"):
            localpath = os.path.abspath(os.path.join(exec_dir, reldir))
            if os.path.isdir(localpath):
                try:
                    open(os.path.join(localpath, "test.write"), "wb").close()
                    os.remove(os.path.join(localpath, "test.write"))
                except IOError:
                    pass  # We cannot write in this directory
                else:
                    data_path = config_path = localpath
                    use_portable_settings = True
                    break

    if not use_portable_settings:
        appname = "pyzo"
        path_dot = os.path.expanduser(
            "~/." + appname
        )  # leading dot means hidden directory
        if sys.platform == "win32":
            data_path = config_path = os.path.join(os.getenv("APPDATA"), appname)
            # typically r"C:\Users\username\AppData\Roaming\pyzo"
        elif os.path.isdir(path_dot):
            # existing legacy data and config directory in Linux or macOS
            data_path = config_path = path_dot
        elif sys.platform == "linux":
            # see https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html
            data_path_base = os.getenv("XDG_DATA_HOME", "") or "~/.local/share"
            config_path_base = os.getenv("XDG_CONFIG_HOME", "") or "~/.config"
            data_path = os.path.expanduser(os.path.join(data_path_base, appname))
            config_path = os.path.expanduser(os.path.join(config_path_base, appname))
        elif sys.platform == "darwin":
            sp = QtCore.QStandardPaths
            data_path_base = sp.writableLocation(sp.AppDataLocation)
            config_path_base = sp.writableLocation(sp.ConfigLocation)
            """
            The AppName added by Qt depends on how pyzo was started, e.g.:
                import pyzo; pyzo.start() --> ''
                python pyzolauncher.py --> 'pyzolauncher.py' or 'python'
                via binary from frozen pyzo --> 'pyzo'
            """
            if QtCore.QCoreApplication.applicationName() != "":
                data_path_base = os.path.split(data_path_base)[0]
                config_path_base = os.path.split(config_path_base)[0]
            data_path = os.path.join(data_path_base, appname)
            config_path = os.path.join(config_path_base, appname)
        else:
            raise NotImplementedError("unsupported operating system: " + sys.platform)

        os.makedirs(data_path, exist_ok=True)
        os.makedirs(config_path, exist_ok=True)

    # Create tooldir if necessary
    tool_dir = os.path.join(data_path, "tools")
    os.makedirs(tool_dir, exist_ok=True)

    return data_path, config_path
