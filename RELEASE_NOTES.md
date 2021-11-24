# Release notes


### Version 4.11.4 (24-11-2021)

- Fix for using PySide6 and PyQt5 in interpreter.
- Fix for running Pyzo with Python 3.10.


### Version 4.11.2 (19-11-2020)

- Fix for MacOS Big Sur (#731).


### Version 4.11.0 (16-10-2020)

- Fix broken support for non-english keyboard layouts.
- Support for Python 3.9 (fix thread.isAlive error, thanks @stonebig).
- Fix slow font enumeration.
- Improve behavior on HiDPI screens.
- Prevent errors during editing syntax styles.
- Change the base port number that Pyzo uses to communicate with the kernels.
- Remove button to stop kernel but leave the shell open, to reduce clutter.
- Added support for toggling comments (Ctrl+Shift+3, thanks @l33tlinuxh4x0r).
- Prevent segfault on PySide2.
- Pyzo now closes faster.
- Better handling of carriage return in shell (#705, Thanks Eelke Spaak).
- Autocompletion is triggered a bit later to make it less anoying (thanks Yann Salmon).


### Version 4.10.2 (10-02-2020)

- Fix that PyInstaller's changes to `LD_LIBRARY_PATH` leak through to the kernels (#665).


### Version 4.10.1 (10-02-2020)

- We've now automized the building of binaries on Azure Pipelines!
- Our code is now formatted with Black, and checked with Flake8.
- CI does not have a lot of tests yet, but we do check linting and importing on Python 3.5 and 3.8.
- Implemented support for highres displays (although I am unable to verify myself).
- Improve the workspace display of list, tuple, dict and array.
- Clean up `LD_LIBRARY_PATH` for the kernels (#665).
- Some improvements to asyncio integration.
- Autocompletion no longer cancels the interactive help.
- Issue a warning when `logging.basicConfig()` is called (because it does nothing).
- Fix that non-breakable space was converted (#621, thanks Yann Salmon).
- Add Jetbrains monospace font.
- Fix introspection of signature containing kw-only args or annotations.
- Add polish translation (thanks wojnilowicz)
- Fix that Pyzo crashes on startup when non-english language is set and status bar is shown.


### Version 4.9.0 (16-09-2019)

- Fix a problem where shells do not start on Windows 10 (For some reason, on some machines, aftter a Windows update, some (ranges of) ports are blocked). Resulting in a "warming up" message. See issue #644 for details.
- Pyzo now has a status bar (thanks kelsa-pi).
- Fix that running as script fails when the "use IPython shell" checkbox in on in the shell config, but IPython is unavailable.
- Fix config path detection on older systems.
- Fix that restart did not work when running Pyzo from source.
- Let the menu display the tooltips correctly - no more black rectangles (thanks Tontyna).


### Version 4.8.1 (27-08-2019)

- A fix to make sure Pyzo runs on Python 3.5
- A fix to make sure Pyzo runs correctly on Debian.


### Version 4.8.0 (27-08-2019)

- Fix block commenting when having empty lines (Thanks adddvent)
- Improve automatic insertion of braces and brackets 
- Improvements to advanced Settings (thanks Kelsi-Pi and Yann Salmon)
- The Python 3 parser does not show Python 2 specifics (like print as a keyword) anymore (Thanks Yann Salmon)
- Unified margins between widgets (thanks Kelsi-Pi)
- Enable brace matching in shell (thanks Yann Salmon)
- Improved PDF export (thanks filman230)
- Improved variable explorer (thanks Yann Salmon)
- Interactive help can now show help for operators and keywords, and has backward and forward buttons (thanks Yann Salmon)
- Pyzo stores config data in a more suitable place on Unix (thanks filman230)
- Increase limit for number of lines of a function def for it to be still shown in the source structure tool.


### Version 4.7.4 (12-04-2019)

- The shell now prints the last expression from a run cell (like Spyder does)
- Fix support for Python 2.4
- fix that themes are not packaged in source dist


### Version 4.7.3 (27-03-2019)

A few fixes related to the new freezing process with PyInstaller, causing
a failure to integrate Qt-based GUI toolkits. Also a fix related to the
discovery of Python interpreters.


### Version 4.7.0 (17-03-2019)

* Pyzo properly works with Miniconda/Anaconda environments on Windows again
  (Conda apparently now needs some specific entries in the PATH environment variable).
* We (finally) have different styles to choose from, and they can be tweaked (thanks Erik Helmers).
* Pyzo should scale propertly on high resolution displays (at least on Windows and OS X).
* Can now specify startup code both for before *and* after integrating the GUI (thanks @Diti24).
* There is now a primitive dialog to set advanced settings (thanks kelsa-pi).
* Pyzo will remove trailing whitespace if the original file contained very little trailing whitespace.
* Pyzo can now detect pipenv interpreters.
* The binaries are now build with PyInstaller and should thus be more
  robust. Windows binaries are build on Windows 7, Linux binaries on Ubuntu
  16.04, OS X binaries on 10.11 El Capitan. All binaries are 64 bit.


### Version 4.6.1 (19-10-2018)

* A few tweaks to make Pyzo work better with non-conda environments
  (interpreter selection and install/uodate/remove commands).
* The editor can now guess the file type from the shebang, if present (thanks Yann Salmon).
* Kernel works with Python 2.4 again.
* French translations.


### Version 4.6.0 (06-08-2018)

* Make Pyzo work with Python 3.7 (thanks @stonebig)
* Fix the broken `xx?` command
* Fix the broken `cd` command
* Fix in history viewer autoscroll (thanks @ssoel)
* New feature: autoclose brackets (thanks to @kelsa-pi)
* New feature: autoclose quotes (thanks to @kelsa-pi)
* Play nice with tools like `click` (see #542)
* Make environment variable settings more resilient to whitespace
* Improvements to asyncio integrated event loop


### Version 4.5.1 (14-02-2018)

* Fixed a few bugs introduced in the previous release.


### Version 4.5.0 (08-02-2018)

* Add toggle case and printify in Edit menu (#518 by kelsa-pi).
* Add syntax highlighting for builtins and `self` (#519 by kelsa-pi).
* Suppress errors for unfound files on startup (#520 by Federico Miorelli).
* Don't try to open source file for e.g. ``open ('foo.txt')`` (#515 by Yann Salmon).
* Allow files with spaces to run as script in IPython (#514 by Yehuda Davis).
* Replace single/all/all files now available as combo box (includes #513 by Antoine Fourmy).
* Allow for a site-wide config file (#512 by Yann Salmon).
* Fix for when ipython checkbox is set but ipython is not available (#517).
* Support for event loop integration with asyncio.
* Add syntax highlighting for async and await keywords.
* Add syntax highlighting for textual Web Assembly (.wat).


### Version 4.4.3 (09-10-2017)

* Fix to appdata format to fix building Pyzo on Freedesktop (#510).


### Version 4.4.2 (13-09-2017)

* Fix that running file as script would not work if the IPython flag was never turned on (#498).
* Fix delete action in filer browser (#505).
* Nicer appearance and coloring of source structure content (thanks to WangYi).
* more translations (e.g. for tool titles) (thanks to WangYi).


### Version 4.4.1 (14-07-2017)

Fixes:

* Fix that code editor fonts are oblique on some OS X machines.
* Restore broken introspection (for interactive help and calltips).
* Calltips now also work for builtins.
* Restore ability to run Python kernels as low as version 2.4.
* More updates to translations.

Small improvements:

* Added config option to change directory when executing file (not as script).
* Use `%run -i` to run script when ipython console is used (Diti24).
* Added another shell context menu entry to change directory.
* Added a config option to make the shell widget floatable.


### Version 4.4 (29-06-2017)

This release represents a large amount of new features and improvements:

Editor and shell:
    
* Tab titles also show part of the filename path if multiple files with the same name are present.
* The command history is now shared between all shells, and saved between sessions.
* Running selection will add to command history, also more options for command history tool.
* The Autocompletion accept keys can now be configured via the menu.
* The Autocompletion has more modes: automatic popup and popup only when pressing tab.
* Ctrl+up/down now "scrolls" the editor.
* Menu action (and shortcut Ctr+Shift+up/down) to move (selected) lines up/down (with help from Yehuda Davis).
* Menu action (and shortcut) to duplicate lines.
* Breakpoints can now be toggled with a menu action (and shortcut).
* Breakpoints now move along when lines are inserted above it.
* Fixed that Shift+Enter inserted a newline.
* Menu action in editor context menu and editor tab menu to open the directory in the file browser.
* Menu action in shell context menu to open current directory in file browser.
* Menu action in shell context menu to change the current directory to match the file browser.
* Fixes to shell help system (#422).
* Add new `install xx`, `update xx` and `remove xx` commands as shortcuts for conda commands.

Tools:

* Fix file browser's data import wizard.
* The file browser now logically sorts files and directories.
* The file browser can now show hidden files (can be turned off by filtering with `!hidden`).
* The `if __name__ == '__main__':` thingy is now shown in the source structure.
* The source structure tool has back/forward buttons (i.e. you can click on a method and then jump back).
* Methods and builtin functions are now also hidden in workspace when "hide function" filter is used.

Other:

* Added GUI integration support for PySide2 (by Rob Reilink).
* Improved support for high resolution (retina) displays (by Seb Jachec).
* Fixed the sometimes blurry icons.
* Fix PDF printing and include line numbers.
* Fix that keyboard shortcuts were not working on Linux with Qt5 (#470).
* More text is now translatable (and more translations have been made, though not yet in all languages).
* Fix that conda' errors messages were not shown.
* And many more small tweaks and fixes ...

### Version 4.3.1 (28-09-2016)

* Fix in workspace variable introspection
* Fix severe regression in PyQt4 GUI integration
* Add PyQt5 GUI integration

### Version 4.3 (27-09-2016)

* Pyzo can now run on PyQt5 (in addition to PyQt4 and PySide)
* Remove dependency on pyzolib
* Reduced scrolling while stepping through the debugger (#417)
* Updated translations
* Fixed regression in call tip (#421)
* The binaries for Linux have improved (fonts, load time, #423, #414)
* Numeric items in workspace are correctly sorted (#428)
* Improved Tornado integration
* And more ...


### Version 4.2 (27-06-2016)

No big refactoring, but a few improvements and fixes:

* Much improved brace matching (skips strings, shows missing/wrong) (thanks to Yann Salmon)
* Brace matching can be configured
* `conda install` looks in `conda-forge` by default
* Add `isatty()` to standard file streams to fix interop with pip (#400)
* Fixed a breakpoint bug
* Fixed TypeError on Fedora #393
* Added freedesktop file (thanks to Ghis Vaillant)
* Passed sys.argv to the QApplication, which helps Linux associate the program (thanks to Mark Harfouche)
* Tornado event loop is now integrated by running Tornado's event loop for real. The downside is that events cannot be processed during debugging, but at least there are no weird delays now (Tornado was not meant to run the way we ran it).
* Fix "open outside Pyzo" on Windows when a path has spaces in it.
* Workspace can hide private variables

### Version 4.1  (04-04-2016)

First announced release after merging the Pyzo and IEP projects.

* Improved dialog that detects an interpreter and guides the user.
* Detect interpreters relative to the Pyzo executable. This way Pyzo can be shipped along with a prebuild anaconda (#382).
* Fixed bug that made Pyzo slow on new Linux kernel (#381).
* New translations for Traditional Chinese.
* Ability to start Jupyter notebook from shell and from file browser tool.
* Clicking on a syntax error for code run as cell brings you to correct line.
* Breakpoints work in cells and code an as selected lines.
* Conda command no longer spams the shell with loads of messages.
* Shell can deal with clearline using `\r`, e.g. used in conda commands.

### Version 4.0

We smashed the Pyzo and IEP projects together into a single project:

* The name is Pyzo
* The logo is the one from IEP
* It is not longer a distribution, but a lightweight IDE (like IEP was) that helps the user install a (miniconda) environment.

Other improvements:
* Cells can be written as in Spyder: `# %% this is a cell`.
* Autodetection of a GUI toolkit.
* Minor tweaks here and there.



### Version 3.6 (18-02-2015)

(Simultaneously released version 3.6.1: a hotfix for OSX)

* Support for Jython! (issue #323)
* New tool: command history
* Smarter copying and pasting 
* Experimental support for integrating the Tornado event loop
* IEP is available in Debian! (issue #337) Thanks Ghis!
* issue #311: Zoom level of code text is inconsistent between architectures
* issue #314: Unable to launch after installing from source.
* issue #330: Comment line puts # on correctly indented position
* issue #172: Filter Workspace view
* issue #317: magic open command should go to appropriate line
* issue #315: sys.stdout has no attribute 'errors'
* issue #332: Cannot save file when File browser shows drives list on Windows
* issue #325: multiprocessing.pool doesn't work
* issue #322: Cannot run IEP form IEP
* issue #318: Line ending removed from last line upon save Editor 
* issue #306: Easier to modify syntax style Menu / settings 
* issue #305: cursor jumping to file beginning upon save

* pr #16: Fix the import wizard on PyQt4 (Scott Logan)
* pr #13: Allowing shell window to float is useful in dual screen mode (Laurent Signac)
* pr #14: Fix previous tab selection without history (Scott Logan)
* pr #11: cell navigation (Jan Müller)


### Version 3.5 (01-07-2014)

(This release ended up in Pyzo 2014a, but binaries for IEP itself were not build)

* issue 301: IEP can now be associated with .py files (on Windows and OSX)
* Running `iep_exe foo.py` will open the file in IEP (using already running process if possible) (see issue #301)
* issue #297: Enable keeping processing GUI events while debugging (via IEP_PROCESS_EVENTS_WHILE_DEBUGGING environment arg)
* issue #298: Add config option to remove trailing whitespace on save
* issue #295: Add goto definition (Thanks to Jason Sexauer)
* issue #292: Add config option to set text justification width
* issue #302: Fix in Spanish translation
* issue #300: Created AppData file for package managers
* issue #296: Easier use of timeit in non-IPython mode
* issue #294: On startup focus on editor
* issue #288: Installing IEP via pip now also installs script to launch IEP
* issue #290: allow executing startup code *after* importing the GUI
* issue #287: Starup script got cleared in shell config
* Added functionality for easily creating screenshots (`iep.screenshot()` in logger shell)
* The Windows installer does not need admin priveleges if installing in the right place.

### Version 3.4 (02-04-2014)

This version is marked by many improvements to the shell. Most notably, we now have *IPython integration*! Further, there are more ways to customize the shell (e.g. define command line and environment args), there is support for coloured text, you can click on filenames in tracebacks to open them, and it just behaves better overall. Also, many improvements have been made to our debug system.

Improvements/fixes related to the shell and kernel:

* issue #136: Embed IPython shell
* Shell can now deal with ANSI control chars to display color text
* issue #261: Allow custom code to execute on startup
* Code/script to run at startup runs before GUI is integrated (fixes issue #264)
* issue #268: Allow specifying extra environment arguments in shell config
* issue #239: Enable passing command line arguments (sys.argv)
* issue #262: Clicking in shell to focus to it causes scrolling to last line to stop
* issue #250: Prevent early exit for programs entering PySide event loop 
* issue #240: On Windows allow kernel to start also if 'cmd' is not recognized.
* issue #275: Paths in shell output (e.g. tracebacks) can be clicked on to open the file at the corresponding file number.
* issue #278: Fixed that on OSX Maverick, App Nap made the IEP kernel slow 

Other notable improvements:

* issue #249: Unclear where to place breakpoints
* issue #241: Debug-stepping in a new module change current file to there
* issue #266: Editor should auto-scroll to breakpoint when it becomes active
* issue #252: Fix that cursor is gone after dragging in a file (Linux)
* issue #267: Improved terminology for different RUN actions
* issue #285: Print/export code to pdf 
* Webbrowser tool used QWebkit if available (Thanks to David Salter)

Other fixes issues: #161, #188, #201, #209, #245, #255, #251, #265, #270, #271, #276, #242, #229, #260, #259, #227, #254, #253, #243, #244

During the beta period we also fixed: #286, #283, #277, #281


### Version 3.3.2 (12-11-2013)

  * Fixed issue #243: Running IEP from source did not work with PyQt4
  * Fixed issue #240: IEP now runs also if 'cmd' is unknown on Windows
  * Fixed problem with registering Pyzo on Windows
  * Fixed problem with IEP binaries (MSVCR runtime) on Windows 32.
  * Fixed problem with IEP binaries (qt.conf) on OS X.


### Version 3.3 (29-10-2013)

Since last release we have a new website, a new logo, and this release introduces our experimental libre license model. In terms of functionality, the biggest change is that IEP now supports debugging with breakpoints! 

The binaries for Linux are now build without -gtkstyle, making them look better or worse, depending on your OS. There is an experimental feature that tries to load PySide from the system libraries. The Python version on your system must be 3.3. E.g. on Ubuntu 13.10 you can do `sudo apt-get install python3-pyside`. To enable this feature, check the `qt.conf` file.

Further, there have been several bug fixes and improvements:

  * Several small improvements to file browser tool
  * New splash screen (with new logo)
  * Added `conda` command to shell
  * Added `pip` command to shell
  * Qt backend runs in the real Qt event loop, which allows Qt applications to be much more responsive.
  * Do not auto-indent in a comment (Gijs van Oort)
  * New translations for Russian (George Volkov)
  * IEP binaries should now not clash with system Qt libraries
  * Project manager tool is now removed.
  * "cd to project dir" option added to file browser (by Laurent Signac)
  * issue #1: debugging with breakpoints
  * issue #225: replace-all scrolls to start
  * issue #226: QTextBlockUserData object has no attribute 'indentation'
  * issues: #182, #197,  #207, #192, #194, #160, #110, #205, #211, #215


### version 3.2 (13-03-2013)

This is the first release for which all binaries are build with Python 3.3 and PySide.

The most notable change is the new file browser, which replaces the old file browser and project manager tools. It combines the power of both in one simple interface. It also has functionality for peeking inside python modules. Since its design uses a generalization of the file system, implementing alternative file systems (like zip files or remote machines) should be quite easy in the future.

IEP now also comes with two fonts: 'DejaVu Sans Mono' (the default font) and Adobes new 'Source code pro'.

IEP now supports multiple languages. Translations for Dutch, French, Spanish and Catalan are available. Hoping for more in future versions.

List of issues that are fixed in this release:

  * issue #82: most texts are now translatable
  * issue #86: redesign of file browser tool
  * issue #149 and issue #150: better context menu in the editor
  * issue #156: Popup window for autocompletion can now be resized (via the config)
  * issue #157: Ctrl+Shift+Enter execute cell and go to next cell (as in Matlab)
  * issue #159: Exit code of Python process was incorrect
  * issue #163, issue #164, issue #165: Fixed problems running on Python 3.3 and Pyside. 
  * issue #166: smart handling of indentation when deleting text.
  * issue #178: The font can now be chosen in the menu, and IEP ships with a good default font.
  * Further: issue #14, issue #138, issue #139, issue #144, issue #147, issue #158, issue #186

Other changes:

  * Tools can now be packages, allowing their code to be better structured.
  * Fault handler module is used on Python 3.3 to debug hard crashes.
  * When IEP closes, it takes better care of stopping daemon threads.
  * Some cosmetic enhancements of the tools.
  * The keys to accept autocompletion can now be configured (e.g. use Enter instead of Tab), see issue #134. 

During the beta period, a few more issues were fixed:

  * issue #189 (cannot mix incompatible Qt libraries)
  * and issue #186, issue #189, issue #200


### version 3.1.1 (21-12-2012)

Fix for issue #137: crucial issue on Ubuntu 12.10.


### version 3.1 (19-12-2012)

Most notable changes:

  * IEP is now a package, making it to easier to integrate in other software.
  * IEP will be the IDE for [Pyzo](http://www.pyzo.org), and now has some functionality to integrate nicely with the Pyzo distro.
  * Multiple lines can now be pasted and executed in the shell (issue #120).
  * Run selection (F9) runs the selected statement if on a single line (issue #42).
  * IEP is now build with PySide (issue #85).
  * Goto-line functionality (double-click on the line number area) (issue #76)
  * Comments and docstrings can now easily be reshaped (CTR+J) (issue #105)
  * The shell widget now uses a powerful menu instead of tabs.
  * IEP now has a Wizard to help new users on their way.
  * Cells are separated more clearly.

Complete list of fixed issues: issue #42, issue #76, issue #85, issue #90, issue #95, issue #99, issue #101, issue #105, issue #106, issue #107, issue #111, issue #112, issue #113, issue #115, issue #116, issue #120, issue #122, issue #123, issue #124, issue #128, issue #129, issue #130, issue #132, issue #133.


### version 3.0 (14-05-2012)

We fixed the issues that we collected for 3.0.beta:

  * We fixed issue #89, issue #91, issue #93, issue #94, issue #95, issue #96, issue #98, issue #100. (See [overview](http://code.google.com/p/iep/issues/list?can=1&q=Milestone%3DRelease3.0|overview))
  * The syntax style now uses a pure-white background; the solarized version becomes pinkish on some systems.
  * The shortcuts are reset. For 3.0.beta we carefully selected the key bindings so that they feel native for Windows, Linux and Mac. By resetting shortcuts, users that already used IEP 2.3 get the new bindings as well.


### version 3.0.beta (18-04-2012)

About 14 months after releasing 2.3, we finally got version 3.0 out. The main reason for this delay that we re-implemented some core components, which took a lot of time to get right. Funny fact: the amount of changesets in the repository has more than doubled since the last release.

The core things that were changed:

  * We have rewritten the code that does the communication between the kernel and the IEP. This code is organized separately in a package we've called [Yoton(http://code.google.com/p/yoton/). We've designed it in such a way that it will allow us to run a kernel on a different machine (remote computing) and to connect multiple users to the same kernel (collaborative computing). You might expect these features in one of the coming releases. Further, it paves the way for parallel computing (but that's for the further future). 
  * Another big change is the editing component. We've gotten rid of Scintilla (which is an old library with an inconsistent API, with bad support for Unicode, and was very buggy on Mac). We have designed our own editing component using pure Qt components. We've designed that part too to be independent of IEP, so it might be reused in other projects. 
  * The code for the menu has been completely redone, allowing for easier incorporation of icons, and using (contex) menus in other places.
  * The editorstack has been gotten rid of. In its place is the project manager and a more classic tab bar, custom-made to make the tabs more compact and provide information about the open documents in a subtle and non-intrusive manner.


There've been tons of other things we've improved and fixed along the way. Because we changed so much to the code, it's hard to list (and remember) all of them.

Because we designed a new editing component, some features are now also removed, e.g. brace matching. We plan on implementing most of these features in the coming releases.


### version 2.3 (23-11-2010)

For this release we implemented many improvements and bug-fixes. Further, we implemented a few new tools and made IEP work for the Mac.

  * From this release, IEP uses the BSD license.
  * Binaries are now also available for 64bit Linux and Mac.
  * Improved the interactive help; it looks better and can show numpy docstrings well.
  * Source structure tool can now also show class attributes (in addition to methods).
  * New Workspace tool.
  * New File browser tool which has the ability to search inside files.
  * New webbrowser tool (very simple though, I did not want to use the QT webkit to keep the binaries small).
  * IEP uses the guisupport.py module to integrate the event loops for GUI toolkits.
  * The GTK event loop can now also be integrated.
  * Many bug/issue fixes:

    * Fixed bug in shell config dialog when there is no Python installed on Windows.
    * Fixed bug: sys.argv = [''] in inreractive mode (and not []).
    * Prevent restoring window position if it's not on screen.
    * Many more that I failed to document properly :)
    * Files with Windows line ending are now correctly executed when running as script.
    * Fixed issue #9 that IEP sometimes hangs when doing 'open xxx'.
    * Better signatures for extension code.
    * newlines are now correctly displayed when showing whitespace.
    * Can now also interrupt files run as script.

  * Loads of other small improvements ...


### version 2.2 (24-08-2010)

A few beta tester played around with the first version and gave me list of things to improve. Special thanks to Stef for his suggestions.

  
  * Better distinction between running code interactively or as a script. Also significantly improved the shell configuration dialog.
  * Append '' to sys.path in interactive mode. In Script mode, add the directory of the script.
  * Allow enter and other chars to complete the autocompletion.
  * Better detection of classes and defs in the code parser (also for cython code).
  * Let user change the PythonPath in shell configs.  
  * Shell always fits 80 colums set to default False.
  * Shells can also be set not to wrap to 80 columns.
  * The code parser handles multiline strings in the code also if they dedent.
  * Fixed autocompletion lag.
  * In keymapping dialog let dubbleclick on name open up shortcut 1.
  * Remove statusbar (for now) as it does contain no extra information.
  * If no project selected, give message when trying to run code in the project.
  * Made a small tutorial file that is loaded on first startup.
  * When showing line endings, show \r and \r\n correctly.
  * Source structure can also show class attributes.
  * Fixed autocompletion list update bug.
  * Handle Unicode correctly when typing in the shell.
  * Fonts and style now work/look better on KDE and older Linuxes.
  * Fixed some issues with check-for-updates.
  * EditorStack can be scrolled with the scroll wheel.
  * IEP can now also integrate the GTK event loop.
  * Many other changes and fixes ...

### version 2.1 (21-07-2010)

The first official version of Iep.


### version 2.0.1

I intended to release alpha release while I was developing Iep, but only released the one right after I finished the editor stack.

### version 1.0

A bit of history ...

When I started working with Python, I used IPython and Pype, which I both really liked, but I felt that the two should be combined in one application. Since I could not find a free IDE that did this (Spyder did not exist yet) I set out to make my own. 

I wrote a first version of IEP in Python 2.5 using the wx GUI toolkit. When I thought it was at a stage that it was suitable for a public release, I tested in on Linux, and it looked like `cr*p`. I could (and should) have expected this, because I used some widgets on a rather low-level, and some widgets behave rather differently on different OS's (since wx wraps the native widgets to the os).

This made me look for other GUI toolkits. I took a (brief) look at fltk, but ended up with Qt4, right around the time that it went LGPL. Although a bit big memory-wise, the consistent library and powerful widgets of PyQt4 gave me hope that I was on the right track.

I started from scratch, reusing as much code as I could, but also redesigning large parts to fix all the little things I was not quite happy about. Since I was designing the same application for the second time, I had a pretty good idea what I wanted and how it should be done. Nevertheless, it took me another year or so to get it to a level I found suitable for release: version 2.1.