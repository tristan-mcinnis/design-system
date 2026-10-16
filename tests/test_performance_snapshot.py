"""Tests for bin/performance-snapshot.

Everything here mocks the external commands (ps, sw_vers, sysctl, uname, git,
footprint) and the clock, so the suite is fast, offline, and does not sample the
real fleet. The tool is loaded through an explicit SourceFileLoader because it
has no .py suffix.
"""
import importlib.machinery
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT = ROOT / "bin" / "performance-snapshot"

LOADER = importlib.machinery.SourceFileLoader("performance_snapshot", str(SNAPSHOT))
SPEC = importlib.util.spec_from_loader("performance_snapshot", LOADER)
MOD = importlib.util.module_from_spec(SPEC)
LOADER.exec_module(MOD)


class Out:
    """Stand-in for subprocess.CompletedProcess."""

    def __init__(self, stdout, returncode=0, stderr=""):
        self.stdout = stdout
        self.returncode = returncode
        self.stderr = stderr


SYSTEM_FACTS = {
    "machdep.cpu.brand_string": "Apple M5\n",
    "hw.physicalcpu": "10\n",
    "hw.logicalcpu": "10\n",
    "hw.perflevel0.physicalcpu": "4\n",
    "hw.perflevel1.physicalcpu": "6\n",
    "hw.memsize": "34359738368\n",
}


def make_runner(ps_outputs, status_paths=(" M foo.swift\n?? bar.txt\n")):
    """A fake `runner(argv, timeout=None)` driving ps through a list of outputs.

    Two ps shapes are served: the full-args scan (`...command=`) and the exec-path
    scan (`...comm=`), the latter deriving argv[0] per line from the last scan.
    """
    ps_iter = iter(ps_outputs)
    last_ps = {"stdout": ""}

    def runner(argv, timeout=None):
        cmd = argv[0]
        if cmd == "ps":
            spec = argv[-1]
            if "command=" in spec:
                last_ps["stdout"] = next(ps_iter)
                return Out(last_ps["stdout"])
            lines = []
            for line in last_ps["stdout"].splitlines():
                parts = line.split(None, 4)
                if len(parts) == 5:
                    pid, _ppid, _rss, _time, command = parts
                    lines.append(f"{pid} {command.split(None, 1)[0]}")
            return Out("\n".join(lines) + ("\n" if lines else ""))
        if cmd == "sw_vers":
            return Out("ProductName:\t\tmacOS\nProductVersion:\t\t26.5.2\nBuildVersion:\t\t25F84\n")
        if cmd == "uname":
            return Out("25.5.0\n")
        if cmd == "sysctl":
            return Out(SYSTEM_FACTS[argv[-1]])
        if cmd == "git":
            # git -C <root> <subcommand> ...
            sub = argv[3]
            if sub == "status":
                return Out("" if status_paths is None else status_paths)
            if sub == "rev-parse":
                return Out("d75274d\n")
            return Out("")
        if cmd == MOD.FOOTPRINT_BIN:
            return Out(
                "======================================================================\n"
                f"proc [{argv[-1]}]: 64-bit    Footprint: 960 KB (16384 bytes per page)\n"
                "======================================================================\n"
                "\n"
                "Auxiliary data:\n"
                "    phys_footprint: 976 KB\n"
                "    phys_footprint_peak: 976 KB\n"
            )
        return Out("", 127)

    return runner


def fake_mono(values):
    it = iter(values)

    def clock():
        return next(it)

    return clock


# --------------------------------------------------------------------------
# CPU time parsing


class CpuTime(unittest.TestCase):
    def test_mm_ss(self):
        self.assertAlmostEqual(MOD.parse_cpu_time("0:00.00"), 0.0)
        self.assertAlmostEqual(MOD.parse_cpu_time("0:00.07"), 0.07)
        self.assertAlmostEqual(MOD.parse_cpu_time("33:20.89"), 33 * 60 + 20.89)

    def test_hh_mm_ss(self):
        self.assertAlmostEqual(MOD.parse_cpu_time("1:02:03"), 1 * 3600 + 2 * 60 + 3)

    def test_day_hh_mm_ss(self):
        self.assertAlmostEqual(MOD.parse_cpu_time("1-02:03:04.89"),
                               1 * 86400 + 2 * 3600 + 3 * 60 + 4.89)
        self.assertAlmostEqual(MOD.parse_cpu_time("10-00:00:01"), 10 * 86400 + 1)

    def test_unparseable_raises(self):
        for bad in ("abc", "1:2:3:4", "", "12", None):
            with self.assertRaises(ValueError):
                MOD.parse_cpu_time(bad)


