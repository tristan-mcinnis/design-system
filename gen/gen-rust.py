#!/usr/bin/env python3
"""Emit house_theme.rs from tokens.json.

    python3 gen/gen-rust.py [--out path]   (default: stdout)

Output: `Rgba` value type, `Palette` struct (one field per colour token),
`LIGHT` / `DARK` consts, `theme()` returning `Theme { light, dark }`, numeric
consts for type / radius / spacing / control / motion, and an objc2-compatible
`Rgba::ns_color()` factory on macOS. Deterministic.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import fmt, header, load_tokens, rgba01  # noqa: E402


def snake(name):
    out = []
    for ch in name:
        if ch.isupper():
            out.append("_" + ch.lower())
        else:
            out.append(ch)
    return "".join(out)


def rgba(v):
    r, g, b, a = rgba01(v)
    return f"Rgba {{ r: {fmt(r)}, g: {fmt(g)}, b: {fmt(b)}, a: {fmt(a)} }}"


def render(t):
    o = [header("//"), "// Source of truth: the design-system repo (DESIGN.md + tokens.json).\n",
         "// Regenerate with `make rust` there; `make check` verifies this copy.\n",
         "#![allow(dead_code)]\n\n",
         "/// sRGB colour, components in 0.0..=1.0.\n",
         "#[derive(Clone, Copy, Debug, PartialEq)]\n",
         "pub struct Rgba {\n    pub r: f64,\n    pub g: f64,\n    pub b: f64,\n    pub a: f64,\n}\n\n",
         "#[cfg(target_os = \"macos\")]\nimpl Rgba {\n",
         "    /// AppKit colour for this value (objc2-app-kit).\n",
         "    pub fn ns_color(&self) -> objc2::rc::Retained<objc2_app_kit::NSColor> {\n",
         "        objc2_app_kit::NSColor::colorWithSRGBRed_green_blue_alpha(self.r, self.g, self.b, self.a)\n",
         "    }\n}\n\n",
         "/// One colour per semantic token.\n",
         "#[derive(Clone, Copy, Debug, PartialEq)]\npub struct Palette {\n"]
    for name, spec in t["color"].items():
        o.append(f"    /// {spec['doc']}\n    pub {snake(name)}: Rgba,\n")
    o.append("}\n\n")
    for mode in ("light", "dark"):
        o.append(f"pub const {mode.upper()}: Palette = Palette {{\n")
        for name, spec in t["color"].items():
            o.append(f"    {snake(name)}: {rgba(spec[mode])},\n")
        o.append("};\n\n")
    o.append("#[derive(Clone, Copy, Debug, PartialEq)]\npub struct Theme {\n    pub light: Palette,\n    pub dark: Palette,\n}\n\n")
    o.append("/// Both appearances. Pick `.light` or `.dark` per window appearance.\n")
    o.append("pub const fn theme() -> Theme {\n    Theme { light: LIGHT, dark: DARK }\n}\n\n")

    o.append("/// Type scale: point sizes (SF system font).\n")
    for name, spec in t["type"].items():
        o.append(f"pub const TYPE_{snake(name).upper()}: f64 = {fmt(spec['size'])};\n")
    o.append("\n/// Font weights as NSFontWeight values.\n")
    o.append("pub const WEIGHT_REGULAR: f64 = 0.0;\npub const WEIGHT_MEDIUM: f64 = 0.23;\npub const WEIGHT_SEMIBOLD: f64 = 0.3;\npub const WEIGHT_BOLD: f64 = 0.4;\n\n")
    for key, prefix in (("radius", "RADIUS"), ("spacing", "SPACE"), ("control", "CONTROL")):
        for name, v in t[key].items():
            o.append(f"pub const {prefix}_{name.upper()}: f64 = {fmt(v)};\n")
        o.append("\n")
    for name, v in t["motion"].items():
        o.append(f"pub const MOTION_{name.upper()}: f64 = {fmt(v)};\n")
    o.append(f"pub const HAIRLINE: f64 = {fmt(t['stroke']['hairline'])};\n\n")
    for name, spec in t["type"].items():
        if "lineHeight" in spec:
            o.append(f"pub const LINE_HEIGHT_{snake(name).upper()}: f64 = {fmt(spec['lineHeight'])};\n")
    for name, spec in t["type"].items():
        if "tracking" in spec:
            o.append(f"/// Letter spacing in points for the {name} style.\npub const TRACKING_{snake(name).upper()}: f64 = {fmt(spec['tracking'] * spec['size'])};\n")
    o.append("\n/// Blur material behind `panel_tint` on floating panels and the pill.\n")
    o.append(f"pub const MATERIAL_BLUR: f64 = {fmt(t['material']['blur'])};\npub const MATERIAL_SATURATE: f64 = {fmt(t['material']['saturate'])};\n\n")
    o.append("/// A soft black shadow: offset, blur radius, and opacity per appearance.\n")
    o.append("#[derive(Clone, Copy, Debug, PartialEq)]\npub struct Shadow {\n    pub y: f64,\n    pub blur: f64,\n    pub light: f64,\n    pub dark: f64,\n}\n\n")
    for name, spec in t["shadow"].items():
        o.append(f"/// {spec['doc']}\npub const SHADOW_{snake(name).upper()}: Shadow = Shadow {{ y: {fmt(spec['y'])}, blur: {fmt(spec['blur'])}, light: {fmt(spec['light'])}, dark: {fmt(spec['dark'])} }};\n")
    o.append("\n/// Fixed layout widths and heights shared by the apps.\n")
    for name, v in t["layout"].items():
        o.append(f"pub const LAYOUT_{snake(name).upper()}: f64 = {fmt(v)};\n")
    return "".join(o)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    a = ap.parse_args()
    text = render(load_tokens())
    if a.out:
        Path(a.out).write_text(text)
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
