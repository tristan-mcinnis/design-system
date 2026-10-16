# Chat surfaces (the house chat grammar)

One look for every house surface where a person asks and an app answers:
Quick Launch, RTI, Memory, Local Dictation, Cotype, Usage, Local Models.
The reference is Quick Launch's Quick AI (a 750 × 475 glass panel) and its
AI Chat window (a normal window). Both draw the same header, thread, and
composer views. Copy those views; do not redraw them from a screenshot.

Source of truth for this file: `quick-launch` on `main`, read 2026-09-12, and the
render proofs `quick-ai-*`, `b2-*`, `g1-*`, `att-*`, `search-*`. Every value is a
`House.` token from `tokens.json` unless the "Not a token yet" list names it.
Paths below are relative to `~/Documents/code/house/quick-launch/`.

## Type names: house versus Quick Launch aliases

Quick Launch reads tokens through `AQDesign` (`Sources/Views/DesignTokens.swift`).
Two of its names differ from the house names. This file uses house names only.

| This file | Size / weight | Quick Launch alias |
| --- | --- | --- |
| `House.TypeToken.body` | 14 regular, line height 1.55 | `AQDesign.TypeToken.prose` |
| `House.TypeToken.bodySmall` | 13 regular | `AQDesign.TypeToken.body` |
| `House.TypeToken.meta` | 12 regular | `metadata`, `detail` |
| subheading | `Font.system(size: House.TypeToken.Size.bodySmall, weight: .semibold)` (13) | `subheading` |
| glyphSmall | `Font.system(size: House.TypeToken.Size.body, weight: .semibold)` (14) | `glyphSmall` |
| glyphMedium | `Font.system(size: House.TypeToken.Size.heading, weight: .semibold)` (16) | `glyphMedium` |
| proseLineSpacing | `Size.body × LineHeight.body` minus SF's native line height (about 5 pt) | `proseLineSpacing` |

subheading, glyphSmall, and glyphMedium are derived from token sizes, not
tokens. Copy the three definitions from `DesignTokens.swift` lines 108 to 139.

## 1. Chat header

**Purpose.** It says what this chat is and which model answers next, and it
holds one way out and one hand-off.

**Anatomy.** Left toggle, title block, flexible space, right-side action.
There is no divider under it.

| Part | Spec |
| --- | --- |
| Row | `HStack(spacing: Spacing.sm)` (12). Height: `Control.input` (58) on a panel; `Control.composer` (52) in a window, where it is the title-bar row. Leading inset `Spacing.sm`; trailing inset `Spacing.lg` (20). |
| Left toggle | A `Control.compact` (28) square glyph button (`QuickAIGlyphButton`). Panel: `chevron.left`, back to search. Window: `sidebar.left`, shows or hides the chat list. glyphSmall in `textSecondary`. |
| Title block | `VStack(alignment: .leading, spacing: Spacing.xxs)`. Title in subheading `textPrimary`, one line, middle truncation. The model line under it is a `Button` in `meta` `textSecondary` that opens the model chooser. |
| Assistant prefix | In an assistant chat the model line starts with the assistant's name in `meta` `textPrimary` (its own button: Change Assistant), then `·` in `textTertiary`, then the model. |
| Source line | When an answer is not the model's (a command's output, a search), the line names the source as plain `meta` `textSecondary` text, not a button. |
| Right action (panel) | A labelled chip: `HStack(spacing: Spacing.xs)` of a glyph in `label`, the action title in `label`, and its `KeyCapGroup`. `textPrimary`, horizontal padding `Spacing.sm`, height `Control.chip` (28), `RoundedRectangle(cornerRadius: Radius.sm, style: .continuous)` filled `chipFill`. Quick AI: `arrow.up.right.square` "Open in AI Chat" `⌘J`. |
| Right action (window) | Glyph buttons at 28 square: `square.and.pencil` (New Chat) in glyphMedium `textPrimary`. The Keep on Top pin shows only while it is on, glyphSmall `textSecondary`, and a click turns it off. |

