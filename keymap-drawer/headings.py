"""Center each layer title over its keyboard in keymap-drawer SVGs (in place).

keymap-drawer left-aligns titles at the layer's origin; this moves them to
the middle of the drawing (text-anchor is set in config.yaml).
Usage: headings.py file.svg [...]
"""

import re
import sys

WIDTH = re.compile(r'<svg width="([\d.]+)"')
LAYER_LABEL = re.compile(
    r'(<g transform="translate\(([\d.]+), [\d.]+\)" class="layer-[^"]*">\s*<text )x="[-\d.]+"')

for path in sys.argv[1:]:
    with open(path) as f:
        svg = f.read()
    width = float(WIDTH.search(svg)[1])
    svg = LAYER_LABEL.sub(lambda m: f'{m[1]}x="{width / 2 - float(m[2]):.0f}"', svg)
    with open(path, "w") as f:
        f.write(svg)
