// The Slate component kit for the house menu-bar apps: panel glass, icon tile,
// key caps, status dot, ink toggle, cards, rows, footer well, rail, segmented
// control. Every value comes from `House` (generated from
// design-system/tokens.json); nothing in this file retypes a token. See
// design-system/DESIGN.md for the rule these components follow.

#if canImport(AppKit)
import AppKit
import HouseDesign
import SwiftUI

// MARK: - Appearance

/// The user's window appearance choice. Dark is the house default; light is
/// first-class. `system` follows macOS.
public enum AppearancePreference: String, CaseIterable, Identifiable {
    case system
    case light
    case dark

    /// UserDefaults key. Registered with `dark` as the default.
    public static let key = "appearance"

    public var id: String { rawValue }

    public var title: String {
        switch self {
        case .system: return "System"
        case .light: return "Light"
        case .dark: return "Dark"
        }
    }

    public var nsAppearance: NSAppearance? {
        switch self {
        case .system: return nil
        case .light: return NSAppearance(named: .aqua)
        case .dark: return NSAppearance(named: .darkAqua)
        }
    }

    public static var current: AppearancePreference {
        AppearancePreference(rawValue: UserDefaults.standard.string(forKey: key) ?? "") ?? .dark
    }

    /// Apply to the whole app, so every app window (settings, menu-bar panel) resolves the same tokens.
    @MainActor
    public static func applyCurrent() {
        NSApp.appearance = current.nsAppearance
    }
}

// MARK: - Shadow plumbing

extension View {
    /// Apply a `House.ShadowSpec` at the given appearance.
    public func houseShadow(_ spec: House.ShadowSpec, dark: Bool) -> some View {
        shadow(
            color: Color.black.opacity(spec.opacity(dark: dark)),
            radius: spec.blur / 2,
            x: 0,
            y: spec.y
        )
    }
}

// MARK: - Glass

/// The blur material behind `panelTint` on every floating app panel.
public struct HouseBlur: NSViewRepresentable {
    public init() {}

    public func makeNSView(context: Context) -> NSVisualEffectView {
        let view = NSVisualEffectView()
        view.material = .hudWindow
        view.blendingMode = .behindWindow
        view.state = .active
        return view
    }

    public func updateNSView(_ nsView: NSVisualEffectView, context: Context) {}
}

/// The shared floating-panel surface: blur material, `panelTint`, `stroke`,
/// `highlightTop`, and the two panel shadows.
public struct HouseGlass<Content: View>: View {
    public var radius: CGFloat = House.Radius.xl
    @Environment(\.colorScheme) private var scheme
    @ViewBuilder public var content: Content

    private var isDark: Bool { scheme == .dark }

    public init(radius: CGFloat = House.Radius.xl, @ViewBuilder content: () -> Content) {
        self.radius = radius
        self.content = content()
    }

    public var body: some View {
        content
            .background(
                ZStack {
                    HouseBlur()
                    House.ColorToken.panelTint
                }
            )
            .clipShape(RoundedRectangle(cornerRadius: radius, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: radius, style: .continuous)
                    .strokeBorder(House.ColorToken.stroke, lineWidth: House.hairline)
            )
            .overlay(alignment: .top) {
                House.ColorToken.highlightTop
                    .frame(height: House.hairline)
                    .padding(.horizontal, radius / 2)
            }
            .houseShadow(House.Shadow.panelNear, dark: isDark)
            .houseShadow(House.Shadow.panelFar, dark: isDark)
    }
}

// MARK: - Key caps

/// One outlined key cap: 20 high, `keyCapStroke`, `Radius.xs`, SF (not mono).
public struct KeyCap: View {
    public let label: String

    public init(label: String) { self.label = label }

