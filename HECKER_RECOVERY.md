# Hecker Recovery 2.0 — Pixel 4 XL (coral)

Experimental full-featured custom recovery built on the existing, tested Coral
OrangeFox/TWRP port. Author/maintainer: **Hecker**. OrangeFox, TeamWin, AOSP
and original contributors retain their upstream copyrights and licenses.

## Source and November compatibility

- Base branch: `fix/november-asb-20261112` at `06c8ac5543fa5f50bbe18078e64cdbb68abe9900`.
- HeckerOS compatibility metadata: Android 17, **2026-11-01** system patch level.
- Pixel 4 XL boot firmware AVB patch stays **2022-10-05**.
- Underlying recovery build remains Android **12.1** based; November metadata
  is NOT a claim that this recovery has been patched to the November Android ASB.
- Preserved features: OrangeFox touch pages, installation, sideload, file manager,
  backups, A/B/dynamic-partition tooling, fastbootd, MTP, logs, and PIN/decryption
  support where it works with the installed ROM.
- Preserved Coral fixes: Keymaster 4.0 + Citadel 4.1, FBE property bridging, QTI
  Gatekeeper, battery Health HAL, slider bounds, and fresh-data storage safeguards.

## Customization implemented in this branch

- Black splash with original **HeckerOS caracal** asset from the HeckerOS
  recovery art (not the OrangeFox logo).
- Blue recovery UI accent in the native recovery theme, including controls,
  radio buttons, checkboxes and sliders; no change to recovery's event engine.
- HeckerOS/Recovery splash lettering, “Hecker Recovery 2.0” welcome and About
  maintainer label, and an updated unsupported-theme message.
- Separate experimental boot image filename `HeckerRecovery-2.0-coral.img`.
- Fail-closed theme adapter that checks exact upstream UI anchors, parses every
  resulting XML file and refuses unknown changes before editing any source.
- A packaging validator that checks the actual boot image for the branded
  splash, caracal PNG checksum, native navigation pages, and blue accent.
- Existing kernel/DTB/boot header, AVB metadata, runtime and decryption packaging
  checks are retained unchanged.

## Build

The existing build workflow uses its pinned OrangeFox 12.1 source/patches:

```bash
git clone -b feat/hecker-recovery-2.0 https://github.com/its-hecker/orangefox_device_google_coral.git
cd orangefox_device_google_coral
python3 -m unittest discover -s scripts -p test_hecker_theme.py -v
bash scripts/build.sh /absolute/path/to/hecker-recovery-build
```

Find the structurally checked image under `artifacts/`, along with SHA256SUMS
and the source manifest. CI uses separate kernel and recovery stages.

## Safe validation and ROM integration

**This is currently a standalone, experimental recovery.** It does **not**
replace the HeckerOS ROM's default AOSP recovery or change `cnb_latest_stable`.
Coral has recovery-as-boot, so dropping this standalone OrangeFox `boot.img`
into a ROM ZIP is NOT a valid integration method. Native HeckerOS ROM
integration requires a separately reviewed dual-mode boot ramdisk strategy,
compatible Android 17 init/service configuration, matched kernel and boot AVB
properties, and full OTA/normal-boot tests.

For first device testing, verify the image's checksum and the device is coral.
Use only a temporary recovery boot on a device with an unlocked bootloader;
keep a backup of the original boot image. Do not format data to test the UI.
Check display/touch, PIN unlock and recognizable existing files, ADB/MTP,
battery, the console, USB OTG and reboot. Existing decryption tests were on
specific installations; a newly built Hecker Recovery image is not yet device
validated. Do not flash it to a boot slot or ship it as the default ROM recovery
before both recovery and normal Android boot are confirmed.

### Regression checks

```bash
python3 -m unittest discover -s scripts -p test_hecker_theme.py -v
python3 scripts/hecker_recovery_theme.py /path/to/bootable/recovery theme/caracal.png --check
```

The image validator also checks the packaged dark/blue theme and caracal, in
addition to all existing OrangeFox image/decryption safety checks.


## Android 17 kernel parity (experimental, separate from ROM shipping)

The Recovery 2.0 branch can now build the *standalone* OrangeFox recovery
using the exact kernel and DTB embedded in a **current Coral HeckerOS 17
boot.img**, rather than relying on the older independently built kernel.

Run on a development machine with sufficient space for the OrangeFox 12.1 tree:

```bash
export HECKER_A17_ROM_BOOT=/absolute/path/to/current-heckeros-coral-boot.img
bash scripts/build.sh /absolute/path/to/clean-recovery-build recovery
```

The source boot must have Android 17 metadata, a v2 boot header, 4096-byte
pages and an LZ4 kernel. The staging script fails closed on invalid metadata,
truncation, or preexisting staging outputs. The recovery validator then checks
that the resulting standalone image includes the *exact* ROM kernel and DTB.
Consequently any KernelSU code already embedded in that kernel is retained
at the binary level; runtime compatibility still requires on-device testing.

This does **not** create an Android 17 normal/recovery dual-mode ramdisk.
The OrangeFox userspace still comes from its independently built Android
12.1 recovery tree. The experimental standalone image MUST NOT replace the
ROM boot image or be copied into the ROM OTA payload. No automatic ROM shipping
is enabled by this option. A successful build is not proof of bootability.

Required remaining gates: real-device standalone recovery boot and decryption;
Android 17 recovery service and SELinux adaptation; audited dual-mode ramdisk;
normal Android boot; KernelSU startup; both A/B slots; OTA and rollback.
