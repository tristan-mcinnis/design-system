# Form spacing (settings panes, sheets, setup forms)

Proximity carries meaning: a small gap ties things together, a large gap separates groups. Every gap between form elements comes from this table. Adapted from Zander Whitehurst's form spacing table (gist: https://gist.github.com/patrykcieszkowski/85a9279b254d2973487f190ec635d7a3). `DESIGN.md` carries the one-line summary; this file is the full rule.

| Relationship | Token |
|---|---|
| Pane padding, top and bottom | `xxxl` 48 |
| Pane padding, left and right | `xxl` 32 (the source's 40 is off the scale) |
| Title to subtitle | `xs` 8 |
| Group to group (header, each card, actions; either side of a divider) | `xl` 24 |
| Label or `section` label to its control or card | `xs` 8 |
| Field to field (label-over-control fields) | `lg` 20 |
| Control to its helper or error text | `xxs` 4 |
| Last field to the primary button | `xl` 24 |
| Button to button; toggle or checkbox to its label | `xs` 8 |

- Set each gap once, on the parent stack, with a `Spacing` token: `VStack(spacing: House.Spacing.xl)` for groups, `VStack(spacing: House.Spacing.lg)` for fields, and a field as `VStack(alignment: .leading, spacing: House.Spacing.xs) { label; VStack(alignment: .leading, spacing: House.Spacing.xxs) { control; helper } }`. Never per-field `.padding(.top/.bottom)` or a `Spacer` as a gap, and never a stack without `spacing:` (the SwiftUI default is not a token). AppKit panes set `NSStackView.spacing` the same way.
- Stack spacing applies only between siblings, so nested stacks never add up.
- The table covers the space between elements. Inside a component (row height, field and button padding, the 40 px settings row and its hairlines) the component rule holds.
- Both appearances use the same spacing. A validation error takes the helper slot and moves nothing else.
