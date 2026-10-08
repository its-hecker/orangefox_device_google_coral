# Pixel 4 XL bring-up

This is an experimental recovery, not an Android 17 validated release. The
12.1 build platform does not establish which ROM encryption schemes it supports.
Infinity's current boot image, kernel, fstab and encryption configuration are
required to assess Android 17 support. No automatic data format, encryption
disable, AVB disable or permanent recovery installation is provided.

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
device-tree commit, ROM build and exact test result when reporting failures.

Build artifacts are uploaded only after header-v2, image-size, kernel, ramdisk,
DTB and truncation checks pass. These checks cannot establish runtime safety,
bootability, correct ramdisk contents, or Android 17 compatibility.
