#!/usr/bin/env python3
"""Save and verify kernel outputs between the two CI runners."""
import argparse
import hashlib
import json
import pathlib
import shutil
import struct
import subprocess

KERNEL_COMMIT = '9d2fb45d1fc6e11ac7e03e73c772b69ce158ea0a'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def revision(path):
    return subprocess.check_output(
        ['git', '-C', str(path), 'rev-parse', 'HEAD'], text=True).strip()


def identity(android, device):
    sources = {p: revision(android / p) for p in (
        'kernel/google/msm-4.14', 'vendor/twrp', 'bootable/recovery',
        'prebuilts/clang/host/linux-x86')}
    if sources['kernel/google/msm-4.14'] != KERNEL_COMMIT:
        raise ValueError('Kernel source does not match the pinned revision')
    return {
        'device_commit': revision(device),
        'sources': sources,
        'defconfig_sha256': digest(android / 'kernel/google/msm-4.14/arch/arm64/configs/floral_defconfig'),
        'kernel_rules_sha256': digest(android / 'vendor/twrp/build/tasks/kernel.mk'),
        'board_rules_sha256': digest(android / 'vendor/twrp/config/BoardConfigKernel.mk'),
    }


def check_dtb(path):
    data = path.read_bytes()
    offset = 0
    while offset < len(data):
        if len(data) - offset < 40:
            raise ValueError('Truncated DTB header')
        magic, size = struct.unpack_from('>II', data, offset)
        if magic != 0xd00dfeed or size < 40 or offset + size > len(data):
            raise ValueError('Invalid concatenated DTB bundle')
        offset += size
    if not offset:
        raise ValueError('Empty DTB bundle')


def export_checkpoint(android, device, checkpoint):
    expected = identity(android, device)
    out = android / 'out/target/product/coral'
    files = {
        'Image.lz4': out / 'kernel',
        'dtb.img': out / 'dtb.img',
        'kernel.config': out / 'obj/KERNEL_OBJ/.config',
    }
    # Preserve installed modules and depmod files at their original output paths.
    for directory in ('vendor/lib/modules', 'root/lib/modules',
                      'recovery/root/vendor/lib/modules'):
        for path in sorted((out / directory).rglob('*')):
            if path.is_file() and not path.is_symlink():
                files['modules/' + str(path.relative_to(out))] = path
    for name, path in files.items():
        if not path.is_file() or (name in ('Image.lz4', 'dtb.img', 'kernel.config')
                                  and not path.stat().st_size):
            raise ValueError(f'Missing or empty kernel output: {name}')
    check_dtb(files['dtb.img'])
    # Validate the compressed kernel before exposing a checkpoint to recovery.
    subprocess.run(['lz4', '-t', str(files['Image.lz4'])], check=True)
    if checkpoint.exists():
        raise ValueError('Checkpoint destination must be new')
    checkpoint.mkdir(parents=True)
    for name, path in files.items():
        destination = checkpoint / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
    metadata = {'format': 1, 'identity': expected,
                'files': {name: digest(checkpoint / name) for name in files}}
    (checkpoint / 'metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print(f'Kernel checkpoint saved: {len(files)} verified files')


def import_checkpoint(android, device, checkpoint):
    destination = android / 'device/google/coral/ci-kernel'
    if destination.exists():
        raise ValueError('Refusing to reuse an existing staged kernel')
    metadata = json.loads((checkpoint / 'metadata.json').read_text())
    if metadata['format'] != 1 or metadata['identity'] != identity(android, device):
        raise ValueError('Kernel checkpoint does not match this build and source revisions')
    required = {'Image.lz4', 'dtb.img', 'kernel.config'}
    if not required.issubset(metadata['files']):
        raise ValueError('Incomplete kernel checkpoint')
    for name, sha in metadata['files'].items():
        relative = pathlib.PurePosixPath(name)
        if relative.is_absolute() or '..' in relative.parts or not (
                name in required or name.startswith('modules/')):
            raise ValueError(f'Invalid checkpoint path: {name}')
        path = checkpoint / name
        if path.is_symlink() or not path.is_file() or digest(path) != sha:
            raise ValueError(f'Kernel checkpoint checksum mismatch: {name}')
    check_dtb(checkpoint / 'dtb.img')
    destination.mkdir(parents=True)
    shutil.copy2(checkpoint / 'Image.lz4', destination / 'Image.lz4')
    (destination / 'dtb').mkdir()
    shutil.copy2(checkpoint / 'dtb.img', destination / 'dtb/coral.dtb')
    out = android / 'out/target/product/coral'
    for name in metadata['files']:
        if name.startswith('modules/'):
            target = out / name.removeprefix('modules/')
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(checkpoint / name, target)
    # This marker activates the BoardConfig include only after every check passes.
    (destination / 'verified').write_text(metadata['identity']['device_commit'] + '\n')
    print('Kernel checkpoint verified and staged for recovery packaging')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('export', 'import'))
    parser.add_argument('android', type=pathlib.Path)
    parser.add_argument('device', type=pathlib.Path)
    parser.add_argument('checkpoint', type=pathlib.Path)
    args = parser.parse_args()
    operation = export_checkpoint if args.mode == 'export' else import_checkpoint
    operation(args.android.resolve(), args.device.resolve(), args.checkpoint.resolve())
