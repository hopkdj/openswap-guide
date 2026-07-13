---
title: "Scala JSON Library Comparison: Circe vs Play-JSON vs Spray-JSON vs Argonaut"
date: "2026-07-14"
tags: ["scala", "json", "circe", "play-json", "spray-json", "serialization", "jvm"]
draft: false
---

JSON serialization is a fundamental concern in any web application, and the Scala ecosystem offers several mature, type-safe approaches that go far beyond simple string manipulation. Unlike dynamic languages where JSON is trivially a hash map, Scala's type system demands compile-time safety and principled encoding/decoding. In this article, we compare four of the most popular Scala JSON libraries — **Circe**, **Play-JSON**, **Spray-JSON**, and **Argonaut** — examining their APIs, type-safety guarantees, performance characteristics, and integration with popular frameworks.

## Quick Comparison

| Feature | Circe | Play-JSON | Spray-JSON | Argonaut |
|---------|-------|-----------|------------|----------|
| **GitHub Stars** | ~2.5K | Part of Play | ~1K | ~500 |
| **Encoding Model** | Type class (automatic/semi-auto) | Type class (Reads/Writes/Format) | Type class (JsonFormat) | Codec-based |
| **Derivation** | Automatic, semi-auto, manual | Manual macros (JSON.format) | Manual (jsonFormatN) | Manual codecs |
| **Shapeless/HList** | Yes (core design) | No | No | No |
| **Cats/Cats-Effect** | Native | Separate module | No | Via argonaut-cats |
| **Performance** | Very good | Good | Good | Moderate |
| **Error Handling** | DecodingFailure (accumulating) | JsError (accumulating) | DeserializationException | Cursor history |
| **JSON AST** | io.circe.Json | play.api.libs.json.JsValue | spray.json.JsValue | argonaut.Json |
| **Scala 3 Support** | Yes | Yes | Community fork | Limited |

## Circe: Type-Class-Driven Purity

Circe (pronounced "SUR-see") is the current gold standard for JSON in Scala. Built on top of the `cats` and `shapeless` libraries, it uses type classes to automatically derive JSON encoders and decoders for case classes at compile time. The name is a pun on Circe the sorceress — it's "compiler-verified JSON codecs."

### Setup

```scala
// build.sbt
libraryDependencies ++= Seq(
  "io.circe" %% "circe-core"    % "0.14.7",
  "io.circe" %% "circe-generic" % "0.14.7",
  "io.circe" %% "circe-parser"  % "0.14.7"
)
```

### Basic Usage

```scala
import io.circe._
import io.circe.generic.auto._
import io.circe.parser._
import io.circe.syntax._

case class User(id: Long, name: String, email: String)
case class ApiResponse(status: String, data: List[User])

// Automatic derivation — no boilerplate
val user = User(1, "Alice", "alice@example.com")

// Encoding
val json: String = user.asJson.noSpaces
// {"id":1,"name":"Alice","email":"alice@example.com"}

// Decoding
val result: Either[Error, User] = decode[User](json)
result match {
  case Right(user) => println(s"Welcome, ${user.name}")
  case Left(error) => println(s"Parse error: ${error.getMessage}")
}

// Parsing raw JSON
val rawJson = """{"status":"ok","data":[{"id":1,"name":"Alice","email":"a@b.com"}]}"""
val apiResponse = decode[ApiResponse](rawJson)
```

### Semi-Automatic Derivation

For better compile times and explicit control, use semi-automatic derivation:

```scala
import io.circe.generic.semiauto._

case class Config(host: String, port: Int, tls: Boolean)

implicit val configDecoder: Decoder[Config] = deriveDecoder[Config]
implicit val configEncoder: Encoder[Config] = deriveEncoder[Config]

// Custom field name mapping with annotations
import io.circe.generic.extras._
implicit val config: Configuration = Configuration.default.withSnakeCaseMemberNames

@ConfiguredJsonCodec
case class DatabaseConfig(maxConnections: Int, connectionTimeout: Int)
// Serializes as {"max_connections":...,"connection_timeout":...}
```

### Optics (Cursor-Based Manipulation)

Circe provides optics for navigating and modifying JSON without decoding to case classes:

