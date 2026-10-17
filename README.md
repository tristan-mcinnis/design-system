# design-system

The house rules for the native Apple apps (macOS and iOS). Read `DESIGN.md`
for the look and `SWIFT.md` for the code. `PERFORMANCE.md` records the measured
performance audit, benchmark budgets, and safe optimization boundaries.

- `tokens.json` is the single source of every value (light and dark).
- `make gen` renders `Sources/HouseDesign/HouseDesign.swift` (AppKit and UIKit in one file, all public) and `generated/house_theme.rs`.
- `python3 icons/make-icon.py --glyph bolt --out AppIcon.icns` renders an app icon.
- `make test` is standalone: it passes on a fresh clone with no siblings (it sets `HOUSE_ALLOW_MISSING=1`, so absent siblings are skipped and present ones are still checked). It also runs `swift test`. `make family-check` needs every sibling cloned next to this repo by folder name (rti, ledger, not the GitHub names) and fails on a missing, drifted or broken one. `make check-consumers` and `make components-check` fail on a missing sibling unless `HOUSE_ALLOW_MISSING=1`.

## Using it from an app

This repo is a Swift package with two library products, versioned by semver tag.

| Product | Holds | Platforms |
| --- | --- | --- |
| `HouseDesign` | `House`, the generated tokens (colour, type, radius, spacing, control, motion, shadow, layout) | macOS 14, iOS 17 |
| `HouseUIKit` | The hand-written Slate kit: `HouseUI.swift` and `MenuBarPanel.swift`. Depends on `HouseDesign`. | macOS 14 (empty on iOS) |

Pin it by GitHub URL and tag. In `Package.swift`:

```swift
.package(url: "https://github.com/tristan-mcinnis/design-system", from: "1.0.0")
// target dependencies:
.product(name: "HouseDesign", package: "design-system"),
.product(name: "HouseUIKit", package: "design-system"),
```

In an xcodegen `project.yml`:

```yaml
packages:
  DesignSystem:
    url: https://github.com/tristan-mcinnis/design-system
    from: "1.0.0"
targets:
  App:
    dependencies:
      - package: DesignSystem
        product: HouseDesign
```

Then `import HouseDesign` where `House.*` is used and `import HouseUIKit` for the kit. Copies of these files in an app fail `make check-consumers`.

Releasing: a token change or a kit change is a new tag. Patch for a value or a fix, minor for new public API, major for a removed or renamed public symbol. Run `make test`, tag `vX.Y.Z`, push the tag, then raise the `from:` pin in each app and commit there. `bin/check-consumers` fails when an app pins a tag newer than this repo's newest tag, uses a relative path, or keeps a copy.
