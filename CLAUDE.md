# design-system

`AGENTS.md` is a symlink to this file. The visual rule is `DESIGN.md` (keep it
under 120 lines); the code rule is `SWIFT.md` (concurrency, tests, platform
floors, iOS). `tokens.json` is the only place a value is typed by hand.

Build and test: `make build`, `make test`; warnings are errors.

- Change a value: edit `tokens.json`, run `make gen`, run `make test` (and `make family-check` with the siblings cloned). `Sources/HouseDesign/HouseDesign.swift` is the generated Swift module; `generated/house_theme.rs` is the generated Rust copy that local-dictation still carries (copy it there and commit). Then release: tag `vX.Y.Z` (patch for a value or fix, minor for new public API, major for a removed or renamed public symbol), push the tag, and raise the `from:` pin in each app (`make check-consumers` lists them).
- The Swift apps depend on this repo as a package by GitHub URL and tag, with two products: `HouseDesign` (tokens) and `HouseUIKit` (the hand-written menu-bar kit in `Sources/HouseUIKit/`: `HouseUI.swift`, `MenuBarPanel.swift`). Everything an app uses is `public`; adding a kit view means a public type, a public `init` and a public `body`. An app's own panel code goes in app-local files (`MenuBarPanelView.swift`, `MenuBarPanelController.swift`), never in the package. `make check-consumers` fails on a missing pin, a relative-path dependency or a copied source file.
- Never hand-edit a generated file. Generators must stay deterministic: no
  timestamps, no environment reads.
- Icons: add a glyph as a path function in `icons/make-icon.py`; render 256 px
  previews and look at them before shipping.
- Semantic token names only. No colour names, no per-app tokens here.

## Holding the view layer

A token file in a repo is plumbing, not a look. Three things hold the look:

- **`bin/design-lint`** scans the view layer of every house repo for literals
  (hard radii, colour names, raw font sizes, hex, AppKit system colours) and
  checks each copied token file carries the current sha. It is a ratchet:
  `make lint` fails only when a repo goes over `.design-lint-baseline.json`, so
  it bites on new drift and tolerates recorded debt. `make lint-strict` allows
  none. A deliberate exception is argued in one line in that repo's
  `.design-lint-allow`; debt is baselined, never allowlisted. Re-cut a baseline
  with `make lint-baselines` only after the count has genuinely fallen.
- **`bin/install-hooks`** (`make hooks`) puts a `pre-commit` hook and a project
  `.claude/settings.json` into every git repo under `house/`. The commit hook
  runs `design-lint --changed`; the Claude Code Stop hook blocks a session
  ending over baseline, and a PostToolUse hook warns the moment an edit adds a
  literal. Idempotent, and it discovers repos rather than listing them.
- **`components.json` + `bin/design-registry`** is the list of shared surfaces.
  `make components` renders the DESIGN.md "Shared components" section from it,
  so the two cannot drift; `make components-check` proves every `implements`
  and `proof` path is real. Register a surface before building it; the
  `/house-design` skill enforces that order.
