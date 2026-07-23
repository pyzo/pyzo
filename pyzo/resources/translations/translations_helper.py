"""
Helper script for adding/updating translations to Pyzo
======================================================

For general information, read the TRANSLATIONS.md file first. It is located
in the root directory of the Pyzo repository.

There are three steps involved in updating/creating translations:
1) create or update the .ts files from Pyzo's Python source code
2) run the "Qt Linguist" tool and edit the .ts file
3) compile the .ts files to .qm files

When adding a new language, then the file "pyzo/util/_locale.py" should be updated as well:
Add the language to the LANGUAGES dict, and optionally a synonym to LANGUAGE_SYNONYMS.

Run the following code cells in Pyzo to execute the steps listed above.
"""


## general code that is needed for all steps

import os
import re
import sys
import inspect
import subprocess

import PySide6  # make sure we have PySide6 installed (for pyside6-linguist etc.)


# We do not use __file__ so that we can run this script in Pyzo via Ctrl+E.
this_script_dir = os.path.realpath(os.path.dirname(inspect.getfile(inspect.currentframe())))
translations_dir = this_script_dir


def is_lang_code(s):
    """returns True if s is a valid language string pattern

    valid patterns are for example: "pl_PL", "fi", "pt_BR"
    """
    return bool(re.fullmatch(r"[a-z]{2}(?:_[A-Z]{2,3})?", s))

def list_language_ts_files():
    """returns a list of ts files in the pyzo translations directory

    e.g.: ['pyzo_pl_PL.ts', 'pyzo_fi.ts', 'pyzo_pt_BR.ts']
    """
    return [
        fn for fn in os.listdir(translations_dir)
        if re.fullmatch(r'pyzo_[a-z]{2}(?:_[A-Z]{2,3})?\.ts', fn)
    ]

def get_pyzo_source_dir():
    pyzo_source_dir = translations_dir
    folders = []
    for _ in range(3):
        pyzo_source_dir, fn = os.path.split(pyzo_source_dir)
        folders.insert(0, fn)

    if (
        folders != ['pyzo', 'resources', 'translations']
        or not os.path.isfile(os.path.join(pyzo_source_dir, 'pyzolauncher.py'))
    ):
        raise ValueError('This script has to be executed in the original location of the Pyzo repository!')

    return pyzo_source_dir

def get_py_source_paths_for_translations():
    sourcePaths = []
    pyzo_source_dir = get_pyzo_source_dir()
    basepath = os.path.join(pyzo_source_dir, 'pyzo')
    for dirpath, dirnames, filenames in os.walk(basepath):
        dirnames[:] = [dn for dn in dirnames if not dn.startswith(('.', '__'))]
        rp = os.path.relpath(dirpath, start=basepath)

        # exclude some directories (paths relative to the "pyzo" dir)
        if rp in ['build', 'pyzokernel', 'resources', 'yoton']:
            dirnames.clear()
            continue

        sourcePaths.append(os.path.realpath(dirpath))
    return sourcePaths

def run_tool(tool_name, args):
    if tool_name not in ['linguist', 'lupdate', 'lrelease']:
        raise ValueError('unsupported tool name')

    python_bin_dir = os.path.abspath(os.path.dirname(sys.executable))
    tool_filepath = os.path.join(python_bin_dir, 'pyside6-' + tool_name)
    if sys.platform == 'win32':
        tool_filepath += '.exe'

    cmd = [tool_filepath] + args
    p = subprocess.run(
        cmd, cwd=translations_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    output = p.stdout.decode('utf-8')
    if p.returncode:
        raise RuntimeError('{} failed ({}): {}'.format(tool_name, p.returncode, output))
    else:
        print(output)


get_pyzo_source_dir()  # calling this to check if this script is executed in the correct place


## Step 1:
if False:
## create or update the .ts files from Pyzo's Python source code

    # TODO: specify the lang_code
    """
    If lang_code is None, all available .ts files will be converted.
    If a lang_code is specified, e.g. "fi" or "pt_BR", then only the specific file
    will be updated resp. created if the file does not exist yet.
    """
    lang_code = None  # ... update all existing .ts files
    # lang_code = 'pt_BR'  # (only) update the existing .ts file for Portuguese (BR)
    # lang_code = 'fi'  # create a new .ts file for Finnish


    if lang_code is None:
        filenames = list_language_ts_files()
    elif is_lang_code(lang_code):
        filenames = ['pyzo_{}.ts'.format(lang_code)]
    else:
        raise ValueError('invalid lang_code: ' + repr(lang_code))

    srcPathsTempFile = os.path.join(translations_dir, '.temporary_source_directories_list.txt')
    with open(srcPathsTempFile, 'wt') as fd:
        fd.write('\n'.join(get_py_source_paths_for_translations()))

    try:
        # We could also write all .ts filepaths in a .txt file and pass it to lupdate,
        # but we do it file by file in a loop instead.
        for fname in filenames:
            args = [
                '-no-obsolete',  # remove translations that are not used anymore
                '-no-recursive',  # only search code files in the directories we specify in srcPathsTempFile
                '-extensions', 'py',
                '@' + srcPathsTempFile,
                '-ts', fname,
            ]
            run_tool('lupdate', args)
    finally:
        os.remove(srcPathsTempFile)


## Step 2:
if False:
## run the "Qt Linguist" tool and edit the .ts file

    # TODO: specify the lang_code
    """
    Specify lang_code for an existing translation file,
    e.g. 'es_ES' or 'it_IT'
    """
    # lang_code = 'es_ES'
    # lang_code = 'fi'
    lang_code = 'de_DE'


    if not is_lang_code(lang_code):
        raise ValueError('invalid lang_code: "{}"'.format(lang_code))

    ts_filepath = os.path.join(translations_dir, 'pyzo_{}.ts'.format(lang_code))

    if not os.path.isfile(ts_filepath):
        raise ValueError('Could not find translation file "{}"'.format(ts_filepath))

    args = [ts_filepath]
    run_tool('linguist', args)


## Step 3:
if False:
## compile the .ts files to .qm files
    args = ['-fail-on-invalid'] + list_language_ts_files()
    run_tool('lrelease', args)