# --------------------------------------------------------------------------
# footprint parsing


class Footprint(unittest.TestCase):
    def test_phys_footprint_is_authoritative(self):
        text = (
            "======================================================================\n"
            "bash [7]: 64-bit    Footprint: 960 KB (16384 bytes per page)\n"
            "======================================================================\n"
            "\n"
            "Auxiliary data:\n"
            "    phys_footprint: 976 KB\n"
            "    phys_footprint_peak: 976 KB\n"
        )
        phys, peak, head = MOD.parse_footprint(text)
        self.assertAlmostEqual(phys, 976 / 1024)
        self.assertAlmostEqual(peak, 976 / 1024)
        self.assertAlmostEqual(head, 960 / 1024)

    def test_gi_multiples(self):
        self.assertAlmostEqual(MOD._as_mib("1 GB"), 1024.0)
        self.assertAlmostEqual(MOD._as_mib("0.5 MB"), 0.5)


# --------------------------------------------------------------------------
# service discovery / classification


class Discovery(unittest.TestCase):
    def row(self, pid, ppid, argv, rss=1000, cpu=0.0, exec_path=None):
        return {"pid": pid, "ppid": ppid, "rss_kib": rss, "cpu_time": cpu,
                "argv": argv, "exec_path": exec_path}

    def test_full_argv_paths_discover_services(self):
        procs = [
            self.row(100, 1, "python3 /Users/example/Documents/code/house/local-models/server/serve.py --port 8080"),
            self.row(102, 1, "python3 -m mlx_vlm.server --host 127.0.0.1"),
            self.row(103, 1, "/Users/example/.local/bin/screenctx"),
            self.row(104, 1, "/Applications/LocalModelsBar/Contents/MacOS/LocalModelsBar"),
            self.row(105, 1, "python3 -m pocket_tts --port 8081"),
            self.row(106, 1, "/Applications/Usage.app/Contents/MacOS/Usage"),
        ]
        MOD.classify(procs)
        got = {p["pid"]: p["service"] for p in procs}
        self.assertEqual(got[100], "local-models-daemon")
        self.assertEqual(got[102], "local-models-vision-server")
        self.assertEqual(got[103], "screenctx")
        self.assertEqual(got[104], "local-models-bar")
        self.assertEqual(got[105], "pocket-tts")
        self.assertEqual(got[106], "usage")

    def test_descendants_are_inherited(self):
        procs = [
            self.row(100, 1, "python3 .../local-models/server/serve.py"),
            self.row(101, 100, "python3 /Users/example/.local/libexec/worker.py"),
            self.row(102, 101, "python3 /Users/example/helper.py"),
            self.row(999, 1, "/usr/sbin/mds"),
        ]
        MOD.classify(procs)
        self.assertEqual(procs[1]["service"], "local-models-daemon")
        self.assertEqual(procs[1]["relationship"], "descendant")
        self.assertEqual(procs[1]["child_of"], 100)
        self.assertEqual(procs[2]["relationship"], "descendant")
        self.assertEqual(procs[2]["child_of"], 100)
        self.assertIsNone(procs[3]["service"], "unrelated process must be excluded")

    def test_dictation_helper_via_descendant(self):
        # argv[0] has a space, so the exec_path must be supplied for the anchor.
        procs = [
            self.row(200, 1, "/Applications/Local Dictation.app/Contents/MacOS/Local Dictation",
                     exec_path="/Applications/Local Dictation.app/Contents/MacOS/Local Dictation"),
            self.row(201, 200, "python3 /Users/example/.local/libexec/mlx_helper.py --model x"),
        ]
        MOD.classify(procs)
        self.assertEqual(procs[0]["service"], "dictation")
        self.assertEqual(procs[1]["service"], "dictation")
        self.assertEqual(procs[1]["relationship"], "descendant")

    def test_process_closure_includes_all_descendants_only(self):
        procs = [self.row(500, 1, "screenctx"),
                 self.row(501, 500, "helper"),
                 self.row(502, 501, "helper"),
                 self.row(600, 1, "screenctx")]
        self.assertEqual(MOD.process_closure(procs, [500]), {500, 501, 502})

    def test_explicit_exclusion_overrides_service_matches(self):
        # All rows would match without exclusion. This exercises the closure,
        # rather than relying on a sampler name not matching a service rule.
        procs = [self.row(500, 1, "screenctx"),
                 self.row(501, 500, "screenctx"),
                 self.row(502, 501, "screenctx"),
                 self.row(600, 1, "screenctx")]
        MOD.classify(procs, exclude_pids=[500])
        self.assertTrue(all(row["service"] is None for row in procs[:3]))
        self.assertEqual(procs[3]["service"], "screenctx")

    def test_custom_matchers(self):
        Matcher = MOD.Matcher
        matchers = (Matcher("custom", "cg", "exe", "custom-marker"),)
        procs = [self.row(1, 0, "/usr/local/bin/custom-marker-tool --flag"),
                 self.row(2, 0, "sleep nothing")]
        MOD.classify(procs, matchers=matchers)
        self.assertEqual(procs[0]["service"], "custom")
        self.assertIsNone(procs[1]["service"])

    def test_anchor_matches_entrypoint_not_argument_text(self):
        # A matcher must fire on the executable/entrypoint, never on a mention of
        # the name in an argument (--git-repo local-tts) or a shell command.
        self.assertIsNone(MOD.match_service(
            "python3 /usr/local/bin/performance-snapshot --git-repo local-tts"))
        self.assertIsNone(MOD.match_service(
            "python3 /usr/local/bin/performance-snapshot --git-repo /Users/example/workspace/local-tts"))
        self.assertIsNone(MOD.match_service(
            "zsh -c \"cd /repo/local-tts && make\""))
        self.assertIsNone(MOD.match_service("bash /repo/local-tts/run.sh"))
        self.assertIsNone(MOD.match_service("git -C /repo/local-tts status"))

    def test_shell_echo_of_an_app_path_is_not_a_service(self):
        # The bundle matcher must anchor to the executable path, not to a path
        # merely printed in an argument (shell echo).
        self.assertIsNone(MOD.match_service('bash -c "echo /Applications/Usage.app"'))
        self.assertIsNone(MOD.match_service('zsh -c "echo /Applications/Local Dictation.app"'))
        self.assertIsNone(MOD.match_service('echo /Applications/RTI.app/Contents/MacOS/RTI'))

    def test_exact_live_forms_match(self):
        # Exact argv captured from the running fleet one-shot ps.
        py = "/Library/Frameworks/Python.framework/Versions/3.14/Resources/Python.app/Contents/MacOS/Python"
        # PID 1175: vision server run via uvicorn ASGI target.
        m = MOD.match_service(py + " -m uvicorn mlx_vlm.server:app --host 127.0.0.1 --port 8080", exec_path=py)
        self.assertEqual(m.label, "local-models-vision-server")
        # PID 1476: vision server run as a module.
        m = MOD.match_service(py + " -m mlx_vlm.server --port 8080", exec_path=py)
        self.assertEqual(m.label, "local-models-vision-server")
        # PID 79268: the local-models daemon, Python.app interpreter, real home path.
        m = MOD.match_service(
            py + " /Users/example/Documents/code/house/local-models/server/serve.py --ensure-vision",
            exec_path=py)
        self.assertEqual(m.label, "local-models-daemon")
        # PID 19220: Local Models menu bar app (bundle name has a space).
        lm = "/Applications/Local Models.app/Contents/MacOS/LocalModelsBar"
        self.assertEqual(MOD.match_service(lm, exec_path=lm).label, "local-models-bar")
        # PID 98779: local-tts service binary.
        ptts = "/Users/example/.local/libexec/local-tts/pocket-tts --server --port 8081"
        self.assertEqual(MOD.match_service(ptts, exec_path="/Users/example/.local/libexec/local-tts/pocket-tts").label,
                         "pocket-tts")
        # PID 98622: screen context collector.
        sc = "/Users/example/.local/bin/screenctx collect"
        self.assertEqual(MOD.match_service(sc, exec_path="/Users/example/.local/bin/screenctx").label, "screenctx")

    def test_bundle_executable_names_are_space_safe(self):
        # App bundle names contain spaces; exe_basename must not truncate them.
        self.assertEqual(
            MOD.exe_basename("/Applications/Quick Launch.app/Contents/MacOS/Quick Launch"),
            "Quick Launch")
        self.assertEqual(
            MOD.exe_basename("/Applications/Local Dictation.app/Contents/MacOS/Local Dictation"),
            "Local Dictation")
        # trailing args must not corrupt the bundle name extraction
        self.assertEqual(
            MOD.exe_basename("/Applications/Quick Launch.app/Contents/MacOS/Quick Launch --flag"),
            "Quick Launch")
        # non-bundle executables still resolve to the basename
        self.assertEqual(MOD.exe_basename("python3 /x/y.py"), "python3")
        self.assertIsNone(MOD.exe_basename(""))


