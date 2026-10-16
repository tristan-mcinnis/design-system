# House performance audit

Audit completed 2026-09-06. This document owns the cross-house measurement plan and summary, not portfolio status. Implementation and detailed results belong in each affected repository.

## Result in plain language

Most of the small apps were already light at rest. The clearest waste was a duplicate model-server process tree, not the interface code. Three targeted changes shipped; the other apps were left alone.

| Area | Before | After | What this means |
| --- | --- | --- | --- |
| Duplicate vision server | Extra parent, worker and tracker; 831 MB combined reported footprint; wildcard port 8080 listener | Extra tree gone; only the original loopback vision listener remains | Removed redundant processes. This is not a claim that system-wide free RAM rose by exactly 831 MB. |
| Recall, live 3,725-file search | 344.32 ms total; 129 ms ranking | Installed: 320.58 ms total; 104 ms ranking | About 7% faster overall, about 19% faster ranking. Seven paired measured runs. |
| Recall, dense synthetic search | 119 ms total | Candidate: 96 ms total | About 19% faster on the fixed dense fixture. Nine measured runs. |
| Memory panel under a simulated slow read | 13 reads submitted, 8 outstanding | 6 submitted, at most 2 running/owed | Same five completed snapshots. Bounded queued work, not a measured normal-idle CPU saving. |
| TTS tuning | Default 22.69x/25.17x realtime on short/long phrases | Alternatives offered at most about 3.5%, within ordinary noise | Defaults retained. Lower decoder thread count was slower. |

The source audit covered all eleven house repositories, including the shared design rules. This was **not** a complete Instruments trace of every interaction. Hotkey-to-panel, typing stalls, real recording latency, energy/wakeups and long-duration leak tests remain unmeasured. Proposed budgets below are targets, not passed gates.

## Meaning of faster and lighter

- Responsive: time from user action to visible feedback, separately from time to finish work.
- Light at rest: CPU time, physical memory footprint, wakeups, and disk/network activity when hidden and inactive.
- Efficient at work: elapsed time, peak memory, CPU/GPU work per fixed task, without lowering quality.
- Reliable: no lost audio, stale/private context, missed clipboard entries, broken permissions, or changed output contracts.

### Reading the numbers

- **Median / p50:** the typical run. **p95:** 95 out of 100 runs should finish within that time; it exposes occasional bad delays that an average hides.
- **Cold / warm:** first use after loading versus use with the model/files already in memory. Always report them separately.
- **Physical footprint:** a better process-memory measure than RSS, which can hide compressed memory or count shared pages differently.
- **CPU % of one core:** 100% means one whole core is busy. A quiet menu-bar app should use a tiny fraction of that.
- **RTFx:** audio seconds produced per second of computation. 25x means ten seconds of audio take about 0.4 seconds to generate, excluding model loading and playback.

## Method and baseline

Host: Apple M5 MacBook Pro, 10 cores (4 performance / 6 efficiency), 32 GB, macOS 26.5.2. AC power. Historical M4 Max numbers are not this machine's baseline.

1. Read-only source audit in three parallel groups; independent risk triage.
2. Inventory installed executables and source revisions. A path does not prove an installed binary matches HEAD. Preserve existing dirty files.
3. Observe existing processes before changes. Baseline sampling: 31 samples over 61.37 seconds, using process cumulative CPU-time deltas. This is a live-session observation, not a controlled idle lab test. No builds during the observation.
4. Add repeatable, offline fixture benchmarks for selected changes. Run the same optimized release build settings before and after. Measure sequentially, not while other builds or models compete for resources. Separate first run from warmed runs. Record n, median and range; report p95 only with at least 30 samples.
5. Make only bounded, behavior-preserving changes. Run unit/regression tests, independent review and independent executable validation.
6. Back up installed artifacts and signing identity before replacement. Use each repo's sanctioned installation path. Never restart an active recorder. Verify launch/health, TCC, installed artifact identity and relevant smoke behavior. Keep rollback artifacts outside Git.
7. Record actual results, including failed gates and unmeasured items. Commit only owned files, not unrelated existing changes.

Observed baseline (RSS, not physical footprint; shared model pages may be counted twice):

| Process | CPU, % of one core | Median RSS MiB |
| --- | ---: | ---: |
| Usage | 0.163 | 26.25 |
| Memory | 0.033 | 30.88 |
| Cotype | 0.212 | 26.89 |
| RTI | 0.342 | 49.55 |
| Quick Launch | 0.033 | 110.55 |
| Local Dictation | 0.147 | 1496.81 |
| Dictation MLX helper | 0.000 | 1390.38 |
| screenctx | 0.407 | 138.39 |
| Local TTS | 0.000 | 6.56 |

