#!/usr/bin/env python3
"""Exercise the actual slider methods with guarded image buffers on the host."""
import argparse
import pathlib
import resource
import signal
import subprocess
import tempfile


def extract_method(source, signature):
    start = source.index(signature)
    begin = source.index('{', start)
    depth, end = 1, begin + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=pathlib.Path)
    parser.add_argument('--expect-crash', action='store_true', help='Reproduce the unpatched Coral overread')
    args = parser.parse_args()
    source = args.source.read_text()
    methods = '\n\n'.join(extract_method(source, signature) for signature in (
        'int GUISliderValue::SetRenderPos(', 'int GUISliderValue::Render('
    ))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    harness = pathlib.Path(__file__).resolve().parent.parent / 'tests/slider_render_harness.cpp'
    with tempfile.TemporaryDirectory(prefix='coral-slider-') as directory:
        root = pathlib.Path(directory)
        (root / 'slider_methods.inc').write_text(methods)
        binary = root / 'slider-render-test'
        subprocess.run(['g++', '-std=c++17', '-O0', '-g', str(harness),
                        '-I', str(root), '-o', str(binary)], check=True)
        if args.expect_crash:
            result = subprocess.run([str(binary), 'coral'], capture_output=True, text=True)
            if result.returncode != -signal.SIGSEGV:
                raise RuntimeError(f'Original Coral overread did not reproduce: {result.returncode}\n{result.stdout}{result.stderr}')
            print('Reproduced SIGSEGV: 128x152 copy from a guarded 128x128 slider handle')
        else:
            for case in ('coral', 'uniform', 'wide', 'hover', 'left_edge', 'fallback'):
                subprocess.run([str(binary), case], check=True)


if __name__ == '__main__':
    main()
