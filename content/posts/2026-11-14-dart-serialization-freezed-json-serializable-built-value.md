---
title: "Dart Serialization in 2026: freezed vs json_serializable vs built_value"
date: "2026-11-14"
tags: ["dart", "flutter", "serialization", "developer-tools"]
draft: false
cover: "/img/screenshots/freezed-codegen-example.jpg"
description: "freezed, json_serializable, and built_value compared for Dart and Flutter in 2026 — build_runner setup, generated code trade-offs, and the codegen traps nobody mentions."
---

# Dart Serialization in 2026: freezed vs json_serializable vs built_value

Every Dart project hits the same wall at roughly model number twelve. Hand-written `fromJson` constructors were fine when the payload had four fields; now you have nested lists, nullable timestamps with dashed keys, an enum that arrives as an integer, and a `copyWith` you wrote by hand that silently forgot the newest field. The bug is never a crash — it is a field that quietly resets to `null` in production and takes two days to trace.

Three packages solve this, and they solve *different problems*: **freezed** generates immutable value classes (with JSON support delegated to `json_serializable`), **json_serializable** generates `fromJson`/`toJson` for classes you write yourself, and **built_value** generates immutable value types with builders and a serializer registry. Choosing wrong costs you either a codebase full of half-immutable models or a build step that regenerates hundreds of files on every save.

## TL;DR

**Use freezed.** It is the default in 2026 for one reason: it generates the boring, high-value parts — `copyWith`, value equality, `toString`, sealed unions — and lets `json_serializable` handle JSON. The two are designed to work together, not compete. Roughly 2.2K GitHub stars and a 4.0.3 release in October 2026.

**Use json_serializable alone** when you only need JSON mapping and your models are already simple, mutable DTOs that never leave the data layer. It is a smaller dependency and generates less code.

**Use built_value** when you need strict immutability with builders across a large, long-lived codebase — or when you are serializing to something other than JSON, since its serializer registry is pluggable. At 884 stars it is the least fashionable of the three, but it is also the one Google's own Dart tooling has used longest.

## Comparison at a Glance

| Dimension | freezed | json_serializable | built_value |
|---|---|---|---|
| Current version | **4.0.3** (2026-10-17) | 6.15.2 (2026-10-20) | 8.13.0 (2026-09-02) |
| GitHub stars | **2,200** | 1,620 | 884 |
| Last push | 2026-11-09 | 2026-11-09 | 2026-09-02 |
| What it generates | Immutable classes, `copyWith`, unions, equality | `fromJson` / `toJson` only | Value types, builders, serializer registry |
| JSON support | Via `json_serializable` | Native | Native (pluggable plugins) |
| Immutability | Enforced | None (`final` fields only) | **Enforced, with builders** |
| Sealed unions | **Yes** (`sealed class`) | No | Partially (via `EnumClass`) |
| Nested serialization | Yes (delegated) | Yes (`@JsonSerializable`) | Yes (registry-based) |
| Custom key names | Via `json_serializable` annotations | **Yes** (`@JsonKey`) | Yes (`Serializers` plugin) |
| Builder dependency | `build_runner` 2.17.1 | `build_runner` 2.17.1 | `build_runner` 2.17.1 |
| Learning curve | Low | Lowest | Highest |
| Null safety story | `required` + nullable | Manual | Nullable fields default to `null` |

The version numbers matter here. All three sit on the same `build_runner`, so the real integration question is not "which generator" but "how many generators am I chaining in one build." Adding freezed *and* json_serializable means two passes over each file; adding built_value means a third kind of output in the same `.g.dart`-adjacent namespace.

## Which One for Which Job

| Use case | Pick | Why |
|---|---|---|
| Flutter app with API models | **freezed** | `copyWith` + equality are what widgets actually need |
| Server DTOs behind a REST layer | **json_serializable** | No immutability requirement; less generated code |
| State classes with variants (loading/error/data) | **freezed** | Sealed unions give exhaustive `switch` |
| Long-lived codebase with builders | **built_value** | Builder pattern survives schema churn better |
| Non-JSON serialization (binary, custom) | **built_value** | Serializer registry is pluggable |
| Generating model classes from OpenAPI | **json_serializable** | Simplest output to post-process |
| Rapid prototyping | **json_serializable** | One annotation, one part file |

## freezed: Immutability Plus Unions

freezed's install command tells you the whole architecture. Note the second block:

```bash
flutter pub add \
  dev:build_runner \
  freezed_annotation \
  dev:freezed

# if using freezed to generate fromJson/toJson, also add:
flutter pub add json_annotation dev:json_serializable
```

freezed does not generate JSON itself — it delegates to `json_serializable`. That is why the package boundary matters: `freezed_annotation` carries the annotations, `freezed` (dev dependency) carries the generator, and `json_annotation`/`json_serializable` are added only if you want serialization.

The canonical model:

```dart
import 'package:freezed_annotation/freezed_annotation.dart';

part 'person.freezed.dart';
part 'person.g.dart';

@freezed
abstract class Person with _$Person {
  const factory Person({
    required String firstName,
    required String lastName,
    required int age,
  }) = _Person;

  factory Person.fromJson(Map<String, Object?> json) => _$PersonFromJson(json);
}
```