A subsequent native `footprint --noCategories` reading gives a better memory screen: Dictation 980 MB, its MLX helper 1568 MB, TTS 331 MB, RTI 110 MB, screenctx 63 MB, Quick Launch 41 MB, Memory 18 MB, Usage 13 MB, Cotype 13 MB. This is one observation, not a leak test. It illustrates why RSS alone is misleading, especially for compressed/model memory.

A process-name-only inventory initially missed generic Python services. Socket and parent-process inspection added: Local Models menu-bar app 12 MB, daemon 20 MB, llama-server child 535 MB, loopback MLX vision server 2657 MB (historical process peak 10 GB). A second wildcard-bound MLX server also owns port 8080 with a 409 MB worker. Its ownership/consumers need checking before removal. These services must be included in future fleet baselines; low app memory does not mean the shared models cost nothing.

Sanitized initial evidence is in `docs/performance/20260906/initial-observation.json` and `initial-footprint.txt`. The follow-up Python/model process footprint readings above were separate one-shot commands, not part of that first artifact. This table alone establishes neither leaks nor a need to unload models.

## Repeatable fleet snapshot

Run from this repository while the machine is otherwise quiet:

```sh
python3 bin/performance-snapshot --duration 300 --interval 2 --footprint \
  --git-repo ../memory-menubar --git-repo ../memory-recall \
  --git-repo ../local-models --output-dir /tmp/house-performance
python3 -m unittest discover -s tests -p 'test_*.py'
```

The snapshot includes generic Python model services and descendant helpers, not just app names. Full process arguments are used for discovery in memory but are not saved. Physical-footprint queries happen after CPU sampling; this is not an energy or latency trace.

## Proposed benchmark budgets

These are engineering targets, not claimed measurements or universal Apple standards. Existing stricter repository contracts take precedence.

- UI feedback: warm hotkey-to-visible p95 <=100ms; identify main-thread stalls >50ms. Cold process launch-to-interactive <=1s for thin menu-bar apps, excluding model warmup and network authentication. Requires actual UI instrumentation, not process launch duration.
- Idle menu-bar process: average CPU <0.5% of one core over 5 quiet minutes. Collector: <1% in a defined static-window scenario; separately test low-AX OCR and normal AX windows. Inspect wakeups with Instruments; a timer is not automatically waste.
- Memory: measure physical footprint and peak working footprint where tooling permits. RSS is a screening metric only. Thin menu-bar apps: investigate >150 MiB steady footprint. Model-backed apps use explicit per-model budgets, not the thin-app ceiling. Flag sustained growth across repeated cycles, not a single warm cache.
- Cotype: keep repo's warm TTFT p50 <500ms / p95 <1.2s, decode >=20 tokens/s, cancellation <150ms; separately account for AX context and configured debounce. Verify contracts before applying these gates.
- Recall: preserve repo scan <1000ms and rank <500ms gates against a documented corpus. Use synthetic fixtures for reproducible comparisons; do not publish search results or personal captures.
- Audio: zero lost/duplicated frames and unchanged transcript behavior on fixed fixtures; record capture-to-first-output and stop-to-final-text. Report transcription real-time factor (processing seconds / audio seconds; lower is better).
- TTS: synthetic fixed phrases and voice; first audio byte separately from full generation; audio duration / generation seconds (higher is better). Compare thread settings locally, not against another chip's historical numbers. Never trade clipped audio for a faster number.
- Network/provider refresh: time to first usable result and all-results completion; mock deterministic delays and failures, avoid billing and rate-limit effects.
- Shipping performance gate: reproducible improvement on the intended path, ideally >=20% or a material absolute saving; no functional regressions. Improvements smaller than run-to-run noise are inconclusive, not wins.

## Harmonization boundaries

Standardize benchmark reporting, monotonic clocks, cold/warm terminology, cancellation checks, install provenance and rollback. Do not unify model runtimes, audio sample rates, deployment floors or polling intervals merely because they differ. Lazy models, background clipboard monitoring, pre-roll audio and capture cadence are product choices. Changing them needs an explicit trade-off rather than being disguised as optimization.

## Triage and scope

