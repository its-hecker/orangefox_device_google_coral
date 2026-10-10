#!/usr/bin/env python3
"""Exercise the packaged shell script with isolated property/mount substitutes.

No device, encryption key, real mount or hardware service is accessed.
"""
import argparse
import os
import pathlib
import subprocess
import tempfile


SYSTEM = '''ro.build.version.sdk=37
ro.build.version.release=17
ro.build.version.security_patch=2026-09-01
'''
VENDOR = '''ro.vendor.build.version.sdk=37
ro.vendor.build.security_patch=2022-10-05
'''
VERSION_PROPERTIES = ('ro.build.version.release',
                      'ro.build.version.security_patch',
                      'ro.vendor.build.security_patch')


def properties(text):
    return dict(line.split('=', 1) for line in text.splitlines()
                if '=' in line and not line.startswith('#'))


def exercise(source, system, vendor, layout, override='true', missing=False):
    with tempfile.TemporaryDirectory(prefix='coral-prepdecrypt-') as directory:
        root = pathlib.Path(directory)
        initial = {
            'ro.build.version.release': '12',
            'ro.build.version.sdk': '32',
            'ro.build.version.security_patch': '2026-09-01',
            'ro.vendor.build.security_patch': '2022-10-05',
            'ro.crypto.type': 'file',
            'ro.build.ab_update': 'true',
            'ro.boot.slot_suffix': '_b',
            'ro.boot.dynamic_partitions': 'true',
            'prepdecrypt.setpatch': override,
            'prepdecrypt.loglevel': '2',
        }
        (root / 'props').mkdir()
        for key, value in initial.items():
            (root / 'props' / key).write_text(value)
        (root / 'cmdline').write_text('twrpfastboot=1')
        (root / 'resetprop').touch()
        (root / 'prop.default').write_text(''.join(f'{k}={v}\n' for k, v in initial.items()))
        (root / 'vendor').mkdir()
        (root / 'vendor/build.prop').write_text(vendor)
        prop_path = root / 'system' / layout
        prop_path.parent.mkdir(parents=True)
        if not missing:
            prop_path.write_text(system)
        else:
            # A mounted system image with other files but no usable properties.
            (root / 'system/other-file').touch()
        replacements = {
            '#!/sbin/sh': '#!/bin/sh',
            'LOGFILE=/tmp/recovery.log': 'LOGFILE="$TEST_ROOT/recovery.log"',
            'DEFAULTPROP=prop.default': 'DEFAULTPROP="$TEST_ROOT/prop.default"',
            'DEFAULTPROP=default.prop': 'DEFAULTPROP="$TEST_ROOT/prop.default"',
            '/proc/cmdline': '"$TEST_ROOT/cmdline"',
            '/system/bin/resetprop': '"$TEST_ROOT/resetprop"',
            '/sbin/resetprop': '"$TEST_ROOT/resetprop"',
            '/dev/block/bootdevice/': '${TEST_ROOT}/block/',
            'TEMPSYS=/s': 'TEMPSYS="$TEST_ROOT/s"',
            'TEMPVEN=/v': 'TEMPVEN="$TEST_ROOT/v"',
        }
        for old, new in replacements.items():
            if old not in source:
                raise ValueError(f'Host substitute no longer matches script: {old}')
            source = source.replace(old, new)
        commands = r'''
getprop() { cat "$TEST_ROOT/props/$1" 2>/dev/null || true; }
resetprop() {
    printf '%s' "$2" > "$TEST_ROOT/props/$1"
    printf '%s=%s\n' "$1" "$2" >> "$TEST_ROOT/events"
}
setprop() { resetprop "$@"; }
sleep() { :; }
mount() {
    [ "$1" = -o ] && [ "$2" = ro ] || return 1
    case "$3:$4" in
        "$TEST_ROOT/block/by-name/vendor:$TEST_ROOT/v") part=vendor ;;
        "$TEST_ROOT/block/by-name/system:$TEST_ROOT/s") part=system ;;
        *) return 1 ;;
    esac
    cp -R "$TEST_ROOT/$part/." "$4/"
}
umount() {
    case "$1" in "$TEST_ROOT/s"|"$TEST_ROOT/v") ;; *) return 1 ;; esac
    rm -rf "$1"
    mkdir "$1"
}
'''
        script = root / 'prepdecrypt.sh'
        script.write_text(commands + source)
        result = subprocess.run(['sh', str(script)], cwd=root, capture_output=True,
                                text=True, timeout=10,
                                env={**os.environ, 'TEST_ROOT': str(root)})
        expected_code = 2 if missing else 0
        assert result.returncode == expected_code, (result.returncode, result.stderr,
                                                   (root / 'recovery.log').read_text())
        events = (root / 'events').read_text().splitlines()
        assert events[-1] == 'crypto.ready=1', events
        expected = initial if override == 'false' or missing else {
            **properties(system), **properties(vendor)}
        for key in VERSION_PROPERTIES:
            assert (root / 'props' / key).read_text() == expected[key], (key, events)
        # Recovery keeps its build SDK while supplying the installed OS version.
        assert (root / 'props/ro.build.version.sdk').read_text() == '32'
        if override == 'true' and not missing:
            for key in VERSION_PROPERTIES:
                assert f'{key}={expected[key]}' in events[:-1], events
        if override == 'true':
            assert not (root / 's').exists() and not (root / 'v').exists()
        print(f'prepdecrypt passed: {layout}, override={override}, missing={missing}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('script', type=pathlib.Path)
    parser.add_argument('--system-prop', type=pathlib.Path)
    parser.add_argument('--vendor-prop', type=pathlib.Path)
    args = parser.parse_args()
    source = args.script.read_text()
    system = args.system_prop.read_text() if args.system_prop else SYSTEM
    vendor = args.vendor_prop.read_text() if args.vendor_prop else VENDOR
    exercise(source, system, vendor, 'system/build.prop')
    exercise(source, system, vendor, 'build.prop')
    exercise(source, system, vendor, 'build.prop', override='false')
    exercise(source, system, vendor, 'build.prop', missing=True)
