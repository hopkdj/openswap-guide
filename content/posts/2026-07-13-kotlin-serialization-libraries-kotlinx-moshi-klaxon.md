---
title: "Kotlin Serialization Libraries: kotlinx.serialization vs Moshi vs Klaxon"
date: "2026-07-13"
tags: ["kotlin", "serialization", "json", "kotlinx-serialization", "moshi", "klaxon", "android", "backend"]
draft: false
---

Serialization — converting data objects to and from formats like JSON, XML, and Protocol Buffers — is one of the most fundamental operations in any application. For Kotlin developers, the choice of serialization library has a direct impact on compile-time safety, runtime performance, and code readability.

Three libraries dominate the Kotlin serialization landscape: **kotlinx.serialization** — JetBrains' official, compiler-plugin-powered approach; **Moshi** — Square's modern JSON library with Kotlin codegen support; and **Klaxon** — a lightweight, pure-Kotlin JSON parser focused on simplicity.

Each takes a fundamentally different approach to the serialization problem. In this guide, we compare them across type safety, performance, multiplatform support, and real-world usability.

## Library Overview

| Feature | kotlinx.serialization | Moshi | Klaxon |
|---------|----------------------|-------|--------|
| **GitHub Stars** | ~5.5K | ~9.8K | ~2K |
| **Approach** | Compiler plugin | Annotation processor + codegen | Runtime reflection |
| **Formats** | JSON, CBOR, ProtoBuf, HOCON, XML, TOML, YAML | JSON only | JSON only |
| **Kotlin Multiplatform** | Yes (JVM, JS, Native, WASM) | JVM + Android only | JVM + Android only |
| **Null Safety** | Compile-time enforced | Runtime via adapters | Manual checking |
| **Default Values** | Full support | Via @Json annotation | Manual |
| **data class Support** | First-class | First-class | Primarily maps |
| **Streaming** | JsonDecoder streaming | JsonReader streaming | Streaming parser |
| **Kotlin-only Features** | Inline classes, sealed classes, value classes, unsigned types | Sealed class via PolymorphicJsonAdapterFactory | Basic sealed class via reflection |
| **Performance** | Very fast (compile-time codegen) | Fast (codegen + reflective fallback) | Slower (pure reflection) |

## Getting Started: Code Examples

### kotlinx.serialization

kotlinx.serialization uses a Gradle compiler plugin to generate serializers at compile time. Add the plugin and dependencies:

```kotlin
// build.gradle.kts
plugins {
    kotlin("jvm") version "1.9.22"
    kotlin("plugin.serialization") version "1.9.22"
}

dependencies {
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.6.3")
}
```

Then annotate your data classes with `@Serializable`:

```kotlin
import kotlinx.serialization.*
import kotlinx.serialization.json.*

@Serializable
data class User(
    val id: Long,
    val name: String,
    val email: String? = null,
    val role: UserRole = UserRole.VIEWER
)

@Serializable
enum class UserRole { ADMIN, EDITOR, VIEWER }

// Serialization
val user = User(1, "Alice", "alice@example.com", UserRole.ADMIN)
val json = Json.encodeToString(user)
// Output: {"id":1,"name":"Alice","email":"alice@example.com","role":"ADMIN"}

// Deserialization with strict type checking
val decoded: User = Json.decodeFromString(json)

// Handling unknown fields gracefully
val config = Json {
    ignoreUnknownKeys = true
    coerceInputValues = true
    prettyPrint = true
}
```

kotlinx.serialization shines with Kotlin-specific features:

```kotlin
@Serializable
data class Event(
    val timestamp: Long,
    val payload: Payload  // sealed class — fully supported
)

@Serializable
sealed class Payload {
    @Serializable
    @SerialName("text_message")
    data class TextMessage(val content: String) : Payload()

    @Serializable
    @SerialName("image_message")
    data class ImageMessage(val url: String, val width: Int, val height: Int) : Payload()
}

// Serialization handles polymorphic dispatch automatically
val event = Event(1700000000, Payload.TextMessage("Hello!"))
val json = Json.encodeToString(event)
// {"timestamp":1700000000,"payload":{"type":"text_message","content":"Hello!"}}
```

