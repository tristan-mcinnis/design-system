"""design-lint holds the view layer; design-registry holds the surface list.

Every case builds a throwaway repo with known drift, so the tests never depend
on what the real house repos happen to contain today.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINT = ROOT / "bin" / "design-lint"
REGISTRY = ROOT / "bin" / "design-registry"
SHA = "deadbeefcafe"

# Nine hits: two radii, one colour name, one Color(red:, one NSColor(srgbRed:,
# one Font.system size, one .foregroundStyle(.secondary), one hex, one
# .foregroundColor(.secondary).
DRIFTY_SWIFT = """import SwiftUI

struct PanelView: View {
    var body: some View {
        VStack {
            Text("hi")
                .font(Font.system(size: 13))
                .foregroundStyle(.secondary)
                .foregroundColor(.secondary)
                .background(Color.blue)
                .background(Color(red: 0.1, green: 0.2, blue: 0.3))
                .background(NSColor(srgbRed: 0.1, green: 0.2, blue: 0.3, alpha: 1))
                .cornerRadius(8)
        }
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }
    // brand hex #4A90D9 lives here
}
"""

CLEAN_SWIFT = """import SwiftUI

struct CleanView: View {
    var body: some View {
        Text("hi")
            .font(House.TypeToken.body)
            .foregroundStyle(House.Color.textSecondary)
            .clipShape(RoundedRectangle(cornerRadius: House.Radius.lg))
    }
}
"""

# Four hits: font size, a system colour, colour components, corner radius.
DRIFTY_RUST = """use objc2_app_kit::{NSColor, NSFont};

fn build() {
    let f = NSFont::systemFontOfSize_weight(13.0, 0.0);
    let c = NSColor::labelColor();
    let d = NSColor::colorWithSRGBRed_green_blue_alpha(0.1, 0.2, 0.3, 1.0);
    unsafe { let _: () = msg_send![layer, setCornerRadius: 8.0]; }
}
"""

CLEAN_RUST = """use super::house_theme::DARK;

fn build() {
    let f = NSFont::systemFontOfSize_weight(theme.size, theme.weight);
    unsafe { let _: () = msg_send![layer, setCornerRadius: radius]; }
}
"""


def run(*args, cwd=None, stdin=None):
    return subprocess.run([sys.executable, str(LINT), *args], cwd=cwd or ROOT,
                          capture_output=True, text=True, input=stdin)


def registry(*args, cwd=None):
    return subprocess.run([sys.executable, str(REGISTRY), *args], cwd=cwd or ROOT,
                          capture_output=True, text=True)


def write(root: Path, rel: str, body: str):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)
    return path


class Fixture(unittest.TestCase):
    """A scratch repo. `self.repo` is its root."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.repo = self.tmp / "app"
        self.repo.mkdir()
        write(self.repo, "Sources/Views/PanelView.swift", DRIFTY_SWIFT)
        write(self.repo, "Sources/Views/CleanView.swift", CLEAN_SWIFT)
        write(self.repo, "src/ui/panel.rs", DRIFTY_RUST)
        write(self.repo, "src/ui/clean.rs", CLEAN_RUST)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def scan(self, *extra):
        r = run("--json", "--tokens-sha", SHA, str(self.repo), *extra)
        self.assertIn(r.returncode, (0, 1), r.stderr)
        return json.loads(r.stdout), r.returncode