    public var body: some View {
        Text(label)
            .font(House.TypeToken.keyCap)
            .foregroundStyle(House.ColorToken.textSecondary)
            .frame(minWidth: House.Control.keyCap, minHeight: House.Control.keyCap)
            .padding(.horizontal, House.Spacing.xxs)
            .background(
                RoundedRectangle(cornerRadius: House.Radius.xs, style: .continuous)
                    .fill(House.ColorToken.keyCapFill)
            )
            .overlay(
                RoundedRectangle(cornerRadius: House.Radius.xs, style: .continuous)
                    .strokeBorder(House.ColorToken.keyCapStroke, lineWidth: House.hairline)
            )
            .accessibilityLabel(label)
    }
}

/// A chord rendered as one cap per key, the way the mockups draw them.
public struct KeyCaps: View {
    public let keys: [String]

    public init(_ keys: [String]) { self.keys = keys }

    /// The modifier glyphs that always get their own cap.
    private static let modifiers: Set<Character> = ["⌘", "⌥", "⌃", "⇧"]

    /// The cap label for a base key, so "Tab" draws as the ⇥ the mockups show.
    private static func capLabel(_ key: String) -> String {
        switch key.lowercased() {
        case "tab": return "⇥"
        case "escape", "esc": return "esc"
        case "return", "enter": return "↩"
        case "delete", "backspace": return "⌫"
        case "space": return "space"
        default: return key
        }
    }

    /// Split a display chord ("⌥Tab", "⌘,", "⌃.") into its caps: one cap per
    /// leading modifier, then one cap for whatever base key remains.
    public init(chord: String) {
        let spaced = chord.split(separator: " ").map(String.init)
        if spaced.count > 1 {
            self.keys = spaced.map(Self.capLabel)
            return
        }
        var caps: [String] = []
        var rest = Substring(chord)
        while let first = rest.first, Self.modifiers.contains(first) {
            caps.append(String(first))
            rest = rest.dropFirst()
        }
        if !rest.isEmpty {
            caps.append(Self.capLabel(String(rest)))
        }
        self.keys = caps.isEmpty ? [chord] : caps
    }

    public var body: some View {
        HStack(spacing: House.Spacing.xxs) {
            ForEach(Array(keys.enumerated()), id: \.offset) { _, key in
                KeyCap(label: key)
            }
        }
    }
}

/// A key hint that pairs a word with its caps ("Next word ⇥").
public struct KeyHint: View {
    public let title: String
    public let chord: String

    public init(title: String, chord: String) {
        self.title = title
        self.chord = chord
    }

    public var body: some View {
        HStack(spacing: House.Spacing.xs) {
            Text(title)
                .font(House.TypeToken.meta)
                .foregroundStyle(House.ColorToken.textSecondary)
                .lineLimit(1)
                .fixedSize()
            KeyCaps(chord: chord)
        }
    }
}

// MARK: - Tiles, dots, pills

/// A row glyph in a tile, so rows align whatever the symbol width.
public struct IconTile: View {
    public let symbol: String
    public var size: CGFloat = House.Control.tile

    public init(symbol: String, size: CGFloat = House.Control.tile) {
        self.symbol = symbol
        self.size = size
    }

    public var body: some View {
        RoundedRectangle(cornerRadius: House.Radius.tile, style: .continuous)
            .fill(House.ColorToken.tileFill)
            .overlay(
                RoundedRectangle(cornerRadius: House.Radius.tile, style: .continuous)
                    .strokeBorder(House.ColorToken.tileStroke, lineWidth: House.hairline)
            )
            .overlay(
                Image(systemName: symbol)
                    .font(.system(size: size * 0.46, weight: .regular))
                    .foregroundStyle(House.ColorToken.textSecondary)
            )
            .frame(width: size, height: size)
    }
}

/// The one piece of colour on any app surface: a status dot. Always paired
/// with a word, never colour alone.
public struct StatusDot: View {
    public var tint: Color = House.ColorToken.success
    public var diameter: CGFloat = 6

    public init(tint: Color = House.ColorToken.success, diameter: CGFloat = 6) {
        self.tint = tint
        self.diameter = diameter
    }

    public var body: some View {
        Circle()
            .fill(tint)
            .frame(width: diameter, height: diameter)
    }
}

