---
title: "Swift Package Managers: SPM vs CocoaPods vs Carthage for iOS and macOS Dependency Management"
date: "2026-07-31"
tags: ["swift", "ios", "macos", "package-manager", "spm", "cocoapods", "carthage", "dependency-management", "apple", "xcode", "developer-tools"]
draft: false
---

## Introduction

Dependency management in Swift and Apple platform development has evolved significantly over the past decade. What started with manual framework copying gave way to **CocoaPods** (centralized, convention-based), then **Carthage** (decentralized, build-your-own), and finally **Swift Package Manager (SPM)** — Apple's official, integrated solution. Each tool represents a different philosophy about how dependencies should be resolved, built, and integrated.

With Swift Package Manager now deeply integrated into Xcode and supporting binary distribution, the landscape has shifted. But CocoaPods' massive library ecosystem (60,000+ pods) and Carthage's build flexibility still make them relevant choices. This comparison helps you navigate the trade-offs.

## Quick Comparison Table

| Feature | SPM (10,201 ⭐) | CocoaPods (14,828 ⭐) | Carthage (15,176 ⭐) |
|---|---|---|---|
| **Maintainer** | Apple (official) | Community (open source) | Community (open source) |
| **Integration** | Native Xcode integration | Workspace-based (`.xcworkspace`) | Manual framework linking |
| **Build Model** | Builds from source (supports binaries) | Builds from source (supports binaries) | Builds frameworks, you link |
| **Central Registry** | No (Git URLs only) | Yes (trunk, 60,000+ pods) | No (Git URLs only) |
| **Dependency Resolution** | SwiftPM's resolver | Molinillo resolver | Manual version pinning |
| **Binary Distribution** | XCFramework support | Podspec with vendored_frameworks | Native binary framework support |
| **Swift/C/Obj-C Support** | Swift packages + C targets | All languages | All languages |
| **CI/CD Setup** | Zero config with Xcode | Requires `pod install` | Requires `carthage bootstrap` |
| **Version Pinning** | `Package.resolved` | `Podfile.lock` | `Cartfile.resolved` |
| **Last Update** | 2026-07-31 | 2026-07-06 | 2025-09-10 |

## Getting Started: Adding Dependencies

### Swift Package Manager (SPM)

SPM is integrated into Xcode. Add dependencies via File → Add Package Dependencies, or edit `Package.swift` directly:

```swift
// Package.swift
// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "MyApp",
    platforms: [
        .iOS(.v16),
        .macOS(.v13)
    ],
    dependencies: [
        .package(url: "https://github.com/Alamofire/Alamofire.git", from: "5.8.0"),
        .package(url: "https://github.com/onevcat/Kingfisher.git", from: "7.0.0"),
        .package(url: "https://github.com/realm/SwiftLint.git", from: "0.54.0"),
    ],
    targets: [
        .executableTarget(
            name: "MyApp",
            dependencies: [
                .product(name: "Alamofire", package: "Alamofire"),
                .product(name: "Kingfisher", package: "Kingfisher"),
            ]
        ),
    ]
)
```

### CocoaPods

CocoaPods uses a `Podfile` and central registry (trunk):

```ruby
# Podfile
platform :ios, '16.0'
use_frameworks!

target 'MyApp' do
  pod 'Alamofire', '~> 5.8'
  pod 'Kingfisher', '~> 7.0'
  pod 'SwiftLint', '~> 0.54'

  target 'MyAppTests' do
    inherit! :search_paths
    pod 'Quick', '~> 7.0'
    pod 'Nimble', '~> 13.0'
  end
end

# Run: pod install
```

### Carthage

Carthage uses a simple `Cartfile` and builds frameworks you manually link:

```
# Cartfile
github "Alamofire/Alamofire" ~> 5.8
github "onevcat/Kingfisher" ~> 7.0
github "realm/SwiftLint" ~> 0.54

# Run:
# carthage bootstrap --platform iOS --use-xcframeworks
```

## CI/CD Pipelines Compared

### SPM (Simplest CI)

```yaml
# .github/workflows/build.yml — SPM needs nothing extra
- name: Build
  run: |
    xcodebuild build       -scheme MyApp       -destination 'platform=iOS Simulator,name=iPhone 15'       -skipPackagePluginValidation
```

### CocoaPods (Requires Additional Steps)

```yaml
# .github/workflows/build.yml
- name: Install Dependencies
  run: |
    gem install cocoapods
    pod install --repo-update

- name: Build
  run: |
    xcodebuild build       -workspace MyApp.xcworkspace       -scheme MyApp       -destination 'platform=iOS Simulator,name=iPhone 15'
```

### Carthage (Slowest CI)

```yaml
# .github/workflows/build.yml
- name: Install Dependencies
  run: |
    brew install carthage
    carthage bootstrap --platform iOS --use-xcframeworks --cache-builds

- name: Build
  run: |
    xcodebuild build       -project MyApp.xcodeproj       -scheme MyApp       -destination 'platform=iOS Simulator,name=iPhone 15'
```

## Dependency Resolution Strategies

The three tools handle version resolution differently, with significant practical implications:

**SPM** uses semantic versioning with a SAT solver. Your `Package.resolved` file acts as a lock file, pinning exact versions. When you run `swift package update`, SPM finds the latest compatible versions within your specified range. SPM also supports `branch` and `revision` dependencies for development.

**CocoaPods** uses the Molinillo resolver (the same algorithm behind Bundler). It resolves versions optimistically by default but supports pessimistic version constraints (`~>`). The `Podfile.lock` pins exact versions. CocoaPods' trunk enforces that once a version is published, it cannot be changed.

