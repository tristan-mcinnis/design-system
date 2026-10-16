.PHONY: scrub scrub-history gen swift rust check check-consumers sync-kit family-check test icons lint lint-strict lint-baselines components components-check hooks

PY ?= python3
HOUSE ?= ..
# Every git repo under house/, discovered. A repo that joins the family is
# linted the next time this runs; nothing to remember to edit.
REPO_PATHS = $(sort $(patsubst %/.git,%,$(wildcard $(HOUSE)/*/.git)))

CONSUMERS = \
  $(HOUSE)/quick-launch/Sources/Views/HouseDesign.swift \
  $(HOUSE)/rti/RTI/Sources/UI/HouseDesign.swift \
  $(HOUSE)/cotype/Sources/CotypeMenuApp/HouseDesign.swift \
  $(HOUSE)/cotype/Sources/CotypeMacOS/HouseDesign.swift \
  $(HOUSE)/memory-menubar/Sources/MemoryBar/HouseDesign.swift \
  $(HOUSE)/local-models/menubar/LocalModelsBar/Sources/LocalModelsBar/HouseDesign.swift \
  $(HOUSE)/usage-menubar/Sources/UsageBar/HouseDesign.swift \
  $(HOUSE)/local-dictation/src/menubar/house_theme.rs

# The menu-bar kit: hand-written, owned here in kit/, copied byte for byte into
# each menu-bar app's source folder. App-specific panel code lives in
# app-local files next to the copies, never in them.
KIT_FILES = HouseUI.swift MenuBarPanel.swift
KIT_DIRS = \
  $(HOUSE)/cotype/Sources/CotypeMenuApp \
  $(HOUSE)/memory-menubar/Sources/MemoryBar \
  $(HOUSE)/usage-menubar/Sources/UsageBar \
  $(HOUSE)/local-models/menubar/LocalModelsBar/Sources/LocalModelsBar
KIT_CONSUMERS = $(foreach d,$(KIT_DIRS),$(addprefix $(d)/,$(KIT_FILES)))

gen: swift rust

swift:
	$(PY) gen/gen-swift.py --out generated/HouseDesign.swift

rust:
	$(PY) gen/gen-rust.py --out generated/house_theme.rs

# Committed generated files must equal a fresh render of tokens.json.
check:
	@$(PY) gen/gen-swift.py | diff -q - generated/HouseDesign.swift >/dev/null || { echo "generated/HouseDesign.swift is stale: run make gen"; exit 1; }
	@$(PY) gen/gen-rust.py | diff -q - generated/house_theme.rs >/dev/null || { echo "generated/house_theme.rs is stale: run make gen"; exit 1; }
	@echo "generated files match tokens.json"

# Consuming repos carry a copy; each must equal the committed generated file
# (HouseDesign.swift, house_theme.rs) or the kit file (kit/HouseUI.swift,
# kit/MenuBarPanel.swift). A consumer that is not cloned next to this repo
# fails, unless HOUSE_ALLOW_MISSING=1 (a standalone checkout). Folder names are
# used, not GitHub names (rti-personal is ../rti, memory-ledger is ../ledger).
check-consumers:
	@bad=0; for f in $(CONSUMERS) $(KIT_CONSUMERS); do \
	  if [ ! -f $$f ]; then \
	    case "$${HOUSE_ALLOW_MISSING:-0}" in 0|"") echo "MISSING: $$f (clone the sibling repo next to design-system, or set HOUSE_ALLOW_MISSING=1 for a standalone check)"; bad=1;; *) echo "skip (absent, allowed): $$f";; esac; \
	    continue; \
	  fi; \
	  case $$f in */HouseDesign.swift) src=generated/HouseDesign.swift;; *.rs) src=generated/house_theme.rs;; *) src=kit/$${f##*/};; esac; \
	  if diff -q $$src $$f >/dev/null; then echo "ok: $$f"; else echo "DRIFT: $$f"; bad=1; fi; \
	done; \
	[ $$bad -eq 0 ] || { echo "check-consumers failed"; exit 1; }

# Copy the kit into every menu-bar app. Run after editing anything in kit/,
# then commit in each app.
sync-kit:
	@for d in $(KIT_DIRS); do \
	  [ -d $$d ] || { echo "MISSING: $$d (clone the sibling repo next to design-system)"; exit 1; }; \
	  for k in $(KIT_FILES); do cp kit/$$k $$d/$$k && echo "copied: $$d/$$k"; done; \
	done

icons:
	$(PY) icons/make-icon.py --glyph bolt --png generated/preview-bolt.png
	$(PY) icons/make-icon.py --glyph waveform --png generated/preview-waveform.png
	$(PY) icons/make-icon.py --glyph record --png generated/preview-record.png

# View-layer drift across the family. Fails when a repo goes over its baseline.
lint:
	@bin/design-lint $(REPO_PATHS)

# Zero tolerance: every hit, baseline ignored. What a new surface must pass.
lint-strict:
	@bin/design-lint --strict $(REPO_PATHS)

# Re-cut the ratchet. Only after the count has genuinely fallen.
lint-baselines:
	@bin/design-lint --baseline write $(REPO_PATHS)

# DESIGN.md "Shared components" is rendered from components.json.
components:
	@bin/design-registry sync

# Fails on an absent sibling repo. HOUSE_ALLOW_MISSING=1 skips absent ones.
components-check:
	@bin/design-registry check

hooks:
	@bin/install-hooks

scrub:
	@sh tests/scrub.sh

scrub-history:
	@sh tests/scrub-history.sh

# Standalone: passes on a fresh clone with no siblings. It checks every
# sibling that is present and skips the ones that are not.
test:
	@$(MAKE) --no-print-directory scrub check
	@HOUSE_ALLOW_MISSING=1 $(MAKE) --no-print-directory check-consumers components-check
	HOUSE_ALLOW_MISSING=1 $(PY) -m unittest discover -s tests -v

# The whole family: every sibling must be cloned next to this repo. Nothing is
# skipped, so a missing consumer, a drifted copy or a bad path all fail.
family-check:
	@$(MAKE) --no-print-directory scrub check check-consumers components-check
	$(PY) -m unittest discover -s tests -v
