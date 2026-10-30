#if canImport(AppKit)
import AppKit
import SwiftUI
import XCTest
import HouseDesign
import HouseUIKit

private func fittingSize<V: View>(_ view: V) -> NSSize {
    NSHostingView(rootView: view).fittingSize
}

final class HouseUIKitTests: XCTestCase {
    func testChordSplitsIntoModifierCapsThenBaseKey() {
        XCTAssertEqual(KeyCaps(chord: "⌥Tab").keys, ["⌥", "⇥"])
        XCTAssertEqual(KeyCaps(chord: "⌘,").keys, ["⌘", ","])
        XCTAssertEqual(KeyCaps(chord: "esc").keys, ["esc"])
    }

    func testSpacedChordKeepsEachWordAsACap() {
        XCTAssertEqual(KeyCaps(chord: "Space Return").keys, ["space", "↩"])
    }

    func testRowsAndTilesReserveTheirTokenSizes() {
        XCTAssertEqual(fittingSize(IconTile(symbol: "bolt")).width, House.Control.tile)
        XCTAssertEqual(fittingSize(SlateRow(title: "Launch at login", detail: "Starts with the Mac")).height, 44, accuracy: 20)
        XCTAssertGreaterThanOrEqual(fittingSize(PaneHeader(title: "General", purpose: "Basics")).height, 60)
    }

    func testPanelActionsDrawAsRowsAtTheRailHeight() {
        var ran = 0
        let action = PanelAction(id: "open", glyph: "bolt", title: "Open", chord: "⌘O", run: { ran += 1 })
        action.run()
        XCTAssertEqual(ran, 1)
        XCTAssertTrue(action.isEnabled)
        let row = PanelRow(action: action, isSelected: true, onHover: {}, onTap: {})
        XCTAssertEqual(fittingSize(row).height, House.Control.railRow, accuracy: 0.5)
    }

    func testCardWrapsItsContent() {
        let card = SlateCard(section: "Section", counter: "1 of 2") {
            SlateRow(title: "Row")
        }
        XCTAssertGreaterThan(fittingSize(card).height, 0)
    }

    // Form spacing (docs/form-spacing.md): label 8 control 4 helper; fields
    // 20 apart; the action row 24 below the last field; buttons 8 apart.
    func testFieldPutsLabelEightAboveAndHelperFourBelowTheControl() {
        let field = SlateField {
            Color.clear.frame(width: 10, height: 10)
        } control: {
            Color.clear.frame(width: 10, height: 20)
        } helper: {
            Color.clear.frame(width: 10, height: 6)
        }
        XCTAssertEqual(fittingSize(field).height, 10 + House.Spacing.xs + 20 + House.Spacing.xxs + 6, accuracy: 0.5)
    }

    func testFieldWithoutLabelOrHelperAddsNoGap() {
        let field = SlateField(label: nil) { Color.clear.frame(width: 10, height: 20) }
        XCTAssertEqual(fittingSize(field).height, 20, accuracy: 0.5)
    }

    func testBlockDefaultsToEightAndTakesAnotherGap() {
        let pad = House.Spacing.sm * 2
        let tight = SlateBlock {
            Color.clear.frame(width: 10, height: 10)
            Color.clear.frame(width: 10, height: 10)
        }
        XCTAssertEqual(fittingSize(tight).height, pad + 20 + House.Spacing.xs, accuracy: 0.5)
        let fields = SlateBlock(spacing: House.Spacing.lg) {
            Color.clear.frame(width: 10, height: 10)
            Color.clear.frame(width: 10, height: 10)
        }
        XCTAssertEqual(fittingSize(fields).height, pad + 20 + House.Spacing.lg, accuracy: 0.5)
    }

    func testFormBlockSpacesFieldsAndPutsActionsTwentyFourBelow() {
        let block = SlateFormBlock {
            Color.clear.frame(width: 10, height: 10)
            Color.clear.frame(width: 10, height: 10)
        } actions: {
            Color.clear.frame(width: 30, height: 12)
            Color.clear.frame(width: 30, height: 12)
        }
        let size = fittingSize(block)
        XCTAssertEqual(size.height, House.Spacing.sm * 2 + 20 + House.Spacing.lg + House.Spacing.xl + 12, accuracy: 0.5)
        XCTAssertGreaterThanOrEqual(size.width, House.Spacing.md * 2 + 60 + House.Spacing.xs - 0.5)
    }

    func testSegmentedControlBindsSelection() {
        var selection = 1
        let binding = Binding(get: { selection }, set: { selection = $0 })
        let view = SlateSegmented(options: [(1, "One"), (2, "Two")], selection: binding)
        XCTAssertGreaterThan(fittingSize(view).width, 0)
    }

    func testAppearancePreferenceDefaultsToDark() {
        let suite = UserDefaults.standard
        let saved = suite.string(forKey: AppearancePreference.key)
        defer { suite.set(saved, forKey: AppearancePreference.key) }
        suite.removeObject(forKey: AppearancePreference.key)
        XCTAssertEqual(AppearancePreference.current, .dark)
        suite.set("light", forKey: AppearancePreference.key)
        XCTAssertEqual(AppearancePreference.current, .light)
    }
}

@MainActor
private final class StubModel: MenuPanelModeling {
    var onClose: () -> Void = {}
    var moves: [Int] = []
    var ran = 0
    var escaped = 0
    func moveSelection(by delta: Int) { moves.append(delta) }
    func runSelection() { ran += 1 }
    func escape() { escaped += 1 }
}

@MainActor
private final class RecordingController: MenuPanelController<Text, StubModel> {
    var extraKeys: [UInt16] = []

    override func handle(_ key: PanelKeyPress) -> Bool {
        if key.keyCode == 0 {
            extraKeys.append(key.keyCode)
            return true
        }
        return super.handle(key)
    }
}

@MainActor
final class MenuPanelControllerTests: XCTestCase {
    private func press(_ code: UInt16) -> PanelKeyPress {
        let event = NSEvent.keyEvent(
            with: .keyDown, location: .zero, modifierFlags: [], timestamp: 0,
            windowNumber: 0, context: nil, characters: "", charactersIgnoringModifiers: "",
            isARepeat: false, keyCode: code
        )!
        return PanelKeyPress(event)
    }

    func testArrowsReturnAndEscapeDriveTheModel() {
        let model = StubModel()
        let controller = RecordingController(model: model, width: 300) { Text("panel") }
        XCTAssertTrue(controller.handle(press(125)))
        XCTAssertTrue(controller.handle(press(126)))
        XCTAssertTrue(controller.handle(press(36)))
        XCTAssertTrue(controller.handle(press(53)))
        XCTAssertFalse(controller.handle(press(9)))
        XCTAssertEqual(model.moves, [1, -1])
        XCTAssertEqual(model.ran, 1)
        XCTAssertEqual(model.escaped, 1)
    }

    func testSubclassFromAnotherModuleCanAddKeys() {
        let controller = RecordingController(model: StubModel(), width: 300) { Text("panel") }
        XCTAssertTrue(controller.handle(press(0)))
        XCTAssertEqual(controller.extraKeys, [0])
    }
}
#endif
