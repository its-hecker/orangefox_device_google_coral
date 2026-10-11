Unofficial OrangeFox R12.0 for **Google Pixel 4 XL (coral)**.

The About card now reads **Hecker (Maintainer)** and uses the selected cat
profile picture. The Pixel 4 Series support link remains underneath.

Maintainer: [Hecker (its-hecker)](https://github.com/its-hecker)
Support: [Pixel 4 Series](https://t.me/pixel4seriesofficial)

This image packages two theme assets into the [previous maintainer image](https://github.com/its-hecker/orangefox_device_google_coral/releases/tag/R12.0-coral-unofficial-20261011), which the tester confirmed boots and displays Hecker. Its base image SHA256 is `31d542c1f26750c6fcbfb529ad5465e97339e44363dd6962ab44dc807ec30cab`; the compiled recovery and kernel came from source commit `6d3c046d8a33ff4194a1e9f17f835c3786c87767`.

Packaging checks require the kernel, DTB, every other ramdisk payload and all
entry permissions/owners to remain identical. The boot ID and AVB hash footer
are regenerated with the source build's original AVB properties. Runtime,
boot-header, maintainer-label and exact-avatar checks also passed.

`theme-update.json` records the base and packaging provenance.
`device-tree-commit.txt` identifies the theme packaging source; the original
kernel provenance and pinned Android source manifest are included. This
specific repackaged image still needs a device boot test.

Temporary boot on **coral**:
```sh
fastboot getvar product
fastboot boot OrangeFox-unofficial-coral.img
```

The previous release remains available. Original OrangeFox and TeamWin credits
and source notices are preserved.