**Carthage** uses simple SemVer matching with no SAT solver. It resolves each dependency independently, then checks out the highest version matching the constraint. This means it can't detect version conflicts between transitive dependencies — you'll discover incompatibilities at build time rather than resolution time.

## Ecosystem and Library Availability

CocoaPods still has the largest ecosystem with over 60,000 pods on trunk. Many older but still-used libraries (Google Analytics, Crashlytics pre-Firebase) are only available via CocoaPods. However, the trend is clear: most actively maintained libraries now support SPM as their primary distribution method.

| Library | SPM | CocoaPods | Carthage |
|---|---|---|---|
| Alamofire | Yes | Yes | Yes |
| Kingfisher | Yes | Yes | Yes |
| Realm | Yes | Yes | Yes |
| Firebase | Yes (partial) | Yes | No |
| GoogleMaps | No | Yes | No |
| Lottie | Yes | Yes | Yes |
| SnapKit | Yes | Yes | Yes |

## When to Choose Each Package Manager

**Choose SPM when:**
- Starting a new project (SPM is Apple's official direction)
- You want zero-configuration CI/CD
- Your dependencies all support SPM
- You're building Swift packages or libraries for distribution

**Choose CocoaPods when:**
- You need libraries not available via SPM (older Google SDKs, niche pods)
- You want the largest library ecosystem
- Your team is already using CocoaPods and migration isn't justified
- You need pod-specific build configurations

**Choose Carthage when:**
- Build speed is the absolute priority (pre-built frameworks)
- You need fine-grained control over framework compilation
- You want to avoid workspace modifications
- You're maintaining an older project that already uses Carthage

## Why Self-Manage Your Dependency Graph?

Managing dependencies through explicit package manifests gives you auditability and reproducibility — critical for teams shipping to the App Store where rejected builds cost days of review time. Self-managed dependency graphs also mean you can fork and patch libraries when needed, without waiting for upstream maintainers. This is especially important on Apple platforms where App Store compliance requirements can change between OS releases.

For Swift server-side development where dependencies have different priorities, see our [Swift server-side frameworks comparison](../2026-07-06-swift-server-side-frameworks-vapor-hummingbird-grpc-swift/). If you're testing Swift applications, our [Swift testing frameworks guide](../2026-07-23-swift-testing-frameworks-xctest-quick-nimble-snapshottesting/) covers XCTest and alternatives. For handling JSON in Swift applications, check our [Swift JSON libraries comparison](../2026-07-26-swift-json-libraries-codable-swiftyjson-handyjson-objectmapper/).

## FAQ

### Is Carthage dead?

Carthage (15,176⭐) hasn't had a significant release since September 2025. While it still works for existing projects, the community has largely migrated to SPM. Carthage's core maintainers have acknowledged that SPM covers the majority of use cases now, and they recommend SPM for new projects. The last major update added XCFramework support, which was the final missing feature.

### Can I use SPM and CocoaPods together in the same project?

Yes, but it's not recommended for new projects. You can have SPM packages and CocoaPods in the same Xcode project — they don't conflict at the build system level. However, managing two dependency systems adds complexity: you'll have both `Package.resolved` and `Podfile.lock` to maintain, and CI needs both `pod install` and SPM resolution. Use this approach only during a migration from CocoaPods to SPM.

### How do I distribute a closed-source binary with SPM?

SPM supports binary targets via XCFrameworks since Swift 5.3. You define a binary target in your `Package.swift` pointing to a zip file URL containing the XCFramework. The zip file must include a checksum for integrity verification. This is how Firebase distributes its closed-source SDK via SPM. Use `swift package compute-checksum` to generate the checksum for your binary.

### What's the difference between `carthage bootstrap` and `carthage update`?

`bootstrap` reads the `Cartfile.resolved` lock file and checks out the pinned versions — use this in CI for reproducible builds. `update` resolves dependencies fresh, updates `Cartfile.resolved`, and then builds — use this when you want to upgrade dependencies. This is analogous to `pod install` vs `pod update`.

### Why does CocoaPods use a workspace instead of a project?

CocoaPods creates an `.xcworkspace` to combine your Xcode project with the Pods project. This workspace allows CocoaPods to manage build settings, link frameworks, and handle configuration files (`.xcconfig`) without modifying your original `.xcodeproj`. The workspace approach means CocoaPods can add and remove dependencies without touching your project file, reducing merge conflicts in team environments.

### How do I handle transitive dependency version conflicts?

SPM is the only tool that properly handles transitive dependency conflicts. Its SAT solver considers the entire dependency graph and finds a version that satisfies all constraints. CocoaPods' Molinillo also handles this but with a simpler algorithm that can fail on complex graphs. Carthage doesn't detect transitive conflicts at all — it builds each dependency independently and you discover conflicts at link time.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Swift Package Managers: SPM vs CocoaPods vs Carthage for iOS and macOS Dependency Management",
  "description": "In-depth comparison of Swift package managers — SPM, CocoaPods, and Carthage — covering CI/CD integration, dependency resolution, and ecosystem analysis for Apple platform development.",
  "datePublished": "2026-07-31",
  "dateModified": "2026-07-31",
  "author": {
    "@type": "Organization",
    "name": "OpenSwap Guide"
  },
  "publisher": {
    "@type": "Organization",
    "name": "OpenSwap Guide",
    "logo": {
      "@type": "ImageObject",
      "url": "https://hopkdj.github.io/openswap-guide/logo.png"
    }
  }
}
</script>
---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)