class Patterns(Fixture):
    def test_finds_every_swift_and_rust_literal(self):
        data, code = self.scan()
        repo = data["repos"][0]
        self.assertEqual(code, 1)
        self.assertEqual(repo["by_file"]["Sources/Views/PanelView.swift"], 9)
        self.assertEqual(repo["by_file"]["src/ui/panel.rs"], 4)
        self.assertEqual(repo["total"], 13)

    def test_token_references_are_not_hits(self):
        data, _ = self.scan()
        by_file = data["repos"][0]["by_file"]
        self.assertNotIn("Sources/Views/CleanView.swift", by_file)
        self.assertNotIn("src/ui/clean.rs", by_file)

    def test_each_rule_fires_once_on_its_own_line(self):
        data, _ = self.scan()
        hits = [h for h in data["repos"][0]["hits"] if h["path"].endswith("PanelView.swift")]
        # Font.system(size:) must count once, not twice as the bare .system too.
        line = [h for h in hits if h["rule"].endswith("font-size-literal")]
        self.assertEqual(len(line), 1)
        self.assertEqual(sorted({h["rule"] for h in hits}), [
            "colour-components", "colour-name", "corner-radius-literal",
            "corner-radius-modifier", "font-size-literal", "hex-colour",
            "hierarchical-ink", "nscolour-components", "secondary-ink",
        ])

    def test_house_and_aqdesign_prefixes_are_allowed(self):
        write(self.repo, "Sources/Views/Prefixed.swift",
              "let a = House.Color.blue\nlet b = AQDesign.Color.blue\n")
        data, _ = self.scan()
        self.assertNotIn("Sources/Views/Prefixed.swift", data["repos"][0]["by_file"])

    def test_generated_files_and_skip_dirs_are_not_scanned(self):
        write(self.repo, "Sources/Views/HouseDesign.swift",
              f"// GENERATED from design-system/tokens.json {SHA}; do not edit\n" + DRIFTY_SWIFT)
        write(self.repo, "Tests/PanelTests.swift", DRIFTY_SWIFT)
        write(self.repo, ".build/Junk.swift", DRIFTY_SWIFT)
        write(self.repo, ".deriveddata-tests/checkouts/Dep.swift", DRIFTY_SWIFT)
        write(self.repo, "target/debug/gen.rs", DRIFTY_RUST)
        data, _ = self.scan()
        self.assertEqual(sorted(data["repos"][0]["by_file"]),
                         ["Sources/Views/PanelView.swift", "src/ui/panel.rs"])


class Baseline(Fixture):
    def test_write_then_clean_then_new_drift_bites(self):
        r = run("--baseline", "write", "--tokens-sha", SHA, str(self.repo))
        self.assertEqual(r.returncode, 0, r.stderr)
        base = json.loads((self.repo / ".design-lint-baseline.json").read_text())
        self.assertEqual(base["total"], 13)

        data, code = self.scan()
        self.assertEqual(code, 0, "existing debt must not fail the ratchet")
        self.assertEqual(data["status"], "held")
        self.assertEqual(data["repos"][0]["over_baseline"], [])

        write(self.repo, "Sources/Views/New.swift", "let r = 7\n.cornerRadius(7)\n")
        data, code = self.scan()
        self.assertEqual(code, 1)
        self.assertEqual([o["path"] for o in data["repos"][0]["over_baseline"]],
                         ["Sources/Views/New.swift"])

    def test_removing_drift_never_fails(self):
        run("--baseline", "write", "--tokens-sha", SHA, str(self.repo))
        (self.repo / "src/ui/panel.rs").unlink()
        data, code = self.scan()
        self.assertEqual(code, 0)
        self.assertEqual(data["repos"][0]["total"], 9)

    def test_strict_ignores_the_baseline(self):
        run("--baseline", "write", "--tokens-sha", SHA, str(self.repo))
        data, code = self.scan("--strict")
        self.assertEqual(code, 1)
        self.assertEqual(data["status"], "drift")


class Allowlist(Fixture):
    def test_whole_file_glob(self):
        (self.repo / ".design-lint-allow").write_text("# reason\nSources/Views/PanelView.swift\n")
        data, _ = self.scan()
        self.assertNotIn("Sources/Views/PanelView.swift", data["repos"][0]["by_file"])
        self.assertIn("src/ui/panel.rs", data["repos"][0]["by_file"])

    def test_line_regex_exempts_only_matching_lines(self):
        (self.repo / ".design-lint-allow").write_text(
            "Sources/Views/*.swift:Color\\(red:\n")
        data, _ = self.scan()
        rules = {h["rule"] for h in data["repos"][0]["hits"]
                 if h["path"].endswith("PanelView.swift")}
        self.assertNotIn("colour-components", rules)
        self.assertIn("corner-radius-modifier", rules)

    def test_comments_and_blank_lines_are_ignored(self):
        (self.repo / ".design-lint-allow").write_text("\n# nothing here\n\n")
        data, _ = self.scan()
        self.assertEqual(data["repos"][0]["total"], 13)


class TokenCopies(Fixture):
    def test_stale_copy_fails_even_with_a_baseline(self):
        write(self.repo, "Sources/Views/HouseDesign.swift",
              "// GENERATED from design-system/tokens.json 000000000000; do not edit\n")
        run("--baseline", "write", "--tokens-sha", SHA, str(self.repo))
        data, code = self.scan()
        self.assertEqual(code, 1)
        self.assertEqual([t["path"] for t in data["repos"][0]["stale_token_files"]],
                         ["Sources/Views/HouseDesign.swift"])

    def test_current_copy_passes(self):
        write(self.repo, "src/ui/house_theme.rs",
              f"// GENERATED from design-system/tokens.json {SHA}; do not edit\n")
        data, _ = self.scan()
        self.assertEqual(data["repos"][0]["stale_token_files"], [])
        self.assertTrue(data["repos"][0]["token_files"][0]["ok"])


