#!/usr/bin/env python3
"""Check Coral's packaged startup services; this cannot test device hardware."""
import gzip
import pathlib
import re
import xml.etree.ElementTree as ET


def ramdisk_files(packed):
    """Read regular files from gzip/newc without extracting paths to the host."""
    data = gzip.decompress(packed)
    files = {}
    offset = 0
    while offset + 110 <= len(data):
        header = data[offset:offset + 110]
        if header[:6] not in (b'070701', b'070702'):
            raise ValueError('Invalid recovery cpio header')
        fields = [int(header[6 + i * 8:14 + i * 8], 16) for i in range(13)]
        mode, size, name_size = fields[1], fields[6], fields[11]
        name_end = offset + 110 + name_size
        if name_size < 1 or name_end > len(data) or data[name_end - 1] != 0:
            raise ValueError('Truncated recovery cpio filename')
        name = data[offset + 110:name_end - 1].decode()
        path = pathlib.PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts:
            raise ValueError('Invalid recovery cpio path')
        offset = (name_end + 3) // 4 * 4
        end = offset + size
        if end > len(data):
            raise ValueError('Truncated recovery cpio file')
        if name == 'TRAILER!!!':
            return files
        if mode & 0o170000 == 0o100000:
            files[str(path)] = data[offset:end]
        offset = (end + 3) // 4 * 4
    raise ValueError('Missing recovery cpio trailer')


def runtime_errors(files, keymaster_version):
    properties = {
        'ro.crypto.state': 'encrypted',
        'ro.crypto.type': 'file',
        'ro.boot.dynamic_partitions': 'true',
        'hwservicemanager.ready': 'true',
        'crypto.ready': '1',
        'vendor.sys.listeners.registered': 'true',
        'keymaster_ver': keymaster_version,
    }
    services, started, errors = {}, set(), []
    for name, data in files.items():
        if not (re.fullmatch(r'init\.recovery\..*\.rc', name) or
                re.fullmatch(r'system/etc/init/[^/]+\.rc', name)):
            continue
        action_matches = False
        for line in data.decode().splitlines():
            line = line.split('#', 1)[0].strip()
            if line.startswith('service '):
                fields = line.split()
                services[fields[1]] = fields[2].lstrip('/')
                action_matches = False
            elif line.startswith('on '):
                clauses = line[3:].split(' && ')
                conditions = [re.fullmatch(r'property:([^=]+)=(.*)', c) for c in clauses]
                # Normal boot and the encrypted-startup properties above are
                # considered; the fastbootd-only trigger must not satisfy this.
                action_matches = line == 'on boot' or all(
                    c is not None and c[1] in properties and
                    (c[2] == '*' or properties[c[1]] == c[2]) for c in conditions
                )
            elif action_matches and line.startswith('start '):
                started.add(line.split()[1])

    for service in ('keymaster-4-0-qti', 'keymaster-4-1-citadel',
                    'gatekeeper-1-0-qti', 'qseecomd',
                    'vendor.citadeld', 'vendor.weaver_hal', 'health-hal-2-1'):
        if service not in services:
            errors.append(f'Missing recovery service: {service}')
        elif not files.get(services[service]):
            errors.append(f'Missing recovery service binary: {services[service]}')
        if service not in started:
            errors.append(f'Recovery startup does not start {service} (Keymaster {keymaster_version})')

    for library in ('hw/android.hardware.gatekeeper@1.0-impl-qti.so',
                    'android.hardware.gatekeeper@1.0.so',
                    'android.hardware.keymaster@4.0.so',
                    'android.hardware.keymaster@4.1-impl.nos.so',
                    'android.hardware.health@2.0.so',
                    'android.hardware.health@2.1.so',
                    'hw/android.hardware.health@2.0-impl-2.1.so',
                    'libqtikeymaster4.so', 'libkeymasterdeviceutils.so',
                    'libqcbor.so', 'libQSEEComAPI.so', 'libhidlbase.so',
                    'libutils.so', 'liblog.so', 'libcutils.so',
                    'libc++.so', 'libc.so', 'libm.so', 'libdl.so'):
        path = 'system/lib64/' + library
        if not files.get(path, b'').startswith(b'\x7fELF\x02'):
            errors.append(f'Missing 64-bit recovery library: {path}')

    device_init = files.get('init.recovery.coral.rc', b'').decode()
    if 'import /init.recovery.qcom_decrypt.rc' not in device_init:
        errors.append('Coral init does not import the decryption services')
    try:
        manifest = ET.fromstring(files['vendor/etc/vintf/manifest.xml'])
        keymaster = next(h for h in manifest.findall('hal')
                         if h.findtext('name') == 'android.hardware.keymaster')
        instances = {n.text for n in keymaster.findall('fqname')}
        if not {'@4.0::IKeymasterDevice/default', '@4.1::IKeymasterDevice/strongbox'} <= instances:
            errors.append('Recovery manifest must declare both Coral Keymaster instances')
    except (KeyError, StopIteration, ET.ParseError):
        errors.append('Missing or invalid recovery Keymaster manifest')
    try:
        manifest = ET.fromstring(files['vendor/etc/vintf/manifest/android.hardware.health@2.1.xml'])
        health = next(h for h in manifest.findall('hal')
                      if h.findtext('name') == 'android.hardware.health')
        if '@2.1::IHealth/default' not in {n.text for n in health.findall('fqname')}:
            errors.append('Recovery manifest must declare Health 2.1/default')
    except (KeyError, StopIteration, ET.ParseError):
        errors.append('Missing or invalid recovery Health manifest')
    return errors


def validate_runtime(packed, keymaster_version):
    errors = runtime_errors(ramdisk_files(packed), keymaster_version)
    if errors:
        raise ValueError('\n'.join(errors))
    print('Ramdisk checks passed: Keymaster and Health startup configured; required implementations packaged')
