Portable settings folder
------------------------
This folder can be used to let the application and the libaries that
it uses to store configuration files local to the executable. One use
case is having this app on a USB drive that you use on different
computers.

This functionality is enabled if the folder is named "settings" and is
writable by the application (i.e. should not be in "c:\program files\..."
or "/usr/..."). This functionality can be deactivated by renaming
it (e.g. prepending an underscore). To reset config files, clear the
contents of the "pyzo" sub-folder (but do not remove the folder itself).

Note that some libraries may ignore this functionality and use the
normal system configuration directory instead.
