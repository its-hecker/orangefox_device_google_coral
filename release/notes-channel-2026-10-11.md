Unofficial OrangeFox R12.0 for **Google Pixel 4 XL (coral)**.

The About card now displays **Channel: t.me/pixel4seriesupdates**, replacing
the previous support-group label. **Hecker (Maintainer)** and the cat avatar
are included.

Channel: [Pixel 4 Series Updates](https://t.me/pixel4seriesupdates)
Maintainer: [Hecker (its-hecker)](https://github.com/its-hecker)

This is a theme update to the tested recovery. The recovery program, kernel,
DTB, decryption and battery configuration are preserved. Checks verify the
new channel label, exact avatar, runtime configuration, boot ID and AVB hash.
The About XML is the only ramdisk file changed relative to the previous
avatar release. This specific image still needs a device boot test.

The original compiled recovery and kernel are from commit
`6d3c046d8a33ff4194a1e9f17f835c3786c87767`; `theme-update.json` records the
base image, channel and theme packaging provenance. Kernel metadata,
source manifest and checksums are included.

Temporary boot on **coral**:
```sh
fastboot getvar product
fastboot boot OrangeFox-unofficial-coral.img
```

The [previous avatar release](https://github.com/its-hecker/orangefox_device_google_coral/releases/tag/R12.0-coral-unofficial-20261011-avatar) remains available. Original OrangeFox and TeamWin credits and source notices are preserved.
