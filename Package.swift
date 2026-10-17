// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "design-system",
    platforms: [.macOS(.v14), .iOS(.v17)],
    products: [
        .library(name: "HouseDesign", targets: ["HouseDesign"]),
        .library(name: "HouseUIKit", targets: ["HouseUIKit"]),
    ],
    targets: [
        .target(name: "HouseDesign"),
        .target(name: "HouseUIKit", dependencies: ["HouseDesign"]),
        .testTarget(
            name: "HouseDesignTests",
            dependencies: ["HouseDesign"],
            path: "tests/swift/HouseDesignTests"
        ),
        .testTarget(
            name: "HouseUIKitTests",
            dependencies: ["HouseUIKit", "HouseDesign"],
            path: "tests/swift/HouseUIKitTests"
        ),
    ]
)
