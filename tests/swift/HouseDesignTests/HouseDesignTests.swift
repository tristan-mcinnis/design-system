import SwiftUI
import XCTest
import HouseDesign

final class HouseDesignTests: XCTestCase {
    func testScalesAreReadableFromOutsideTheModule() {
        XCTAssertEqual(House.hairline, 1, accuracy: 0.5)
        XCTAssertGreaterThan(House.Radius.xl, House.Radius.lg)
        XCTAssertGreaterThan(House.Radius.lg, House.Radius.md)
        XCTAssertGreaterThan(House.Spacing.lg, House.Spacing.sm)
        XCTAssertGreaterThan(House.TypeToken.Size.heading, House.TypeToken.Size.meta)
    }

    func testShadowSpecPicksOpacityPerAppearance() {
        let spec = House.Shadow.panelNear
        XCTAssertEqual(spec.opacity(dark: false), spec.light)
        XCTAssertEqual(spec.opacity(dark: true), spec.dark)
    }

    #if canImport(AppKit)
    func testColoursResolvePerAppearance() throws {
        let light = try XCTUnwrap(NSAppearance(named: .aqua))
        let dark = try XCTUnwrap(NSAppearance(named: .darkAqua))
        func resolved(_ appearance: NSAppearance) -> NSColor {
            var color = NSColor.clear
            appearance.performAsCurrentDrawingAppearance {
                color = House.NSColorToken.surface.usingColorSpace(.sRGB) ?? .clear
            }
            return color
        }
        XCTAssertNotEqual(resolved(light), resolved(dark))
    }
    #endif

    func testUppercaseStylesAreNamed() {
        XCTAssertTrue(House.TypeToken.uppercase.contains("section"))
    }
}
