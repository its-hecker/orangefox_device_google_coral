import tempfile
import unittest
import struct
from pathlib import Path
from stage_a17_rom_kernel import stage


def boot(major=17, version=2, kernel=b"\x02\x21\x4c\x18TEST", dtb=b"DTB!"):
    page = 4096
    ramdisk = b"\x1f\x8btest"
    packed = major << 25 | (26 << 4 | 11)
    header = bytearray(page)
    header[:8] = b"ANDROID!"
    struct.pack_into("<I", header, 8, len(kernel))
    struct.pack_into("<I", header, 16, len(ramdisk))
    struct.pack_into("<II", header, 36, page, version)
    struct.pack_into("<I", header, 44, packed)
    struct.pack_into("<I", header, 1648, len(dtb))
    align = lambda b: b + b"\0" * ((-len(b)) % page)
    return bytes(header) + align(kernel) + align(ramdisk) + dtb


class A17KernelStagingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.image = self.root / "boot.img"
        self.device = self.root / "device"
        self.device.mkdir()

    def test_exact_rom_kernel_and_dtb_are_staged(self):
        self.image.write_bytes(boot())
        report = stage(self.image, self.device)
        self.assertEqual((self.device / "ci-kernel/Image.lz4").read_bytes(), b"\x02\x21\x4c\x18TEST")
        self.assertEqual((self.device / "ci-kernel/dtb/coral.dtb").read_bytes(), b"DTB!")
        self.assertFalse(report["safe_to_ship_in_rom_ota"])

    def test_wrong_android_version_is_rejected(self):
        self.image.write_bytes(boot(major=12))
        with self.assertRaises(ValueError):
            stage(self.image, self.device)

    def test_existing_staging_cannot_be_overwritten(self):
        self.image.write_bytes(boot())
        stage(self.image, self.device)
        with self.assertRaises(ValueError):
            stage(self.image, self.device)

    def test_truncated_boot_is_rejected(self):
        self.image.write_bytes(boot()[:-2])
        with self.assertRaises(ValueError):
            stage(self.image, self.device)

    def test_wrong_kernel_compression_is_rejected(self):
        self.image.write_bytes(boot(kernel=b"not lz4"))
        with self.assertRaises(ValueError):
            stage(self.image, self.device)


if __name__ == "__main__":
    unittest.main()