What you get for those nine lines: an immutable class, a `copyWith` that covers every field, `operator ==` and `hashCode` based on field values, a readable `toString`, and `toJson`/`fromJson`. The `_$Person` mixin is the contract — if you rename a field and forget to regenerate, the analyzer fails loudly instead of failing at runtime.

The feature that justifies freezed over plain immutability is unions. Modelling a network result as three separate nullable fields (`isLoading`, `data`, `error`) is the single most common source of invalid states in Flutter code. freezed lets you express it as a closed set:

```dart
@freezed
sealed class Result with _$Result {
  const factory Result.loading() = Loading;
  const factory Result.data(Person person) = Data;
  const factory Result.failure(String message) = Failure;
}
```

A `switch` over `Result` now has to handle all three, and the compiler tells you when a fourth variant appears. There is no nullable-field equivalent of that guarantee.

The cost is build time and generated surface. Every freezed file produces a `.freezed.dart` (often several hundred lines) that you must not edit, must commit or regenerate in CI consistently, and must keep out of code review noise.

## json_serializable: The Minimal Contract

json_serializable does one thing and does it well. Its own example file is the shortest useful specification of the package:

```dart
import 'package:json_annotation/json_annotation.dart';

part 'example.g.dart';

@JsonSerializable()
class Person {
  final String firstName;
  @JsonKey(includeIfNull: false)
  final String? middleName;
  final String lastName;

  @JsonKey(name: 'date-of-birth')
  final DateTime dateOfBirth;

  @JsonKey(name: 'last-order')
  final DateTime? lastOrder;

  List<Order> orders;

  Person(
    this.firstName,
    this.lastName,
    this.dateOfBirth, {
    this.middleName,
    this.lastOrder,
    List<Order>? orders,
  }) : orders = orders ?? <Order>[];

  factory Person.fromJson(Map<String, dynamic> json) => _$PersonFromJson(json);

  Map<String, dynamic> toJson() => _$PersonToJson(this);
}
```

Three things to notice, because they are where real payloads break:

**`@JsonKey(name: ...)`** is how you survive an API that returns `date-of-birth` while Dart wants `dateOfBirth`. Every real integration has at least one of these.

**`@JsonKey(includeIfNull: false)`** stops you from sending `"middleName": null` to a backend that treats explicit nulls as "clear this field." That distinction has caused more production incidents than any serialization performance issue.

**Nested types need their own annotation.** `List<Order>` only works because `Order` is also annotated; the generator recurses. If `Order` is missing `@JsonSerializable()`, you get a compile error in the generated file, which is confusing the first time you see it.

What json_serializable does *not* give you: equality, `copyWith`, or immutability. A `@JsonSerializable()` class with non-final fields is mutable, and two instances with identical data are not `==`. If your widget rebuilds are driven by equality checks, that missing `==` is a subtle performance and correctness bug.

![freezed before/after codegen example](/img/screenshots/freezed-codegen-example.jpg "freezed removes hand-written boilerplate from your model classes")

## built_value: Builders, Serializers, and Deliberate Verbosity

built_value is the oldest idea here and the most opinionated. Instead of annotations on a hand-written class, you declare an abstract value type and let the generator produce implementations:

```dart
// Values must be created with all required fields.
final value = SimpleValue((b) => b..anInt = 3);

// All values implement operator==, hashCode and toString.
final value2 = SimpleValue((b) => b
  ..anInt = 3
  ..aString = 'three');
assert(value != value2);

// New values are created via "rebuild".
final value3 = value.rebuild((b) => b..aString = 'three');
assert(value2 == value3);

// Convert to a builder and hold it for a while.
final builder = value3.toBuilder();
builder.anInt = 4;
final value4 = builder.build();
assert(value3 != value4);
```

That builder-rebuild cycle is the whole design philosophy. In a large app where a form edits a deep object graph, `rebuild` with a nested builder (`b..simpleValue.anInt = 1`) is considerably safer than a `copyWith` chain, because the mutation is scoped and the result is immutable at every level.

Serialization goes through a registry, which is a real architectural difference:

```dart
import 'package:built_value/standard_json_plugin.dart';

@SerializersFor([SimpleValue, CompoundValue, ValidatedValue])
final Serializers serializers = (_$serializers.toBuilder()
      ..addPlugin(StandardJsonPlugin()))
    .build();
```

The plugin list is why built_value can serialize to formats other than JSON — you swap the plugin instead of rewriting every model. If you are talking to a binary protocol or a legacy XML service, that flexibility is worth the ceremony.

The cost is genuine: more concepts (serializers, builders, `EnumClass`, `built_collection`), a `.g.dart` file that is harder to read, and slow generator startup on large projects. Its last push was 2026-09-02 while the other two pushed on 2026-11-09 — not abandoned, but not where daily development happens.

## Traps That Bite After the Honeymoon