**Title rule.** Before the first answer the title is the surface name ("Quick
AI"). After it, the conversation title; the fallback is the first question.

**States.** Empty: surface name over the model. Streaming, stopped, queued,
error: unchanged, since state belongs to the thread and the composer.
Only a source change (command output, search) swaps the second line.

**Keys.** `esc` on a panel goes back, keeping the chat (after layers close and
typed text clears). `⌘\` toggles the rail in a window. The chip's key (`⌘J`)
works from anywhere. Change Model and Change Assistant have their own keys, in the button help text.

**Accessibility.** Glyph buttons carry `accessibilityLabel` and `.help` with the
key. The model button: label "Model: <name>", hint "Change the model", value
"Open" or "Closed" for the chooser. The rail toggle's value says "Open" or "Closed".

**Copy.** `Sources/Views/QuickAITitleBlock.swift` (title block, `QuickAIGlyphButton`,
`QuickAIAnnouncement`); the header bodies in `QuickAIView.swift` (`header`) and
`AIChatWindowView.swift` (`header`).

## 2. Thread

**Purpose.** One reading column: what you asked on the right, what came back
on the left, and nothing else competing.

**Column.** `ScrollView` over a `LazyVStack(alignment: .leading, spacing: Spacing.md)`.
Width at most `Layout.panelWidth − 2 × Spacing.lg` (710), centred with
`.frame(maxWidth: .infinity)`, so a wider window never stretches lines.
Padding: top `Spacing.xl` (24), sides `Spacing.lg`, bottom `Spacing.md`.

| Element | Spec |
| --- | --- |
| User pill | Right aligned. Text `bodySmall` `textSecondary`, wraps left aligned inside. Padding `Spacing.sm` horizontal, `Spacing.xs` vertical (about 31 high on one line). `RoundedRectangle(cornerRadius: Radius.pill, style: .circular)` filled `chipFill`. Max width `Layout.quickAIAnswerMaxWidth` (690). No "You" label. |
| Sent attachments | Over the pill, right aligned, wrapping (`ChipFlowLayout`, `Spacing.xs` gaps), same max width. See section 4. |
| Answer prose | `MarkdownTextView`, left, `body` (14) `textPrimary`, line height 1.55 through proseLineSpacing. Max width `Layout.quickAIAnswerMaxWidth`. No card, no fill, no "Answer" label. |
| Code block | Inside the prose: `Radius.sm`, `surfaceTint` fill, `stroke` hairline. A header strip `Control.compact + Spacing.xxs` (32) high on `well`, with the language in `code` `textTertiary`, then Wrap and Copy. `HouseDivider` under the strip. Wrap starts off. |
| Tool or status line | A glyph in `bodySmall` `textTertiary` in a fixed `Control.keyCap` (20) column, `Spacing.xs` gap, text in `bodySmall` `textTertiary`, one line, tail truncation, min height 20. Consecutive lines group at `Spacing.xs`. Web search: `globe`. Thinking with no text yet: `ThinkingIndicator` in the glyph slot and "Thinking…" (or the status). Accent is never used, not even for the globe. |
| Sources list | Under the prose, `VStack(spacing: Spacing.xxs)`, max width 690. Each row: `doc.text` in `meta` `textTertiary` in the 20 column, the title in `meta` `textSecondary` (middle truncation), the day in `meta` `textTertiary`. At most 5 rows; then "N more in ⌘K › Open Source" in `meta` `textTertiary`, inset `Control.keyCap + Spacing.xs`. A row with a local file is a button that opens it. |
| Error line | Under the failed question, in the tool line's place: `exclamationmark.triangle` and the message in `bodySmall` `danger` (two lines max), a spacer, then a `KeyHint` "Retry" with `⌘R` as a button. |
| Question card | When the model asks: `raisedCard`, padding `Spacing.sm`, max width `Layout.answerMaxWidth` (620), option rows `Control.row` (40) with the house selection. After the pick it stays as a read-only record. |
| Latest chip | `HouseChip("Latest", icon: "arrow.down")` on `raisedCard(radius: Radius.sm, fill: surfaceRaised)` with the `card` shadow, centred over the composer, bottom padding `Spacing.xs`. |
| Empty hints | Three lines in `bodySmall` `textTertiary`, centred in the thread, `Spacing.xs` apart, each naming a way in with its real key. |
| Notice line | After a hand-off, a stop, a move, or a delete: one tool line (for example `terminal` "Opened in pi · tmux session ql-…"). |

**States.**

| State | What the thread draws |
| --- | --- |
| Empty | The empty hints only. |
| Searching | The question as a pill at once, the search line under it. Nothing else. The previous answer has already left. |
| Streaming | The status line until text lands, then live prose with a caret. It follows the bottom only while the reader is within `Control.row` (40) of it. |
| Scrolled up while streaming | The view stays still. The Latest chip shows (only when the content is taller than the view). A click or `⌘↓` returns and follows again. |
| Stopped | `esc` during the answer keeps the question and the text that arrived, drawn as a normal answer with no "stopped" mark. `⌘R` asks the same turn again. A stop during the search puts the question back in the composer. |
| Queued | The thread is unchanged. The queue shows in the composer only. |
| Error | The error line under its question, with Retry. The failed question stays but is not sent to the model again. An error that belongs to no turn (permission, no key) goes above the composer (section 3). |

**Collapse rules.** Only user turns collapse. Answers always draw in full.
The threshold is measured at the pill's width (about 105 characters a line).
The control sits inside the pill: a chevron in `micro` semibold and "Show more"
or "Collapse" in `meta` `textSecondary`, padding `Spacing.xs`, on `chipFill` at
`Radius.sm`. `⇧⌘M` toggles the newest collapsible turn, and only that turn shows
the key caps. A toggle scrolls the message's first line to the top.

**Keys.** PageUp and PageDown (or `⌥↑` `⌥↓` on an empty composer) scroll a page
(the view height less `Spacing.xxxl`). `⌘↑` and `⌘↓` jump to the top and the
bottom. `⌘R` asks again. `⌘[` and `⌘]` switch chats. The question card keeps
`↑↓` and `↩` while it is live.

**Accessibility.** The pill reads "You: <text>" to VoiceOver (a spoken label,
never a drawn one). Errors post a high-priority announcement ("Error. …");
notices and composer confirmations post medium priority. With Reduce Motion,
scrolls jump without animation and the thinking dots stand still at 55 %.
Tool lines combine into one element each; the sources list is a container named "Sources".

**Copy.** `Sources/Views/QuickAIThread.swift` (whole file),
`CollapsibleMessageText.swift`, `MarkdownTextView.swift`, `CodeBlockView.swift`,
`AskUserQuestionCard.swift`; `ThinkingIndicator` from `OverlayView.swift` (line 1368).

## 3. Composer row

**Purpose.** One row along the bottom edge that asks, shows what `↩` will do,
and opens context and actions. On a chat surface it is the footer.

**Anatomy.** `HStack(alignment: .bottom, spacing: Spacing.xs)`, padded
`Spacing.xs` on all sides. The row is `Control.pill` (36) high, so the row plus its
inset is 52 (`QuickAIView.composerRowHeight`).

| Part | Spec |
| --- | --- |
| Plus circle | `plus` in glyphMedium `textPrimary`, a `Control.pill` circle filled `surfaceTint` with a `stroke` hairline. Opens Add Context; `@` typed in the field does the same. |
| Field | `Control.pill` high. `RoundedRectangle(cornerRadius: Radius.pill, style: .circular)` with a `stroke` hairline and no fill (a `Capsule` stroke leaves a stray hairline on macOS 26). Leading padding `Spacing.md`, trailing `Spacing.sm`. Text in `bodySmall` `textPrimary`. |
| Placeholder | An overlay at the text origin in `bodySmall` `textTertiary`, not the field's prompt (a styled prompt takes the field's ink on macOS). |
| Action inside the field | The primary action's title in `label` `textPrimary`, then its `KeyCapGroup`. After a copy, a `checkmark` and the confirmation word replace it for a moment. |
| Command circle | `command` in glyphMedium `textPrimary`, a `Control.pill` circle, `stroke` hairline, no fill; `hoverFill` while the `⌘K` palette is open. |
| Floating layers | Choosers (model, assistant, Add Context, Transform) float above the row at the full inner width: `panelGlass(radius: Radius.lg)`, `panelShadows()`, side padding `Spacing.xs`, bottom offset 52. The `⌘K` palette floats bottom right. |

**Multi-line variant (windows).** `TextField(axis: .vertical)` with
`lineLimit(1...8)`. Vertical padding centres one `bodySmall` line in 36
(`QuickAIComposer.multilineTextInset`), so one line looks like the panel's field.
The circles stay on the last line (`.bottom` alignment). `↩` sends, `⇧↩` adds a
line, and Tab moves on to the window's other controls. While the draft holds text, `⌘↑`, `⌘↓`, `⌥↑`, `⌥↓`, PageUp,
and PageDown move the caret. With an empty draft, they scroll the thread.

**States.**

| State | Placeholder | Action |
| --- | --- | --- |
| Empty, new chat | "Ask anything, @ tools, or / for commands…" | Ask `↩` |
| Follow-up | "Ask a follow-up…" | Ask `↩` |
| Answer shown, field empty | "Ask a follow-up…" | Paste Response `↩` or Copy Response `↩` (per setting) |
| Streaming | "Type a follow-up; it sends when this answer ends" | Stop `esc` |
| Queued (`↩` while streaming) | typed text stays | Queued `↩`; sent when the answer ends. `esc` stops and keeps it unsent. Clearing the field unqueues it. |
| Question card live | "Pick an option above… esc stops" | Pick `↩` |
| A chooser open | unchanged | The chooser's own verb (Use Model, Add, Run) `↩` |
| Chat list in place of the thread | "Search chats…" | Open `↩` |
| Stopped or error | "Ask a follow-up…" | Ask `↩` (`⌘R` retries) |

An error that belongs to no turn sits above the row in `meta` `danger`, padded
`Spacing.lg` by `Spacing.xs`, with an `InkButtonStyle` fix-it button when one exists.

**Keys.** The field keeps focus the whole time the surface is open, streaming
included. `↑` on an empty field puts back the last question. `↩` sends. With an
answer and an empty field it runs the primary action. `esc` pops one layer at a
time: an open layer, then the stream (queued text stays), then typed text, then the surface. `⌘K` opens actions.
IME composition (marked text) owns `↩` and `esc` until it commits.

**Accessibility.** The field is named "Ask Quick AI" on a panel, "Message" in a
window, "Search chats" in a list. The field group's value is "<action>, <keys>".
The circles are "Add Context" and "Actions", each with value "Open" or "Closed".

**Copy.** `Sources/Views/QuickAIComposer.swift`, `QuickAIFloatingChooser.swift`;
`ComposerKeyRouting` from `OverlayView.swift`; action and placeholder rules from
`QuickViewModel.quickAIComposerAction` and `quickAIComposerPlaceholder`.

## 4. Attachment chips and strip

**Chip.** `Control.chip` (28) high, `Radius.sm` (continuous), `chipFill`.
`HStack(spacing: Spacing.xxs)`, leading padding `Spacing.xs`, trailing
`Spacing.xs` (or `Spacing.xxs` with a remove button). No colour in any state.

| Part | Spec |
| --- | --- |
| Leading | Kind glyph in `caption` `textSecondary` in a 16 × 16 frame (`Spacing.md`), or an image thumbnail 20 × 20 (`Control.keyCap`) clipped at `Radius.xs`. |
| Name | `meta` `textPrimary`, one line, middle truncation, max 180 wide. |
| Detail | `meta` `textTertiary` with monospaced digits: "42 pp · 1.2 MB", "1944 × 1464", a link's host, "· cut" when text was cut. |
| Remove (strip only) | `xmark` in glyphSmall `textSecondary` in a 20 × 20 frame. |
| Hover / selected | Hover: `hoverFill` (only when the chip does something). Keyboard-selected: `selectionFill` plus a `selectionRing` hairline. |

| Phase | Draws |
| --- | --- |
| Reading | Detail "Reading…" and a mini `ProgressView` in 12 × 12. |
| Ready | Name, detail, and remove. |
| Failed | `exclamationmark.triangle` in place of the glyph (still `textSecondary`), and the reason as the detail ("Password-protected; not read"). |
| Not loaded (a sent chip after a relaunch) | "Not loaded" or "Image not kept" as the detail, and "Re-attach" in `meta` `textSecondary`. |

**Strip.** A row above the composer, `Control.chip + 2 × Spacing.xs` (44) high.
It scrolls sideways; chips sit `Spacing.xs` apart; side inset `Spacing.xs`. At the
trailing end: the routing line in `meta` `textTertiary` ("Will be cut to fit
Local Models"), then clear-all (`xmark.circle.fill`, `label` `textTertiary`, 28 square).
A notice in `meta` `textSecondary` may sit above the strip ("Board pack.pdf is already attached.").

**Drop target.** While a drag is over it: `hoverFill` at `Radius.xl` with a
`strokeStrong` hairline, and "Drop to attach" in `label` on a raised pill
(`Control.pill`, `Radius.pill`, `surfaceRaised`, `stroke`). Over a composer it
covers the typed text. Quick AI: the whole panel. AI Chat: the composer and the thread.

**Keys.** `⇧Tab` from the field enters the strip. `←` and `→` move. Backspace
removes; Backspace in an empty field removes the newest. Space opens Quick Look,
and `esc` leaves the strip. `⌘V` of files, an image, or a lone link into an
empty field attaches it, and `⌘Z` turns a pasted link back into text.

**Accessibility.** One element per chip: "Attachment: Q3 report.pdf, PDF, 42
pages, cut to the …" (spoken units: pages, not "pp"; "by", not "×"). VoiceOver
actions Remove, Open, and Re-attach. The strip is named "N attachments".

**Copy.** `Sources/Views/AttachmentChip.swift` (chip, strip, pill chips, flow
layout, drop overlay, pasteboard reader, Quick Look). The tray model is
`Sources/ViewModels/AttachmentTray.swift`.

## 5. Chat list rail

**Purpose.** Find and switch chats without leaving the conversation. It is
hidden by default. It is never a permanent split.

| Part | Spec |
| --- | --- |
| Rail | `Layout.chatRail` (220) wide on `surfaceSunken`, a 1 pt `divider` on its trailing edge. It slides in from the leading edge (`Motion.select`, ease out); with Reduce Motion, it fades. A clear `Control.composer` (52) row at the top leaves room for the traffic lights. |
| Search field | `Control.chip` high, `Radius.sm`, `surfaceTint` fill, `stroke` hairline, horizontal padding `Spacing.sm`, inset `Spacing.sm`. `magnifyingglass` in `meta` `textTertiary`; text `bodySmall`; placeholder "Search chats…". It searches titles and message text. |
| Sections | `SectionLabel` (`section`, uppercase, `textTertiary`): PINNED, then RECENT. While a query is typed: one ranked RESULTS list, and pinned rows keep a `pin.fill` glyph (`micro` semibold `textTertiary`). |
| Row | `Control.row` (40) high, horizontal padding `Spacing.xs`, rows `Spacing.xxs` apart. Title in `label` `textPrimary`, one line. Second line in `meta` `textTertiary`: "2 questions · 23:41" (time today, day before). |
| Snippet | A row found by its text shows a snippet on the second line: "You: …revenue incl…" or "Answer: …". The match is `meta` medium in `textPrimary`; the rest is `meta` `textTertiary`. The count and time move to the tooltip. |
| Selection | `RowHighlight`: `selectionFill`, `selectionRing` hairline, `selection` shadow, `Radius.row`. |
| Open-chat marker | A 2 × 20 ink capsule (`textPrimary`) on the row's leading edge, apart from the keyboard highlight. |
| `⌘1`…`⌘9` | A `KeyCap` "⌘3" on the highlighted row and the open row. All rows show theirs while `⌘` is held. They work whether or not the rail is showing. |
| Row actions | `⌘K` on a row: a `raisedCard` at `Radius.lg` on `surfaceRaised` with the `card` shadow over the rail's foot. Rows are `Control.railRow` (36) with glyph, `label` title, and key caps. Delete is `danger` ink and needs two presses. The same actions are in the context menu and in VoiceOver actions. |

**States.** Empty: "No chats yet" or "No chats match" in `bodySmall`
`textTertiary`. Rename: an inline field in the row, outside the row's button.

**Keys.** `⌘\` or the header toggle opens the rail with focus in its search and
the open chat highlighted. `↑↓` move and `↩` opens, then focus goes back to the
composer. `⌘K` shows row actions. `esc` clears the search, then closes the rail.

**Accessibility.** Row label "<title>, <detail or snippet>, pinned, open";
value "Selected, 3 of 9"; `.isSelected` trait on the highlighted row.

**Copy.** `AIChatRail` and `OpenChatMarker` in `Sources/Views/AIChatWindowView.swift`;
`ChatSnippetText` in `CatalogPanes.swift`; rail state in `Sources/ViewModels/AIChatWindowModel.swift`.
On a panel (Quick AI), the list takes the thread's place instead (`⌘P`, `RecentChatsList` in `QuickAIView.swift`).

## 6. Find bar

`⌘F` in a window. It sits under the header, above the thread.

| Part | Spec |
| --- | --- |
| Bar | `Control.pill` (36) high, `Radius.md` (continuous), `surfaceTint` fill, `stroke` hairline, inner padding `Spacing.md`, outer padding `Spacing.lg` at the sides and `Spacing.xs` below. |
| Contents | `magnifyingglass` in `bodySmall` `textTertiary`; the field in `bodySmall` (placeholder "Find in chat"); the count "2 of 17" or "No matches" in `meta` `textTertiary` with monospaced digits; `KeyHint` Next `↩`, Previous `⇧↩`; `xmark` close in glyphSmall `textSecondary` at 28 square. |
| Hits | In the text: every hit on `hoverFill`, the current hit on `selectionFill`. The thread puts the current hit a third of the way down the view. A hit inside a collapsed question opens that question. |

**Keys.** `↩` or `⌘G` goes to the next hit, and `⇧↩` or `⇧⌘G` to the previous one. Both wrap across
messages. `esc` closes. **Accessibility.** The count is announced at medium
priority as it changes. **Copy.** `AIChatFindBar` in `AIChatWindowView.swift`;
hit search in `AIChatWindowModel` (find section); painting in `MarkdownTextView.swift`.

## 7. Normal window chrome for a menu-bar app

A chat that outgrows a panel opens a normal window. A menu-bar app must then
behave like a normal app for as long as the window is open.

| Concern | Rule |
| --- | --- |
| Style | `[.titled, .closable, .miniaturizable, .resizable, .fullSizeContentView]`; `titleVisibility = .hidden`; `titlebarAppearsTransparent = true`. |
| Title-bar row | An empty `NSToolbar` with `toolbarStyle = .unified`, so the title-bar row is as tall as the 52 header and the traffic lights centre on it. |
| Ground | Opaque `surface` (not glass). `Layout.chatWidth` × `chatHeight` (860 × 620), `contentMinSize` `chatMinWidth` × `chatMinHeight` (720 × 480). Frame autosaved; a saved frame smaller than the minimum resets to the standard size, centred. |
| Header shares the row | The root view uses `.ignoresSafeArea(.container, edges: .top)`. The header paints `surface`, has `zIndex(1)`, and its leading inset is 88 (`Spacing.xxxxl + Spacing.xl`) for the traffic lights; `Spacing.sm` while the rail is out or in full screen. |
| Content clipped | The thread gets `.clipped()`, so it never scrolls up under the header or the title bar. |
| Drag | `isMovableByWindowBackground = false` (selecting text must not move the window). The header carries `.gesture(WindowDragGesture())`. |
| Window flags | `isReleasedWhenClosed = false`, `tabbingMode = .disallowed`, `collectionBehavior = [.managed, .participatesInCycle, .fullScreenPrimary]`, `hosting.sizingOptions = []` (the window sizes the view). |
| Menu bar | Install a menu when the window opens, only if `NSApp.mainMenu == nil`: App (About, Settings…, Hide, Close <Window> `⌘Q`, Quit `⌥⌘Q`), Edit (Undo, Redo, Cut, Copy, Paste, Select All, Find), View, Window (Minimize, Zoom, Keep on Top, Close `⌘W`). `⌘Q` closes the window so a stray press never kills the menu-bar app. Items validate against the key window. |
| Focus | `AppActivation.becomeRegularApp(showing:)`: switch to `.regular`, `makeKeyAndOrderFront`, `NSApp.activate()`. If the app is still not active, open its own bundle through `NSWorkspace.openApplication` with `activates = true`. After a policy change, activate the Dock for a moment and come back, so macOS hands over the menu bar. |
| Back to accessory | In `windowWillClose`, call `AppActivation.settleAfterClosing(window)`. When no other titled window is visible or minimised, set `mainMenu = nil` and the policy to `.accessory`. Whichever normal window closes last hands the menu bar back. |
| Keys | Subclass `NSWindow` and take `↩`, `⇧↩`, and `esc` in `sendEvent` (text views eat them before SwiftUI), skipping marked text. `⌘W` closes. |
| Life of the chat | The view model outlives the window. A stream goes on after `⌘W`, is saved, and posts one banner-only notice ("Answer ready") if it ends while the window is closed. |

**Copy.** `Sources/App/AIChatWindowController.swift` (window, `AIChatWindow`,
shell, notices), `AIChatMenu.swift`, `AppActivation.swift` (with `WindowPresence`).

## 8. Live and cockpit surfaces

RTI while it records, the Local Dictation pill, and Usage's meters show a live
state. That state keeps its own registered form. Such a surface still uses the
header, thread, and composer grammar for the parts where a person asks.

**What does not change.**

- The recording chip: a `danger` dot plus a clock, the only chroma on screen (Chips).
- The Pill: 36 high glass, ink waveform in a sunken well (Local Dictation, Rust).
- Meter rows: 4 px ink bars on `tileFill`, no colour for a full window (Usage).
- RTI's six speaker colours: data, not chrome, and only on a speaker's name (its text, or a 6 px dot beside it).
- Transcript text stays in `bodySmall` at line height 1.5. A speaker's name is plain text in `label` at the start of their turn, never a filled or outlined box, and consecutive lines from one speaker sit under one name, as in a meeting-notes app rather than a chat log.
- Capture controls (mic mute, device picker, screen trail) keep their controls and their words.

**How the grammar still applies.**

| Part | On a live surface |
| --- | --- |
| Header | Left toggle as usual. Title block: the session name over a state line in `meta` `textSecondary` that starts with a 6 px `StatusDot` and a word ("Recording · 12:04"). The right slot holds the one live action as the labelled chip ("Stop" plus its key). The recording chip may sit before it. Meters sit in the body or in the header's right slot, never in the composer. |
| Thread | Questions to the assistant are user pills, and answers are prose at the same widths. The transcript is its own body (a tab or the list), not a stream of pills. |
| Composer | The same row: plus, pill field, and command circle. The primary label is the ask ("Ask `↩`"). Live state never enters the field. The placeholder may name it ("Ask about this meeting…"). |
| Footer | None. Status that lived in a footer well moves to the header's second line. |

## Adopting in an existing app

1. Regenerate and recopy `HouseDesign.swift` (`make gen`). Add the three derived fonts and proseLineSpacing.
2. Copy `SlateChrome.swift` primitives: `KeyCap`, `KeyCapGroup`, `KeyHint`, `SectionLabel`, `HouseChip`, `RowHighlight`, `raisedCard`, `panelGlass`, `houseShadow`, `panelShadows`, `HouseDivider`, `InkButtonStyle`.
3. Copy the views in the order header, thread, composer, then chips, rail, and find. Keep the view names, so a grep finds each copy.
4. Put a small adapter between the app's view model and the views' reads (messages, `isStreaming`, `output`, `threadError`, composer action, placeholder), and do not rename them inside the views.
5. Delete the old chrome on the chat surface: section labels over turns, answer cards, the footer well, split panes.
6. For a normal window, copy section 7 whole, including the menu, `AppActivation`, and the close hand-back.
7. Check the floor (below) and swap in the fallbacks the app needs.
8. Register the surface in `components.json` and add render proofs for empty, streaming, answered, error, stopped, queued, and Latest, in both appearances (DESIGN.md: register and render-prove before it ships).
9. Run `bin/design-lint --strict` on touched files, and open the app and look at it.

**Floor.** Quick Launch is macOS 26. RTI, Cotype, Memory, Usage, and Local Models are macOS 14.

| API in the reference | Needs | macOS 14 fallback |
| --- | --- | --- |
| `ScrollPosition`, `.scrollPosition`, `onScrollGeometryChange`, `onScrollPhaseChange` | macOS 15 | `ScrollViewReader` + `scrollTo(id:anchor:)`; judge "at bottom" with a `GeometryReader` on a bottom sentinel view. |
| `WindowDragGesture` | macOS 15 | An `NSViewRepresentable` whose `mouseDown` calls `window.performDrag(with:)`. |
| `onModifierKeysChanged` | macOS 15 | An `NSEvent` local monitor for `.flagsChanged`. |
| `Observations` (stream watch) | macOS 26 | `withObservationTracking` re-armed on change. |
| `NSApp.activate()` | macOS 14 | Available; keep it. |

## Do not

- No split pane by default. A rail is hidden until asked for, and a panel's chat list replaces the thread.
- No uppercase ANSWER or YOU labels, and no "You:" drawn over a turn. Pills and prose say who is speaking.
- No footer well and no status dot row on a chat surface. The composer row is the footer.
- No cards or fills behind answers, and no collapsing answers.
- No accent on chrome: not the globe, not the send action, not a tab. Accent is for focus rings and links.
- No `activate(ignoringOtherApps:)`. Use `AppActivation.becomeRegularApp`, which falls back to LaunchServices.
- No clipboard write of generated text without the transient markers: write through
  `writeTransientString`, which declares `org.nspasteboard.TransientType` and
  `org.nspasteboard.AutoGeneratedType` (`Sources/Services/SystemServices.swift`).
- No `Capsule()` stroke for the field; use `RoundedRectangle(cornerRadius: Radius.pill, style: .circular)`.
- No hard sizes. If the reference has one, it is on the list below; copy it by name, do not retype it.

## Not a token yet (reference liberties to register, not to copy blind)

| Value | Where |
| --- | --- |
| subheading 13 semibold, glyphSmall 14 semibold, glyphMedium 16 semibold | `DesignTokens.swift` |
| Collapse control height `Control.chip − 6` (22) | `CollapsibleMessageText.swift` |
| `KeyHint` gap 6 and label ink at 80 %; `KeyCap` side padding 6 | `SlateChrome.swift` |
| Thinking dots 5 pt, gap 3, 0.35 s step | `OverlayView.swift` `ThinkingIndicator` |
| Attachment name max 180; `⌘K` palette 520 wide, 460 max high | `Services/PanelSizing.swift` |
| Open-chat marker 2 wide (`Spacing.xxs / 2`); traffic-light inset 88 | `AIChatWindowView.swift` |

## Drift against DESIGN.md (for the registry owner)

- DESIGN.md's Quick AI entry still names an `arrow.up.right.square` expand glyph on the right. The code now draws the labelled chip "Open in AI Chat `⌘J`".
- DESIGN.md's AI Chat entry gives the header as `Control.input` (58). The window header is `Control.composer` (52), the unified title-bar row.
- The `att-pill-chips-*` proof draws its sample question pill at a small radius. The thread's real pill is `Radius.pill`; re-render that proof from the thread view.
