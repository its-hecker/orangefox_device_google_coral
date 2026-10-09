# OrangeFox for Google Pixel 4 XL (coral)

Experimental port for Infinity Android 17. Boot, touch, USB, sideload and encrypted-data support have not been validated. A successful build is not confirmation of Android 17 compatibility.

Based on TeamWin/android_device_google_coral, android-12.1 commit b3f760ee3d17805e895c0d6e0387fd59d1f39120. Original copyright and licensing notices are preserved.

CI builds the pinned kernel and DTB bundle first and saves a checkpoint artifact.
A fresh recovery job verifies its checksums and source revisions, then packages
that kernel without compiling it again. If recovery fails, rerun the failed job
to reuse the completed kernel checkpoint. Both jobs stream resource diagnostics
to the Actions log and save detailed logs when the runner remains available.

For a local source build, run `bash scripts/build.sh /absolute/build/directory`.
The optional `kernel` and `recovery` stages use `kernel-checkpoint/` by default.
The image artifact includes checksums, the source manifest and kernel provenance;
the validator checks header v2, the 64 MiB partition limit, and exact checkpoint
kernel and DTB contents. Device testing is described in [TESTING.md](TESTING.md).

The first Infinity device test reached the OrangeFox splash but blocked waiting
for Qualcomm Keymaster 4.0/default. Coral also has Citadel 4.1/strongbox;
the fallback now uses `4.x` to start both services. The ramdisk includes the
QTI Gatekeeper implementation that was missing in that test. CI checks these
startup triggers and packaged libraries before uploading the image. Reaching
the UI and decrypting Android 17 data still require a new device test.