/// "Granted", "Warm": an outlined pill with a 6 px status dot.
public struct StatusPill: View {
    public let text: String
    public var tint: Color = House.ColorToken.success

    public init(text: String, tint: Color = House.ColorToken.success) {
        self.text = text
        self.tint = tint
    }

    public var body: some View {
        HStack(spacing: House.Spacing.xxs) {
            StatusDot(tint: tint)
            Text(text)
                .font(House.TypeToken.meta)
                .foregroundStyle(House.ColorToken.textSecondary)
        }
        .padding(.horizontal, House.Spacing.xs)
        .frame(height: House.Control.chip)
        .overlay(
            RoundedRectangle(cornerRadius: House.Radius.sm, style: .continuous)
                .strokeBorder(House.ColorToken.keyCapStroke, lineWidth: House.hairline)
        )
        .accessibilityElement(children: .combine)
        .accessibilityLabel(text)
    }
}

/// A done mark: an 18 px ink disc with an ink-inverse check. Not-done is the
/// same disc as a quiet outline, so the pair reads without colour.
public struct DoneDisc: View {
    public let done: Bool

    public init(done: Bool) { self.done = done }

    public var body: some View {
        ZStack {
            if done {
                Circle().fill(House.ColorToken.textPrimary)
                Image(systemName: "checkmark")
                    .font(.system(size: House.TypeToken.Size.micro, weight: .bold))
                    .foregroundStyle(House.ColorToken.textInverse)
            } else {
                Circle().strokeBorder(House.ColorToken.keyCapStroke, lineWidth: House.hairline)
            }
        }
        .frame(width: 18, height: 18)
        .accessibilityLabel(done ? "Done" : "Not done")
    }
}

/// A small outlined action chip ("Record", "Enable").
public struct HouseChipButtonStyle: ButtonStyle {
    public var destructive = false

    public init(destructive: Bool = false) { self.destructive = destructive }

    public func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(House.TypeToken.meta)
            .foregroundStyle(destructive ? House.ColorToken.danger : House.ColorToken.textPrimary)
            .padding(.horizontal, House.Spacing.sm)
            .frame(height: House.Control.tile)
            .background(
                RoundedRectangle(cornerRadius: House.Radius.tile, style: .continuous)
                    .fill(configuration.isPressed ? House.ColorToken.selectionFill : House.ColorToken.keyCapFill)
            )
            .overlay(
                RoundedRectangle(cornerRadius: House.Radius.tile, style: .continuous)
                    .strokeBorder(House.ColorToken.keyCapStroke, lineWidth: House.hairline)
            )
            .contentShape(Rectangle())
    }
}

/// The primary action: an ink fill with inverse ink text. Never accent.
public struct HouseInkButtonStyle: ButtonStyle {
    public init() {}

    public func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(House.TypeToken.label)
            .foregroundStyle(House.ColorToken.textInverse)
            .padding(.horizontal, House.Spacing.md)
            .frame(height: House.Control.chip)
            .background(
                RoundedRectangle(cornerRadius: House.Radius.tile, style: .continuous)
                    .fill(House.ColorToken.textPrimary.opacity(configuration.isPressed ? 0.8 : 1))
            )
            .contentShape(Rectangle())
    }
}

/// A quiet text action, for links and secondary verbs.
public struct HouseLinkButtonStyle: ButtonStyle {
    public var destructive = false

    public init(destructive: Bool = false) { self.destructive = destructive }

    public func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(House.TypeToken.meta)
            .foregroundStyle(destructive ? House.ColorToken.danger : House.ColorToken.accent)
            .opacity(configuration.isPressed ? 0.7 : 1)
            .contentShape(Rectangle())
    }
}

// MARK: - Ink toggle

/// The switch itself: ink when on, a quiet tile when off. Never blue.
public struct InkSwitch: View {
    @Binding var isOn: Bool
    public var enabled = true

    private static let trackWidth: CGFloat = 38
    private static let trackHeight: CGFloat = 22
    private static let knob: CGFloat = 16

    public init(isOn: Binding<Bool>, enabled: Bool = true) {
        self._isOn = isOn
        self.enabled = enabled
    }

