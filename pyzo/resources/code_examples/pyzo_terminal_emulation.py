## newline

print('nothing\nspecial\nhere')


## horizontal tab

print('abc\tdef\tghi')
print('1\t2.0\t3.33')


## vertical tab

print('abc\vdefg\vhi')


## backspace

print('1 + 1 = 35', end='')  # stay in this line
print('\b\b2')  # we still can delete characters of the current line and add new ones

## backspace (continued)

# we cannot go further back than the start of the line
print('first line')
print('\b' * 100, end='')  # we cannot delete characters from the line before
print('second line')

## backspace (continued)
import sys

print('1 + 1 = 35', end='')  # stay in this line
print('[unexpected interruption]', end='', file=sys.stderr)
print('\b\b2')  # we cannot delete from a different output stream

## backspace (continued)
import time

# remove characters one by one from the current line
print('first line')
print('12345', end='')
for i in range(10):
    time.sleep(0.3)
    print('\b', end='')
print('finished')


## carriage return

# a '\r' followed by a '\n' is interpreted as a single line break ('\n')
print('first line\r\nsecond line')

# any other character after '\r' means that the current line should be cleared
print('something we want to remove\rcorrected text')

## carriage return (continued)
import time

# the previous examples also work if the text is split into fragments:
print('first line\r', end='')  # the line is already visible here
time.sleep(1.0)
print('\nsecond line')  # now Pyzo knows it was a '\r\n' --> normal line break
time.sleep(1.0)
print('third line\r', end='')  # the line is still visible here
time.sleep(1.0)
print('still third line')  # now Pyzo knows it was a just a'\r' --> remove current (third) line


## format sequence

print('HELLOU\x1b[1;31m\bABCD\x1b[0m')
# note that the '\b' removes the 'U' without damaging the format sequence between

## format sequence (continued)
import time

# If the format sequence is not written in one go, the incomplete sequence will be
# written at first, but then deleted again when the second fragment is processed.
print('abcd' '\x1b[0;1', end='')
time.sleep(1.0)
print(';4;31m' 'hello' '\x1b[39m' 'world' '\x1b[0m' 'efgh')

## format sequence (continued)
import sys

# An interruption by another stream keeps the incomplete format from the first fragment
# but the format is processed correctly anyways:
print('abcd' '\x1b[0;1', end='')
print('HI FROM STDERR', file=sys.stderr)
print(';4;31m' 'hello' '\x1b[39m' 'world' '\x1b[0m' 'efgh')


## formats are stream-specific
import sys

print('normal text to stdout')
print('THIS IS STDERR, in red, and\x1b[0;1;36m now in bold cyan', file=sys.stderr)
print('another text to stdout', file=sys.stdout)
print('STDERR HAS KEPT THE FORMAT (still bold cyan)', file=sys.stderr)
print('normal stdout stream is not affected ...')
print('resetting STDERR FORMAT:\x1b[0m DONE', file=sys.stderr)

## formats are stream-specific (continued)
import sys, time, subprocess

# Note that raw streams of other processes, e.g. via subprocess.run(...) share the same
# format for stdout and stderr in the Pyzo shell.

def srun(cmd):
    subprocess.run([sys.executable, '-c', cmd])

print('starting ...')
time.sleep(0.5)
srun("import sys; print('this is stdout via raw stream')")
srun("import sys; print('this is stderr via raw stream', file=sys.stderr)")
srun("import sys; print('changing \x1b[1;32mcolor in stdout raw stream')")
srun("import sys; print('again stdout via raw stream')")
srun("import sys; print('again stderr via raw stream', file=sys.stderr)")
srun("import sys; print('resetting \x1b[0mcolor in stderr raw stream', file=sys.stderr)")
srun("import sys; print('finally stdout via raw stream')")
srun("import sys; print('finally stderr via raw stream', file=sys.stderr)")


## supported text format escape sequences
# this is a subset of https://en.wikipedia.org/wiki/ANSI_escape_code#3-bit_and_4-bit

class Fmt:
    reset = 0
    bold = 1
    light = 2
    italic = 3
    underline = 4
    no_bold_light = 22
    no_italic = 23
    no_underline = 24
    black = 30
    red = 31
    green = 32
    yellow = 33
    blue = 34
    magenta = 35
    cyan = 36
    white = 37

def build_fmt(*fmt_values):
    return '\x1b[' + ';'.join([str(v) for v in fmt_values]) + 'm'

for k, v in Fmt.__dict__.items():
    if not k.startswith('_'):
        print('\x1b[{}m{}\x1b[0m'.format(v, k))

print()

normal = build_fmt(Fmt.reset)
underline = build_fmt(Fmt.underline)
bold_red = build_fmt(Fmt.bold, Fmt.red)
blue_italic = build_fmt(Fmt.blue, Fmt.italic)
yellow = build_fmt(Fmt.yellow)

print(f'Hello {underline}world {bold_red}via {blue_italic}Py{yellow}thon{normal}!')


## resetting only the text color via escape code 39

print(
    '\x1b[3m'
    'italic'  # --> default color, italic
    '  '
    '\x1b[31m'
    'italic red'  # --> as before, but with red text
    '  '
    '\x1b[39m'  # --> reset text color, but keep italic
    'normal color'
    '  '
    '\x1b[0m'  # --> reset whole format (use color, and remove italic)
    'normal'
)


## progress bar example

import time

for i, p in enumerate(range(0, 100+1, 2)):
    bar = '=' * (i + 1) + ' ' * (50 - i)
    colored_bar = '\x1b[{}m'.format(32 if p == 100 else 31) + bar + '\x1b[0m'
    c = '-\\|/'[i % 4]
    if p == 100:
        c = 'finished'
    print('\rprogress: [' + colored_bar + ']', p, '%  ', c, end='')
    time.sleep(0.1)
print()


## progress bar using package tqdm

import time, tqdm

for i in tqdm.tqdm(range(10)):
    time.sleep(0.5)


## automatic line splitting

# To improve performance with text wrapping in the shell, very long lines are split
# into lines of 80 characters.

print('A' * 1050, end='')  # lines longer than 1024 chars are split
print('B' * 500)  # still split, because this is in the same line as the 'A's
print('c' * 500)  # still split, because we had long lines before
print('d' * 50)  # line shorter than 81 chars (and a '\n') stops splitting long lines
print('e' * 500)  # not split, because shorter than 1024 chars
