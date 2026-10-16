#!/usr/bin/env python3
"""Emit HouseDesign.swift from tokens.json.

    python3 gen/gen-swift.py [--out path]   (default: stdout)

Output: `enum House` with ColorToken (SwiftUI.Color, adaptive), a platform
colour enum (NSColorToken on AppKit via NSColor(name:dynamicProvider:),
UIColorToken on UIKit via UIColor(dynamicProvider:)), TypeToken, Radius,
Spacing, Control, Motion, Hairline. One file compiles on macOS and iOS.
Deterministic.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import fmt, header, load_tokens, rgba01  # noqa: E402

WEIGHTS = {"regular": ".regular", "medium": ".medium", "semibold": ".semibold", "bold": ".bold"}


def ns(v):
    r, g, b, a = rgba01(v)
    return f"NSColor(srgbRed: {fmt(r)}, green: {fmt(g)}, blue: {fmt(b)}, alpha: {fmt(a)})"


def ui(v):
    r, g, b, a = rgba01(v)
    return f"UIColor(red: {fmt(r)}, green: {fmt(g)}, blue: {fmt(b)}, alpha: {fmt(a)})"


def render(t):
    out = [header("//"), "// Source of truth: the design-system repo (DESIGN.md + tokens.json).\n",
           "// Regenerate with `make swift` there; `make check` verifies this copy.\n\n",
           "import SwiftUI\n",
           "#if canImport(AppKit)\nimport AppKit\n#elseif canImport(UIKit)\nimport UIKit\n#endif\n\n",
           "/// House design tokens. Semantic names only; colours adapt to the\n"
           "/// window appearance (light / dark) without per-view code.\n",
           "enum House {\n"]

    out.append("#if canImport(AppKit)\n")
    out.append("    /// AppKit colours, one per token, resolved per appearance.\n")
    out.append("    enum NSColorToken {\n")
    for name, spec in t["color"].items():
        out.append(f"        /// {spec['doc']}\n")
        out.append(f"        static let {name} = adaptive(\n")
        out.append(f"            light: {ns(spec['light'])},\n")
        out.append(f"            dark: {ns(spec['dark'])}\n")
        out.append("        )\n")
    out.append("\n        static func adaptive(light: NSColor, dark: NSColor) -> NSColor {\n")
    out.append("            NSColor(name: nil) { appearance in\n")
    out.append("                appearance.bestMatch(from: [.aqua, .darkAqua]) == .darkAqua ? dark : light\n")
    out.append("            }\n        }\n    }\n\n")

    out.append("    /// SwiftUI colours wrapping `NSColorToken`.\n")
    out.append("    enum ColorToken {\n")
    for name in t["color"]:
        out.append(f"        static let {name} = Color(nsColor: NSColorToken.{name})\n")
    out.append("    }\n")
    out.append("#elseif canImport(UIKit)\n")
    out.append("    /// UIKit colours, one per token, resolved per trait collection.\n")
    out.append("    enum UIColorToken {\n")
    for name, spec in t["color"].items():
        out.append(f"        /// {spec['doc']}\n")
        out.append(f"        static let {name} = adaptive(\n")
        out.append(f"            light: {ui(spec['light'])},\n")
        out.append(f"            dark: {ui(spec['dark'])}\n")
        out.append("        )\n")
    out.append("\n        static func adaptive(light: UIColor, dark: UIColor) -> UIColor {\n")
    out.append("            UIColor { traits in\n")
    out.append("                traits.userInterfaceStyle == .dark ? dark : light\n")
    out.append("            }\n        }\n    }\n\n")

    out.append("    /// SwiftUI colours wrapping `UIColorToken`.\n")
    out.append("    enum ColorToken {\n")
    for name in t["color"]:
        out.append(f"        static let {name} = Color(uiColor: UIColorToken.{name})\n")
    out.append("    }\n")
    out.append("#endif\n\n")

    out.append("    /// Type scale: SF system font, fixed point sizes.\n")
    out.append("    enum TypeToken {\n")
    for name, spec in t["type"].items():
        w = WEIGHTS[spec["weight"]]
        design = ", design: .monospaced" if spec.get("mono") else ""
        out.append(f"        static let {name} = Font.system(size: {fmt(spec['size'])}, weight: {w}{design})\n")
    out.append("\n        /// Point sizes, for views that scale type manually.\n")
    out.append("        enum Size {\n")
    for name, spec in t["type"].items():
        out.append(f"            static let {name}: CGFloat = {fmt(spec['size'])}\n")
    out.append("        }\n\n")
    out.append("        /// Line height as a multiple of the size, where the scale sets one.\n")
    out.append("        enum LineHeight {\n")
    for name, spec in t["type"].items():
        if "lineHeight" in spec:
            out.append(f"            static let {name}: CGFloat = {fmt(spec['lineHeight'])}\n")
    out.append("        }\n\n")
    out.append("        /// Letter spacing in points (em fraction times size) for tracked styles.\n")
    out.append("        enum Tracking {\n")
    for name, spec in t["type"].items():
        if "tracking" in spec:
            out.append(f"            static let {name}: CGFloat = {fmt(spec['tracking'] * spec['size'])}\n")
    out.append("        }\n\n")
    out.append("        /// Styles set in capitals.\n")
    out.append("        static let uppercase: Set<String> = [" + ", ".join(f'"{n}"' for n, sp in t["type"].items() if sp.get("uppercase")) + "]\n")
    out.append("    }\n\n")

    out.append("    /// Blur material behind `panelTint` on floating panels and the pill.\n")
    out.append("    enum Material {\n")
    out.append(f"        static let blur: CGFloat = {fmt(t['material']['blur'])}\n")
    out.append(f"        static let saturate: CGFloat = {fmt(t['material']['saturate'])}\n")
    out.append("    }\n\n")

    out.append("    /// A soft black shadow: offset, blur radius, and opacity per appearance.\n")
    out.append("    struct ShadowSpec {\n        let y: CGFloat\n        let blur: CGFloat\n        let light: Double\n        let dark: Double\n")
    out.append("        /// Opacity for the given appearance.\n")
    out.append("        func opacity(dark isDark: Bool) -> Double { isDark ? dark : light }\n    }\n\n")
    out.append("    enum Shadow {\n")
    for name, spec in t["shadow"].items():
        out.append(f"        /// {spec['doc']}\n")
        out.append(f"        static let {name} = ShadowSpec(y: {fmt(spec['y'])}, blur: {fmt(spec['blur'])}, light: {fmt(spec['light'])}, dark: {fmt(spec['dark'])})\n")
    out.append("    }\n\n")

    out.append("    /// Fixed layout widths and heights shared by the apps.\n")
    out.append("    enum Layout {\n")
    for name, v in t["layout"].items():
        out.append(f"        static let {name}: CGFloat = {fmt(v)}\n")
    out.append("    }\n\n")

    for enum, key in (("Radius", "radius"), ("Spacing", "spacing"), ("Control", "control")):
        out.append(f"    enum {enum} {{\n")
        for name, v in t[key].items():
            out.append(f"        static let {name}: CGFloat = {fmt(v)}\n")
        out.append("    }\n\n")

    out.append("    enum Motion {\n")
    for name, v in t["motion"].items():
        out.append(f"        static let {name}: TimeInterval = {fmt(v)}\n")
    out.append("    }\n\n")
    out.append(f"    static let hairline: CGFloat = {fmt(t['stroke']['hairline'])}\n")
    out.append("}\n")
    return "".join(out)


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