class Privacy(unittest.TestCase):
    def test_records_never_carry_raw_argv(self):
        procs = [
            {"pid": 100, "ppid": 1, "rss_kib": 50, "cpu_time": 1.0,
             "argv": "python3 /Users/example/Documents/code/house/local-models/server/serve.py --private --token ABC"},
        ]
        MOD.classify(procs)
        rec = MOD.record_for_output(procs[0])
        self.assertEqual(set(rec), {"pid", "ppid", "service", "group", "executable",
                                    "relationship", "child_of", "rss_kib", "cpu_time"})
        dumped = json.dumps(rec)
        self.assertNotIn("local-models/server/serve.py", dumped)
        self.assertNotIn("--token", dumped)
        self.assertNotIn("ABC", dumped)
        self.assertEqual(rec["executable"], "python3")


# --------------------------------------------------------------------------
# summary aggregation


class Summary(unittest.TestCase):
    def rec(self, pid, service, rss_kib, cpu_time, child_of=None, rel="matched"):
        return {"pid": pid, "ppid": 1, "service": service, "group": "g",
                "executable": "x", "relationship": rel, "child_of": child_of,
                "rss_kib": rss_kib, "cpu_time": cpu_time}

    def test_cpu_delta_and_percent(self):
        snapshots = [
            {"index": 0, "elapsed": 0.0, "ts": "t0", "processes": [self.rec(10, "s", 1000, 1.0)]},
            {"index": 1, "elapsed": 5.0, "ts": "t1", "processes": [self.rec(10, "s", 2000, 3.0)]},
            {"index": 2, "elapsed": 10.0, "ts": "t2", "processes": [self.rec(10, "s", 1500, 5.0)]},
        ]
        row = MOD.build_summary(snapshots)[0]
        self.assertEqual(row["pid"], 10)
        self.assertEqual(row["samples"], 3)
        self.assertEqual(row["cpu_delta_seconds"], 4.0)  # 5.0 - 1.0
        self.assertEqual(row["cpu_percent_of_one_core"], 40.0)  # 4.0 / 10.0 * 100
        self.assertEqual(row["observed_seconds"], 10.0)
        self.assertEqual(row["rss_kib_median"], 1500.0)
        self.assertAlmostEqual(row["rss_mib_median"], 1500 / 1024, places=2)

    def test_late_joiner_uses_its_own_window(self):
        snapshots = [
            {"index": 0, "elapsed": 0.0, "ts": "t0", "processes": [self.rec(10, "s", 1000, 1.0)]},
            {"index": 1, "elapsed": 5.0, "ts": "t1",
             "processes": [self.rec(10, "s", 1000, 1.5), self.rec(20, "s", 500, 0.0)]},
            {"index": 2, "elapsed": 10.0, "ts": "t2",
             "processes": [self.rec(10, "s", 1000, 2.0), self.rec(20, "s", 500, 0.2)]},
        ]
        rows = {r["pid"]: r for r in MOD.build_summary(snapshots)}
        self.assertEqual(rows[20]["observed_seconds"], 5.0)
        self.assertEqual(rows[20]["cpu_delta_seconds"], 0.2)
        self.assertEqual(rows[20]["cpu_percent_of_one_core"], 4.0)

    def test_single_sample_has_no_percent(self):
        snapshots = [{"index": 0, "elapsed": 0.0, "ts": "t0", "processes": [self.rec(10, "s", 1000, 1.0)]}]
        row = MOD.build_summary(snapshots)[0]
        self.assertIsNone(row["cpu_percent_of_one_core"])
        self.assertEqual(row["cpu_delta_seconds"], 0.0)

    def test_dying_process_measured_until_it_exits(self):
        snapshots = [
            {"index": 0, "elapsed": 0.0, "ts": "t0", "processes": [self.rec(30, "s", 1000, 1.0)]},
            {"index": 1, "elapsed": 3.0, "ts": "t1", "processes": [self.rec(30, "s", 1200, 1.5)]},
            {"index": 2, "elapsed": 6.0, "ts": "t2", "processes": []},
        ]
        row = MOD.build_summary(snapshots)[0]
        self.assertEqual(row["observed_seconds"], 3.0)
        self.assertEqual(row["cpu_delta_seconds"], 0.5)


