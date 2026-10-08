#!/usr/bin/env bash
set -eo pipefail
port_root=$(cd "$(dirname "$0")/.." && pwd)
build_root=${1:?Usage: build.sh ABSOLUTE_BUILD_DIRECTORY}
[[ "$build_root" = /* ]] || { echo 'Use an absolute build directory'; exit 1; }
mkdir -p "$build_root" "$port_root/logs" "$port_root/artifacts"
exec > >(tee -a "$port_root/logs/session.log") 2>&1
set -E
trap 'status=$?; echo "ERROR: line $LINENO: $BASH_COMMAND (exit $status)" >&2' ERR
git clone https://gitlab.com/OrangeFox/sync.git "$build_root/sync-tools"
git -C "$build_root/sync-tools" checkout 53a303ecfb622c516082d3e61dbaa7d9f02f0120
# The upstream tool resolves its bundled patches relative to its working directory.
(
    cd "$build_root/sync-tools"
    test -f patches/patch-manifest-fox_12.1.diff
    # The pinned upstream script looks for this patch one directory too high.
    ln -s patches/patch-vendor-twrp-fox_12.1.diff patch-vendor-twrp-fox_12.1.diff
    ./orangefox_sync.sh --branch 12.1 --path "$build_root/android"
) 2>&1 | tee "$port_root/logs/sync.log"
cd "$build_root/android"
mkdir -p device/google/coral
tar -C "$port_root" --exclude=.git --exclude=logs --exclude=artifacts -cf - . | tar -C device/google/coral -xf -
# Resolve the dependencies supplied by the upstream device tree. Avoid implicit
# roomservice branch selection, particularly for the kernel.
python3 - <<'PY'
import json, pathlib, xml.etree.ElementTree as ET
root = ET.Element('manifest')
ET.SubElement(root, 'remote', name='coral-aosp', fetch='https://android.googlesource.com/')
ET.SubElement(root, 'remote', name='coral-github', fetch='https://github.com/')
for dep in json.loads(pathlib.Path('device/google/coral/twrp.dependencies').read_text()):
    aosp = dep['remote'] == 'aosp'
    revision = dep.get('branch', '9d2fb45d1fc6e11ac7e03e73c772b69ce158ea0a')
    ET.SubElement(root, 'project', name=dep['repository'] if aosp else 'TeamWin/' + dep['repository'], path=dep['target_path'], remote='coral-aosp' if aosp else 'coral-github', revision=revision)
pathlib.Path('.repo/local_manifests').mkdir(exist_ok=True)
ET.ElementTree(root).write('.repo/local_manifests/coral.xml', encoding='unicode')
PY
# Sync only the newly declared device dependencies. The legacy sync tool
# deliberately replaces repo-managed TWRP with a standalone OrangeFox clone.
# A whole-tree repo sync here would attempt to overwrite that checkout.
mapfile -t dependency_paths < <(python3 -c 'import json; print("\n".join(d["target_path"] for d in json.load(open("device/google/coral/twrp.dependencies"))))')
repo sync -c -j4 --no-clone-bundle --no-tags "${dependency_paths[@]}" 2>&1 | tee "$port_root/logs/dependencies.log"
export FOX_BUILD_DEVICE=coral
source device/google/coral/vendorsetup.sh
# Android envsetup is an interactive shell initializer and uses optional
# probes that return nonzero. Source it without errexit, then check that the
# required build functions exist. Keep strict failure handling for lunch/build.
set +e
trap - ERR
source build/envsetup.sh
setup_status=$?
set -e
trap 'status=$?; echo "ERROR: line $LINENO: $BASH_COMMAND (exit $status)" >&2' ERR
echo "envsetup returned $setup_status; checking build functions"
declare -F lunch >/dev/null
declare -F mka >/dev/null
lunch twrp_coral-eng
mka bootimage -j2 2>&1 | tee "$port_root/logs/build.log"
out=out/target/product/coral
image="$out/boot.img"
test -s "$image"
python3 "$port_root/scripts/validate_image.py" "$image"
cp "$image" "$port_root/artifacts/OrangeFox-unofficial-coral.img"
repo manifest -r -o "$port_root/artifacts/source-manifest.xml"
git -C "$port_root" rev-parse HEAD > "$port_root/artifacts/device-tree-commit.txt"
cd "$port_root/artifacts"
sha256sum OrangeFox-unofficial-coral.img > SHA256SUMS
