#!/usr/bin/env python3
"""Structural checks only; these cannot prove bootability or decryption."""
import argparse
import pathlib
import struct
import subprocess
import sys
from validate_recovery_runtime import validate_runtime
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('image', type=pathlib.Path)
parser.add_argument('--kernel', type=pathlib.Path)
parser.add_argument('--dtb', type=pathlib.Path)
parser.add_argument('--keymaster-version', help='Check Coral decryption startup using the build configuration')
parser.add_argument('--os-version', help='Expected Keymaster OS version in the boot header')
parser.add_argument('--os-patch-level', help='Expected system patch month in the boot header (YYYY-MM-DD)')
parser.add_argument('--avb-tool', type=pathlib.Path, help='Build-tree avbtool.py for inspecting boot AVB metadata')
parser.add_argument('--boot-security-patch', help='Expected boot firmware patch in the AVB property descriptor')
args = parser.parse_args()
image = args.image.read_bytes()
assert 1660 <= len(image) <= 64 * 1024 * 1024, 'Invalid coral boot image size'
assert image[:8] == b'ANDROID!', 'Missing Android boot magic'
kernel_size, = struct.unpack_from('<I', image, 8)
ramdisk_size, = struct.unpack_from('<I', image, 16)
page_size, header_version = struct.unpack_from('<II', image, 36)
assert header_version == 2, f'Expected coral header v2, got {header_version}'
assert page_size == 4096, f'Unexpected page size {page_size}'
version_field, = struct.unpack_from('<I', image, 44)
os_version = version_field >> 11
os_components = ((os_version >> 14) & 127, (os_version >> 7) & 127, os_version & 127)
os_patch = version_field & 2047
patch_month = f'{2000 + (os_patch >> 4):04d}-{os_patch & 15:02d}'
if args.os_version:
    expected = tuple(int(v) for v in args.os_version.split('.'))
    expected += (0,) * (3 - len(expected))
    assert os_components == expected, f'Boot header OS version {os_components} does not match {expected}'
if args.os_patch_level:
    assert patch_month == args.os_patch_level[:7], f'Boot header patch {patch_month} does not match {args.os_patch_level[:7]}'
if args.boot_security_patch:
    assert args.avb_tool, 'An AVB tool is required to check the boot firmware patch'
    avb_info = subprocess.check_output(
        [sys.executable, str(args.avb_tool), 'info_image', '--image', str(args.image)], text=True)
    expected = f"Prop: com.android.build.boot.security_patch -> '{args.boot_security_patch}'"
    assert expected in avb_info, 'Boot AVB firmware patch differs from the device configuration'
assert kernel_size > 0 and ramdisk_size > 0, 'Missing kernel or recovery ramdisk'
align = lambda size: (size + page_size - 1) // page_size * page_size
second_size, = struct.unpack_from('<I', image, 24)
recovery_dtbo_size, = struct.unpack_from('<I', image, 1632)
dtb_size, = struct.unpack_from('<I', image, 1648)
assert dtb_size > 0, 'Missing DTB'
minimum = page_size + align(kernel_size) + align(ramdisk_size) + align(second_size) + align(recovery_dtbo_size) + dtb_size
assert len(image) >= minimum, 'Truncated boot image'
if args.kernel:
    assert image[page_size:page_size + kernel_size] == args.kernel.read_bytes(), 'Boot image kernel differs from the verified checkpoint'
if args.dtb:
    dtb_offset = minimum - dtb_size
    assert image[dtb_offset:dtb_offset + dtb_size] == args.dtb.read_bytes(), 'Boot image DTBs differ from the verified checkpoint'
if args.keymaster_version:
    ramdisk_offset = page_size + align(kernel_size)
    validate_runtime(image[ramdisk_offset:ramdisk_offset + ramdisk_size], args.keymaster_version)
print(f'Structural checks passed: {len(image)} bytes; kernel, ramdisk and DTB present; OS {os_components}, system patch {patch_month}')
