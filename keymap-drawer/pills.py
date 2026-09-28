"""Put a rounded pill behind each layer title in keymap-drawer SVGs (in place).

SVG text has no CSS background, so this inserts a <rect class="label-bg">
sized from the title length; its color comes from the layer's --layer
variable in config.yaml.
Usage: pills.py file.svg [...]
"""

import re
import sys

CHAR_W = 12.5  # uppercase, 17px, bold, 1px letter spacing
PAD_X = 12
HEIGHT = 28

LABEL = re.compile(r'<text x="([-\d.]+)" y="([-\d.]+)" class="label" id="([^"]*)">([^<]*)</text>')


def pill(match):
    x, y, name, text = float(match[1]), float(match[2]), match[3], match[4]
    width = len(text) * CHAR_W + 2 * PAD_X
    rect = (f'<rect class="label-bg" x="{x}" y="{y - HEIGHT / 2}" width="{width:.0f}" '
            f'height="{HEIGHT}" rx="{HEIGHT / 2}"/>')
    label = f'<text x="{x + PAD_X}" y="{y}" class="label" id="{name}">{text}</text>'
    return rect + label


for path in sys.argv[1:]:
    with open(path) as f:
        svg = f.read()
    with open(path, "w") as f:
        f.write(LABEL.sub(pill, svg))