- Cotype: debounced per-generation AX traversal, not every keystroke. Keep privacy/focus rechecks and lazy model loading. Defer changes until a real UI profile identifies expensive calls. TTL context caching is not safely equivalent.
- Quick Launch: hidden clipboard monitoring is required behavior. Leave its cheap timer intact.
- Local Dictation: installed GUI uses a blocking idle worker; the 120ms experimental CLI listener is not its idle path. Keep pre-roll, warm model policy and audio protocol intact.
- Memory panel: investigate bounded single-flight polling to prevent stale queued work during slow subprocess reads. Test the delayed case, do not claim normal idle savings from that simulation.
- Recall: benchmark exact-output-preserving scan/rank changes on synthetic documents. No index, service or persistent cache.
- screenctx: unchanged low-AX windows can repeat OCR. Defer exact-image memoization until pixel stability and privacy invalidation are tested. Frame encoding already happens after change detection; all-display captures are required behavior. Existing G2 read-boundary verification is blocked by old hashes/paths, so do not ship capture changes on an unreviewed boundary.
- Usage: provider reads already update the panel incrementally and protect mutable accounting state. Leave serial polling intact.
- RTI: no measured recording bottleneck yet. No audio-pipeline changes.
- TTS: run an interleaved thread-only benchmark. Preserve trimming, temperature defaults and models in production.
- Local Models: managed-owner startup must wait rather than launch a competing server; unmanaged fallback must bind loopback and avoid a reload worker. This is a bounded ownership repair, not a runtime merger. Complete duplicate process-tree footprint measurement is 831 MB (parent 413 MB, worker 409 MB, tracker 10 MB, rounding applies), recorded in `docs/performance/20260906/duplicate-vision-before.txt`. Review and health checks precede cleanup. The old spawner is inferred from matching argv, not proven from the now-orphaned parentage.

## Harmonization follow-up, not bundled into this release

1. **Installation provenance and rollback:** add tested backup/restore support to the owning installers, including executable hashes, signed identities and source revision. Recall's symlink points directly into its build folder, so isolated candidate builds are essential until install time.
2. **User-action timing:** add small monotonic timing seams for hotkey-to-panel, context capture, first token and stop-to-final-transcript. Use Instruments App Launch / CPU Profiler / Animation Hitches for real UI traces. Do not compare configured debounce with inference time or report a mocked delay as live latency.
3. **Collector correctness gate first:** repair the separate read-boundary review fixture in its owning memory project before introducing OCR reuse. Then test exact pixels, window identity and privacy invalidation; never skip text changes based on perceptual hashes alone.
4. **Background work policy:** use single-flight/coalescing where stale queued work is useless, but retain each app's freshness contract. Memory's shared work queue can still delay search behind a slow read; measure that interaction before splitting queues.
5. **Model lifecycle:** one named process owner per backend, with explicit warm/unload behavior and budgets. Keep TTS, dictation and vision as separate runtimes unless a demonstrated benefit justifies moving them. Do not equate a warm model's retained memory with a leak.

## Shipped and verified

- **Memory.app**, commit `ebf464e`: signed bundle installed and opened, doctor exit 0, installed executable hash matches the reviewed build. 59 tests passed; independent static review passed; light/dark collection and search render fixtures visually passed. Poll wiring remains statically reviewed rather than integration-tested.
- **Recall**, commit `4f09eca`: installed, 80 tests passed, synthetic capture/CLI/JSON gates passed, and exact search-output comparison passed against a baseline rebuilt from archived commit `235072f`. The installed live paired numbers above are recorded in `../memory-recall/docs/performance/20260906/live-installed.json`. A stale pre-move Swift module cache initially blocked installation; cleaning generated build products and rebuilding fixed it.
- **Local Models**, commit `f116261`: 50 tests, daemon smoke and scrub passed. Restarted the daemon using `make restart`. Kept the original vision PID 1175 and its warm model. Gracefully terminated the verified duplicate parent and its surviving worker, then verified all three duplicate PIDs gone. The daemon restart released the old completion child, so the prior `s1-mini` warm state was explicitly restored. Health reports both vision and completion ready. Planned transcription remains unavailable by design.
- **Local TTS**, commits `4a61a41` and `54ed2c5`: benchmark tooling and evidence only, 26 tests passed. The follow-up corrects the result document's host attribution to M5. No service settings changed and no TTS restart.
- **Shared benchmark tool**: 65 design-system tests passed, including 30 snapshot tests. Live validation found and fixed both self-matching and generic-Python discovery errors before final evidence was retained. The final observation is `docs/performance/20260906/fleet-after.json`.

The final 60-second fleet observation is a health screen, not a controlled five-minute idle certification. It includes brief provider-helper processes and active collector work. Do not count lower freshly restarted app memory as an optimization gain. The two initial `GATES.md` user edits in recall and screenctx were preserved; only a separately staged new Recall G11 gate was committed.

## Recovery

Rollback artifacts are outside Git under `~/Library/Application Support/HousePerformance/rollback-20260906/`: original signed Memory.app, original recall executable, original launchd plists and a source archive of Local Models before changes.

