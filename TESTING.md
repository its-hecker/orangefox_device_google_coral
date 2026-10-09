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

Build artifacts are uploaded only after header-v2, image-size, kernel, ramdisk,
DTB and truncation checks pass. The decryption packaging check also requires
startup of both Qualcomm Keymaster 4.0/default and Citadel 4.1/strongbox, and
the 64-bit QTI Gatekeeper implementation under `/system/lib64/hw`.
These checks cannot establish runtime safety, bootability, hardware-service
registration or Android 17 compatibility.
