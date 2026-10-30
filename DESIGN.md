# House Design (Slate)

The one visual rule for the native Apple apps, macOS and iOS: Quick Launch, RTI, Local Dictation, Cotype, Memory, Local Models, and any that follows.
`tokens.json` is the machine source of every value; generators in `gen/` emit `HouseDesign.swift`
(AppKit and UIKit) and `house_theme.rs`, which apps consume and never retype.
Mockups: Claude Design "Modernize HouseDesign" (Slate). Code rule: `SWIFT.md`.

## The rule in six lines

1. Monochrome, warm neutrals: warm near-white ink on a dark ground, warm near-black ink on a light ground. Dark is the default; light is first-class.
2. No accent on chrome. The only colour is a status dot: `success` for ready or on, `danger` for off, error, or recording. `accent` exists for focus rings and links only.
3. Depth comes from shadow and a 1 px top highlight, not from stroke weight. Panel strokes are quiet; dividers are quieter still.
4. Hover is not selection: hover is half the selection fill; selection adds an inset ring and a 1 px drop.
5. One radius scale, one spacing scale, one type scale (SF), one set of control heights. Text tiers are ink at reduced alpha (about 60 % and 40 % on dark, 62 % and 50 % on light), so they track any ground.
6. Floating panels and the dictation pill are the same glass: blur material, `panelTint`, `stroke`, `highlightTop`, two panel shadows.

## Colour tokens (semantic names only, never colour names)

| Token | Use |
| --- | --- |
| `surface`, `surfaceRaised`, `surfaceSunken` | Opaque window ground, raised cards and composers, rails |
| `surfaceTint`, `well`, `tileFill` + `tileStroke`, `chipFill` | Quiet grouped fill; sunken footer well; 26 px icon tile; chips |
| `textPrimary`, `textSecondary`, `textTertiary`, `textInverse` | Ink at full, secondary, and tertiary alpha; text on ink or the HUD |
| `success`, `warning`, `danger` | Status dots and destructive actions only |
| `accent`, `accentSoft` | Focus rings and links. Never a button fill, never a tab tint |
| `stroke`, `strokeStrong`, `divider`, `highlightTop` | Panel hairline; focused hairline; row line; top-edge highlight |
| `selectionFill`, `selectionRing`, `hoverFill` | Selected row (fill + inset ring); hover |
| `keyCapFill`, `keyCapStroke` | Key caps are outlined (fill is clear) |
| `panelTint` | Tint over the blur material of a panel or the pill |
| `hudFill`, `hudText`, `hudStroke`, `hudMuted` | Full-screen HUD overlays only (Type to Click). Same in both modes |

Ink is 237/235/232 on dark and 28/27/26 on light. `textSecondary` clears 4.5:1
on `surface` in both modes; `textTertiary` clears 3:1, for metadata only.

**One allowed categorical palette.** RTI's speaker names use six data colours so Speaker 1, 2, 3 stay distinct: data, not chrome, local to RTI, and the only set. A speaker name is text, never a boxed chip.

## Type scale (SF Pro; SF Mono for `code` only)

| Token | Size / weight | Use |
| --- | --- | --- |
| `display` / `title` / `heading` | 28 / 20 / 16 semibold | Settings pane titles and the like |
| `input` | 16 regular | The launcher field and composers |
| `body` | 14 regular, line height 1.55 | Answers and prose |
| `bodySmall` | 13 regular, line height 1.5 | Transcript and history text |
| `label` | 13 medium | Row titles |
| `meta` | 12 regular | Row detail, footer text, times |
| `caption` / `micro` | 11 / 10 regular | Hints |
| `section` | 10.5 semibold, uppercase, tracking 0.08 em | Section labels ("SUGGESTIONS", "TODAY") |
| `keyCap` | 11 medium, SF (not mono) | Key caps |
| `code` | 12 regular mono | Identifiers only |

Key caps are 20 px tall, outlined with `keyCapStroke`, at `Radius.xs`. A row glyph sits in a 26 px tile (`tileFill`, `tileStroke`, `Radius.tile`) so rows align whatever the symbol width.
Overlay surfaces that must honour the system text-size setting may use the matching Dynamic Type styles, same weights.

## Shape, space, size, motion

