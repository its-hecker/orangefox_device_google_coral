# Recovery source patches

`0001-fit-slider-handles-to-scaled-images.patch` applies to
`gui/slidervalue.cpp` in OrangeFox Recovery `fox_12.1`, tested at
`cbcc4f713dbef98d76d6d2cfd019b1ebfd9418e9`.

Coral's 1440x3040 screen scales the 1080x1920 theme by 4/3 horizontally and
19/12 vertically. The 96x96 handle SVG has `retainaspect`, so its loaded
surface is 128x128. The XML slider dimensions independently become 128x152.
The original renderer copies that larger rectangle without resizing, reading
past the image buffer. The Screen settings page and console both contain
these sliders, matching the pages opened before the three SIGSEGV/restart
events in the supplied logs. This makes the overread a plausible cause, but
those crashes have no backtrace confirming it. The tester subsequently
identified the phone as Flame, while the logs report Coral and 1440x3040;
the patch fixes the reproduced overread independently of that discrepancy.

The patch uses the loaded handle's dimensions for slider layout and the
selected normal/hover image's dimensions for each blit. Hover images remain
centered on the same track position. Sliders without images retain their XML
dimensions. The original source's copyright and GPL notices remain intact.

The build checks patch applicability before applying it, then compiles the
actual patched `SetRenderPos` and `Render` methods into a host harness. Image
buffers end at a protected memory page. Tests cover Coral's aspect mismatch,
uniform scaling, a wide screen, a larger hover image, a negative destination
coordinate, and an image-free slider. The unpatched Coral case reproduces
SIGSEGV; the patched cases pass. This test does not replace Android/device
testing.

`0002-read-system-properties-from-both-layouts.patch` applies to
`crypto/system/bin/prepdecrypt.sh` in TeamWin/android_device_qcom_twrp-common,
tested at `98506f7919102378c8d52ee7d6a94a867f1b4c55`. The Android 12.1 build
SDK selects `system/build.prop`, but newer system filesystems can put
`build.prop` at their root. The patch accepts either path after the temporary
read-only mount. If neither exists it uses the script's existing error cleanup
and signals `crypto.ready`, allowing startup to complete with a logged error.

Coral init separately enables the upstream `prepdecrypt.setpatch` override
before decryption services start, including temporary fastboot boots. The host
test runs the actual script with isolated property and mount substitutes,
verifies the OS/system/vendor values before `crypto.ready`, and verifies
cleanup. It does not exercise Keymaster, metadata keys or PIN decryption.

`0003-show-coral-maintainer-support.patch` updates the portrait About page to
show `Hecker (Maintainer)` with `Channel: t.me/pixel4seriesupdates` beneath it.
The build installs `theme/maintainer.png`, the maintainer's selected circular
cat avatar, in the existing 192x192 About image resource.
`OF_MAINTAINER := Hecker` in `twrp.mk` sets that name; the older
`FOX_MAINTAINER` environment variable does not set this About field. Image
validation checks the executable, packaged About XML and exact avatar bytes.

`0004-prepare-fresh-data-media.patch` applies to `partition.cpp`,
`partitionmanager.cpp` and `partitions.hpp` at OrangeFox core revision
`cbcc4f713dbef98d76d6d2cfd019b1ebfd9418e9`, now explicitly selected by the
build script. It handles uninitialized userdata before normal FBE setup,
after metadata decryption mounts `/data`, and after a successful Format Data.

The October 17 Coral logs show metadata decryption and the f2fs mount succeed,
but `/data/media` is absent, `/sdcard` is not bind mounted, and USB is in ADB
mode. The tester confirmed file transfers after manually creating
`/data/media` with media_rw ownership, binding it to `/sdcard`, and enabling
MTP. This validates the workaround for that session; the compiled fix still
requires device testing.

The helper accepts only a writable mounted ext4/f2fs userdata filesystem whose
root contains directories named `lost+found`, `recovery`, or `media`, or is
empty. Any other entry, including FBE key/user directories, rejects the helper.
Symlink entries, an existing `media/0`, and a media directory with an encryption
policy also reject it. Mount, inspection, labeling and bind failures do not
mark storage unlocked. Existing encrypted installations use the original
decryption flow. This deliberately conservative check can decline a partially
initialized or unfamiliar layout; it does not attempt to repair those layouts.

For accepted layouts, recovery creates only `/data/media`, applies its label
when file_contexts is available, sets 1023:1023 and mode 0770, binds `/sdcard`,
and updates recovery's storage state. It retains the metadata mapping and
fstab encryption configuration. It neither creates `media/0` nor changes any
fscrypt policy, key blob, ROM property or forced-encryption setting. Android
must initialize its FBE users. MTP uses the normal server and preference;
an already running server receives the refreshed storage entry.

The host test compiles the actual patched helper, `Decrypt_Data` and
`Format_Data`, using a temporary directory tree and substituted mount, metadata,
SELinux and MTP operations. It checks direct and metadata-assisted startup,
same-session formatting, retained staged files, ext4/f2fs, existing key/user
layouts, symlinks, read-only/tmpfs mounts, and inspection/bind failures. The
image validator also requires the compiled fix's log marker in the packaged
recovery executable. These checks do not exercise real fscrypt, F2FS mounts,
USB enumeration, device PIN unlocking or the subsequent Android first boot.
