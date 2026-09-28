"""Print the Advantage 360 Pro's active layer, battery and output.

Reads the raw HID status report sent by src/status_report.c.
"""

import argparse
import json
import sys
import time

try:
    # Linux: hidraw backend, which sees usage pages and Bluetooth devices (the default libusb one doesn't)
    import hidraw as hid
except ImportError:
    import hid

USAGE_PAGE = 0xFF60
USAGE = 0x61
REPORT_SIZE = 32
MAGIC = ord("Z")
TRANSPORTS = {0: "none", 1: "USB", 2: "BLE"}


def find_devices():
    return [
        d for d in hid.enumerate()
        if d["usage_page"] == USAGE_PAGE and d["usage"] == USAGE
        and "adv360" in (d["product_string"] or "").lower()
    ]


def open_device(path=None):
    if path is None:
        devices = find_devices()
        if not devices:
            return None
        path = devices[0]["path"]
    dev = hid.device()
    dev.open_path(path)
    return dev


def request_status(dev):
    # Leading 0 is the report ID (the firmware uses none)
    dev.write([0, MAGIC, ord("?")] + [0] * (REPORT_SIZE - 2))


def parse(report):
    if len(report) < REPORT_SIZE or report[0] != MAGIC:
        return None
    mask = int.from_bytes(bytes(report[3:7]), "little")
    name = bytes(report[12:]).split(b"\0", 1)[0].decode(errors="replace")

    def battery(b):
        return None if b == 0xFF else b

    return {
        "layer": report[2],
        "layer_name": name,
        # Base (0) is always active but has no bit in the mask
        "active_layers": [0] + [i for i in range(1, 32) if mask >> i & 1],
        "battery_left": battery(report[7]),
        "battery_right": battery(report[8]),
        "transport": TRANSPORTS.get(report[9], "unknown"),
        "ble_profile": report[10],
        "ble_connected": bool(report[11]),
    }


def format_line(s):
    def pct(v):
        return "?" if v is None else f"{v}%"

    output = s["transport"]
    if output == "BLE":
        state = "connected" if s["ble_connected"] else "not connected"
        output = f"BLE profile {s['ble_profile']} ({state})"
    return (f"layer {s['layer_name']} ({s['layer']})"
            f" | battery L {pct(s['battery_left'])} R {pct(s['battery_right'])}"
            f" | output {output}")


def emit(status, as_json):
    print(json.dumps(status) if as_json else format_line(status), flush=True)


def read_status(dev, timeout_ms):
    report = dev.read(64, timeout_ms)
    return parse(report) if report else None


def once(args):
    dev = open_device(args.path)
    if dev is None:
        sys.exit("adv360-status: keyboard not found (is the left half connected?)")
    try:
        request_status(dev)
        deadline = time.monotonic() + args.timeout
        while time.monotonic() < deadline:
            status = read_status(dev, 200)
            if status:
                emit(status, args.json)
                return
        sys.exit("adv360-status: no reply from keyboard (firmware without status reports?)")
    finally:
        dev.close()


def watch(args):
    last = None
    while True:
        dev = open_device(args.path)
        if dev is None:
            time.sleep(2)
            continue
        try:
            request_status(dev)
            while True:
                status = read_status(dev, 1000)
                if status and status != last:
                    emit(status, args.json)
                    last = status
        except OSError:
            # Unplugged or disconnected; reopen when it comes back
            last = None
        finally:
            dev.close()
        time.sleep(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-w", "--watch", action="store_true", help="print on every change")
    parser.add_argument("-j", "--json", action="store_true", help="JSON output, one object per line")
    parser.add_argument("--path", type=lambda p: p.encode(), help="HID device path to use")
    parser.add_argument("--timeout", type=float, default=2.0, help="seconds to wait for a reply")
    parser.add_argument("--list", action="store_true", help="list matching HID devices")
    args = parser.parse_args()

    if args.list:
        for d in find_devices():
            print(d["path"].decode(), d["product_string"], f"{d['vendor_id']:04x}:{d['product_id']:04x}")
        return
    try:
        watch(args) if args.watch else once(args)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
