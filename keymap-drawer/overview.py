"""Fold the parsed layers into one Miryoku-style overview layer.

Layers held by a left thumb key only use the right hand, and vice versa, so
each key shows its Base legend plus the opposite-thumb layers in its corners.
Usage: overview.py adv360pro.yaml > adv360pro-overview.yaml
"""

import sys

import yaml

LEFT_HAND = set(range(0, 7)) | set(range(14, 21)) | set(range(28, 37)) \
    | set(range(46, 53)) | set(range(60, 68))

# corner -> layer, per hand
LEFT_CORNERS = {"tr": "sym", "bl": "fun", "br": "num"}
RIGHT_CORNERS = {"tr": "nav", "bl": "media", "br": "mouse"}

COLORS = {"sym": "#16a34a", "fun": "#dc2626", "num": "#2563eb",
          "nav": "#d97706", "media": "#c026d3", "mouse": "#0891b2"}

# Short forms so corner legends fit
SHORT = {
    "Mouse ←": "M←", "Mouse ↓": "M↓", "Mouse ↑": "M↑", "Mouse →": "M→",
    "Wheel ←": "W←", "Wheel ↓": "W↓", "Wheel ↑": "W↑", "Wheel →": "W→",
    "Click L": "Clk L", "Click R": "Clk R", "Click M": "Clk M",
    "RGB on/off": "RGB", "RGB effect": "Eff", "RGB hue": "Hue", "RGB sat": "Sat",
    "RGB bright": "Bri", "LED power": "LEDs", "USB/BLE": "Out",
    "BT 0": "BT0", "BT 1": "BT1", "BT 2": "BT2", "BT 3": "BT3",
    "Caps Word": "CapsW", "PAUSE BREAK": "Pause", "PSCRN": "PrtSc", "SLCK": "ScrLk",
    "VOL DN": "Vol-", "VOL UP": "Vol+", "PREV": "Prev", "NEXT": "Next",
    "STOP": "Stop", "PP": "Play", "MUTE": "Mute", "APP": "Menu",
    "PG DN": "PgDn", "PG UP": "PgUp", "HOME": "Home", "END": "End", "INS": "Ins",
    "LEFT": "←", "DOWN": "↓", "UP": "↑", "RIGHT": "→",
    "BSPC": "Bspc", "RET": "Ret", "DEL": "Del", "SPACE": "Spc", "TAB": "Tab",
}

HEADER = ("Overview - left hand: Sym (green) Fun (red) Num (blue); "
          "right hand: Nav (amber) Media (magenta) Mouse (teal); grey: hold")

MODS = {"LGUI", "LALT", "LCTRL", "LSHFT", "RALT", "RGUI", "RCTRL", "RSHFT"}


def legend(key):
    if isinstance(key, str):
        return key, "", ""
    if key.get("type") == "trans":
        return "", "", ""
    return key.get("t", ""), key.get("h", ""), key.get("type", "")


def corner_style(corners, hand):
    return "\n".join(
        f".{hand} text.{pos} {{ fill: {COLORS[layer]}; font-weight: bold; }}"
        for pos, layer in corners.items())


def main():
    data = yaml.safe_load(open(sys.argv[1]))
    layers = data["layers"]
    overview = []
    for pos, base in enumerate(layers["base"]):
        tap, hold, _ = legend(base)
        hand = "lh" if pos in LEFT_HAND else "rh"
        key = {"t": tap, "type": hand}
        # Home-row mods and layer names move to the top-left corner
        if hold:
            key["tl"] = hold
        corners = LEFT_CORNERS if hand == "lh" else RIGHT_CORNERS
        for corner, layer in corners.items():
            value, _, _ = legend(layers[layer][pos])
            value = SHORT.get(value, value)
            # Mouse repeats Nav's clipboard row; show it once
            if value and value not in MODS and value not in key.values():
                key[corner] = value
        overview.append(key)

    out = {
        "layout": data["layout"],
        "layers": {HEADER: overview},
        "draw_config": {
            "key_w": 84,
            "key_h": 72,
            "svg_extra_style": "\n".join([
                "text.tl, text.tr, text.bl, text.br { font-size: 11px; }",
                "text.tl { fill: #6b7280; }",
                corner_style(LEFT_CORNERS, "lh"),
                corner_style(RIGHT_CORNERS, "rh"),
            ]),
        },
    }
    yaml.safe_dump(out, sys.stdout, allow_unicode=True, sort_keys=False)


if __name__ == "__main__":
    main()
