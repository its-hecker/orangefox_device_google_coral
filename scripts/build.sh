#!/usr/bin/env bash
set -eo pipefail
port_root=$(cd "$(dirname "$0")/.." && pwd)
build_root=${1:?Usage: build.sh ABSOLUTE_BUILD_DIRECTORY [all|kernel|recovery] [CHECKPOINT_DIRECTORY]}
build_stage=${2:-all}
checkpoint=${3:-$port_root/kernel-checkpoint}
[[ "$build_root" = /* ]] || { echo 'Use an absolute build directory'; exit 1; }
case "$build_stage" in
    all|kernel|recovery) ;;
    *) echo 'Build stage must be all, kernel or recovery'; exit 1 ;;
esac
[[ "$checkpoint" = /* ]] || { echo 'Use an absolute checkpoint directory'; exit 1; }
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
tar -C "$port_root" --exclude=.git --exclude=logs --exclude=artifacts --exclude=kernel-checkpoint --exclude=ci-kernel --exclude=__pycache__ -cf - . | tar -C device/google/coral -xf -
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
# The theme keeps SVG handles square while Coral scales X and Y differently.
# Patch the renderer before either stage records its source identity.
slider_patch="$port_root/patches/0001-fit-slider-handles-to-scaled-images.patch"
git -C bootable/recovery apply --check "$slider_patch"
git -C bootable/recovery apply "$slider_patch"
python3 "$port_root/scripts/test_slider_render.py" "$build_root/android/bootable/recovery/gui/slidervalue.cpp"
if [[ "$build_stage" = recovery ]]; then
    python3 "$port_root/scripts/kernel_checkpoint.py" import "$build_root/android" "$port_root" "$checkpoint"
fi
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
# Use the host CPU count, capped at four jobs for the 16 GiB hosted runner.
build_jobs=${BUILD_JOBS:-$(nproc)}
[[ "$build_jobs" =~ ^[1-9][0-9]*$ ]] || { echo 'BUILD_JOBS must be a positive integer'; exit 1; }
(( build_jobs <= 4 )) || build_jobs=4
export WITH_TIDY=false
resource_monitor() {
    while :; do
        date -u '+%Y-%m-%dT%H:%M:%SZ'
        free -m
        df -h "$build_root"
        # Ninja buffers each task's output until completion. Show kernel progress
        # and resource use while the long kernel task is still running.
        kernel_out="$build_root/android/out/target/product/coral/obj/KERNEL_OBJ"
        if [[ -d "$kernel_out" ]]; then
            echo "Kernel object files: $(find "$kernel_out" -name '*.o' -type f | wc -l)"
        fi
        ps -eo comm,pcpu,pmem --sort=-pcpu | head -n 8 || true
        sleep 60
    done
}
resource_monitor > >(tee "$port_root/logs/resources.log") 2>&1 &
monitor_pid=$!
trap 'kill "$monitor_pid" 2>/dev/null || true' EXIT
echo "Building stage $build_stage with $build_jobs jobs; host CPUs: $(nproc)"
lunch twrp_coral-eng
if [[ "$build_stage" = kernel ]]; then
    # Run separately so the two nested kernel make processes do not compete.
    mka kernel -j"$build_jobs" 2>&1 | tee "$port_root/logs/kernel.log"
    mka dtbimage -j"$build_jobs" 2>&1 | tee "$port_root/logs/dtb.log"
    python3 "$port_root/scripts/kernel_checkpoint.py" export "$build_root/android" "$port_root" "$checkpoint"
    exit 0
fi
mka bootimage -j"$build_jobs" 2>&1 | tee "$port_root/logs/build.log"
out=out/target/product/coral
image="$out/boot.img"
test -s "$image"
if [[ "$build_stage" = recovery ]]; then
    python3 "$port_root/scripts/validate_image.py" "$image" --kernel "$checkpoint/Image.lz4" --dtb "$checkpoint/dtb.img" --keymaster-version "$OF_DEFAULT_KEYMASTER_VERSION"
    cp "$checkpoint/metadata.json" "$port_root/artifacts/kernel-metadata.json"
else
    python3 "$port_root/scripts/validate_image.py" "$image" --keymaster-version "$OF_DEFAULT_KEYMASTER_VERSION"
fi
cp "$image" "$port_root/artifacts/OrangeFox-unofficial-coral.img"
repo manifest -r -o "$port_root/artifacts/source-manifest.xml"
git -C "$port_root" rev-parse HEAD > "$port_root/artifacts/device-tree-commit.txt"
cd "$port_root/artifacts"
sha256sum OrangeFox-unofficial-coral.img > SHA256SUMS
