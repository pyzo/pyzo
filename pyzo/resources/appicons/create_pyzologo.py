import inspect
import os

__this_dir__ = os.path.abspath(os.path.dirname(inspect.getfile(inspect.currentframe())))
os.chdir(__this_dir__)

##

WIDTH = HEIGHT = 256

svg_contents = []
svg_contents.append('<?xml version="1.0" encoding="UTF-8" standalone="no"?>')
svg_contents.append(f'<svg width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">')
svg_contents.append(f'<!-- created via a Python script - do not edit this SVG file directly -->')

# add filled background, only for debugging
# svg_contents.append(f'<rect fill="#777" stroke="#000" x="0" y="0" width="{WIDTH}" height="{HEIGHT}"/>')

# https://developer.mozilla.org/en-US/docs/Web/SVG/Tutorials/SVG_from_scratch/Paths


def make_path_rounded_rect(x_left, y_top, w, h, r):
    return ' '.join([
        f'M {x_left + r} {y_top}',  # move to x y
        f'L {x_left + w - r} {y_top}',  # draw line to x y
        f'A {r} {r} 0 0 1 {x_left + w} {y_top + r}',
        f'L {x_left + w} {y_top + h - r}',  # draw line to x y
        f'A {r} {r} 0 0 1 {x_left + w - r} {y_top + h}',
        f'L {x_left + r} {y_top + h}',  # draw line to x y
        f'A {r} {r} 0 0 1 {x_left} {y_top + h - r}',
        f'L {x_left} {y_top + r}',  # draw line to x y
        f'A {r} {r} 0 0 1 {x_left + r} {y_top}',
        'z',  # close path
    ])

def make_path_gtsign(x_inner, y_inner, thickness, r_outer, length_inner):
    r = r_outer
    r2 = 0.5 * thickness
    k = 1 / 2**0.5
    x1 = x_inner - k * length_inner
    y1 = y_inner - k * length_inner
    x2 = x1 + k * 2 * r2
    y2 = y1 - k * 2 * r2
    x3 = x_inner + thickness / k - k * r
    y3 = y_inner - k * r

    return ' '.join([
        f'M {x_inner} {y_inner}',  # move to x y
        f'L {x1} {y1}',  # draw line to x y
        f'A {r2} {r2} 0 0 1 {x2} {y2}',
        f'L {x3} {y3}',  # draw line to x y
        f'A {r} {r} 0 0 1 {x3} {y_inner + (y_inner - y3)}',
        f'L {x2} {y_inner + (y_inner - y2)}',  # draw line to x y
        f'A {r2} {r2} 0 0 1 {x1} {y_inner + (y_inner - y1)}',
        f'L {x_inner} {y_inner}',  # draw line to x y
        'z',  # close path
    ])

def make_path_textline(x, y, thickness, length):
    r = 0.5 * thickness
    return ' '.join([
        f'M {x + r} {y - r}',  # move to x y
        f'L {x + length - r} {y - r}',  # draw line to x y
        f'A {r} {r} 0 0 1 {x + length - r} {y + r}',
        f'L {x + r} {y + r}',  # draw line to x y
        f'A {r} {r} 0 0 1 {x + r} {y - r}',
        'z',  # close path
    ])


for shadow in [True, False]:
    sx = sy = 0
    sc = ''
    if shadow:
        sx = sy = 4
        sc = '#' + 'b0' * 3  # fixed color shadow, without transparency

    svg_contents.append('<path d="{}" fill="{}" />'.format(make_path_rounded_rect(12 + sx, 45 + sy, 104, 168, 8), sc or '#268bd2'))
    svg_contents.append('<path d="{}" fill="{}" />'.format(make_path_rounded_rect(124 + sx, 45 + sy, 120, 88, 8), sc or '#dc322f'))
    svg_contents.append('<path d="{}" fill="{}" />'.format(make_path_rounded_rect(124 + sx, 141 + sy, 56, 72, 8), sc or '#859900'))
    svg_contents.append('<path d="{}" fill="{}" />'.format(make_path_rounded_rect(188 + sx, 141 + sy, 56, 72, 8), sc or '#859900'))

for i in range(3):
    svg_contents.append('<path d="{}" fill="#a52523" />'.format(make_path_gtsign(154 + i * 32, 80, 8, 3, 19)))

for i in range(4):
    svg_contents.append('<path d="{}" fill="#1c689d" />'.format(make_path_textline(27, 80 + i * 32, 8, 73 if i != 3 else 57)))

svg_contents.append('</svg>')


with open('pyzologo256.svg', 'wt') as fd:
    fd.write('\n'.join(svg_contents))