class Changed(Fixture):
    def git(self, *args):
        subprocess.run(["git", "-C", str(self.repo), *args], capture_output=True, check=True)

    def test_changed_limits_to_the_working_tree(self):
        self.git("init", "-q")
        self.git("config", "user.email", "t@example.com")
        self.git("config", "user.name", "t")
        self.git("add", "-A")
        self.git("commit", "-qm", "seed")
        run("--baseline", "write", "--tokens-sha", SHA, str(self.repo))

        data, code = self.scan("--changed")
        self.assertEqual(code, 0)
        self.assertEqual(data["repos"][0]["total"], 0, "a clean tree touches nothing")

        write(self.repo, "Sources/Views/Fresh.swift", ".cornerRadius(9)\n")
        data, code = self.scan("--changed")
        self.assertEqual(code, 1)
        self.assertEqual(sorted(data["repos"][0]["by_file"]), ["Sources/Views/Fresh.swift"])


class Hooks(Fixture):
    def test_stop_hook_blocks_with_the_offending_rows(self):
        r = run("--hook", "stop", "--tokens-sha", SHA, str(self.repo),
                stdin=json.dumps({"cwd": str(self.repo)}))
        self.assertEqual(r.returncode, 0)
        payload = json.loads(r.stdout)
        self.assertEqual(payload["decision"], "block")
        self.assertIn("Sources/Views/PanelView.swift", payload["reason"])
        self.assertIn("corner-radius-modifier", payload["reason"])

    def test_stop_hook_is_silent_when_held(self):
        run("--baseline", "write", "--tokens-sha", SHA, str(self.repo))
        r = run("--hook", "stop", "--tokens-sha", SHA, str(self.repo),
                stdin=json.dumps({"cwd": str(self.repo)}))
        self.assertEqual((r.returncode, r.stdout.strip()), (0, ""))

    def test_stop_hook_does_not_loop(self):
        r = run("--hook", "stop", "--tokens-sha", SHA, str(self.repo),
                stdin=json.dumps({"cwd": str(self.repo), "stop_hook_active": True}))
        self.assertEqual((r.returncode, r.stdout.strip()), (0, ""))

    def test_post_tool_hook_warns_on_the_touched_file(self):
        target = self.repo / "Sources/Views/PanelView.swift"
        r = run("--hook", "post-tool", "--tokens-sha", SHA, str(self.repo),
                stdin=json.dumps({"cwd": str(self.repo),
                                  "tool_input": {"file_path": str(target)}}))
        self.assertEqual(r.returncode, 2)
        self.assertIn("PanelView.swift", r.stderr)
        self.assertEqual(len(r.stderr.strip().splitlines()), 1, "one line only")

    def test_post_tool_hook_stays_quiet_on_a_clean_file(self):
        target = self.repo / "Sources/Views/CleanView.swift"
        r = run("--hook", "post-tool", "--tokens-sha", SHA, str(self.repo),
                stdin=json.dumps({"cwd": str(self.repo),
                                  "tool_input": {"file_path": str(target)}}))
        self.assertEqual((r.returncode, r.stderr.strip()), (0, ""))

    def test_hook_never_breaks_a_session(self):
        for payload in ("", "not json", "{}"):
            r = run("--hook", "post-tool", "--tokens-sha", SHA, str(self.repo), stdin=payload)
            self.assertEqual(r.returncode, 0, payload)


