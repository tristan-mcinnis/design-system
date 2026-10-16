"""Generators are deterministic; icons build for every glyph."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "gen"))
import common  # noqa: E402


def run(*args):
    return subprocess.run([sys.executable, *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout


class Generators(unittest.TestCase):
    def test_swift_deterministic_and_headed(self):
        a, b = run("gen/gen-swift.py"), run("gen/gen-swift.py")
        self.assertEqual(a, b)
        self.assertTrue(a.startswith(f"// GENERATED from design-system/tokens.json {common.tokens_sha()}; do not edit"))
        self.assertIn("enum House {", a)
        for name in common.load_tokens()["color"]:
            self.assertIn(f"static let {name} = adaptive(", a)

    def test_swift_compiles_for_appkit_and_uikit(self):
        """One generated file serves macOS (NSColor) and iOS (UIColor)."""
        a = run("gen/gen-swift.py")
        for needle in ("#if canImport(AppKit)", "enum NSColorToken", "Color(nsColor:",
                       "#elseif canImport(UIKit)", "enum UIColorToken", "Color(uiColor:"):
            self.assertIn(needle, a)
        self.assertNotIn("import AppKit\nimport SwiftUI", a)

    def test_rust_deterministic_and_headed(self):
        a, b = run("gen/gen-rust.py"), run("gen/gen-rust.py")
        self.assertEqual(a, b)
        self.assertTrue(a.startswith(f"// GENERATED from design-system/tokens.json {common.tokens_sha()}; do not edit"))
        self.assertIn("pub const fn theme() -> Theme", a)
        self.assertIn("pub const LIGHT: Palette", a)
        self.assertIn("pub const DARK: Palette", a)

    def test_new_roles_are_emitted(self):
        swift, rust = run("gen/gen-swift.py"), run("gen/gen-rust.py")
        for needle in ("enum Shadow", "static let panelFar", "enum Material", "enum Layout", "static let panelWidth",
                       "enum Tracking", "static let section", "enum LineHeight"):
            self.assertIn(needle, swift)
        for needle in ("pub const SHADOW_PANEL_FAR", "pub const MATERIAL_BLUR", "pub const LAYOUT_PANEL_WIDTH",
                       "pub const TRACKING_SECTION", "pub divider: Rgba", "pub well: Rgba"):
            self.assertIn(needle, rust)

    def test_semantic_names_only(self):
        banned = {"black", "white", "blue", "red", "green", "grey", "gray", "amber"}
        for name in common.load_tokens()["color"]:
            self.assertFalse(any(b in name.lower() for b in banned), name)


def luminance(rgb):
    def ch(c):
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(c) for c in rgb[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def blend(fg, bg):
    """Composite an rgba foreground over an opaque background."""
    a = fg[3] if len(fg) > 3 else 1.0
    return [fg[i] * a + bg[i] * (1 - a) for i in range(3)]


def contrast(a, b):
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


class Contrast(unittest.TestCase):
    def test_text_tiers_clear_4_5_on_surface(self):
        c = common.load_tokens()["color"]
        for mode in ("light", "dark"):
            for tier in ("textPrimary", "textSecondary", "textTertiary", "accent"):
                ratio = contrast(blend(c[tier][mode], c["surface"][mode]), c["surface"][mode])
                floor = 3.0 if tier == "textTertiary" else 4.5
                self.assertGreaterEqual(ratio, floor, f"{tier} {mode}: {ratio:.2f}")
        self.assertGreaterEqual(contrast(c["hudText"]["light"], c["hudFill"]["light"]), 4.5)


class Kit(unittest.TestCase):
    """The hand-written menu-bar kit is copied byte for byte; drift fails."""

    FILES = ("HouseUI.swift", "MenuBarPanel.swift")
    APPS = (
        "cotype/Sources/CotypeMenuApp",
        "memory-menubar/Sources/MemoryBar",
        "usage-menubar/Sources/UsageBar",
        "local-models/menubar/LocalModelsBar/Sources/LocalModelsBar",
    )

    def make(self, house, *targets):
        env = {**os.environ, "HOUSE_ALLOW_MISSING": "1"}
        return subprocess.run(["make", "--no-print-directory", f"HOUSE={house}", *targets],
                              cwd=ROOT, capture_output=True, text=True, env=env)

    def test_kit_files_say_where_they_come_from(self):
        for name in self.FILES:
            head = (ROOT / "kit" / name).read_text().splitlines()[0]
            self.assertTrue(head.startswith("// SHARED KIT, DO NOT EDIT. Source: design-system/kit/"), name)

    def test_sync_then_check_is_green_and_drift_is_red(self):
        house = Path(tempfile.mkdtemp())
        try:
            for app in self.APPS:
                (house / app).mkdir(parents=True)
            synced = self.make(house, "sync-kit")
            self.assertEqual(synced.returncode, 0, synced.stderr)
            green = self.make(house, "check-consumers")
            self.assertEqual(green.returncode, 0, green.stdout)
            for app in self.APPS:
                for name in self.FILES:
                    self.assertEqual((house / app / name).read_bytes(), (ROOT / "kit" / name).read_bytes())
            drifted = house / self.APPS[2] / "MenuBarPanel.swift"
            drifted.write_text(drifted.read_text() + "\n// local tweak\n")
            red = self.make(house, "check-consumers")
            self.assertNotEqual(red.returncode, 0)
            self.assertIn(f"DRIFT: {drifted}", red.stdout)
        finally:
            shutil.rmtree(house)


def glyph_names():
    """Every glyph make-icon.py offers, so a new glyph is tested with no edit here."""
    import importlib.machinery
    import importlib.util
    loader = importlib.machinery.SourceFileLoader("make_icon", str(ROOT / "icons" / "make-icon.py"))
    mod = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
    loader.exec_module(mod)
    return sorted(mod.GLYPHS)


class Icons(unittest.TestCase):
    def test_every_glyph_renders(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            for glyph in glyph_names():
                run("icons/make-icon.py", "--glyph", glyph, "--png", str(tmp / f"{glyph}.png"), "--iconset", str(tmp / f"{glyph}.iconset"))
                self.assertTrue((tmp / f"{glyph}.png").stat().st_size > 500)
                self.assertEqual(len(list((tmp / f"{glyph}.iconset").glob("*.png"))), 10)
            if shutil.which("iconutil"):
                run("icons/make-icon.py", "--glyph", "bolt", "--out", str(tmp / "bolt.icns"))
                self.assertTrue((tmp / "bolt.icns").stat().st_size > 1000)
        finally:
            shutil.rmtree(tmp)


if __name__ == "__main__":
    unittest.main()
