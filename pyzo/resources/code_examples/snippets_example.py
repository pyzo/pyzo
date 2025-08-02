# This is an example file for the "Snippets" tool.
# If there is no "snippets" folder in the Pyzo userdata directory, Pyzo will automatically
# create that folder and copy this file there, just as an example to get started.
# To obtain the Pyzo userdata directory, see the "About Pyzo" dialog ("Help -> About Pyzo"
# in the menu).

# You can put multiple *.py files into the snippets directory.
# It is even possible to create namespace groups by placing files into nested subfolders.
# Snippet files must have UTF-8 encoding (or ASCII, which is a subset of UTF-8).
# Snippet and subfolder names must be valid ASCII identifiers: "[a-zA-Z_][a-zA-Z_0-9]*"
# Snippet names of all snippets in the same directory (without subfolders) must be unique.

# Every snippet starts with a cell comment line, such as "## SNIP: name_of_the_snippet".
# All comment lines directly below the cell comment line are an optional description
# of the snippet. This description will be shown in the tooltip text in the Snippets tool
# as well as in the "Interactive help" tool, but it will not be inserted with the code.

# On insertion, the snippet code will be inserted at the current location of the text
# cursor in the active editor tab. If there is only whitespace before the cursor position,
# the snippet code lines will be prefixed by the same whitespace characters to have the
# same indentation.

# Empty lines before and after the snippet will be removed when reading the file.
# Snippets with only one code line will be inserted without a linebreak at the end.


## SNIP: readme
# This is an example snippet.
# In the Pyzo "Snippets" tool, right click on the list entry and select "Edit" to open
# this file.
# All comment lines below the snippet header are part of the description.
# The description stops on the first non-comment line, such as the following empty line.

# This line is already part of the snippet code.

import antigravity


## SNIP: changepath
import inspect
import os

__this_dir__ = os.path.abspath(os.path.dirname(inspect.getfile(inspect.currentframe())))
os.chdir(__this_dir__)


## SNIP: changepath_and_modulespath
# change path to path of current script
# this also works when executing code as cell (contrary to __file__)

import inspect
import os
import sys

__this_dir__ = os.path.abspath(os.path.dirname(inspect.getfile(inspect.currentframe())))
os.chdir(__this_dir__)

__my_modules_path__ = os.path.join(__this_dir__, r'my_modules')
if __my_modules_path__ not in sys.path:
    sys.path.append(__my_modules_path__)


## SNIP: plot_with_imports
import numpy as np
import matplotlib.pyplot as plt
plt.ion()

fig, ax = plt.subplots(num=10, clear=True)
ax.plot([1, 2, 4], '-x')
ax.grid(True)


## SNIP: lowpass
# digital lowpass filter, bessel, 2nd order
# with cutoff frequency fc and sample frequency fs

import scipy.signal

filter_b_a = scipy.signal.bessel(2, fc/(fs/2), 'lowpass')
sig_f = scipy.signal.lfilter(*filter_b_a, sig)