# --------------------------------------------------------------------------
# environment + git provenance


class Env(unittest.TestCase):
    def test_env_facts_and_git(self):
        runner = make_runner([], status_paths=" M foo.swift\n?? bar.txt\n")
        env = MOD.env_info(runner)
        self.assertEqual(env["chip"], "Apple M5")
        self.assertEqual(env["os_name"], "macOS")
        self.assertEqual(env["os_version"], "26.5.2")
        self.assertEqual(env["os_build"], "25F84")
        self.assertEqual(env["kernel_release"], "25.5.0")
        self.assertEqual(env["performance_cores"], 4)
        self.assertEqual(env["efficiency_cores"], 6)
        self.assertEqual(env["cpu_physical_cores"], 10)
        self.assertEqual(env["memory_mib"], 32768.0)
        # no identifying hardware fields
        self.assertNotIn("uuid", json.dumps(env).lower())
        self.assertNotIn("serial", json.dumps(env).lower())

        git = MOD.git_info(["/tmp/some-repo"], runner)
        self.assertEqual(git[0]["revision"], "d75274d")
        self.assertTrue(git[0]["head_dirty"])
        self.assertEqual(git[0]["dirty_paths"], ["foo.swift", "bar.txt"])

    def test_git_path_normalizes_home(self):
        # A repo path under the real home dir must be emitted as `~`, never with
        # the username (the earlier /tmp-masked test did not exercise this).
        home = str(Path.home())
        repo = os.path.join(home, "Documents", "code", "house", "design-system")
        runner = make_runner([], status_paths=" M foo.swift\n")
        git = MOD.git_info([repo], runner)
        self.assertTrue(git[0]["path"].startswith("~"), git[0]["path"])
        self.assertNotIn(home, git[0]["path"])
        # the git command still ran against the real resolved path
        self.assertEqual(git[0]["revision"], "d75274d")


