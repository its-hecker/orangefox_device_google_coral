#!/usr/bin/env python3
"""Replace only Coral's About XML and avatar in a checksum-pinned boot image.

Preserve every cpio entry's metadata and all other payloads. Update the v2
boot ID and regenerate its unsigned AVB hash footer with the original
salt/properties, using the source build's pinned AOSP avbtool.
"""
import argparse
import gzip
import hashlib
import json
import pathlib
import re
import struct
import subprocess
import sys
import tempfile


def sha(data):
    return hashlib.sha256(data).hexdigest()


def align(size, boundary):
    return (size + boundary - 1) // boundary * boundary


def entries(data):
    result, offset = [], 0
    while offset + 110 <= len(data):
        header = data[offset:offset + 110]
        assert header[:6] == b'070701', 'Expected newc without CRC'
        size = int(header[54:62], 16)
        namesize = int(header[94:102], 16)
        assert namesize > 0
        name_end = offset + 110 + namesize
        assert name_end <= len(data) and data[name_end - 1] == 0
        name = data[offset + 110:name_end - 1].decode()
        path = pathlib.PurePosixPath(name)
        assert not path.is_absolute() and '..' not in path.parts
        start = align(name_end, 4)
        assert start + size <= len(data)
        result.append((name, header, data[offset + 110:name_end], data[start:start + size]))
        offset = align(start + size, 4)
        if name == 'TRAILER!!!':
            assert not data[offset:].strip(b'\0'), 'Unexpected archive following trailer'
            assert len({r[0] for r in result}) == len(result), 'Duplicate cpio path'
            return result
    raise ValueError('Missing cpio trailer')


def replace_entries(original, replacements):
    result, seen = bytearray(), set()
    for name, header, encoded_name, payload in entries(original):
        if name in replacements:
            assert int(header[14:22], 16) & 0o170000 == 0o100000
            payload = replacements[name]
            header = header[:54] + f'{len(payload):08x}'.encode() + header[62:]
            seen.add(name)
        result.extend(header + encoded_name)
        result.extend(b'\0' * (align(len(result), 4) - len(result)))
        result.extend(payload)
        result.extend(b'\0' * (align(len(result), 4) - len(result)))
    assert seen == set(replacements)
    result.extend(b'\0' * (align(len(result), 512) - len(result)))
    # Compare every entry, including symlinks, modes, owners and timestamps.
    for before, after in zip(entries(original), entries(result)):
        assert before[0] == after[0] and before[2] == after[2]
        if before[0] in replacements:
            assert before[1][:54] + before[1][62:] == after[1][:54] + after[1][62:]
            assert after[3] == replacements[before[0]]
        else:
            assert before == after, 'Unexpected ramdisk change: ' + before[0]
    return bytes(result)


def parts(image):
    assert image[:8] == b'ANDROID!' and len(image) == 67108864
    kernel_size = struct.unpack_from('<I', image, 8)[0]
    ramdisk_size = struct.unpack_from('<I', image, 16)[0]
    page, version = struct.unpack_from('<II', image, 36)
    assert (page, version) == (4096, 2)
    assert struct.unpack_from('<I', image, 24)[0] == 0, 'Unexpected second stage'
    assert struct.unpack_from('<IQI', image, 1632) == (0, 0, 1660), 'Unexpected DTBO/header'
    dtb_size = struct.unpack_from('<I', image, 1648)[0]
    assert min(kernel_size, ramdisk_size, dtb_size) > 0
    ramdisk_start = page + align(kernel_size, page)
    dtb_start = ramdisk_start + align(ramdisk_size, page)
    return image[:page], image[page:page + kernel_size], image[ramdisk_start:ramdisk_start + ramdisk_size], image[dtb_start:dtb_start + dtb_size]


def boot_id(kernel, ramdisk, dtb):
    # AOSP mkbootimg v2: kernel, ramdisk, absent second and DTBO, then DTB.
    digest = hashlib.sha1()
    for payload in (kernel, ramdisk, b'', b'', dtb):
        digest.update(payload)
        digest.update(struct.pack('<I', len(payload)))
    return digest.digest() + b'\0' * 12