    public var body: some View {
        Button {
            guard enabled else { return }
            isOn.toggle()
        } label: {
            InkSwitchTrack(isOn: isOn, enabled: enabled)
        }
        .buttonStyle(.plain)
        .disabled(!enabled)
        .accessibilityAddTraits(isOn ? [.isButton, .isSelected] : .isButton)
        .accessibilityValue(isOn ? "On" : "Off")
    }
}

/// The switch's painted track, shared by `InkSwitch` and `InkToggleStyle`.
public struct InkSwitchTrack: View {
    public let isOn: Bool
    public var enabled = true

    public init(isOn: Bool, enabled: Bool = true) {
        self.isOn = isOn
        self.enabled = enabled
    }

    public var body: some View {
        ZStack(alignment: isOn ? .trailing : .leading) {
            Capsule()
                .fill(isOn ? House.ColorToken.textPrimary : House.ColorToken.tileFill)
                .overlay(
                    Capsule().strokeBorder(
                        isOn ? Color.clear : House.ColorToken.tileStroke,
                        lineWidth: House.hairline
                    )
                )
            Circle()
                .fill(isOn ? House.ColorToken.textInverse : House.ColorToken.textTertiary)
                .frame(width: 16, height: 16)
                .padding(.horizontal, 3)
        }
        .frame(width: 38, height: 22)
        .opacity(enabled ? 1 : 0.45)
        .animation(.easeOut(duration: House.Motion.hover), value: isOn)
    }
}

/// The house toggle style, for call sites that keep SwiftUI's `Toggle`.
public struct InkToggleStyle: ToggleStyle {
    public init() {}

    public func makeBody(configuration: Configuration) -> some View {
        HStack(spacing: House.Spacing.sm) {
            configuration.label
                .font(House.TypeToken.label)
                .foregroundStyle(House.ColorToken.textPrimary)
                .frame(maxWidth: .infinity, alignment: .leading)
            InkSwitch(isOn: configuration.$isOn)
        }
    }
}

/// A toggle for a capability the app cannot honour yet: shown, off, and inert.
public struct InertToggle: View {
    public init() {}

    public var body: some View {
        InkSwitchTrack(isOn: false, enabled: false)
    }
}

// MARK: - Cards and rows

/// A settings group: a card at `Radius.lg` on `surfaceRaised` with `stroke`
/// and a 1 px top highlight. The uppercase `section` label is the card's first
/// row, with an optional counter on the right, exactly as the mockup draws it.
public struct SlateCard<Content: View>: View {
    public var section: String?
    /// A short right-hand fact on the header row ("4 of 5 complete").
    public var counter: String?
    /// A full-width line of purpose under the header row.
    public var footnote: String?
    @ViewBuilder public var content: Content

    public init(
        section: String? = nil,
        counter: String? = nil,
        footnote: String? = nil,
        @ViewBuilder content: () -> Content
    ) {
        self.section = section
        self.counter = counter
        self.footnote = footnote
        self.content = content()
    }

    public var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            if let section {
                HStack(spacing: House.Spacing.sm) {
                    Text(section.uppercased())
                        .font(House.TypeToken.section)
                        .tracking(House.TypeToken.Tracking.section)
                        .foregroundStyle(House.ColorToken.textTertiary)
                    Spacer(minLength: House.Spacing.xs)
                    if let counter {
                        Text(counter)
                            .font(House.TypeToken.meta)
                            .foregroundStyle(House.ColorToken.textTertiary)
                            .lineLimit(1)
                    }
                }
                .padding(.horizontal, House.Spacing.md)
                .padding(.top, House.Spacing.sm)
                .padding(.bottom, House.Spacing.xs)
                SlateDivider()
            }
            if let footnote {
                SlateBlock {
                    Text(footnote)
                        .font(House.TypeToken.meta)
                        .foregroundStyle(House.ColorToken.textTertiary)
                        .fixedSize(horizontal: false, vertical: true)
                }
                SlateDivider()
            }
            content
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            RoundedRectangle(cornerRadius: House.Radius.lg, style: .continuous)
                .fill(House.ColorToken.surfaceRaised)
        )
        .overlay(
            RoundedRectangle(cornerRadius: House.Radius.lg, style: .continuous)
                .strokeBorder(House.ColorToken.stroke, lineWidth: House.hairline)
        )
        .overlay(alignment: .top) {
            House.ColorToken.highlightTop
                .frame(height: House.hairline)
                .padding(.horizontal, House.Radius.lg / 2)
        }
    }
}

