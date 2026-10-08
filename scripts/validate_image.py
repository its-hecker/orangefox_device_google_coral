#!/usr/bin/env python3
"""Structural checks only; these cannot prove bootability or decryption."""
import argparse
import pathlib
import struct
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('image', type=pathlib.Path)
parser.add_argument('--kernel', type=pathlib.Path)
parser.add_argument('--dtb', type=pathlib.Path)
args = parser.parse_args()
image = args.image.read_bytes()
assert 1660 <= len(image) <= 64 * 1024 * 1024, 'Invalid coral boot image size'
assert image[:8] == b'ANDROID!', 'Missing Android boot magic'
kernel_size, = struct.unpack_from('<I', image, 8)
ramdisk_size, = struct.unpack_from('<I', image, 16)
page_size, header_version = struct.unpack_from('<II', image, 36)
assert header_version == 2, f'Expected coral header v2, got {header_version}'
assert page_size == 4096, f'Unexpected page size {page_size}'
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
print(f'Structural checks passed: {len(image)} bytes; kernel, ramdisk and DTB present')
