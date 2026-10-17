#!/usr/bin/env python3
"""Run actual patched partition/storage entry points against isolated host data."""
import argparse
import pathlib
import subprocess
import tempfile


def method(source, signature):
    start = source.index(signature)
    begin = source.index('{', start)
    depth, end = 1, begin + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('recovery', type=pathlib.Path)
    args = parser.parse_args()
    partition = (args.recovery / 'partition.cpp').read_text()
    manager = (args.recovery / 'partitionmanager.cpp').read_text()
    methods = '\n\n'.join((
        method(partition, 'bool TWPartition::Prepare_Fresh_Data_Media('),
        method(manager, 'void TWPartitionManager::Decrypt_Data('),
        method(manager, 'int TWPartitionManager::Format_Data('),
    ))
    harness = pathlib.Path(__file__).resolve().parent.parent / 'tests/fresh_data_media_harness.cpp'
    with tempfile.TemporaryDirectory(prefix='coral-fresh-data-') as directory:
        root = pathlib.Path(directory)
        (root / 'fresh_data_methods.inc').write_text(methods)
        binary = root / 'fresh-data-test'
        subprocess.run(['g++', '-std=c++17', '-Wall', '-Wextra', '-Werror',
                        '-Wno-unused-parameter', str(harness), '-I', str(root),
                        '-o', str(binary)], check=True)
        subprocess.run([str(binary), str(root)], check=True)


if __name__ == '__main__':
    main()
