# Pixel 4 XL bring-up

This is an experimental recovery, not an Android 17 validated release. The
12.1 build platform does not establish which ROM encryption schemes it supports.
Infinity's current boot image, kernel, fstab and encryption configuration are
required to assess Android 17 support. No automatic data format, encryption
disable, AVB disable or permanent recovery installation is provided.

The October 9 test of device-tree commit `a56060a` was subsequently reported
as a Pixel 4 (flame) boot of the Coral image, with Files, touch, ADB and MTP
working. It does not confirm those features on Coral. The supplied logs identify
`androidboot.hardware=coral` and a 1440x3040 framebuffer, so their association
with the reported Flame test needs confirmation. They record three
recovery-process SIGSEGVs: one after opening Screen settings and two after
opening the console. Metadata decryption also failed; the Files page opening
does not establish access to encrypted data. Retest on Coral with the slider
fix, including Screen settings, the console, slider dragging and returning to
Files, then collect the same three logs if a restart occurs.

On October 10 the tester confirmed the latest test is on a Pixel 4 XL and
provided a photograph of the Files UI. The status bar has a battery icon and
percent sign but no value. The Health service is included but was only started
when entering fastbootd. The next build starts `health-hal-2-1` on normal boot.
The tester also reports that storage remains encrypted and OrangeFox does not
ask for a password despite the installed OS having a screen lock. The supplied
logs fail at metadata-key use before credential-protected file unlocking;
the missing prompt is consistent with that failure. Decryption remains failed
in this test and is separate from the Health service startup fix.

The same tester subsequently ran `adb shell start health-hal-2-1`, restoring a
51% reading and charging indicator. Fresh logs show successful Health 2.1
registration. They contain one recovery-process startup and no fatal recovery
signal, including a visit to Screen settings; the console was not opened in
this capture. This validates manual Health startup, not the new automatic
startup trigger or complete UI stability.

The fresh logs still fail metadata-key use with `KEY_REQUIRES_UPGRADE (-62)`
followed by `INVALID_ARGUMENT (-38)` during upgrade. The ROM is detected as
Android 17, while recovery reports Android 12 and the placeholder patch date
2127-12-31. The tested image's boot header also contains Android 12 and a
December 2127 patch level. `prepdecrypt` reports `SETPATCH=false`. The installed
properties supplied afterwards confirm Android 17, system patch 2026-09-01
and vendor patch 2022-10-05. Infinity's Coral source also sets the boot firmware
patch to 2022-10-05. The next image enables ROM property updates on init even
for temporary boot, before QSEE/Keymaster start, and accepts both system image
property layouts. It replaces the future patch dates and encodes Android 17 /
September 2026 in the legacy boot header, with the separate AVB boot firmware
patch at 2022-10-05. No encryption key blobs are edited by this configuration
change. A device retest is required to determine whether this resolves the
metadata-key failure or exposes another Android 17 compatibility issue.

Only test on **coral** with an unlocked bootloader. Confirm the product with
`fastboot getvar product`. Preserve the exact Infinity boot image and a data
backup before testing. Coral uses recovery in boot, not a separate recovery
partition. Do not run `fastboot flash recovery`.

After a successful build, verify the downloaded image against SHA256SUMS.
The first test is temporary boot: `fastboot boot OrangeFox-unofficial-coral.img`.
Do not flash the image to either boot slot during initial bring-up. Temporary
boot avoids replacing the ROM boot image, but recovery operations can still
modify data. Exit by rebooting without installing or formatting anything.

Record boot/display/touch, USB ADB, MTP, battery reporting, read-only partition
mounting, reboot targets and fastbootd separately. Encrypted-data support is
unverified; don't format data to work around a decryption failure. Sideload
installation and A/B OTA behavior require separate testing with the ROM's
supported packages after basic bring-up succeeds.

Collect `adb pull /tmp/recovery.log`, `adb logcat -d > logcat.txt` and
`adb shell dmesg > dmesg.txt` when available. Include the source-manifest.xml,
device-tree commit, ROM build, the product reported by `fastboot getvar product`,
and exact test result when reporting failures.

## Device checks in recovery

1. Open Screen settings, move the brightness slider, return to Files, then open
   and close the console several times. Leave recovery idle for five minutes
   and note any restart or freeze.
2. If a decrypt prompt appears, enter the device's PIN/password on the phone.
   Browse `/sdcard/Download` or `/data/media/0/Download` and confirm existing,
   recognizable filenames. Read one small existing file through MTP or with
   `adb pull /sdcard/Download/NAME`. A `/data` directory, an empty folder or
   storage capacity alone does not prove decryption. Do not format data.
3. Check battery capacity and charging status, then connect/disconnect a
   charger and compare the status bar after a few seconds:

   ```sh
   adb shell cat /sys/class/power_supply/battery/capacity
   adb shell cat /sys/class/power_supply/battery/status
   adb shell getprop init.svc.health-hal-2-1
   ```

   On the previous build, `adb shell start health-hal-2-1` starts the packaged
   service for this boot. If the percentage appears, that confirms the missing
   normal startup trigger. If it stays blank or the service restarts, collect
   logs rather than changing the theme or battery values.
4. Read the active mounts with `adb shell cat /proc/mounts`. Check that the
   `/data` mount is present when testing storage; successful sysfs battery
   reads do not depend on `/data` decryption.
   After booting the version-metadata fix, record:

   ```sh
   adb shell getprop prepdecrypt.setpatch
   adb shell getprop ro.build.version.release
   adb shell getprop ro.build.version.security_patch
   adb shell getprop ro.vendor.build.security_patch
   ```

   Expected values for the supplied Infinity build are `true`, `17`,
   `2026-09-01`, and `2022-10-05`. Recovery's build SDK remains 32; it is not
   changed to the ROM's SDK 37. These property checks alone do not prove data
   decryption; confirm the PIN prompt and existing files as described above.
5. After a restart, blank battery reading or storage failure, collect the
   three logs above and report the exact image/build tested. Once these checks
   pass, USB OTG and ROM installation can be tested separately with compatible
   packages.

For the current metadata-decryption failure, use the ROM property copies saved
by the OrangeFox startup script. It mounts system/vendor read-only while reading
ROM information, caches the files under `/FFiles/temp`, and unmounts its
temporary mounts. The original paths may therefore be unavailable afterwards.
These copies do not require access to user files or key blobs:

```sh
adb pull /FFiles/temp/system_build_prop system-build.prop
adb pull /FFiles/temp/vendor_build_prop vendor-build.prop
```

If a copy is absent, collect `adb shell ls -l /FFiles/temp` so its presence can
be checked before attempting another path.

Build artifacts are uploaded only after header-v2, image-size, kernel, ramdisk,
DTB and truncation checks pass. The decryption packaging check also requires
startup of both Qualcomm Keymaster 4.0/default and Citadel 4.1/strongbox, and
the 64-bit QTI Gatekeeper implementation under `/system/lib64/hw`.
It also checks normal-boot startup of Health 2.1/default and its packaged
binary, implementation and VINTF declaration.
It requires `prepdecrypt.setpatch=true` on init, the property-updating script
and resetprop, and checks the boot header OS/system patch and AVB boot firmware
patch against the build settings. Host tests exercise the actual prepdecrypt
script with fake mounts/properties in both system layouts and the temporary
fastboot path, including a missing-property-file failure.
These checks cannot establish runtime safety, bootability, hardware-service
registration or Android 17 compatibility.
