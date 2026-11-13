#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Host contract tests for the limited Hecker Recovery OrangeFox theme patch."""
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).parent))
from hecker_recovery_theme import apply, plan, transform, ROOT, CARACAL, SNIPPETS

XML_FIXTURES = {
    "splash.xml": """<recovery><resources><image name="splash_logo" filename="SVG/Logos/logo_o.svg"/></resources><pages><page name="splash"><text>OrangeFox</text><text>Recovery</text></page></pages></recovery>""",
    "themes/accent.xml": """<recovery><resources><image tint="#ed6f02"/><image tint="#ed6f02"/></resources><variables><variable name="theme_accent_dark" value="#D86100"/></variables></recovery>""",
    "pages/main.xml": """<recovery><pages><page name="main"><action function="page">navbar</action></page><page name="welcome"><text>{@welcome_msg}</text><text>{@welcome_msg2}</text></page></pages></recovery>""",
    "pages/settings.xml": """<recovery><pages><page name="settings"><text>%of_maintainer% (Maintainer)</text><action function="page">files</action></page></pages></recovery>""",
    "pages/recovery.xml": """<recovery><pages><page name="main"><text>Install OrangeFox recovery</text></page></pages></recovery>""",
}


class HeckerRecoveryThemeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "bootable/recovery"
        self.root.mkdir(parents=True)
        for relative, xml in XML_FIXTURES.items():
            path = self.root / ROOT / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(xml, encoding="utf-8")
        self.png = Path(self.tmp.name) / "caracal.png"
        # A tiny deterministic PNG fixture: only its header/dimensions are used.
        self.png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\0" * 8 +
                             struct.pack(">II", 256, 160) + b"\0" * 300)

    def test_guarded_apply_idempotence_and_revert(self):
        expected = len(XML_FIXTURES) + 1
        self.assertEqual(len(plan(self.root, self.png)), expected)
        self.assertEqual(len(apply(self.root, self.png)), expected)
        self.assertEqual(apply(self.root, self.png), {})
        for relative, xml in XML_FIXTURES.items():
            generated = (self.root / ROOT / relative).read_text()
            ET.fromstring(generated)
            self.assertNotEqual(generated, xml)
            if relative == "pages/main.xml":
                self.assertIn('function="page">navbar', generated)
        self.assertEqual((self.root / CARACAL).read_bytes(), self.png.read_bytes())
        self.assertEqual(len(apply(self.root, self.png, revert=True)), len(XML_FIXTURES))
        for relative, xml in XML_FIXTURES.items():
            self.assertEqual((self.root / ROOT / relative).read_text(), xml)
        self.assertEqual(apply(self.root, self.png, revert=True), {})

    def test_unknown_upstream_refused_before_any_write(self):
        path = self.root / ROOT / "splash.xml"
        path.write_text(path.read_text().replace("OrangeFox", "UnexpectedLogo"))
        before = {r: (self.root / ROOT / r).read_bytes() for r in XML_FIXTURES}
        with self.assertRaisesRegex(ValueError, "Unrecognized"):
            apply(self.root, self.png)
        for relative, value in before.items():
            self.assertEqual((self.root / ROOT / relative).read_bytes(), value)
        self.assertFalse((self.root / CARACAL).exists())

    def test_duplicate_anchor_rejected(self):
        with self.assertRaisesRegex(ValueError, "repeated"):
            transform("<recovery><text>OrangeFox</text><text>OrangeFox</text>" +
                      '<image filename="SVG/Logos/logo_o.svg"/></recovery>', "splash.xml")

    def test_preserve_backend_and_no_destructive_automatic_actions(self):
        for relative, content in XML_FIXTURES.items():
            before = ET.fromstring(content)
            after = ET.fromstring(transform(content, relative))
            original_actions = [(n.get("function"), n.text) for n in before.iter("action")]
            patched_actions = [(n.get("function"), n.text) for n in after.iter("action")]
            self.assertEqual(original_actions, patched_actions)
        for relative in SNIPPETS:
            self.assertFalse(relative.startswith("partition"))
            self.assertFalse(relative.startswith("install/"))


if __name__ == "__main__":
    unittest.main()
