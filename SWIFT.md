# House Swift (the code rule)

The one Swift rule for the native Apple apps: every Swift target under
`house/`, macOS today and iOS on the same tokens. `DESIGN.md` says how an app
looks; this file says how its Swift is written, tested, and built. Rust apps
(Local Dictation) follow their own crate conventions and only the design rule.

## The rule in six lines

1. A service that owns I/O (files, SQLite, Keychain, child processes, the network, audio) is an `actor`. State the UI reads is a `@MainActor final class`.
2. `@unchecked Sendable` carries a comment naming what guards the state. `nonisolated(unsafe)` is debt: allowed only with a comment and a ticket to remove it.
3. New concurrency is structured: `async let`, task groups, `AsyncStream`. `DispatchQueue` and `Task {}` fire-and-forget are legacy; do not add more.
4. New test targets use Swift Testing. A repo on XCTest stays on XCTest until it migrates whole; never mix the two in one target.
5. Views are SwiftUI. AppKit or UIKit is the seam only: windows, status items, hotkeys, Accessibility, capture, audio. Every colour, size, and radius comes from `House.` (DESIGN.md).
6. The deployment target wins over any skill or article. Do not use an API newer than the target's floor; do not raise a floor to use one.

## Platform floors

| Repo | Floor | Tools | Tests | Status |
| --- | --- | --- | --- | --- |
| quick-launch | macOS 26 | 6.2 | Swift Testing | The reference repo. |
| rti | macOS 14 | Xcode, Swift 6.0 | XCTest | Highest legacy count (DispatchQueue, `nonisolated(unsafe)`). |
| cotype, usage-menubar, local-models | macOS 14 | 5.10 | XCTest | Hold at floor; migrate as a unit, not per file. |
| memory-recall | macOS 14 | 5.9 | XCTest | Same hold; the one repo below 5.10. |
| a new app | macOS 26, or iOS 26 | 6.2, `swiftLanguageMode(.v6)` | Swift Testing | Starts on the rule from day one. |

A repo's `CLAUDE.md` states its floor. Raising a floor is a deliberate act in
that repo, recorded in its `CLAUDE.md` and `Package.swift` or `project.yml`.

## iOS

An iOS app is a house app: same tokens, same rule, same registry.

- The `HouseDesign` product compiles on both platforms (the package declares macOS 14 and iOS 17). `NSColorToken` on AppKit, `UIColorToken` on UIKit, `ColorToken` on both. Depend on the package by GitHub URL and tag, as on macOS. `HouseUIKit` is AppKit only and is empty on iOS.
- Build with an `xcodegen` `project.yml` (the RTI pattern), not a bare SwiftPM executable: iOS needs a bundle, signing, and a simulator destination.
- Verify on the simulator: `xcodebuild -project X.xcodeproj -scheme X -destination 'platform=iOS Simulator,name=iPhone 17' build test`.
- Register iOS surfaces in `components.json` before building them, with a render proof in both appearances, as on macOS.
- Dynamic Type is not optional on iOS: use the matching text styles from the type scale, and test at the largest accessibility size.

## Skills

Three plugins are installed at user scope and fire on their own when the work
matches. Invoke them by name for a review pass.

| Skill | Use |
| --- | --- |
| `/swift-concurrency-pro` | Before touching actors, `Sendable`, tasks, streams, or a strict-concurrency error. Run it on any RTI change. |
| `/swift-testing-pro` | Writing or migrating tests in a Swift Testing repo. |
| `/swiftui-pro` | New views, navigation, state flow, VoiceOver, Reduce Motion. Complements DESIGN.md; it never overrides a token. |

They assume Swift 6.2 and OS 26. On a macOS 14 or 5.10 repo their advice is
directional: take the pattern, keep the floor (rule 6). More skills exist in
Paul Hudson's catalogue (accessibility, App Store, simulator); add one only
when a repo has the need, and record it here.

## Build and verify

- SwiftPM repos: `swift build`, `swift test`, then the repo's `scripts/build-app.sh` and `make install` or `scripts/install.sh`.
- RTI: `xcodebuild -project RTI/RTI.xcodeproj -scheme RTI build`, then `scripts/install-local.sh`.
- Before reporting done: tests green, `$DS/bin/design-lint --strict` clean on touched files, and the app opened and seen.
- No `/Users/...` paths, no shell interpolation in `Process`, secrets in Keychain or a 0600 file. Each repo's `CLAUDE.md` names its resolvers.

## Consuming the rule

`house-swift` (the global skill) loads this file on Swift work under `house/`
or any iOS app. A repo's `CLAUDE.md` links here and adds only what is local to
it: its floor, its seams, its resolvers. Do not copy the rule into a repo; a
copy drifts.