def avb_info(tool, image):
    info = subprocess.check_output([sys.executable, str(tool), 'info_image', '--image', str(image)], text=True)
    assert re.search(r'^Algorithm:\s+NONE$', info, re.M), 'Only the unsigned source image is supported'
    assert re.findall(r'^\s*Flags:\s+(\d+)$', info, re.M) == ['0', '0']
    assert re.search(r'^Rollback Index:\s+0$', info, re.M)
    assert re.search(r'^Rollback Index Location:\s+0$', info, re.M)
    assert re.search(r'^\s+Partition Name:\s+boot$', info, re.M)
    assert re.search(r'^\s+Hash Algorithm:\s+sha256$', info, re.M)
    assert info.count('Hash descriptor:') == 1
    salt = re.search(r'^\s+Salt:\s+([0-9a-f]+)$', info, re.M).group(1)
    props = re.findall(r"^\s+Prop: ([^ ]+) -> '([^'\n]+)'$", info, re.M)
    assert {k for k, _ in props} == {'com.android.build.boot.fingerprint', 'com.android.build.boot.os_version', 'com.android.build.boot.security_patch'}
    return salt, props


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base_image', type=pathlib.Path)
    parser.add_argument('output', type=pathlib.Path)
    parser.add_argument('--avatar', type=pathlib.Path, required=True)
    parser.add_argument('--avb-tool', type=pathlib.Path, required=True)
    parser.add_argument('--config', type=pathlib.Path, default=pathlib.Path('release/avatar-update.json'))
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    image = args.base_image.read_bytes()
    assert sha(image) == config['base_image_sha256'], 'Source image checksum mismatch'
    assert sha(args.avatar.read_bytes()) == config['avatar_sha256'], 'Selected avatar checksum mismatch'
    assert sha(args.avb_tool.read_bytes()) == config['avbtool_sha256'], 'AVB tool checksum mismatch'
    assert not args.output.exists(), 'Output image must be new'
    header, kernel, packed, dtb = parts(image)
    assert header[576:608] == boot_id(kernel, packed, dtb), 'Source boot ID is invalid'
    salt, props = avb_info(args.avb_tool, args.base_image)
    archive = gzip.decompress(packed)
    files = {e[0]: e[3] for e in entries(archive)}
    old_label = b'<text>%of_maintainer%</text>'
    settings = files['twres/pages/settings.xml']
    assert settings.count(old_label) == 1
    old_link = b'<text>Support: t.me/pixel4seriesofficial</text>'
    assert settings.count(old_link) == 1
    channel_url = config['channel_url']
    assert re.fullmatch(r'https://t\.me/[A-Za-z0-9_]+', channel_url), 'Invalid channel URL'
    channel_label = ('<text>Channel: ' + channel_url.removeprefix('https://') + '</text>').encode()
    settings = settings.replace(old_label, b'<text>%of_maintainer% (Maintainer)</text>').replace(old_link, channel_label)
    replacements = {
        'twres/pages/settings.xml': settings,
        'twres/images/Default/About/maintainer.png': args.avatar.read_bytes(),
    }
    updated = gzip.compress(replace_entries(archive, replacements), compresslevel=9, mtime=0)
    new_header = bytearray(header)
    struct.pack_into('<I', new_header, 16, len(updated))
    new_header[576:608] = boot_id(kernel, updated, dtb)
    assert new_header[:16] + new_header[20:576] + new_header[608:] == header[:16] + header[20:576] + header[608:]
    result = bytearray(new_header)
    for payload in (kernel, updated, dtb):
        result.extend(payload)
        result.extend(b'\0' * (align(len(result), 4096) - len(result)))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(result)
    cmd = [sys.executable, str(args.avb_tool), 'add_hash_footer', '--image', str(args.output),
           '--partition_size', '67108864', '--partition_name', 'boot', '--algorithm', 'NONE', '--salt', salt]
    for k, value in props:
        cmd.extend(['--prop', k + ':' + value])
    subprocess.run(cmd, check=True)
    # avbtool resolves a hash descriptor's partition name to boot.img.
    with tempfile.TemporaryDirectory() as temporary:
        verification = pathlib.Path(temporary) / 'boot.img'
        verification.symlink_to(args.output.resolve())
        subprocess.run([sys.executable, str(args.avb_tool), 'verify_image', '--image', str(verification)], check=True)
    assert avb_info(args.avb_tool, args.output) == (salt, props), 'AVB properties changed'
    after_header, after_kernel, after_ramdisk, after_dtb = parts(args.output.read_bytes())
    assert after_header == new_header and after_kernel == kernel and after_dtb == dtb
    assert gzip.decompress(after_ramdisk) == replace_entries(archive, replacements)
    provenance = {
        'base_image_sha256': sha(image), 'base_device_commit': config['base_commit'],
        'packaging_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'modified_ramdisk_paths': sorted(replacements), 'avatar_sha256': config['avatar_sha256'],
        'channel_url': channel_url,
        'kernel_sha256': sha(kernel), 'dtb_sha256': sha(dtb),
        'image_sha256': sha(args.output.read_bytes()), 'avbtool_revision': config['avbtool_revision'],
    }
    args.output.with_name('theme-update.json').write_text(json.dumps(provenance, indent=2) + '\n')
    print('Verified: only the two About assets changed; kernel, DTB, all other ramdisk entries and AVB properties preserved')


if __name__ == '__main__':
    main()