### Moshi

Moshi is Square's JSON library designed for Android and JVM Kotlin. It uses annotation processing (KAPT or KSP) for code generation:

```kotlin
// build.gradle.kts
dependencies {
    implementation("com.squareup.moshi:moshi-kotlin:1.15.1")
    ksp("com.squareup.moshi:moshi-kotlin-codegen:1.15.1")
}
```

```kotlin
import com.squareup.moshi.*
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory

@JsonClass(generateAdapter = true)
data class User(
    val id: Long,
    val name: String,
    val email: String? = null
)

val moshi = Moshi.Builder()
    .addLast(KotlinJsonAdapterFactory())
    .build()

val adapter: JsonAdapter<User> = moshi.adapter(User::class.java)

// Serialization
val user = User(1, "Alice", "alice@example.com")
val json = adapter.toJson(user)

// Deserialization
val decoded = adapter.fromJson(json) ?: error("null returned")
```

Moshi handles sealed classes through polymorphic adapters:

```kotlin
sealed class Animal {
    @JsonClass(generateAdapter = true)
    data class Dog(val bark: String) : Animal()

    @JsonClass(generateAdapter = true)
    data class Cat(val meow: String) : Animal()
}

val animalAdapter = PolymorphicJsonAdapterFactory.of(Animal::class.java, "type")
    .withSubtype(Animal.Dog::class.java, "dog")
    .withSubtype(Animal.Cat::class.java, "cat")
```

### Klaxon

Klaxon is a lightweight, pure-Kotlin JSON parser with no code generation or annotation processing required:

```kotlin
// build.gradle.kts
dependencies {
    implementation("com.beust:klaxon:5.6")
}
```

```kotlin
import com.beust.klaxon.*

data class User(val id: Long, val name: String, val email: String? = null)

// Parse JSON to a Map-like structure
val parser = Parser.default()
val json = """{"id": 1, "name": "Alice", "email": "alice@example.com"}"""
val obj = parser.parse(json) as JsonObject
println(obj.string("name"))  // "Alice"

// Convert to data class
val user = Klaxon().parse<User>(json)
println(user?.name)

// Streaming large JSON arrays
Klaxon().parseJsonArray(File("users.json").reader()).use { array ->
    for (item in array) {
        val user = Klaxon().parseFromJsonObject<User>(item as JsonObject)
        println(user?.name)
    }
}
```

Klaxon is ideal when you need quick JSON parsing without setting up annotation processors or compiler plugins. It's also excellent for reading JSON where the schema is dynamic or unknown at compile time.

## Kotlin Multiplatform (KMP) Support

One area where kotlinx.serialization stands alone is Kotlin Multiplatform. If you're sharing code between Android, iOS, web (JavaScript/TypeScript), and desktop (JVM/Native), kotlinx.serialization is the only option that works across all targets:

```kotlin
// shared/src/commonMain/kotlin
@Serializable
data class ApiResponse<T>(
    val data: T,
    val meta: PageMeta
)

// Works identically on Android, iOS Swift interop, and JS
val response = Json.decodeFromString<ApiResponse<User>>(jsonString)
```

Moshi and Klaxon are JVM-only, limiting them to Android and server-side Kotlin.

## Performance Comparison

In benchmarks measuring throughput (MB/s parsed), kotlinx.serialization leads due to its compile-time codegen that eliminates all reflection overhead. Moshi is close behind, especially when using KSP codegen (15-20% slower on deserialization). Klaxon, relying on runtime reflection, is typically 3-5x slower for large payloads.

For most applications processing under 1MB of JSON per request, the differences are imperceptible. The real performance concerns arise when serializing large collections (10,000+ items) or processing streaming data.

## Docker Deployment for Kotlin Services

A Kotlin backend service using these serialization libraries can be containerized with a standard Gradle build:

```yaml
version: "3.9"
services:
  kotlin-api:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8080:8080"
    environment:
      - KTOR_ENV=production
      - DB_HOST=postgres
    depends_on:
      - postgres
    restart: unless-stopped

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: app
      POSTGRES_USER: app
      POSTGRES_PASSWORD: secret
    volumes:
      - pgdata:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  pgdata:
```

