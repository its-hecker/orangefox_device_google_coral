#!/usr/bin/env python3
"""Stage the exact kernel and DTB from a HeckerOS Android 17 ROM boot image.

This prepares a *standalone recovery test image*, not a ROM replacement.
The extracted kernel retains whatever KSU patches are in the supplied ROM boot.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

MAX_SIZE = 64 * 1024 * 1024
PAGE = 4096


def align(n):
    return ((n + PAGE - 1) // PAGE) * PAGE


def stage(image_path, device_dir):
    image_path, device_dir = Path(image_path), Path(device_dir)
    raw = image_path.read_bytes()
    if not PAGE <= len(raw) <= MAX_SIZE or raw[:8] != b"ANDROID!":
        raise ValueError("Expected a coral Android boot image not exceeding 64 MiB")
    kernel_size, ramdisk_size, second_size = (struct.unpack_from("<I", raw, n)[0]
                                              for n in (8, 16, 24))
    page, version = struct.unpack_from("<II", raw, 36)
    dtbo_size, = struct.unpack_from("<I", raw, 1632)
    dtb_size, = struct.unpack_from("<I", raw, 1648)
    packed, = struct.unpack_from("<I", raw, 44)
    android_major = packed >> 25
    patch_month = packed & 15
    if page != PAGE or version != 2 or android_major != 17 or not 1 <= patch_month <= 12:
        raise ValueError("Expected HeckerOS Android 17, header v2, 4096-byte pages")
    if not 0 < kernel_size < MAX_SIZE or not 0 < ramdisk_size < MAX_SIZE or not 0 < dtb_size < MAX_SIZE:
        raise ValueError("Invalid kernel, ramdisk or DTB size")
    kstart = PAGE
    dstart = PAGE + align(kernel_size) + align(ramdisk_size) + align(second_size) + align(dtbo_size)
    if dstart + dtb_size > len(raw):
        raise ValueError("Truncated Android boot image")
    kernel = raw[kstart:kstart + kernel_size]
    dtb = raw[dstart:dstart + dtb_size]
    if not kernel.startswith((b"\x02\x21\x4c\x18", b"\x04\x22\x4d\x18")):
        raise ValueError("Expected Image.lz4 kernel; refusing unrecognized kernel compression")
    out = device_dir / "ci-kernel"
    if out.exists():
        raise ValueError("Refusing to overwrite an existing kernel staging directory")
    (out / "dtb").mkdir(parents=True)
    (out / "Image.lz4").write_bytes(kernel)
    (out / "dtb" / "coral.dtb").write_bytes(dtb)
    report = {
        "source_rom_boot_sha256": hashlib.sha256(raw).hexdigest(),
        "kernel_sha256": hashlib.sha256(kernel).hexdigest(),
        "dtb_sha256": hashlib.sha256(dtb).hexdigest(),
        "android_major": android_major,
        "mode": "standalone_recovery_only",
        "safe_to_ship_in_rom_ota": False,
    }
    (out / "metadata.json").write_text(json.dumps(report, indent=2) + "\n")
    # BoardConfig enables prebuilt boot components only after validating this marker.
    (out / "verified").write_text(report["source_rom_boot_sha256"] + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom_boot", type=Path)
    parser.add_argument("device_dir", type=Path)
    args = parser.parse_args()
    print(json.dumps(stage(args.rom_boot, args.device_dir), indent=2))