**1. Committing generated files without a regeneration check.** If CI trusts committed `.g.dart` files, a developer who changes a model and forgets `build_runner` can merge a stale generated file. Add a CI step that runs the generator and fails if `git diff` is non-empty. This single check prevents the most common class of "works on my machine" bug in Dart projects.

**2. `build_runner` fighting itself.** freezed and json_serializable both want to write alongside your source. Running `build_runner watch` while also running `build` in a pre-commit hook produces truncated part files. Pick one workflow per environment: `watch` locally, `build --delete-conflicting-outputs` in CI.

**3. Forgetting `--delete-conflicting-outputs`.** When two generators claim the same `.g.dart`, build_runner refuses to write. Everyone hits this once; the flag is the fix, and it belongs in your documented command, not in tribal knowledge.

**4. Nullable-vs-missing is not the same thing.** `null` and "key absent" both deserialize to `null` by default. If your backend distinguishes them — PATCH semantics usually do — you need an explicit tri-state or the raw JSON map. No generator solves this for you.

**5. DateTime and timezone drift.** `DateTime.parse` preserves the offset only if the string has one; a naive timestamp becomes local time. Store UTC at the boundary and convert at render time, and write a test with an explicit `Z` suffix and one without.

**6. Enum values that arrive as integers.** Production APIs change enum wire formats more often than docs admit. Pin each enum with `@JsonValue`, otherwise a new server-side value arrives as an unmapped string and your `switch` throws at runtime rather than failing at compile time.

For how these models behave inside a full app architecture, our [Flutter state management comparison](../2026-09-05-flutter-state-management-riverpod-vs-bloc-vs-provider/) covers why immutable state classes pair so naturally with Riverpod and BLoC. If your models are being deserialized from HTTP responses, the [Dart HTTP client comparison](../2026-08-19-dio-vs-chopper-vs-http-dart-flutter-http-clients-comparison/) covers where to put that decode step so retries and interceptors do not re-parse payloads. And if the same models cross the network boundary to a Dart backend, the [Dart server-side frameworks guide](../2026-09-04-dart-server-side-frameworks-serverpod-dart-frog-shelf/) shows how Serverpod shares model definitions between client and server.

## Migrating Between Them

The migrations are asymmetric, and knowing the direction saves a rewrite.

**json_serializable → freezed** is mechanical and incremental: add `@freezed`, change `class` to `abstract class ... with _$X`, add the `freezed.dart` part, keep the existing `json_serializable` annotations and `part 'x.g.dart'`. One model at a time, no big-bang branch.

**freezed → json_serializable** is a downgrade you should only do deliberately: you lose `copyWith` and equality, and every call site that relied on structural equality keeps compiling while behaving differently. That is the worst kind of refactor — silent semantic change.

**built_value → freezed** requires replacing builder calls with `copyWith` at every call site. Nested builder updates (`b..child.field = x`) have no direct `copyWith` equivalent, so expect to write explicit transformations for deep graphs.

## FAQ

### Do I need both freezed and json_serializable?

If you want JSON support with freezed, yes. freezed generates the class, `copyWith`, equality, and unions; json_serializable generates `fromJson`/`toJson`. The freezed install instructions add both packages for exactly this reason. If you do not need JSON at all — for example, models built purely from local database rows — freezed alone is enough.

### Is built_value still maintained in 2026?

Yes, but at a slower cadence than the alternatives. The latest release is 8.13.0 (September 2026) with the repository last pushed the same month, versus November 2026 activity for freezed and json_serializable. It remains a sound choice for codebases already built around builders and serializer plugins; it is not the package to pick for greenfield work unless you specifically need its pluggable serialization or builder semantics.

### Which package produces the least generated code?

json_serializable, by a wide margin, because it only emits mapping functions. freezed emits a full class implementation plus, when combined with json_serializable, the mapping as well. built_value emits value implementations, builders, and serializer wiring. Generated code size matters for analyzer performance and repository size, not for runtime speed.

### Does codegen slow down hot reload?

No. Generation is a build-time step; the running app consumes plain Dart classes. What does slow down is your edit loop when `build_runner watch` reprocesses a large project, which is why keeping generated output scoped per feature directory rather than in one giant models folder helps.

### Can I use these with Dart on the server, not just Flutter?

Yes, all three are pure Dart packages with no Flutter dependency. Serverpod projects, for example, generate their own model classes and can coexist with freezed models in the same package as long as the part files are distinct. The one caveat is that server-side generators sometimes claim the same output paths — check for conflicting `.g.dart` names before adding a second generator to a package.

### What about `dart_mapp` or hand-written extensions?

Smaller generators exist and are worth evaluating for narrow use cases, but they trade ecosystem maturity for novelty. Hand-written `fromJson` is legitimate for one or two tiny models and becomes a liability the moment a nullable field is added and one of the three hand-written copies is missed. The decision threshold I use: three models or one nested list, whichever comes first.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Dart Serialization in 2026: freezed vs json_serializable vs built_value",
  "description": "freezed, json_serializable, and built_value compared for Dart and Flutter in 2026, including build_runner setup and codegen traps.",
  "datePublished": "2026-11-14",
  "dateModified": "2026-11-14",
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