```dockerfile
FROM gradle:8.5-jdk21 AS builder
WORKDIR /app
COPY build.gradle.kts settings.gradle.kts gradle.properties ./
COPY src ./src
RUN gradle build -x test --no-daemon

FROM eclipse-temurin:21-jre-alpine
COPY --from=builder /app/build/libs/*-all.jar /app.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "/app.jar"]
```

## Why Self-Host Your Kotlin Backend?

Kotlin's conciseness and null safety make it an excellent choice for self-hosted backend services. Combined with kotlinx.serialization's compile-time type safety, you get a system where invalid JSON schemas are caught at build time rather than at 3 AM production alerts.

For more Kotlin ecosystem comparisons, see our [Kotlin testing frameworks guide](../2026-07-06-kotlin-testing-frameworks-kotest-mockk-mockito-kotlin/). For Java developers exploring JSON handling on the JVM, our [Java JSON libraries comparison](../2026-06-22-java-json-libraries-jackson-gson-moshi-guide/) covers the broader JVM serialization landscape.

## Choosing the Right Library

| Use Case | Recommended Library |
|----------|-------------------|
| Kotlin Multiplatform (KMP) | kotlinx.serialization |
| Multi-format support (JSON+ProtoBuf+CBOR) | kotlinx.serialization |
| Android-first project with existing Square ecosystem | Moshi |
| Quick scripts and dynamic JSON | Klaxon |
| Compile-time safety as a hard requirement | kotlinx.serialization |
| Maximum backward compatibility (Java interop) | Moshi |
| Large existing Jackson/Gson codebase migration | Moshi |

## FAQ

### Do I need the Kotlin compiler plugin for kotlinx.serialization?

Yes — the compiler plugin is required. It generates the serializer code at compile time based on the `@Serializable` annotation. Without the plugin, your annotated classes won't have generated serializers and you'll get compilation errors. Add `kotlin("plugin.serialization")` to your Gradle plugins block.

### Can I use Moshi with Kotlin Multiplatform?

No. Moshi is built on Java reflection and annotation processing (KAPT/KSP), which limits it to JVM and Android targets. For Kotlin Multiplatform projects, kotlinx.serialization is the only production-ready JSON serialization option across all KMP targets.

### How does Klaxon handle null safety compared to kotlinx.serialization?

Klaxon is less strict about null safety. When parsing JSON that's missing a non-nullable field in your data class, Klaxon will create the object with the field set to the type's default value (0 for Long, "" for String, etc.). kotlinx.serialization throws a `MissingFieldException` at deserialization time, catching schema mismatches immediately.

### Is Moshi still maintained after Square's shift in focus?

Yes. Moshi continues to receive updates (latest 1.15.x as of 2026). It remains the recommended JSON library for Android development in many large organizations and has a stable, mature API. The KSP codegen migration has improved build performance significantly.

### What's the best choice for a Spring Boot Kotlin project?

Spring Boot uses Jackson by default, but you can configure it to use kotlinx.serialization via `spring-boot-starter-json` replacement. Moshi integrates well with Retrofit for API clients. If you're in the Spring ecosystem, Jackson is still the path of least resistance, but kotlinx.serialization offers better compile-time safety for Kotlin-first codebases.

### Can kotlinx.serialization handle unknown JSON fields gracefully?

Yes — use `Json { ignoreUnknownKeys = true }` in your configuration. This tells the parser to skip any JSON keys that don't match fields in your data class, rather than throwing `UnknownKeyException`. This is useful when consuming APIs that may add new fields without notice.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Kotlin Serialization Libraries: kotlinx.serialization vs Moshi vs Klaxon",
  "description": "A comprehensive comparison of Kotlin serialization libraries — kotlinx.serialization, Moshi, and Klaxon — covering multiplatform support, performance, type safety, and production deployment patterns.",
  "datePublished": "2026-07-13",
  "dateModified": "2026-07-13",
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
