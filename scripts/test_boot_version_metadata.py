#!/usr/bin/env python3
"""Exercise actual Make/avbtool output and reject inconsistent boot metadata."""
import argparse
import pathlib
import re
import shlex
import struct
import subprocess
import sys
import tempfile


def footer_args(makefile, override):
    # Evaluate the real patched boot-property rules, not a copy of their logic.
    source = makefile.read_text()
    start = source.index('BOARD_AVB_BOOT_OS_VERSION ?=')
    end = source.index('\n\n', start)
    rules = source[start:end]
    firmware = re.search(
        r'ifdef BOOT_SECURITY_PATCH\n(BOARD_AVB_BOOT_ADD_HASH_FOOTER_ARGS \+= \\\n.*?)(?:\nendif)',
        source, re.DOTALL).group(1)
    config = 'PLATFORM_VERSION_LAST_STABLE := 12\nBUILD_FINGERPRINT_FROM_FILE := test/coral\nBOOT_SECURITY_PATCH := 2022-10-05\n'
    if override:
        config += f'BOARD_AVB_BOOT_OS_VERSION := {override}\n'
    config += rules + '\n' + firmware + '\nall:\n\t@echo $(BOARD_AVB_BOOT_ADD_HASH_FOOTER_ARGS)\n'
    output = subprocess.check_output(
        ['make', '--no-print-directory', '-f', '-'], input=config, text=True)
    return shlex.split(output.strip())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('makefile', type=pathlib.Path)
    parser.add_argument('avbtool', type=pathlib.Path)
    args = parser.parse_args()
    validator = pathlib.Path(__file__).with_name('validate_image.py')
    configured = footer_args(args.makefile, '17')
    default = footer_args(args.makefile, None)
    assert 'com.android.build.boot.os_version:17' in configured
    assert 'com.android.build.boot.os_version:12' in default
    assert 'com.android.build.boot.security_patch:2022-10-05' in configured
    # Each case is a synthetic header-v2 image with a real AVB hash footer.
    cases = [
        ('matching', configured, 11, True, ''),
        ('legacy-avb-version', default, 11, False, 'Boot AVB OS version'),
        ('september-header', configured, 9, False, 'Boot header patch'),
        ('october-header', configured, 10, False, 'Boot header patch'),
        ('wrong-firmware-patch', [x.replace('security_patch:2022-10-05', 'security_patch:2026-11-01') for x in configured], 11, False, 'Boot AVB firmware patch'),
        ('duplicate-os-property', configured + ['--prop', 'com.android.build.boot.os_version:12'], 11, False, 'Expected exactly one AVB property'),
    ]
    with tempfile.TemporaryDirectory() as directory:
        for name, properties, month, succeeds, error in cases:
            image = pathlib.Path(directory) / (name + '.img')
            data = bytearray(16384)
            data[:8] = b'ANDROID!'
            struct.pack_into('<I', data, 8, 1)  # kernel
            struct.pack_into('<I', data, 16, 1)  # ramdisk
            struct.pack_into('<II', data, 36, 4096, 2)
            struct.pack_into('<I', data, 44, (17 << 25) | (26 << 4) | month)
            struct.pack_into('<I', data, 1648, 1)  # DTB
            image.write_bytes(data)
            subprocess.run([sys.executable, str(args.avbtool), 'add_hash_footer',
                            '--image', str(image), '--partition_name', 'boot',
                            '--partition_size', '1048576'] + properties, check=True)
            result = subprocess.run([
                sys.executable, str(validator), str(image), '--os-version', '17',
                '--os-patch-level', '2026-11-01', '--boot-security-patch', '2022-10-05',
                '--avb-tool', str(args.avbtool)], text=True, capture_output=True)
            if (result.returncode == 0) != succeeds or (error and error not in result.stderr):
                raise AssertionError(f'{name}: unexpected validation result\n{result.stdout}{result.stderr}')
            print(f'PASS: {name}')
    print('Boot metadata checks passed; hardware decryption remains untested.')


if __name__ == '__main__':
    main()
