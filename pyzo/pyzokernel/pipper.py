import re
import sys
import time
import subprocess


r"""
Some explanations regarding the progress bars
=============================================

When executing "pip install ..." or "pip download ..." pip will display a progress bar
for the download progress in the terminal.

For older pip versions it was enough to just fordward the stdout of pip to the Pyzo shell
to have a continuosly updating progress bar.
But this stopped working with newer pip versions -- the progressbar was only displayed
once when the whole download was already completed.


With the curernt pip release v25.2 we have three ways to display the progress bar:
1) use no workarounds, as in Pyzo <= v4.20:
    The progressbar will only be displayed when finished.
    --> bad user experience, because pip seems to be stuck for larger downloads
2) use advanced terminal escape sequences
    We can do this by setting some environment variables when calling pip via subprocess:
        TERM="" (instead of "dumb")
        TTY_COMPATIBLE=1
    We would also have to implement or cleverly replace escape sequences such as:
        b'\x1b[?25l'
        b'\x1b[2K'
        b'\x1b[?25h'
    This would require some bigger workarounds, and future pip releases could make use of
    different escape sequences.
    --> not a stable interface
3) use raw progress bars, which were introduced in pip v24.1 (2024-06-20)
    see https://github.com/pypa/pip/issues/11508
    To use these, we need to pass "--progress-bar=raw" to pip, if pip is new enough.
    Instead of the rendered progress bar, pip will write simple lines such as
        b'Progress 19398656 of 73160002\n'
    for each update.
    In Pyzo, we parse these lines and render our own progress bar.

--> we use 3)


more information about pip:
    https://github.com/pypa/pip
    https://pip.pypa.io/en/stable/news/
"""


def datasize_to_string(size_bytes):
    size_bytes = float(size_bytes)  # only needed for Python 2.7
    prefixes = ["", "k", "M", "G", "T"]
    k = 1000
    precision = 0 if size_bytes < k else 1
    for i, prefix in enumerate(prefixes):
        v = size_bytes / k**i
        if v < k:
            break
    return "{:.{}f} {}B".format(v, precision, prefix)


def build_progress_line(current, total, fill_char):
    bar_length = 40
    if total > 0 and current >= 0:
        percent = 100 * min(1, max(0, current / total))
    else:
        percent = 0
    filled_length = round(percent / 100 * bar_length)
    bar = fill_char * filled_length + " " * (bar_length - filled_length)
    line = "[{}] {:3d} %   {} of {}".format(
        bar, round(percent), datasize_to_string(current), datasize_to_string(total)
    )
    return line


def subprocess_with_callback(callback, cmd, use_raw_progress_bar, **kwargs):
    """Execute command in subprocess, stdout is passed to the
    callback function. Returns the returncode of the process.
    If callback is None, simply prints any stdout.
    """

    # Set callback to void if None
    if callback is None:
        callback = lambda x: None

    # Execute command
    try:
        p = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **kwargs
        )
    except OSError:
        type, err, tb = sys.exc_info()
        del tb
        callback(str(err) + "\n")
        return -1

    progress_bar_dash = b"\xe2\x94\x81"  # U+2501, a thick horizontal line character
    pending = b""
    last_line_was_raw_progress_bar = False
    while p.poll() is None:
        time.sleep(0.001)
        # Read text and process
        c = p.stdout.read(1)
        pending += c

        if use_raw_progress_bar:
            if c == b"\n":
                # instead of
                # mo = re.fullmatch(rb"Progress (\d+) of (\d+)\r?\n", pending)
                # we use
                mo = re.match(b"^Progress (\\d+) of (\\d+)\\r?\\n$", pending)
                # because of Python 2.7

                if mo:
                    current = int(mo[1])
                    total = int(mo[2])
                    pending = build_progress_line(
                        current, total, progress_bar_dash.decode("utf-8")
                    ).encode("utf-8")
                    if last_line_was_raw_progress_bar:
                        pending = b"\r" + pending
                    last_line_was_raw_progress_bar = True
                else:
                    if last_line_was_raw_progress_bar:
                        pending = b"\n" + pending
                    last_line_was_raw_progress_bar = False

                callback(pending.decode("utf-8", "ignore"))
                pending = b""
        else:
            if c in b"-.\n" or pending.endswith(progress_bar_dash):
                callback(pending.decode("utf-8", "ignore"))
                pending = b""

    # Process remaining text
    pending += p.stdout.read()
    if last_line_was_raw_progress_bar:
        pending = b"\n" + pending

    callback(pending.decode("utf-8", "ignore"))
    p.stdout.close()  # avoid ResourceWarning: unclosed file <_io.BufferedReader>

    # Done
    return p.returncode


def print_(p):
    sys.stdout.write(p)
    sys.stdout.flush()


def pip_command(*args):
    """Do a pip command, e.g. "install networkx".
    Installs in the current interpreter.
    """
    args = list(args)
    use_raw_progress_bar = True
    if len(args) > 0 and args[0] in ["install", "download"]:
        if get_pip_version() >= (24, 1):
            args.insert(1, "--progress-bar=raw")
        else:
            use_raw_progress_bar = False

    # By using use_raw_progress_bar=True as a default,
    # writing to the Pyzo shell will only be performed on '\n'.
    # --> better performance for "pip list" etc.

    cmd = [sys.executable, "-m", "pip"] + args
    subprocess_with_callback(print_, cmd, use_raw_progress_bar)


def get_pip_version():
    """Returns a tuple of mayor and minor version of the pip module."""
    version = (0, 0)  # fallback value
    cmd = [sys.executable, "-m", "pip", "--version"]
    try:
        returned_bytes = subprocess.check_output(cmd)  # e.g. b'pip 25.2 from ...'
        version_string = returned_bytes.split(None, 2)[1].decode("ascii")
        version = tuple(int(s) for s in version_string.split(".")[:2])
    except Exception:
        pass
    return version


if __name__ == "__main__":
    pip_command("install", "networkx")