# --------------------------------------------------------------------------
# end-to-end snapshot with mocked commands + clock


class Snapshot(unittest.TestCase):
    def test_full_snapshot_is_wired_and_sanitised(self):
        ps0 = (
            "100  1  50000  0:01.00 python3 /Users/example/Documents/code/house/local-models/server/serve.py\n"
            "101  100  20000  0:00.00 python3 /Users/example/.local/libexec/child.py\n"
            "999  1  60000  5:00.00 /usr/sbin/mds\n"
        )
        ps1 = (
            "100  1  50000  0:01.50 python3 /Users/example/Documents/code/house/local-models/server/serve.py\n"
            "101  100  20000  0:00.20 python3 /Users/example/.local/libexec/child.py\n"
            "999  1  60000  5:00.00 /usr/sbin/mds\n"
        )
        ps2 = (
            "100  1  50000  0:02.00 python3 /Users/example/Documents/code/house/local-models/server/serve.py\n"
            "999  1  60000  5:00.00 /usr/sbin/mds\n"
        )
        runner = make_runner([ps0, ps1, ps2])
        config = {"samples": 3, "interval": 0.0, "duration": 0.0, "footprint": False,
                  "footprint_timeout": 5.0, "git_repos": ["/tmp/repo"], "no_raw": False}

        with mock.patch.object(MOD, "mono_clock", fake_mono([0.0, 0.0, 1.0, 2.0, 2.0])), \
                mock.patch.object(MOD, "sleep", lambda s: None):
            snap = MOD.snapshot_fleet(config, runner)

        self.assertEqual(snap["schema_version"], 1)
        self.assertEqual(snap["tool"]["name"], "performance-snapshot")
        # environment
        self.assertEqual(snap["environment"]["chip"], "Apple M5")
        self.assertEqual(snap["environment"]["os_version"], "26.5.2")
        self.assertEqual(snap["environment"]["cpu_physical_cores"], 10)
        self.assertEqual(snap["environment"]["memory_mib"], 32768.0)
        # git
        self.assertEqual(snap["git_repositories"][0]["revision"], "d75274d")
        self.assertEqual(snap["git_repositories"][0]["dirty_paths"], ["foo.swift", "bar.txt"])
        # sampling
        self.assertEqual(snap["sampling"]["sample_count"], 3)
        self.assertIn("local-models-daemon", snap["sampling"]["matched_services"])
        self.assertEqual(snap["sampling"]["wall_elapsed_seconds"], 2.0)
        # processes
        procs = {p["pid"]: p for p in snap["processes"]}
        self.assertNotIn(999, procs, "unrelated process must be excluded")
        self.assertEqual(procs[100]["service"], "local-models-daemon")
        self.assertEqual(procs[100]["relationship"], "matched")
        self.assertEqual(procs[100]["cpu_delta_seconds"], 1.0)
        self.assertEqual(procs[100]["cpu_percent_of_one_core"], 50.0)
        self.assertEqual(procs[101]["relationship"], "descendant")
        self.assertEqual(procs[101]["child_of"], 100)
        self.assertEqual(procs[101]["cpu_delta_seconds"], 0.2)
        self.assertEqual(procs[101]["cpu_percent_of_one_core"], 20.0)
        # privacy: raw argv, private path fragments never reach the JSON
        dumped = json.dumps(snap)
        self.assertNotIn("local-models/server/serve.py", dumped)
        self.assertNotIn("child.py", dumped)
        self.assertNotIn("/Users/example", dumped)
        self.assertNotIn("\"argv\"", dumped)
        # limitations
        self.assertTrue(any("RSS is resident set size" in l for l in snap["limitations"]))
        self.assertTrue(any("footprint(1) not run" in l for l in snap["limitations"]))

    def test_tool_and_its_children_are_not_classified(self):
        # A snapshot invoked as `performance-snapshot --git-repo local-tts` must
        # not classify ITSELF (or its transient children) as a service: the
        # matcher anchors to the entrypoint, not to the argument text.
        ps = (
            "100  1  30000  0:01.00 /Users/example/.local/libexec/local-tts/pocket-tts --server --port 8081\n"
            "500  1  40000  0:00.10 python3 /usr/local/bin/performance-snapshot --git-repo local-tts\n"
            "501  500  20000  0:00.00 python3 -c pass\n"
        )
        runner = make_runner([ps])
        config = {"samples": 1, "interval": 0.0, "duration": 0.0, "footprint": False,
                  "footprint_timeout": 5.0, "git_repos": ["/tmp/repo"], "no_raw": True}
        with mock.patch.object(MOD, "mono_clock", lambda: 0.0), \
                mock.patch.object(MOD, "sleep", lambda s: None):
            snap = MOD.snapshot_fleet(config, runner)
        pids = {p["pid"] for p in snap["processes"]}
        self.assertIn(100, pids, "the real pocket-tts service must be tracked")
        self.assertNotIn(500, pids, "the tool itself must not be classified")
        self.assertNotIn(501, pids, "the tool's child must not be classified")
        self.assertNotIn("local-tts", snap["sampling"]["matched_services"])

    def test_footprint_when_enabled(self):
        ps = "100  1  50000  0:01.00 python3 .../local-models/server/serve.py\n"
        runner = make_runner([ps])
        config = {"samples": 1, "interval": 0.0, "duration": 0.0, "footprint": True,
                  "footprint_timeout": 5.0, "git_repos": ["/tmp/repo"], "no_raw": True}
        with mock.patch.object(MOD, "mono_clock", lambda: 0.0), \
                mock.patch.object(MOD, "sleep", lambda s: None):
            snap = MOD.snapshot_fleet(config, runner)
        self.assertIsNotNone(snap["footprint"])
        self.assertEqual(snap["footprint"][0]["phys_footprint_mib"], 976 / 1024)
        self.assertFalse(snap["limitations"][-1].startswith("footprint(1) not run"))


class Main(unittest.TestCase):
    def test_refuses_to_run_as_root(self):
        with mock.patch("os.geteuid", return_value=0):
            rc = MOD.main(["--samples", "2"])
        self.assertEqual(rc, 2)

    def test_list_services(self):
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = MOD.main(["--list-services"])
        self.assertEqual(rc, 0)
        self.assertIn("local-models-daemon\tlocal-models\tscript\tlocal-models/server/serve.py", buf.getvalue())

    def test_rejects_samples_less_than_one(self):
        # Raw `--samples <= 0` must exit 2, not silently clamp to one sample.
        self.assertEqual(MOD.main(["--samples", "0"]), 2)
        self.assertEqual(MOD.main(["--samples=-1"]), 2)
        self.assertEqual(MOD.main(["--samples", "-1"]), 2)

    def test_write_snapshot_writes_json(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            path = MOD.write_snapshot({"schema_version": 1, "hello": "world"}, tmp, "snap")
            self.assertTrue(path.exists())
            self.assertEqual(json.loads(path.read_text())["hello"], "world")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
