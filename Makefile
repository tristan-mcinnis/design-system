.PHONY: scrub scrub-history gen swift rust check check-consumers family-check test icons lint lint-strict lint-baselines components components-check hooks

PY ?= python3
HOUSE ?= ..
# Every git repo under house/, discovered. A repo that joins the family is
# linted the next time this runs; nothing to remember to edit.
REPO_PATHS = $(sort $(patsubst %/.git,%,$(wildcard $(HOUSE)/*/.git)))

SWIFT_SRC = Sources/HouseDesign/HouseDesign.swift

gen: swift rust

swift:
	$(PY) gen/gen-swift.py --out $(SWIFT_SRC)

rust:
	$(PY) gen/gen-rust.py --out generated/house_theme.rs

# Committed generated files must equal a fresh render of tokens.json.
check:
	@$(PY) gen/gen-swift.py | diff -q - $(SWIFT_SRC) >/dev/null || { echo "$(SWIFT_SRC) is stale: run make gen"; exit 1; }
	@$(PY) gen/gen-rust.py | diff -q - generated/house_theme.rs >/dev/null || { echo "generated/house_theme.rs is stale: run make gen"; exit 1; }
	@echo "generated files match tokens.json"

# Swift apps pin this package by GitHub URL and tag; the Rust token file in
# local-dictation is the one remaining generated copy. bin/check-consumers
# fails on a missing pin, a relative-path dependency, a copied source file or
# a drifted Rust copy. A consumer that is not cloned next to this repo fails,
# unless HOUSE_ALLOW_MISSING=1 (a standalone checkout).
check-consumers:
	@$(PY) bin/check-consumers --house $(HOUSE)

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
	swift test
	HOUSE_ALLOW_MISSING=1 $(PY) -m unittest discover -s tests -v

# The whole family: every sibling must be cloned next to this repo. Nothing is
# skipped, so a missing consumer, a drifted copy or a bad path all fail.
family-check:
	@$(MAKE) --no-print-directory scrub check check-consumers components-check
	swift test
	$(PY) -m unittest discover -s tests -v