```scala
import io.circe.optics.JsonPath.root

val json = parse("""{"users":[{"name":"Alice","age":30},{"name":"Bob","age":25}]}""")
  .getOrElse(Json.Null)

// Navigate and modify using optics
val ages = root.users.each.age.int.getAll(json)
// List(30, 25)

val modified = root.users.each.age.int.modify(_ + 1)(json)
// Adds 1 to every user's age
```

### Error Accumulation

Circe's `DecodingFailure` accumulates errors so you see all problems at once:

```scala
val badJson = """{"id":"not-a-number","name":null,"email":123}"""

import cats.implicits._
val result = decodeAccumulating[User](badJson)
// Invalid: 
//   DecodingFailure at .id: Got value '"not-a-number"' with wrong type, expecting Long
//   DecodingFailure at .name: Got value 'null' with wrong type, expecting String
```

### Pros and Cons

**Pros:**
- Compile-time derivation with zero runtime reflection
- Excellent error messages with accumulating failures
- Optics library for JSON manipulation without case classes
- Deep integration with the Scala type-level programming ecosystem (cats, shapeless)
- Best Scala 3 support of any JSON library

**Cons:**
- Depends on shapeless which increases compilation time
- Learning curve for developers new to type classes and implicit resolution
- Generic auto-derivation can cause implicit resolution conflicts in large projects

## Play-JSON: The Framework Standard

Play-JSON originated as part of the Play Framework but is now a standalone library. It uses a `Reads[T]` / `Writes[T]` / `Format[T]` type class pattern and is the default choice for any Play Framework application.

### Setup

```scala
// build.sbt
libraryDependencies += "org.playframework" %% "play-json" % "3.0.2"
```

### Basic Usage

```scala
import play.api.libs.json._
import play.api.libs.functional.syntax._

case class User(id: Long, name: String, email: String)

// Manual format definition — explicit field mapping
implicit val userFormat: Format[User] = (
  (__ \ "id").format[Long] and
  (__ \ "name").format[String] and
  (__ \ "email").format[String]
)(User.apply, unlift(User.unapply))

// For simple cases, use macro-based derivation
implicit val userFormat2: Format[User] = Json.format[User]

// Encoding and decoding
val user = User(1, "Alice", "alice@example.com")
val json = Json.toJson(user)
// {"id":1,"name":"Alice","email":"alice@example.com"}

val parsed = Json.parse("""{"id":2,"name":"Bob","email":"bob@test.com"}""")
val result: JsResult[User] = parsed.validate[User]  // JsSuccess or JsError
```

### Custom Validation

Play-JSON's `Reads` allows inline validation during parsing:

```scala
import play.api.libs.json.Reads._

implicit val userReads: Reads[User] = (
  (__ \ "id").read[Long](min(1L)) and
  (__ \ "name").read[String](minLength[String](1) keepAnd maxLength[String](100)) and
  (__ \ "email").read[String](email)
)(User.apply _)

val invalid = Json.parse("""{"id":0,"name":"","email":"not-an-email"}""")
invalid.validate[User] match {
  case JsSuccess(user, _) => println(s"OK: $user")
  case JsError(errors)    => errors.foreach(e => println(s"${e._1}: ${e._2.mkString(",")}"))
}
// /id: error.min (must be >= 1)
// /name: error.minLength (must be >= 1)
// /email: error.email (not a valid email)
```

### JsonTransformers

Play-JSON provides a powerful transformation DSL for updating nested JSON structures:

```scala
val original = Json.parse("""{"user":{"name":"Alice","meta":{"version":1}}}""")

val transformer = (__ \ "user" \ "meta" \ "version").json.update(
  __.read[JsNumber].map(v => JsNumber(v.value.toInt + 1))
)

val updated = original.transform(transformer)
// {"user":{"name":"Alice","meta":{"version":2}}}
```

### Pros and Cons

**Pros:**
- First-class integration with Play Framework
- `Reads` combinators allow validation during parsing
- JSON transformer API for complex JSON manipulation
- Mature, battle-tested in production since 2012

**Cons:**
- Combinator-based format syntax becomes verbose for large case classes
- Macro derivation (`Json.format`) has limited customization
- Less ergonomic outside of Play Framework projects
- No built-in accumulating errors (manual collection required)