/// One card row: `label` title, optional `meta` detail, trailing control.
/// Rows are 38–48 high and split by `divider`.
public struct SlateRow<Trailing: View>: View {
    public var title: String?
    public var detail: String?
    public var minHeight: CGFloat = 44
    @ViewBuilder public var trailing: Trailing

    public init(
        title: String? = nil,
        detail: String? = nil,
        minHeight: CGFloat = 44,
        @ViewBuilder trailing: () -> Trailing
    ) {
        self.title = title
        self.detail = detail
        self.minHeight = minHeight
        self.trailing = trailing()
    }

    public var body: some View {
        HStack(alignment: .center, spacing: House.Spacing.sm) {
            if title != nil || detail != nil {
                VStack(alignment: .leading, spacing: 2) {
                    if let title {
                        Text(title)
                            .font(House.TypeToken.label)
                            .foregroundStyle(House.ColorToken.textPrimary)
                    }
                    if let detail {
                        Text(detail)
                            .font(House.TypeToken.meta)
                            .foregroundStyle(House.ColorToken.textTertiary)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }
                Spacer(minLength: House.Spacing.sm)
            }
            trailing
        }
        .padding(.horizontal, House.Spacing.md)
        .padding(.vertical, House.Spacing.sm)
        .frame(minHeight: minHeight)
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

extension SlateRow where Trailing == EmptyView {
    public init(title: String? = nil, detail: String? = nil, minHeight: CGFloat = 44) {
        self.init(title: title, detail: detail, minHeight: minHeight) { EmptyView() }
    }
}

/// A free-form row: arbitrary content on the card's row grid.
public struct SlateBlock<Content: View>: View {
    @ViewBuilder public var content: Content

    public init(@ViewBuilder content: () -> Content) { self.content = content() }

    public var body: some View {
        VStack(alignment: .leading, spacing: House.Spacing.xs) {
            content
        }
        .padding(.horizontal, House.Spacing.md)
        .padding(.vertical, House.Spacing.sm)
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

/// The line between rows. Quieter than the panel stroke, and inset to the
/// card's horizontal padding so it reads as a row rule, not a panel edge.
public struct SlateDivider: View {
    public var inset: CGFloat = House.Spacing.md

    public init(inset: CGFloat = House.Spacing.md) { self.inset = inset }

    public var body: some View {
        House.ColorToken.divider
            .frame(height: House.hairline)
            .padding(.horizontal, inset)
    }
}

/// Prose inside a card, at `bodySmall` with the scale's line height.
public struct SlateProse: View {
    public let text: String
    public var tertiary = false

    public init(_ text: String, tertiary: Bool = false) {
        self.text = text
        self.tertiary = tertiary
    }

    public var body: some View {
        Text(text)
            .font(House.TypeToken.bodySmall)
            .foregroundStyle(tertiary ? House.ColorToken.textTertiary : House.ColorToken.textSecondary)
            // `LineHeight` is the total multiple; the font already supplies
            // about 1.25 of it, so only the remainder is extra leading.
            .lineSpacing(House.TypeToken.Size.bodySmall * (House.TypeToken.LineHeight.bodySmall - 1.25))
            .fixedSize(horizontal: false, vertical: true)
            .frame(maxWidth: .infinity, alignment: .leading)
    }
}

/// A two-column identifier row: `meta` label left, `code` value right.
public struct SlateInfoRow: View {
    public var title: String
    public var value: String
    public var monospaced = false

    public init(title: String, value: String, monospaced: Bool = false) {
        self.title = title
        self.value = value
        self.monospaced = monospaced
    }

    public var body: some View {
        HStack(alignment: .firstTextBaseline, spacing: House.Spacing.sm) {
            Text(title)
                .font(House.TypeToken.meta)
                .foregroundStyle(House.ColorToken.textTertiary)
                .frame(minWidth: 108, alignment: .leading)
            Text(value)
                .font(monospaced ? House.TypeToken.code : House.TypeToken.meta)
                .foregroundStyle(House.ColorToken.textSecondary)
                .textSelection(.enabled)
                .lineLimit(1)
                .truncationMode(.middle)
            Spacer(minLength: 0)
        }
    }
}

// MARK: - Pane header and footer

/// The pane header: 60 high, `heading` title with a one-line `meta` purpose.
public struct PaneHeader: View {
    public let title: String
    public let purpose: String

    public init(title: String, purpose: String) {
        self.title = title
        self.purpose = purpose
    }

    public var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(title)
                .font(House.TypeToken.heading)
                .foregroundStyle(House.ColorToken.textPrimary)
            Text(purpose)
                .font(House.TypeToken.meta)
                .foregroundStyle(House.ColorToken.textTertiary)
                .lineLimit(1)
        }
        .frame(maxWidth: .infinity, minHeight: 60, alignment: .leading)
        .padding(.horizontal, House.Spacing.lg)
    }
}

/// The footer well: a sunken bar with status on the left and the primary key
/// hints on the right.
public struct FooterWell<Leading: View, Trailing: View>: View {
    public var height: CGFloat = House.Control.footer
    @ViewBuilder public var leading: Leading
    @ViewBuilder public var trailing: Trailing

    public init(
        height: CGFloat = House.Control.footer,
        @ViewBuilder leading: () -> Leading,
        @ViewBuilder trailing: () -> Trailing
    ) {
        self.height = height
        self.leading = leading()
        self.trailing = trailing()
    }

    public var body: some View {
        VStack(spacing: 0) {
            SlateDivider()
            HStack(spacing: House.Spacing.sm) {
                leading
                Spacer(minLength: House.Spacing.sm)
                trailing
            }
            .padding(.horizontal, House.Spacing.md)
            .frame(height: height - House.hairline)
            .background(House.ColorToken.well)
        }
        .frame(height: height)
    }
}

/// The footer's left half: a status dot and a line of context.
public struct FooterStatus: View {
    public let text: String
    public var tint: Color = House.ColorToken.success

    public init(text: String, tint: Color = House.ColorToken.success) {
        self.text = text
        self.tint = tint
    }

    public var body: some View {
        HStack(spacing: House.Spacing.xs) {
            StatusDot(tint: tint)
            Text(text)
                .font(House.TypeToken.meta)
                .foregroundStyle(House.ColorToken.textTertiary)
                .lineLimit(1)
        }
    }
}

// MARK: - Rail

/// A settings rail row: a 24 px icon tile, a `label` title, and the section's
/// key hint. Selected is a raised tile with an inset ring and a 1 px drop;
/// hover is half the selection fill.
public struct RailRow: View {
    public let symbol: String
    public let title: String
    public let isSelected: Bool
    public let action: () -> Void

    @State private var isHovering = false
    @Environment(\.colorScheme) private var scheme

    public init(symbol: String, title: String, isSelected: Bool, action: @escaping () -> Void) {
        self.symbol = symbol
        self.title = title
        self.isSelected = isSelected
        self.action = action
    }

    public var body: some View {
        Button(action: action) {
            HStack(spacing: House.Spacing.xs) {
                IconTile(symbol: symbol, size: 24)
                Text(title)
                    .font(House.TypeToken.label)
                    .foregroundStyle(House.ColorToken.textPrimary)
                    .lineLimit(1)
                Spacer(minLength: House.Spacing.xxs)
            }
            .padding(.horizontal, House.Spacing.xs)
            .frame(height: 34)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(selectionBackground)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .onHover { isHovering = $0 }
        .accessibilityAddTraits(isSelected ? [.isButton, .isSelected] : .isButton)
    }

    @ViewBuilder
    private var selectionBackground: some View {
        let shape = RoundedRectangle(cornerRadius: House.Radius.md, style: .continuous)
        if isSelected {
            shape
                .fill(House.ColorToken.surfaceRaised)
                .overlay(shape.strokeBorder(House.ColorToken.selectionRing, lineWidth: House.hairline))
                .houseShadow(House.Shadow.selection, dark: scheme == .dark)
        } else if isHovering {
            shape.fill(House.ColorToken.hoverFill)
        } else {
            shape.fill(Color.clear)
        }
    }
}

/// The rail's app mark: a 28 px tile plus the app name over a `section` label.
public struct AppMark: View {
    public let symbol: String
    public let name: String
    public let caption: String

    public init(symbol: String, name: String, caption: String) {
        self.symbol = symbol
        self.name = name
        self.caption = caption
    }

    public var body: some View {
        HStack(spacing: House.Spacing.xs) {
            RoundedRectangle(cornerRadius: House.Radius.md, style: .continuous)
                .fill(House.ColorToken.textPrimary)
                .overlay(
                    Image(systemName: symbol)
                        .font(.system(size: House.TypeToken.Size.body, weight: .medium))
                        .foregroundStyle(House.ColorToken.textInverse)
                )
                .frame(width: 28, height: 28)
            VStack(alignment: .leading, spacing: 1) {
                Text(name)
                    .font(House.TypeToken.label)
                    .foregroundStyle(House.ColorToken.textPrimary)
                Text(caption.uppercased())
                    .font(House.TypeToken.section)
                    .tracking(House.TypeToken.Tracking.section)
                    .foregroundStyle(House.ColorToken.textTertiary)
            }
            Spacer(minLength: 0)
        }
    }
}

// MARK: - Segmented control

/// The house segmented control. The system's `.segmented` picker paints the
/// selected segment with the system accent (blue), which Slate forbids, so the
/// selection is the same raised tile the rail uses.
public struct SlateSegmented<Value: Hashable>: View {
    public let options: [(value: Value, title: String)]
    @Binding var selection: Value

    @Environment(\.colorScheme) private var scheme

    public init(options: [(value: Value, title: String)], selection: Binding<Value>) {
        self.options = options
        self._selection = selection
    }

    public var body: some View {
        HStack(spacing: 2) {
            ForEach(Array(options.enumerated()), id: \.offset) { _, option in
                Button {
                    selection = option.value
                } label: {
                    Text(option.title)
                        .font(House.TypeToken.meta)
                        .foregroundStyle(
                            selection == option.value
                                ? House.ColorToken.textPrimary
                                : House.ColorToken.textSecondary
                        )
                        .padding(.horizontal, House.Spacing.sm)
                        .frame(maxWidth: .infinity)
                        .frame(height: House.Control.tile)
                        .background(background(isSelected: selection == option.value))
                        .contentShape(Rectangle())
                }
                .buttonStyle(.plain)
                .accessibilityAddTraits(selection == option.value ? [.isButton, .isSelected] : .isButton)
            }
        }
        .padding(2)
        .background(
            RoundedRectangle(cornerRadius: House.Radius.md, style: .continuous)
                .fill(House.ColorToken.well)
        )
        .overlay(
            RoundedRectangle(cornerRadius: House.Radius.md, style: .continuous)
                .strokeBorder(House.ColorToken.stroke, lineWidth: House.hairline)
        )
    }

    @ViewBuilder
    private func background(isSelected: Bool) -> some View {
        let shape = RoundedRectangle(cornerRadius: House.Radius.sm, style: .continuous)
        if isSelected {
            shape
                .fill(House.ColorToken.surfaceRaised)
                .overlay(shape.strokeBorder(House.ColorToken.selectionRing, lineWidth: House.hairline))
                .houseShadow(House.Shadow.selection, dark: scheme == .dark)
        } else {
            shape.fill(Color.clear)
        }
    }
}

#endif