class InstallHooks(Fixture):
    """bin/install-hooks, run on a scratch repo only (never on the real house)."""

    def git(self, *args, check=True):
        return subprocess.run(["git", "-C", str(self.repo), *args],
                              capture_output=True, text=True, check=check)

    def install(self):
        r = subprocess.run([sys.executable, str(ROOT / "bin" / "install-hooks"), str(self.repo)],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def setUp(self):
        super().setUp()
        self.git("init", "-q")
        self.git("config", "user.email", "t@example.com")
        self.git("config", "user.name", "t")
        # install-hooks writes .git/hooks; pin it so a global core.hooksPath
        # (this Mac has one) neither decides the result nor runs its own hooks.
        self.git("config", "core.hooksPath", str(self.repo / ".git" / "hooks"))
        self.git("add", "-A")
        self.git("commit", "-qm", "seed")
        hooks = self.repo / ".git" / "hooks"
        hooks.mkdir(exist_ok=True)
        local = hooks / "pre-commit"
        local.write_text("#!/bin/sh\ntouch \"$(git rev-parse --show-toplevel)/.local-hook-ran\"\n")
        local.chmod(0o755)
        (self.repo / ".claude").mkdir()
        (self.repo / ".claude" / "settings.json").write_text(json.dumps(
            {"model": "keep", "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "other.sh"}]}]}}))

    def test_chains_the_old_hook_and_merges_settings_idempotently(self):
        self.assertIn("chained the existing hook", self.install())
        self.assertIn("updated", self.install())
        hooks = self.repo / ".git" / "hooks"
        self.assertIn("touch", (hooks / "pre-commit.local").read_text())
        self.assertIn("design-lint pre-commit", (hooks / "pre-commit").read_text())
        settings = json.loads((self.repo / ".claude" / "settings.json").read_text())
        self.assertEqual(settings["model"], "keep")
        stop = [h["command"] for e in settings["hooks"]["Stop"] for h in e["hooks"]]
        self.assertEqual(stop, ["other.sh", "$CLAUDE_PROJECT_DIR/.claude/hooks/design-stop.sh"])
        self.assertEqual(len(settings["hooks"]["PostToolUse"]), 1)
        for name in ("design-stop.sh", "design-post-tool.sh"):
            self.assertTrue(os.access(self.repo / ".claude" / "hooks" / name, os.X_OK))

    def test_installed_hook_refuses_new_drift_and_passes_clean_work(self):
        self.install()
        run("--baseline", "write", str(self.repo))
        self.git("add", "-A")
        self.assertEqual(self.git("commit", "-qm", "baseline", check=False).returncode, 0)
        self.assertTrue((self.repo / ".local-hook-ran").exists(), "the chained hook ran first")

        write(self.repo, "Sources/Views/Fresh.swift", ".cornerRadius(9)\n")
        self.git("add", "-A")
        r = self.git("commit", "-qm", "drift", check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Commit refused", r.stderr)

        write(self.repo, "Sources/Views/Fresh.swift", CLEAN_SWIFT)
        self.git("add", "-A")
        r = self.git("commit", "-qm", "clean", check=False)
        self.assertEqual(r.returncode, 0, r.stderr)


class Output(Fixture):
    def test_deterministic_and_free_of_escapes_when_piped(self):
        a = run("--tokens-sha", SHA, str(self.repo))
        b = run("--tokens-sha", SHA, str(self.repo))
        self.assertEqual(a.stdout, b.stdout)
        self.assertNotIn("\033", a.stdout)

    def test_house_terminal_shape(self):
        out = run("--tokens-sha", SHA, str(self.repo)).stdout
        first = out.splitlines()[0]
        self.assertTrue(first.startswith("● "), first)
        self.assertIn("hits", first)
        self.assertIn("baseline", first)
        self.assertIn("\nHITS\n", out)
        for banned in ("=", "─", "│", "+--"):
            self.assertNotIn(banned * 3, out)

    def test_no_color_env_is_honoured(self):
        env = dict(os.environ, NO_COLOR="1")
        r = subprocess.run([sys.executable, str(LINT), "--tokens-sha", SHA, str(self.repo)],
                           capture_output=True, text=True, env=env)
        self.assertNotIn("\033", r.stdout)


class Registry(unittest.TestCase):
    def test_design_md_matches_components_json(self):
        r = registry("check")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_render_is_deterministic_and_lands_in_design_md(self):
        a = registry("render").stdout
        self.assertEqual(a, registry("render").stdout)
        self.assertIn(a.strip(), (ROOT / "DESIGN.md").read_text())

    def test_every_component_has_purpose_spec_implements_and_proof(self):
        data = json.loads((ROOT / "components.json").read_text())
        keys = [c["key"] for c in data["components"]]
        self.assertEqual(len(keys), len(set(keys)), "keys must be unique")
        for c in data["components"]:
            for field in ("name", "purpose", "spec", "implements", "mockup", "proof"):
                self.assertTrue(c.get(field), f"{c['key']} is missing {field}")
            for entry in c["implements"] + c["proof"]:
                repo = ROOT.parent / entry["repo"]
                if not repo.is_dir() and os.environ.get("HOUSE_ALLOW_MISSING", "") not in ("", "0"):
                    continue  # standalone checkout: the sibling is not cloned
                self.assertTrue((repo / entry["path"]).exists(),
                                f"{c['key']}: {entry['repo']}/{entry['path']}")

    def test_every_token_consumer_is_checked_for_registration(self):
        """A repo that carries a generated token file has a view layer, so
        `check` must flag it when it registers nothing."""
        import importlib.machinery
        import importlib.util
        import re
        loader = importlib.machinery.SourceFileLoader("design_registry", str(REGISTRY))
        mod = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
        loader.exec_module(mod)
        makefile = (ROOT / "Makefile").read_text()
        consumers = set(re.findall(r"^\s*(?:\.\.|\$\(HOUSE\))/([^/\s]+)/", makefile, flags=re.M))
        self.assertTrue(consumers)
        self.assertEqual(sorted(consumers - set(mod.VIEW_REPOS)), [])

    def test_absent_sibling_fails_unless_allowed(self):
        """A standalone clone has no siblings: check fails by default and
        passes with --allow-missing or HOUSE_ALLOW_MISSING=1."""
        with tempfile.TemporaryDirectory() as tmp:
            clone = Path(tmp) / "design-system"
            shutil.copytree(ROOT, clone, ignore=shutil.ignore_patterns(".git", "__pycache__"))
            env = {k: v for k, v in os.environ.items() if k != "HOUSE_ALLOW_MISSING"}
            run = lambda *a, **e: subprocess.run(
                [sys.executable, str(clone / "bin" / "design-registry"), "check", *a],
                cwd=clone, capture_output=True, text=True, env={**env, **e})
            r = run()
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("ABSENT SIBLING REPOS", r.stdout)
            r = run("--allow-missing")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("skipped", r.stdout)
            r = run(HOUSE_ALLOW_MISSING="1")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            # A sibling that is present but lacks a registered path still fails.
            (Path(tmp) / "quick-launch").mkdir()
            r = run("--allow-missing")
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("MISSING PATHS", r.stdout)

    def test_a_retired_view_layer_is_stale_not_unregistered(self):
        """A repo that stays but loses its app (chief-of-staff's app/, retired
        2026-09-26) must fail check as a stale VIEW_REPOS entry."""
        import contextlib
        import importlib.machinery
        import importlib.util
        import io
        import tempfile
        loader = importlib.machinery.SourceFileLoader("design_registry_stale", str(REGISTRY))
        mod = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
        loader.exec_module(mod)
        with tempfile.TemporaryDirectory() as tmp:
            house = Path(tmp)
            (house / "kept" / "Sources").mkdir(parents=True)
            (house / "kept" / "Sources" / "View.swift").write_text("")
            (house / "retired").mkdir()  # repo still here, app/ gone
            data = {"components": [{"key": "k", "name": "K", "purpose": "p", "spec": ["s"],
                                    "implements": [{"repo": "kept", "path": "Sources/View.swift"}],
                                    "proof": [{"repo": "kept", "path": "Sources/View.swift"}]}]}
            design = house / "DESIGN.md"
            design.write_text(f"{mod.BEGIN}\n{mod.render(data)}\n{mod.END}\n")
            mod.HOUSE, mod.DESIGN, mod.load = house, design, lambda: data
            mod.VIEW_REPOS = {"kept": "Sources"}
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(mod.cmd_check(None), 0)
            mod.VIEW_REPOS = {"kept": "Sources", "retired": "app/Sources"}
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(mod.cmd_check(None), 1)
            self.assertIn("STALE VIEW REPOS", out.getvalue())
            self.assertIn("retired (app/Sources)", out.getvalue())
            self.assertNotIn("UNREGISTERED", out.getvalue())

    def test_show_and_list_run(self):
        self.assertEqual(registry("list").returncode, 0)
        self.assertEqual(registry("show", "menu-bar-panel").returncode, 0)
        self.assertEqual(registry("show", "no-such-thing").returncode, 1)


class DesignDoc(unittest.TestCase):
    def test_stays_under_120_lines(self):
        lines = (ROOT / "DESIGN.md").read_text().splitlines()
        self.assertLess(len(lines), 120, f"DESIGN.md is {len(lines)} lines")


if __name__ == "__main__":
    unittest.main()