Shapes follow their role across apps: circles for standalone icon actions; capsules for chat fields, compact selectors, and tags; rounded rectangles for content cards and panels. Rows keep `Radius.row` and key caps keep `Radius.xs`. Choose the shared component treatment before changing a radius token.

- Radius: `xs` 5 (key caps), `sm` 6 (chips, fields), `tile` 7, `md` 8 (menus), `row` 10, `lg` 12 (cards), `xl` 16 (panels), `pill` 18, `xxl` 24.
- Spacing: 4, 8, 12, 16, 20, 24, 32, 48, 64 (`xxs` to `xxxxl`). Nothing in between. Forms and settings panes: pane padding `xxxl` 48 top and bottom, `xxl` 32 at the sides; title to subtitle `xs`; group to group `xl`; label to its control `xs`; field to field `lg`; control to helper or error `xxs`; last field to primary button `xl`; button to button `xs`. Set each gap once on the parent stack with a `Spacing` token (`VStack(spacing: House.Spacing.lg)`), never per-field padding; in cards use HouseUIKit `SlateField` and `SlateFormBlock`; the table and rules are in `docs/form-spacing.md`.
- Control heights: `keyCap` 20, `tile` 26, `chip` 28, `railRow` 36, `pill` 36, `row` 40, `footer` 40, `sessionRow` 44, `composer` 52, `input` 58.
- Layout: launcher panel 750 wide, the Raycast width, and the same 750 with an answer; Quick AI is a fixed 750 × 475 surface with answer text capped at 690; RTI answer text capped at 620; settings rail 220 in an 860 × 620 window; AI Chat opens at 860 × 620 (720 × 480 at the least) with a 220 chat rail, hidden until asked for.
- Shadows: `panelNear` (0 8 24) + `panelFar` (0 40 80) under every floating panel; `card` under raised cards; `selection` under the selected row. Opacities per appearance are in the tokens.
- Material: blur 48, saturate 1.3, then `panelTint`. Hairline stroke is 1 pt.
- Motion: `hover` 0.10 s, `select` 0.14 s ease-out (the selection fill slides between rows), `open` 0.12 s fade with a 0.98 to 1 scale. Honour Reduce Motion: no movement, fade only.

## Shared components

