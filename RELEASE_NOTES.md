### Version 3.3 (about to release)

Since last release we have a new website, a new logo, and this release introduces our experimental libre license model. In terms of functionality, the biggest change is that IEP now supports debugging with breakpoints! 

The binaries for Linux are now build without -gtkstyle, making them look better or worse, depending on your OS. There is an experimental feature that tries to load use PySide from the system libraries. The Python verson on your system must be 3.3. E.g. on Ubunty 13.10 you can do `sudo apt-get install python3-pyside`. To enable this feature, remove/rename the `qt.conf` file.

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