## Spray-JSON: The Lightweight Contender

Spray-JSON is a minimalist JSON library developed alongside the Spray HTTP toolkit (predecessor to Akka HTTP). It requires you to define `JsonFormat` instances for each type but compensates with simplicity and zero dependencies beyond the Scala standard library.

### Setup

```scala
// build.sbt
libraryDependencies += "io.spray" %% "spray-json" % "1.3.6"
```

### Basic Usage

```scala
import spray.json._
import DefaultJsonProtocol._

case class User(id: Long, name: String, email: String)

// Define format manually or use helper
implicit val userFormat: RootJsonFormat[User] = jsonFormat3(User.apply)

// Encoding
val user = User(1, "Alice", "alice@example.com")
val json = user.toJson
println(json.prettyPrint)
// {
//   "id": 1,
//   "name": "Alice",
//   "email": "alice@example.com"
// }

// Decoding
val parsed = """{"id":2,"name":"Bob","email":"bob@test.com"}""".parseJson
val user2 = parsed.convertTo[User]
```

### Handling Optional and Nested Types

```scala
case class Address(street: String, city: String, zip: Option[String])
case class Person(name: String, age: Int, address: Address)

implicit val addressFormat: RootJsonFormat[Address] = jsonFormat3(Address.apply)
implicit val personFormat: RootJsonFormat[Person] = jsonFormat3(Person.apply)

val person = Person("Alice", 30, Address("123 Main St", "Springfield", None))
val json = person.toJson.compactPrint
// {"address":{"city":"Springfield","street":"123 Main St"},"age":30,"name":"Alice"}
// Note: None fields are omitted entirely
```

### Custom Formats

Spray-JSON makes custom formats straightforward:

```scala
import java.time.Instant

// Custom format for java.time.Instant
implicit val instantFormat: RootJsonFormat[Instant] = new RootJsonFormat[Instant] {
  def write(instant: Instant): JsValue = JsString(instant.toString)
  def read(json: JsValue): Instant = json match {
    case JsString(str) => Instant.parse(str)
    case _             => throw DeserializationException("Expected ISO-8601 string")
  }
}

case class Event(id: Long, timestamp: Instant)
implicit val eventFormat: RootJsonFormat[Event] = jsonFormat2(Event.apply)

val event = Event(1, Instant.now())
println(event.toJson.compactPrint)
// {"id":1,"timestamp":"2026-07-14T10:30:00Z"}
```

### Pros and Cons

**Pros:**
- No dependencies beyond Scala stdlib
- Simple, predictable API with minimal magic
- `jsonFormatN` helpers for case classes up to 22 fields
- Fast compilation with minimal implicit resolution overhead

**Cons:**
- No support for Scala 3 (community forks available)
- Limited error messages (no cursor path in `DeserializationException`)
- No accumulating errors — stops at the first failure
- Manual format definition required for complex types

## Argonaut: The Pioneer

Argonaut pioneered purely functional JSON handling in Scala. While its influence on the ecosystem is immense (Circe was directly inspired by it), the project has slowed in maintenance. It remains a solid choice if you need its specific features or are working with an existing Argonaut-based codebase.

### Setup

```scala
// build.sbt
libraryDependencies += "io.argonaut" %% "argonaut" % "6.3.9"
```

### Basic Usage

```scala
import argonaut._
import Argonaut._

case class User(id: Long, name: String, email: String)

implicit def UserCodecJson: CodecJson[User] =
  casecodec3(User.apply, User.unapply)("id", "name", "email")

val user = User(1, "Alice", "alice@example.com")
val json: Json = user.asJson
println(json.spaces2)

val decoded: Either[String, User] = json.as[User]
```

### Cursor-Based Navigation

Argonaut's cursor provides detailed navigation with history tracking:

```scala
val complex = """
{
  "response": {
    "users": [
      {"id": 1, "profile": {"name": "Alice", "role": "admin"}},
      {"id": 2, "profile": {"name": "Bob", "role": "user"}}
    ]
  }
}
""".parseOption.get

// Cursor navigation with error history
val cursor = complex.cursor
val names = cursor.downField("response")
                  .downField("users")
                  .downArray
                  .downField("profile")
                  .downField("name")

names.focus.foreach(println) // "Alice"

// When navigation fails, cursor.history shows the exact path attempted
val badCursor = complex.cursor.downField("missing")
println(badCursor.history)  // shows attempted path
```

### Pros and Cons

**Pros:**
- Pioneered functional JSON in Scala — deeply influential design
- Excellent cursor API with full navigation history
- Decent type-class derivation for standard case classes
- Integration with scalaz (argonaut-scalaz module)

**Cons:**
- Dormant maintenance (last release in 2023)
- No official Scala 3 support
- Slower than Circe for large JSON documents
- Smaller community and fewer learning resources

## Performance and Ecosystem Integration

For JSON-intensive applications, performance matters. Circe consistently leads in benchmarks due to its use of Jawn (a fast JSON parser) and compile-time codec generation. Spray-JSON is also fast for simple cases but defers to runtime reflection for `jsonFormatN` helpers. Play-JSON's transformer API introduces overhead for complex transformations, making it best suited for request/response handling in Play applications rather than batch JSON processing.

| Scenario | Recommendation |
|----------|---------------|
| New Scala 3 project | Circe |
| Play Framework application | Play-JSON |
| Minimal dependencies | Spray-JSON |
| Akka HTTP / Pekko HTTP | Spray-JSON (native integration) |
| Cats/Cats-Effect stack | Circe |
| Legacy Argonaut codebase | Argonaut (or migrate to Circe) |

For a broader look at Scala development tools, see our [Scala testing frameworks guide](../2026-07-06-scala-testing-frameworks-scalatest-specs2-utest/) and our [JVM build tools comparison](../2026-06-24-jvm-build-tools-gradle-maven-sbt-bazel/).

## FAQ

### Which library has the best Scala 3 support?

Circe has the most robust Scala 3 support. The core library compiles under Scala 3, and `circe-generic` uses Scala 3's native `derives` keyword for automatic derivation: `case class User(id: Long, name: String) derives Codec.AsObject`. Play-JSON also supports Scala 3, while Spray-JSON and Argonaut rely on community forks.

### How do I handle `camelCase` to `snake_case` conversion?

Circe provides `Configuration.default.withSnakeCaseMemberNames` via `circe-generic-extras`. Play-JSON requires manual `(JsPath \ "field_name").format[T]` mapping. Spray-JSON needs a custom `jsonFormatN` with explicit field names. Argonaut's `casecodecN` accepts explicit field name parameters.

### Can these libraries handle streaming JSON (JSON Lines, NDJSON)?

Yes. Circe has `circe-fs2` and `circe-iteratee` modules for streaming. Play-JSON integrates with Akka Streams for JSON streaming. Spray-JSON can parse NDJSON line by line using the standard `parseJson` per line. For large datasets, consider using a dedicated streaming JSON parser like `jawn-ast` or `zio-json`.

### What about ADT (sealed trait) serialization?

All four libraries support sealed trait hierarchies, but the approach differs. Circe uses `circe-generic-extras` and discriminators: `@JsonCodec sealed trait Event; case class Click(x: Int, y: Int) extends Event`. Play-JSON requires custom `Reads`/`Writes` with pattern matching. Spray-JSON uses `jsonFormat` with a discriminator field. This is the area where Circe's type-class approach provides the most ergonomic developer experience.

### Is it worth migrating from Argonaut to Circe?

If you're starting a new project, choose Circe. For existing Argonaut codebases, migration is worthwhile if you need Scala 3 support, better performance, or active maintenance. The migration path is well-documented: both libraries use the `CodecJson` pattern, and Circe's API was directly inspired by Argonaut. Typical migration effort for a medium codebase is 1-2 days.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Scala JSON Library Comparison: Circe vs Play-JSON vs Spray-JSON vs Argonaut",
  "description": "In-depth comparison of Scala JSON libraries — Circe, Play-JSON, Spray-JSON, and Argonaut — with code examples, type-class patterns, error handling, and Scala 3 compatibility.",
  "datePublished": "2026-07-14",
  "dateModified": "2026-07-14",
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
