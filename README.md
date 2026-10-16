# design-system

The house rules for the native Apple apps (macOS and iOS). Read `DESIGN.md`
for the look and `SWIFT.md` for the code. `PERFORMANCE.md` records the measured
performance audit, benchmark budgets, and safe optimization boundaries.

- `tokens.json` is the single source of every value (light and dark).
- `make gen` renders `generated/HouseDesign.swift` (AppKit and UIKit in one file) and `generated/house_theme.rs`; copy them into an app.
- `python3 icons/make-icon.py --glyph bolt --out AppIcon.icns` renders an app icon.
- `kit/` holds the hand-written menu-bar kit (`HouseUI.swift`, `MenuBarPanel.swift`); `make sync-kit` copies it byte for byte into the four menu-bar apps, and `make check-consumers` fails on any drifted copy.
- `make test` is standalone: it passes on a fresh clone with no siblings (it sets `HOUSE_ALLOW_MISSING=1`, so absent siblings are skipped and present ones are still checked). `make family-check` needs every sibling cloned next to this repo by folder name (rti, ledger, not the GitHub names) and fails on a missing, drifted or broken one. `make check-consumers` and `make components-check` fail on a missing sibling unless `HOUSE_ALLOW_MISSING=1`.
