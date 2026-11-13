#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Guarded Hecker Recovery 2.0 presentation layer for the pinned OrangeFox 12.1 UI.

The November Keymaster, encryption, touch, partition, installer, fastbootd,
and USB implementations are not modified. Unknown upstream UI revisions fail
closed instead of allowing a silently partially branded recovery.
"""
from pathlib import Path
import argparse
import os
import struct
import xml.etree.ElementTree as ET

ROOT = Path("gui/theme/portrait_hdpi")
SNIPPETS = {
    "splash.xml": (
        ('filename="SVG/Logos/logo_o.svg"', 'filename="Default/About/hecker_caracal.png"'),
        ("<text>OrangeFox</text>", "<text>HeckerOS</text>"),
    ),
    "themes/accent.xml": (
        ("#ed6f02", "#82A9FF"),
        ("#D86100", "#5277B3"),
    ),
    "pages/main.xml": (
        ("<text>{@welcome_msg}</text>", "<text>Hecker Recovery 2.0</text>"),
        ("<text>{@welcome_msg2}</text>", "<text>Pixel 4 XL | Coral</text>"),
    ),
    "pages/settings.xml": (
        ("<text>%of_maintainer% (Maintainer)</text>",
         "<text>Hecker Recovery 2.0 - %of_maintainer%</text>"),
    ),
    "pages/recovery.xml": (
        ("Install OrangeFox recovery", "Install Hecker Recovery"),
    ),
}
CARACAL = ROOT / "images/Default/About/hecker_caracal.png"


def transform(content, relative, revert=False):
    if relative not in SNIPPETS:
        raise ValueError("Unknown theme path: " + relative)
    for before, after in SNIPPETS[relative]:
        original, modified = (after, before) if revert else (before, after)
        original_count = content.count(original)
        modified_count = content.count(modified)
        if original_count and modified_count:
            raise ValueError("Mixed original/patched UI source: " + relative)
        if original_count:
            # Accent appears repeatedly; every occurrence gets the same palette.
            if relative != "themes/accent.xml" and original_count != 1:
                raise ValueError("Unexpected repeated theme anchor: " + relative)
            content = content.replace(original, modified)
        elif not modified_count:
            raise ValueError("Unrecognized OrangeFox theme source: " + relative)
    ET.fromstring(content)
    return content


def plan(recovery_root, caracal, revert=False):
    recovery_root = Path(recovery_root)
    caracal = Path(caracal)
    data = caracal.read_bytes()
    if not data.startswith(b"\x89PNG\r\n\x1a\n") or len(data) < 256:
        raise ValueError("HeckerOS caracal asset is not a valid PNG")
    width, height = struct.unpack_from(">II", data, 16)
    if not 1 <= width <= 2048 or not 1 <= height <= 2048:
        raise ValueError("Unexpected HeckerOS caracal dimensions")
    result = {}
    for relative in SNIPPETS:
        target = recovery_root / ROOT / relative
        text = target.read_text(encoding="utf-8")
        changed = transform(text, relative, revert=revert)
        if changed != text:
            result[target] = changed.encode("utf-8")
    if not revert:
        asset = recovery_root / CARACAL
        if not asset.exists() or asset.read_bytes() != data:
            result[asset] = data
    return result


def apply(recovery_root, caracal, check=False, revert=False):
    # Fully compute and validate every modification before changing any file.
    updates = plan(recovery_root, caracal, revert=revert)
    if check:
        return updates
    staged = []
    try:
        for target, data in updates.items():
            target.parent.mkdir(parents=True, exist_ok=True)
            temp = target.with_name(target.name + ".hecker-staging")
            if temp.exists():
                raise ValueError("Existing staging file: " + str(temp))
            temp.write_bytes(data)
            staged.append((temp, target))
        for temp, target in staged:
            os.replace(temp, target)
    finally:
        for temp, _ in staged:
            temp.unlink(missing_ok=True)
    return updates


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recovery", type=Path, help="Synced bootable/recovery checkout")
    parser.add_argument("caracal", type=Path, help="Existing HeckerOS PNG")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--revert", action="store_true")
    args = parser.parse_args()
    changed = apply(args.recovery, args.caracal, check=args.check, revert=args.revert)
    for target in changed:
        print(("WOULD_UPDATE" if args.check else "UPDATED") + ": " + str(target))
    print("PASS: Hecker Recovery UI guard; flashing, Keymaster and userdata logic untouched")


if __name__ == "__main__":
    main()
