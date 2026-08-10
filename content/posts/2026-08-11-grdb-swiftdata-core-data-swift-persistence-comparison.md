---
title: "GRDB.swift vs SwiftData vs Core Data in 2026: Which Swift Persistence Layer Should You Actually Use?"
date: "2026-08-11"
tags: ["swift", "database", "ios", "developer-tools", "sqlite"]
draft: false
---

Every iOS team hits the same wall about six months in: the persistence layer you picked in week one is now the thing blocking every feature. Fetching is slow, migrations are terrifying, and the codebase is welded to APIs you barely understood. The good news? The Swift data layer has never been better — or more confusingly fragmented. In 2026 you have three serious options: **GRDB.swift** (8,593 stars, the SQLite power tool), **SwiftData** (Apple's modern framework, iOS 17+), and **Core Data** (the 20-year-old veteran that still ships in every Apple OS). This guide compares all three with real code, real trade-offs, and a clear recommendation for your situation.

## TL;DR / Quick Verdict

**Choose GRDB.swift if** you need real SQL power, complex queries, reactive UI updates, or fine control over your database file. **Choose SwiftData if** you're starting a greenfield SwiftUI app on iOS 17+ and want the least code. **Choose Core Data if** you have an existing codebase on it, need CloudKit sync with minimum effort, or must support OS versions older than iOS 17. My honest recommendation for most new apps in 2026: **GRDB.swift for anything data-heavy, SwiftData for simple apps that will stay simple.**

## The Quick Comparison

| Dimension | GRDB.swift | SwiftData | Core Data |
|---|---|---|---|
| License | MIT (open source) | Proprietary (Apple) | Proprietary (Apple) |
| GitHub stars / activity | 8,593⭐, updated 2026-08 | N/A (closed source) | N/A (closed source) |
| Storage engine | Direct SQLite | SQLite (Core Data stack underneath) | SQLite, XML, binary, in-memory |
| Minimum OS | iOS 11 / macOS 10.13 | iOS 17 / macOS 14 | iOS 3 / macOS 10.4 |
| Query interface | Typed SQL, Codable records | `#Predicate` macros | `NSPredicate` |
| Reactive updates | `ValueObservation` + Combine | `@Query` (SwiftUI only) | NSFetchedResultsController |
| CloudKit sync | Via GRDBCloudKit (manual) | Native (`cloudKitDatabase`) | Native (`NSPersistentCloudKitContainer`) |
| Concurrency model | async/await, actors, explicit queues | `@MainActor` by default, ModelActor | Context-per-thread (manual) |
| Learning curve | Medium (SQL knowledge helps) | Low (macros do the work) | Medium-high (many moving parts) |
| Best for | Power users, complex data | New simple SwiftUI apps | Legacy code, broad OS support |

## The Decision Matrix

| Use Case | Recommended Tool | Why |
|---|---|---|
| Complex queries, joins, full-text search | GRDB.swift | Full SQLite access, no ORM impedance |
| Greenfield SwiftUI app, iOS 17+ only | SwiftData | ~80% less boilerplate than Core Data |
| Existing Core Data app | Core Data | Migration cost exceeds any benefit |
| CloudKit sync out of the box | Core Data | NSPersistentCloudKitContainer is one line |
| Reactive SwiftUI lists | SwiftData | `@Query` is the cleanest API in the list |
| Precise control over DB file (encryption, backup) | GRDB.swift | Direct file access, SQLCipher integration |
| WatchOS / tvOS / macOS all at once | Core Data | 20 years of platform maturity |

## GRDB.swift — The SQLite Power Tool

GRDB.swift is a toolkit for SQLite databases "with a focus on application development." It is not an ORM in the traditional sense — it gives you the full power of SQLite with a thin, Swift-native layer on top. You write typed records that are `Codable`, and you can drop down to raw SQL whenever you need it. That flexibility is why it's my pick for data-heavy apps.

```swift
import GRDB

// A record is just a Codable struct — no base class required
struct Player: Codable, FetchableRecord, PersistableRecord {
    var id: Int64?
    var name: String
    var score: Int
}

// Open a database queue and run migrations
var dbQueue: DatabaseQueue!
try dbQueue = DatabaseQueue(path: "/path/to/app.sqlite")

try dbQueue.write { db in
    try db.create(table: "player") { t in
        t.autoIncrementedPrimaryKey("id")
        t.column("name", .text).notNull()
        t.column("score", .integer).notNull().defaults(to: 0)
    }
}

// Reactive UI: observe a query and get updates on every change
let observation = ValueObservation.tracking { db in
    try Player.filter(Column("score") >= 1000).fetchAll(db)
}
let cancellable = try observation.start(in: dbQueue) { players in
    print("Top players: \(players.map(\.name))")
}
```

And because GRDB apps ship a plain, standard SQLite file, you get the whole SQLite ecosystem for free — replicate it off-device with tools like Litestream, or inspect it with web-based management UIs. We've covered both angles in our [SQLite server deployments guide](../2026-06-17-self-hosted-sqlite-server-deployments-rqlite-litestream-mvsqlite-sqlite-web/) and our [SQLite management tools roundup](../2026-05-16-self-hosted-sqlite-management-datasette-sqlite-web-litecli-guide/).

What stands out: **ValueObservation** gives you database-driven reactive updates without needing SwiftUI at all — it works with Combine, so you can drive UIKit, AppKit, or SwiftUI views. Migrations are explicit and inspectable. And because you control the SQLite file directly, you can use **SQLCipher encryption**, share the database with extensions, or back it up with standard file tooling. The trade-off: you write more code than with SwiftData, and you must understand SQL concepts like transactions and foreign keys to get the most out of it.

## SwiftData — Apple's Modern Answer

SwiftData debuted at WWDC 2023 as the "modern" replacement for Core Data, built on the same underlying stack but with a Swift-first API powered by macros. The pitch is radical simplicity: a `@Model` macro turns a plain class into a persisted model, and `@Query` in SwiftUI turns a fetch into a live-updating property.

```swift
import SwiftData
import SwiftUI

// A model is a plain class + one macro
@Model
final class Player {
    var name: String
    var score: Int
    var createdAt: Date = Date()

    init(name: String, score: Int) {
        self.name = name
        self.score = score
    }
}

// Wire up the container once
let container = try ModelContainer(for: Player.self)

// In a SwiftUI view, @Query gives you live results
struct LeaderboardView: View {
    @Query(sort: \Player.score, order: .reverse)
    var players: [Player]

    var body: some View {
        List(players) { player in
            Text("\(player.name): \(player.score)")
        }
    }
}
```

SwiftData's killer feature is that **a single `@Query` replaces fetch requests, fetched results controllers, and manual observation** — the three pieces that made Core Data verbose. Since iOS 18, SwiftData also gained `SchemaMigrationPlan`, a declarative migration API, and `ModelActor` for background work. The catches: models are `@MainActor`-isolated by default (background writes require a `ModelActor`), it requires iOS 17 or later, and it is still much younger than Core Data — the sharp edges are fewer than in 2023 but they exist. CloudKit sync is native but has historically been the flakiest part.

## Core Data — The Veteran

Core Data has been in every iOS and macOS release since 2009 (macOS 10.4). It is an object graph and persistence framework that uses SQLite as its default store, and its age shows in both directions: an unmatched ecosystem of tutorials and battle-tested behavior, but an API that feels archaic next to SwiftData.

```swift
import CoreData

// The classic setup: a persistent container
let container = NSPersistentContainer(name: "PlayerModel")
container.loadPersistentStores { _, error in
    if let error = error { print("Store failed: \(error)") }
}

// Create and save — NSManagedObject subclasses, not plain types
let context = container.viewContext
let player = NSEntityDescription.insertNewObject(
    forEntityName: "Player", into: context
) as! Player
player.name = "Alice"
player.score = 2500
try context.save()

// Fetch with NSPredicate (string-based, not compile-time checked)
let request = NSFetchRequest<Player>(entityName: "Player")
request.predicate = NSPredicate(format: "score >= %d", 1000)
request.sortDescriptors = [NSSortDescriptor(key: "score", ascending: false)]
let results = try context.fetch(request)
```

Core Data's strengths are precisely where the others are weakest: **NSPersistentCloudKitContainer** gives you iCloud sync across devices with one line of setup, it supports iOS 3+ (if you're cursed enough to need that), and its undo/redo, faulting, and caching machinery are thoroughly debugged. Its weaknesses: `NSPredicate` strings are unchecked at compile time, `NSManagedObject` is not a plain Swift type (bye-bye Codable), and concurrency rules (never touch a managed object outside its context's queue) are easy to violate silently.

## Migration and Coexistence Strategies

The persistence layer you choose today becomes a migration problem tomorrow, so plan for it. **Core Data → SwiftData**: Apple provides no automatic migration path — you rewrite your models as `@Model` classes and move data with a one-off copy script. For models under ~10 entities this is a weekend job; for large graphs, weigh it carefully. **Core Data → GRDB**: you keep your SQLite file but must rebuild the object layer; GRDB's `Record` types are far simpler than `NSManagedObject`, so most teams find the new code *less* code. **SwiftData → GRDB**: because SwiftData stores in SQLite, you can open the same file with GRDB for reporting or ad-hoc queries while the app keeps using SwiftData — a pragmatic coexistence pattern many teams adopt during transition.

A few rules that apply regardless of choice: (1) **Version your schema from day one** — add a `schemaVersion` key in UserDefaults and a migration path before you ship v1. (2) **Never store large blobs in the main store** — keep images/files on disk and store only paths. (3) **Design for background writes early** — every framework here punishes you if you do heavy writes on the main thread once your dataset grows past a few thousand rows. (4) **Test migrations in CI** — a migration that works on a dev database can fail on a production database that's been through five previous migrations; keep a fixture database that exercises the full history.

## Common Pitfalls and Performance Traps

- **SwiftData main-actor surprise**: by default your `@Model` classes are main-actor isolated. If you import thousands of rows on a background queue without a `ModelActor`, you get hangs or crashes. Set up a `ModelActor` from day one if you sync or bulk-import.
- **Core Data context leaks**: holding an `NSManagedObject` reference after its context is deallocated is a classic crash source. Use `performBackgroundTask` for background work and never store managed objects in singletons.
- **GRDB observation over-firing**: `ValueObservation` re-runs your tracking closure on every relevant write. Add `.removeDuplicates()` and filter the tracked region (`tracking(region:)`) to avoid repainting the UI on unrelated writes.
- **CloudKit quota and rate limits**: iCloud sync is free only within your container's quota (1 PB per app but per-user storage limits apply, and there are daily record-operation caps). Sudden sync storms — e.g., first launch after importing 50k rows — can throttle sync for hours.
- **Undo/redo expectations**: Core Data ships undo management; SwiftData and GRDB do not. If your app needs multi-step undo, budget for implementing it yourself.
- **WatchOS and extension support**: all three run on watchOS, but Core Data is the only one with a decade of edge-case fixes in that environment. GRDB needs the SQLite file in a shared app group container for watch+phone sync.

## FAQ

**Is SwiftData production-ready in 2026?** Yes for new apps targeting iOS 17 and later. It has been stable across three major OS releases and gained migration tooling in iOS 18. It remains younger than Core Data, so expect occasional rough edges with advanced features like CloudKit sync and custom migrations.

**Can I use GRDB.swift with SwiftUI?** Yes. GRDB publishes Combine publishers through `ValueObservation` and has first-party SwiftUI support patterns (e.g., `@DatabaseObservation` or bridging observations into `ObservableObject`). You get reactive views with more control than SwiftData's `@Query`, at the cost of more glue code.

**Which of the three is fastest?** GRDB.swift is typically fastest for reads and bulk writes because it talks to SQLite directly with no object-graph layer. SwiftData and Core Data add overhead from their model layer, which is negligible at small scale but measurable on large datasets (tens of thousands of rows or more).

**Does SwiftData support CloudKit sync?** Yes, natively — declare `cloudKitDatabase: .private("iCloud.com.example.app")` on your `ModelContainer`, and your models sync across devices. It has matured since iOS 17 but still generates the most support threads of any SwiftData feature, so test sync-heavy flows early.

**Should I migrate my existing Core Data app to SwiftData?** Only if your model graph is small or you're already rewriting the data layer. Migration is manual, and Core Data continues to be fully supported by Apple — there is no announced deprecation. For a healthy Core Data app, "don't fix what works" is a defensible engineering decision.

**Can GRDB.swift be used on the server (Vapor) too?** GRDB.swift is officially supported on Apple platforms (iOS, macOS, watchOS, tvOS). If you're building server-side Swift, see our [Swift server-side framework comparison](../2026-07-06-swift-server-side-frameworks-vapor-hummingbird-grpc-swift/) — Vapor teams typically use Fluent with SQLiteKit there, which shares the same SQLite engine philosophy.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "GRDB.swift vs SwiftData vs Core Data in 2026: Which Swift Persistence Layer Should You Actually Use?",
  "description": "Deep comparison of GRDB.swift, SwiftData, and Core Data for Swift apps in 2026: performance, code examples, migration strategies, CloudKit sync, and pitfalls.",
  "datePublished": "2026-08-11",
  "dateModified": "2026-08-11",
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
