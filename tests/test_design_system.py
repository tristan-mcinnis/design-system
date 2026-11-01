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
        self.assertIn("public enum House {", a)
        for name in common.load_tokens()["color"]:
            self.assertIn(f"public static let {name} = adaptive(", a)

    def test_swift_declarations_are_public_except_the_adaptive_helpers(self):
        a = run("gen/gen-swift.py")
        for line in a.splitlines():
            stripped = line.strip()
            if stripped.startswith(("enum ", "struct ", "static let ", "let ")):
                self.fail(f"internal declaration in generated module: {stripped}")
        self.assertIn("public struct ShadowSpec: Sendable {", a)
        self.assertEqual(a.count("static func adaptive("), 2)
        self.assertNotIn("public static func adaptive", a)

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


PACKAGE_SWIFT = """// swift-tools-version: 5.10
import PackageDescription
let package = Package(name: "App", dependencies: [
    .package(url: "https://github.com/tristan-mcinnis/design-system", from: "1.0.0"),
    .package(url: "https://github.com/tristan-mcinnis/house-chat-core", from: "1.0.0"),
])
"""
PROJECT_YML = """packages:
  HouseDesign:
    url: https://github.com/tristan-mcinnis/design-system
    from: "1.0.0"
  HouseChatCore:
    url: https://github.com/tristan-mcinnis/house-chat-core
    from: "1.0.0"
  Yams:
    url: https://github.com/jpsim/Yams
    from: "5.1.0"
"""
MANIFESTS = {
    "quick-launch/Package.swift": PACKAGE_SWIFT,
    "rti/RTI/project.yml": PROJECT_YML,
    "cotype/Package.swift": PACKAGE_SWIFT,
    "usage-menubar/Package.swift": PACKAGE_SWIFT,
    "local-models/menubar/LocalModelsBar/Package.swift": PACKAGE_SWIFT,
}


class ConsumerPins(unittest.TestCase):
    """Apps pin the Swift packages by GitHub URL and tag; copies and path
    dependencies fail. The Rust token file is still compared byte for byte."""

    def setUp(self):
        self.house = Path(tempfile.mkdtemp()).resolve()
        for rel, text in MANIFESTS.items():
            path = self.house / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        rust = self.house / "local-dictation/src/menubar/house_theme.rs"
        rust.parent.mkdir(parents=True)
        rust.write_bytes((ROOT / "generated/house_theme.rs").read_bytes())

    def tearDown(self):
        shutil.rmtree(self.house)

    def check(self, *flags):
        env = {k: v for k, v in os.environ.items() if k != "HOUSE_ALLOW_MISSING"}
        return subprocess.run([sys.executable, str(ROOT / "bin/check-consumers"), "--house", str(self.house), *flags],
                              capture_output=True, text=True, env=env)

    def edit(self, rel, old, new):
        path = self.house / rel
        path.write_text(path.read_text().replace(old, new))

    def test_pinned_consumers_are_green(self):
        run = self.check()
        self.assertEqual(run.returncode, 0, run.stdout)
        self.assertIn("pins design-system from 1.0.0", run.stdout)

    def test_relative_path_dependency_is_red(self):
        self.edit("cotype/Package.swift",
                  '.package(url: "https://github.com/tristan-mcinnis/design-system", from: "1.0.0")',
                  '.package(path: "../design-system")')
        run = self.check()
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("UNPINNED", run.stdout)

    def test_branch_pin_is_red(self):
        self.edit("usage-menubar/Package.swift", '.package(url: "https://github.com/tristan-mcinnis/design-system", from: "1.0.0")',
                  '.package(url: "https://github.com/tristan-mcinnis/design-system", branch: "main")')
        run = self.check()
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("without a semver tag requirement", run.stdout)

    def test_missing_pin_in_project_yml_is_red(self):
        self.edit("rti/RTI/project.yml", 'url: https://github.com/tristan-mcinnis/house-chat-core\n    from: "1.0.0"',
                  "path: ../../house-chat-core")
        run = self.check()
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("rti/RTI/project.yml does not depend on house-chat-core", run.stdout)

    def test_copied_source_file_is_red(self):
        copy = self.house / "cotype/Sources/CotypeMenuApp/HouseUI.swift"
        copy.parent.mkdir(parents=True, exist_ok=True)
        copy.write_text("// copy\n")
        run = self.check()
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(f"COPY: {copy}", run.stdout)

    def test_build_directories_are_not_scanned(self):
        built = self.house / "cotype/.build/checkouts/design-system/Sources/HouseDesign/HouseDesign.swift"
        built.parent.mkdir(parents=True)
        built.write_text("// checkout\n")
        self.assertEqual(self.check().returncode, 0)

    def test_rust_drift_is_red(self):
        rust = self.house / "local-dictation/src/menubar/house_theme.rs"
        rust.write_text(rust.read_text() + "\n// local tweak\n")
        run = self.check()
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(f"DRIFT: {rust}", run.stdout)

    def test_absent_consumer_fails_unless_allowed(self):
        shutil.rmtree(self.house / "quick-launch")
        self.assertNotEqual(self.check().returncode, 0)
        self.assertEqual(self.check("--allow-missing").returncode, 0)


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