- Memory: quit the app, move the current bundle aside, restore the preserved signed bundle to `/Applications/Memory.app`, verify its signature and reopen it.
- Recall: restore the preserved executable to the installed symlink target, then run `install.sh --no-build` and its read-only doctor check. The old executable SHA is recorded below.
- Local Models: if recovery is needed, restore `server/serve.py` and `server/backends/mlx_vlm.py` from the source archive and run `make restart`, checking model warm state again. Do not recreate the redundant wildcard-bound server.

Original backup executable hashes: Memory `bfefb16e10ea5222e4b0dc85dc685feaa22bd8bf11f6fa29476cd9c944890561`; recall `720737984c7bddf0ef4fc0c292a73f7cd581d63fd7a2ce19b68541b96f1a0f1b`.
Installed executable hashes: Memory `d3475a01254dcea071f90117bdb80193c6c395865e10042a6c56bddcfdeabf52`; recall `da98b7f45f7603c184a4a600c7d01fc9c994ccacd05ba401b1fdd7318296b572`.

No Git remotes were pushed. No audio capture settings, model weights, clipboard behavior, visual tokens or deployment floors changed.

## Follow-up completed, 2026-09-06

Real-use responsiveness benchmarking remained excluded. The user separately
requested a Local Dictation input-field repair, described below.

- **Background observation:** 181 samples over **912.75 seconds** on AC power.
  Steady-process CPU summed to **1.889% of one core**; summed endpoint footprints
  were **6366 → 6367 MiB**. No sustained growth signal appeared in this window.
  This is not battery-life, watts, controlled-idle, or leak-free certification.
  See `docs/performance/20260906-followup/soak-15min-2026-09-06.md` and its JSON.
- **Automatic installer recovery:** Memory `1a87602`, Usage `5b5e24f`, Recall
  `f6d724c`. Verified retained snapshots, honest unknown-source provenance,
  signature preservation, failure compensation and explicit rollback. Independent
  suites passed **87 assertions per bundle installer** and **125 for Recall**.
  Genuine signed bundles and compiled Recall versions also installed/rolled back
  in temporary destinations/checkouts. No live installation was replaced merely
  to test a script. Stale locks refuse rather than being stolen; snapshots are
  never auto-pruned. Details live in each repo's installer-safety document.
- **Repeated TTS use:** `51e52d7`. An isolated process completed **100/100** varied
  synthetic requests with no failures/timeouts, after three warmups. Physical
  footprint at warmup/10/50/100 was **1186/1187/1188/571 MiB**. The run lasted
  **30.68 seconds**, not 15 minutes; 900 seconds was its deadline. No sustained
  growth appeared at those four checkpoints; the final drop is not causally
  attributed. **51 + 26** Python tests and **2/2** actual CTest tests passed.
  See `../local-tts/docs/performance-followup-20260906.md` and its raw evidence.
- **TTS localhost correction:** the user explicitly approved removing LAN access.
  After the isolated test, the backed-up runtime was replaced and restarted.
  The sole 8081 listener is now **127.0.0.1:8081** and health passes. The plist
  and voice WAV hashes are unchanged. No audio-generation settings changed.
  Restoring its old binary would restore wildcard binding too.
- **Screen privacy gate:** `f9a33de`. Read-only SQLite opens no longer issue
  write-shaped pragmas. **54 Swift tests** passed, including remote-host,
  redirect, proxy, permissions and read-only rollback/WAL tests. The signed
  collector was deployed with its existing TCC identity and advancing ticks.
  Behavioral checks passed before the reviewed binary/five native source hashes
  were re-frozen; only the obsolete Python helper pin was removed. One Finder
  metadata file was corrected from 0644 to 0600, with no permission exception.
  Parent and independent full checks returned **MEMORY_SCREEN_RECALL_OK**, 3/3
  recall cases and an advancing tick. Missing/changed pins still fail closed.
  Memory-repo maintenance uses its automatic sync, not a manual commit.
- **User-added Local Dictation repair:** `3a8cb0d`. The focus gate rejected
  Ghostty's AX text area because it could not be written through AX. Known
  terminal text surfaces now reach the existing clipboard path; non-input
  controls and non-terminal read-only/unknown focus remain denied. A regression
  went red then green; independent suites passed **323/348** library tests and
  Release built. After explicit restart approval, the backed-up signed app was
  installed with the same designated requirement. Event-tap startup passed.
  The user subsequently confirmed the live paste. Post-restart logs showed three
  successful dictations, a Ghostty focus marker, and no no-field holds, injection
  failures or worker errors. See the owning repo's terminal-focus repair note.

Follow-up deployment backups are under
`~/Library/Application Support/HousePerformance/rollback-followup-20260906/`.
Other installers remain a later rollout of the tested convention. The existing
user edits in Recall and screenctx `GATES.md` were left untouched. No remotes
were pushed. These observations do not establish further speed or energy gains.