<!-- components:begin (generated from components.json: make components) -->
- **Launcher panel**: `input` row 58 high with a leading search glyph and one 28 px square menu; section labels in `section`; rows 40 high with a tile, `label` title, `meta` detail, and either key caps or a `meta` type label on the right; footer 40 high painted as a `well`, status dot + context on the left, primary key and ⌘K on the right.
- **Composer** (Quick Launch and RTI): a pill-shaped field on a quiet stroke, beginning at `Control.pill` height and growing within a bounded line limit before scrolling; a leading plus circle and trailing command circle at `Control.pill`, using the same glyph, stroke, hover and focus roles; a real primary-action button inside the field; Return sends, Shift-Return inserts a line, `⇧⌘A` attaches, and `⌘K` opens searchable actions; attachment readiness and failures remain visible above the field; floating choices fit in the remaining space and keyboard selection scrolls into view; `@` and `+` open searchable context choices; `/new` clears draft and pending sources without deleting saved history or ending a recording; the context choices name how far the search reaches, so source-only versus broader retrieval stays reachable before Send; the effective image destination remains visible above the field; completed answers expose their model and used context; empty Return keeps the app's explicitly labelled delivery or quick action; IME composition and active choices take precedence.
- **Hidden launcher items** (Quick Launch): Settings Items has a searchable Hidden view using the existing settings table and type filters; each row names the item and kind, marks unavailable sources, and offers Restore; Restore All is explicit; Hide from Quick Launch is distinct from Hide Windows; hidden items keep aliases, pins and hotkeys.
- **Chat context record** (Quick Launch and RTI): a compact answer detail exposes effective model, provider destination, reasoning, used sources and phase timings; attachment rows distinguish retained, partial and unavailable content; refresh creates a new source version; history actions distinguish new chat, removal of pending context and confirmed deletion of saved records.
- **Settings shell**: 220 px rail on `surfaceSunken` with 36 px rows, the selected row a raised tile; pane title in `heading` `xs` over a `meta` subtitle, inset `xxl` like the pane; groups as cards at `Radius.lg`, `xl` apart, the uppercase `section` label the card's own header row (`sm` above, `xs` below, then a divider, so the form table's label-to-card gap does not apply) over 40 px rows; ink toggles; footer well with the hint on the left and the primary key on the right.
- **Pill** (Local Dictation): compact height is `Control.pill - Spacing.xxs` (32), standard height is `Control.pill` (36), with radius equal to half the height and the shared panel glass; a danger recording dot becomes a cancel glyph on hover inside a stable hit target; Escape and click cancel before insertion begins, without activating the pill; the ink waveform rests near-flat in silence and responds to microphone levels; sensitivity is adjustable without changing recorded audio; optional live transcript text uses the existing sentence-based transcription stream; processing shows Transcribing, Cleaning up when used, and Pasting at insertion, without artificial stage delays; processing details, size, live preview, waveform response, and completion feedback are exposed in Settings; Reduce Motion disables decorative movement; success, copied recovery, held text, and errors state their outcome with words and the existing status tokens.
- **Chips**: 28 high at `Radius.sm`, `chipFill`, `meta` text; recording is the only chroma, a `danger` dot + clock.
- **Menu bar panel** (Cotype, Memory, Local Models, Usage): a 300 px glass panel in place of an NSMenu; header of a 26 px icon tile, app name in `label`, a status line in `caption` with a 6 px dot, and an ink toggle for the one master switch; `divider`; action rows 36 high with a glyph, `label` text, and outlined key caps, selection = `selectionFill` + `selectionRing`; rows may carry two lines (a `label` id over `meta` detail) with a 26 px icon tile, as Local Models' model rows do; a second group for rarer actions; footer well 36 high, Settings ⌘, on the left, Quit ⌘Q on the right; arrows, Return, and Escape drive it, and it closes on focus loss.
- **Meter row** (Usage): 28 high under a two-line provider row, inset to the provider's text column; window name in `meta` on the left in a fixed 96 px column so the bars of every provider line up; a 4 px ink bar on a `tileFill` track at `Radius.xs`; the percent in `label` with monospaced digits on the right; percent used is the one axis: a rate window reports it directly, a balance as spend since its 30-day peak; no colour: a window at its cap says 100 % and the `caption` footnote under the group says when it resets; an unknown draws an empty track, never a zero.
- **Status item** (every menu-bar app): one SF Symbol from the app-icon family, as a template image at `Control.statusGlyph` (15 pt) medium weight, so every house item sits on one baseline at one weight; outline when idle; the `.fill` variant means on (a model warm, a capture running); never filled for decoration; colour only for a state that needs a word too: `danger` for recording or a permission fault, in the tooltip and the panel as well; no title text beside the glyph unless the app is a meter (Usage may show its percent in `bodySmall` monospaced digits).
- **Quick AI** (Quick Launch): header 58 high with no divider: a `chevron.left` in `glyphSmall` `textSecondary`, the chat title in `subheading` over the model display name in `meta`, and an `arrow.up.right.square` expand glyph in `glyphMedium` on the right; thread: user turns as right-aligned pills on `chipFill` at `Radius.pill` in `bodySmall` `textSecondary`; answers as `body` prose capped at `Layout.quickAIAnswerMaxWidth`, no card; one tool or status line in `bodySmall` `textTertiary`; composer row along the bottom edge, inset `Spacing.xs`: a `Control.pill` plus circle on `surfaceTint`, a field at `Radius.pill` with a `stroke` hairline and no fill, and a matching `command` circle; the field grows from one to four lines, then scrolls; its primary action is a button with `label` text and a key cap; `↩` sends and `⇧↩` inserts a new line; attachment and action panes scroll within the remaining space above the measured composer; no footer well; Recent Chats (`⌘P`) in place of the thread: a `section` label with its key hints, then the launcher-panel chat rows (26 px `IconTile`, `label` title, `meta` question count and time, 40 high) pinned first, selection = `selectionFill` + `selectionRing`; the composer reads Open ↩.
- **AI Chat window** (Quick Launch): a normal titled window with a transparent title bar on the opaque `surface` ground, `Layout.chatWidth` × `Layout.chatHeight`, at least `chatMinWidth` × `chatMinHeight`, its frame kept; header `Control.input` high sharing its row with the traffic lights: a `sidebar.left` glyph in `glyphSmall` `textSecondary`, the Quick AI title block (title in `subheading` over the model in `meta`), and a `square.and.pencil` new-chat glyph in `glyphMedium` on the right; the Quick AI thread and composer as shared subviews; the composer grows to eight lines, `↩` sends and `⇧↩` starts a new line; find bar (`⌘F`) under the header: `Control.pill` high at `Radius.md` on `surfaceTint` with a `stroke` hairline, the count in `meta` `textTertiary`, Next and Previous key hints; the current match drawn with `selectionFill` + `selectionRing`; chat list rail `Layout.chatRail` wide on `surfaceSunken`, hidden until `⌃⌘S`: a `Control.chip` search field at `Radius.sm`, `section` labels Pinned then Recent, two-line rows `Control.row` high (`label` title over `meta` count and time), selection = `selectionFill` + `selectionRing`, `⌘1`…`⌘9` caps on the open and highlighted rows, `⌘K` row actions with a separate fuzzy search on a raised card; the chat list rail begins with the pinned Chief of Staff row (never renamed or deleted, no ⌘ number), its waiting count as `meta` digits on a `chipFill` capsule; opened, a status line carries health as a status dot and words, the project filter chip, and List, Board, Activity, Artifacts and Charter (⌥⌘1 to ⌥⌘5; ⌘1 to ⌘9 stay the rail's), the current one selected with its caps; Activity groups the day under `section` labels with `meta` times, Artifacts lists drafts as 40-high rows with Open and Discuss, Charter shows its sections read only with Add rule and Edit charter and the rungs with Remove; its other keys (⌥↑ Cards, ⌘N New task, ⇧⌘P Project, ⇧⌘↩ Do all Today, ⌘I Health, ⇧⌘T Tasks) as key caps in a strip over the composer; the List (DECIDE, TODAY, WAITING ON OTHERS, PROJECTS rows with a risk dot and words, LATER, FYI) scrolls within 60 % of the conversation over the thread; the Board's columns (Decide, Today, Waiting, Later, Done this week) take the thread's room; ↑ from an empty composer or ⌥↑ moves onto the cards, esc back; the root view forces no minimum width, so any window width reflows.
- **Selected text preview** (Quick AI and AI Chat): a Preview button on the selected-text chip, also opened with `⌥⌘I`; a popover with the source app, a complete selectable and scrollable text view in `body`, and a clear next-message status; uses `surface`, `textPrimary`, shared spacing and corner radii; stays readable in both appearances.
- **Dictation recovery detail** (Local Dictation): shows the saved audio with playback and the dictation status, followed by selectable raw and processed text versions; Recover re-transcribes the saved audio with optional cleanup and copies the result to the clipboard; existing versions remain available; audio is local, retained for 30 days by default, with retention and recovery controls in Settings; expired or unavailable audio is stated beside its actions; uses House settings/list surfaces, semantic text and status tokens, and native keyboard-accessible controls in both appearances.
- **Session browser** (RTI): sidebar rows use `Radius.row`; file selectors are compact pills; content sections use `Radius.lg` and a readable column capped at `Layout.rtiAnswerMaxWidth`; Copy, Share, Trash, and playback icon controls are circles with the shared icon-action treatment; audio playback aligns the retained microphone and system legs; the player shows play/pause, seek, time and explicit availability; saved chat content has a clear route to the existing session-grounded House composer; deletion confirms Move to Trash for owned archives.
- **Setup checklist** (Local Dictation): a standalone panel on the opaque `surface` ground at `Layout.panelWidth`, with the shared panel chrome; a pane title in `title` over a `meta` subtitle stating what is still needed; one requirement per row, `Control.row` high: a 26 px icon tile, the requirement in `label` over its live state in `meta`, a status dot, and a chip carrying its single action on the right; status is a dot plus a word, never colour alone: `success` when satisfied, `danger` when not; state is re-read about once a second while the window is open, so a grant made in System Settings lands without a relaunch and the row's action drops away; footer well with the hint on the left.
- **Live transcript** (RTI): one left reading column for every speaker, the mic wearer included, with no box, bubble or dot; a turn (consecutive lines of one speaker, until another speaker, a note or 30 s of silence) carries one label line: the name in `label` semibold in the speaker's palette colour, the time in `meta` `textTertiary` at the right edge of the reading width; the text is `body` in `textPrimary` with `Spacing.xxs` between lines, capped at `Layout.answerMaxWidth`; turns `Spacing.lg` apart, label to text `Spacing.xxs`; speaker labels come from the speaker id and never change mid-meeting (You, Speaker N, Room speaker N); a click names the speaker, offering the confirmed meeting's invitees first; the mic's echo of the system leg is never shown; interim words follow the final words in `textTertiary` in the turn they belong to, so a final result recolours them in place; a long turn breaks into paragraphs `Spacing.sm` apart at sentence ends; a break never moves once made, and interim words join only the open paragraph; lines leaving the top fade over `Spacing.lg`; a note is a glyph label over `textSecondary` text; the list follows the latest line until the user scrolls up, then a `Control.chip` capsule on `surfaceRaised` offers Jump to latest; archived transcripts in the Session browser keep a dot-and-name label line, once per run of one speaker, with the dot colour the live view gives that speaker.
- **Main workspace**: a persistent header carries the current capture status and recording controls above a labelled navigation row using existing ink selection and spacing tokens; Live, Sessions, Chats and Settings replace content in the same window; each remains reachable from every page, including an empty or unavailable library; switching pages keeps the live composer, selected record and settings navigation; hidden content is excluded from keyboard input and accessibility; closing the window leaves capture running; the window rules and release checks are in `docs/window-navigation.md`; transient launchers and dictation pills keep their separate task roles; the unified window opens at chatWidth by chatHeight plus Control.row, with a shared minimum of chatMinWidth by chatMinHeight plus Control.row; page changes preserve the frame; tonal depth uses surfaceSunken chrome and rails, a surface workspace gutter, and surfaceRaised reading panels and settings cards with the existing card shadow and top highlight; primary navigation has a raised active tab.
<!-- components:end -->

## Terminal surfaces (recall and any house CLI)

A CLI has no chrome, so the same rule shows up as text discipline:

- Monochrome. No ANSI colour except the status dot: `●` in green for ready or on, in red for off or error, dim for idle. Everything else is default foreground, with bold for row titles and dim for secondary text. Honour `NO_COLOR` and a non-TTY (plain dots, no escapes).
- Section labels are uppercase, like the app section labels: `TODAY`, `OPEN TASKS`, `STORE`.
- Rows read like launcher rows: a title, then secondary detail on the same line, aligned in two columns; times and counts right-aligned in the detail column.
- Key and value lines use two spaces of indent and one aligned column: `Route    memory-capture.py`.
- One-line status first, like the footer: `● Ready · 1,204 frames · 63 MB`. Help text lists verbs as rows, not prose.
- No banners, no boxes, no emoji.

## App icon

Rounded square at the macOS 26 squircle radius (22.5 % of the tile), tile inset 100 px on a
1024 canvas. One flat fill: the near-black ink. One white glyph at 46 % of the tile, optically
centred. No gradients, no shadows, no letters in circles. Glyphs: bolt (Quick Launch), waveform
(Local Dictation), record ring (RTI), I-beam with ghost dots (Cotype), chip (Local Models), bookmark
(Memory), gauge (Usage), tray (Chief of Staff, now the pinned row in Quick Launch); the Status item component carries the same glyph
into the menu bar. A new app gets one SF-style silhouette naming its verb, as a path in `icons/make-icon.py`:

    python3 icons/make-icon.py --glyph bolt --out AppIcon.icns

## Accessibility

- Text contrast 4.5:1 minimum for primary and secondary ink, 3:1 for tertiary; check both modes.
- Keyboard first: every action reachable without a pointer, focus ring visible (`strokeStrong` or `accent`). Respect Reduce Motion and Increase Contrast. Never rely on colour alone for status; pair the dot with a word.

## Consuming the system

Swift apps take the tokens as the `HouseDesign` package product and the menu-bar kit as `HouseUIKit`, pinned by GitHub URL and tag; the Rust file is the one generated copy (its header carries the `tokens.json` sha). Change a value in `tokens.json`, run `make gen`, tag a release, then raise the pin in each app. A token file in the repo is plumbing, not a look: `make lint` runs `bin/design-lint`, which refuses a repo that gains a hard radius, colour or size, and the atlas flags one as `DESIGN-DRIFT`. `components.json` registers every shared surface: register and render-prove a new one before it ships.
