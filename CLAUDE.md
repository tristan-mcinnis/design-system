# design-system

`AGENTS.md` is a symlink to this file. The visual rule is `DESIGN.md` (keep it
under 120 lines); the code rule is `SWIFT.md` (concurrency, tests, platform
floors, iOS). `tokens.json` is the only place a value is typed by hand.

- Change a value: edit `tokens.json`, run `make gen`, run `make test` (and `make family-check` with the siblings cloned), then copy
  `generated/HouseDesign.swift` and `generated/house_theme.rs` into every
  consuming repo (the `CONSUMERS` list in the Makefile) and commit there too.
  The Swift file compiles on macOS and iOS. The atlas flags a stale copy as
  `DESIGN-DRIFT`.
- The menu-bar kit is hand-written and lives in `kit/` (`HouseUI.swift`,
  `MenuBarPanel.swift`). Edit it here, run `make sync-kit` to copy it into the
  four menu-bar apps (cotype, memory-menubar, usage-menubar, local-models), and
  commit there too. `make check-consumers` fails on any drifted copy. An app's
  own panel code goes in app-local files (`MenuBarPanelView.swift`,
  `MenuBarPanelController.swift`), never in the copies.
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
