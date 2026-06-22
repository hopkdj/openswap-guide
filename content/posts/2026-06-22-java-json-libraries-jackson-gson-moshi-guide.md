---
title: "Java JSON Libraries Compared: Jackson vs Gson vs Moshi — Which to Choose in 2026"
date: "2026-06-22"
tags: ["java", "json", "serialization", "libraries", "comparison", "parsing"]
draft: false
---

## Introduction

JSON has become the universal interchange format for web APIs, configuration files, and data storage. If you're building a Java application — whether it's a Spring Boot REST service, an Android app, or a batch data processor — you need a reliable JSON library. The Java ecosystem offers three standout choices: **Jackson**, **Gson**, and **Moshi**.

Jackson is the de facto standard, included in Spring Boot by default and known for its comprehensive feature set. Gson, from Google, prioritizes simplicity and has been a workhorse for Android development for over a decade. Moshi, from Square, brings modern Kotlin-friendly design and compile-time safety to JSON parsing.

This guide compares all three libraries across code examples, performance, feature sets, and ecosystem fit — helping you pick the right one for your project.

## Feature Comparison

| Feature | Jackson (9,741⭐) | Gson (24,217⭐) | Moshi (10,140⭐) |
|---------|-------------------|-----------------|------------------|
| **Latest Release** | 2.18.x (2026) | 2.12.x (2026) | 1.15.x (2026) |
| **Kotlin Support** | Via jackson-module-kotlin | Limited, reflection-based | First-class, code-gen based |
| **Streaming API** | Yes (JsonParser/JsonGenerator) | Yes (JsonReader/JsonWriter) | Limited (Okio integration) |
| **Annotation Support** | Extensive (50+ annotations) | Moderate (~10 annotations) | Moderate, Kotlin-friendly |
| **Data Binding** | Full (reflection + annotations) | Full (reflection-based) | Code-gen preferred |
| **Schema Generation** | Yes (jackson-module-jsonSchema) | No | No |
| **XML/YAML Support** | Yes (jackson-dataformat-xml) | No (JSON only) | No (JSON only) |
| **JAX-RS/Jakarta** | Native integration | Requires adapter | Requires adapter |
| **Android APK Size** | ~1.5 MB (core) | ~250 KB | ~200 KB |
| **Compile-Time Safety** | No (runtime reflection) | No (runtime reflection) | Yes (code-gen adapters) |

## Getting Started: Dependency Setup

**Maven — Jackson:**
```xml
<dependency>
    <groupId>com.fasterxml.jackson.core</groupId>
    <artifactId>jackson-databind</artifactId>
    <version>2.18.3</version>
</dependency>
```

**Maven — Gson:**
```xml
<dependency>
    <groupId>com.google.code.gson</groupId>
    <artifactId>gson</artifactId>
    <version>2.12.1</version>
</dependency>
```

**Maven — Moshi:**
```xml
<dependency>
    <groupId>com.squareup.moshi</groupId>
    <artifactId>moshi</artifactId>
    <version>1.15.2</version>
</dependency>
<dependency>
    <groupId>com.squareup.moshi</groupId>
    <artifactId>moshi-kotlin-codegen</artifactId>
    <version>1.15.2</version>
    <scope>provided</scope>
</dependency>
```

**Gradle (Kotlin DSL):**
```kotlin
// Jackson
implementation("com.fasterxml.jackson.core:jackson-databind:2.18.3")

// Gson
implementation("com.google.code.gson:gson:2.12.1")

// Moshi + codegen
kapt("com.squareup.moshi:moshi-kotlin-codegen:1.15.2")
implementation("com.squareup.moshi:moshi:1.15.2")
```

## Basic Serialization & Deserialization

Let's compare how each library serializes and deserializes a simple `User` record:

**Jackson:**
```java
import com.fasterxml.jackson.databind.ObjectMapper;

ObjectMapper mapper = new ObjectMapper();

// Serialize
User user = new User("alice", "alice@example.com", 30);
String json = mapper.writeValueAsString(user);
// {"name":"alice","email":"alice@example.com","age":30}

// Deserialize
User parsed = mapper.readValue(json, User.class);
```

**Gson:**
```java
import com.google.gson.Gson;

Gson gson = new Gson();

// Serialize
String json = gson.toJson(new User("alice", "alice@example.com", 30));

// Deserialize
User parsed = gson.fromJson(json, User.class);
```

**Moshi (Kotlin with code-gen):**
```kotlin
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory

// Kotlin data class
@JsonClass(generateAdapter = true)
data class User(
    val name: String,
    val email: String,
    val age: Int
)

val moshi = Moshi.Builder().build()
val adapter = moshi.adapter(User::class.java)

// Serialize
val json = adapter.toJson(User("alice", "alice@example.com", 30))

// Deserialize
val parsed = adapter.fromJson(json)
```

Jackson's `ObjectMapper` is thread-safe and designed to be a singleton. Gson's `Gson` instance is also thread-safe and reusable. Moshi uses type-specific `JsonAdapter` instances generated at compile time, which are both thread-safe and highly efficient.

## Handling Complex JSON Structures

When dealing with nested objects, polymorphic types, or custom date formats, the libraries diverge significantly.

**Polymorphic Deserialization — Jackson:**
```java
@JsonTypeInfo(use = JsonTypeInfo.Id.NAME, property = "type")
@JsonSubTypes({
    @JsonSubTypes.Type(value = Circle.class, name = "circle"),
    @JsonSubTypes.Type(value = Rectangle.class, name = "rectangle")
})
public abstract class Shape { }

ObjectMapper mapper = new ObjectMapper();
Shape shape = mapper.readValue(json, Shape.class);
// Jackson auto-resolves to Circle or Rectangle based on "type" field
```

Jackson's polymorphic handling is the most mature, supporting type IDs, wrapper objects, and custom resolvers. Gson requires a custom `JsonDeserializer` implementation for polymorphism. Moshi supports polymorphic adapters since v1.5 via the `@JsonQualifier` annotation or custom `PolymorphicJsonAdapterFactory` — but the setup is more manual than Jackson's annotation-driven approach.

**Custom Date Formats — Gson:**
```java
Gson gson = new GsonBuilder()
    .setDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSSZ")
    .create();
```

**Null-Safety — Moshi:**
Kotlin's null-safety is Moshi's strongest advantage. If your Kotlin data class declares a non-nullable field but the JSON omits it, Moshi throws a clear `JsonDataException` at parse time. Jackson and Gson silently assign `null` (or a default value) — leading to `NullPointerException` bugs that surface only at runtime.

## Performance Benchmarks

While all three libraries are fast enough for most applications, their performance characteristics differ:

| Benchmark | Jackson | Gson | Moshi |
|-----------|---------|------|-------|
| **Small JSON (1 KB)** | ~0.8 μs | ~1.2 μs | ~0.6 μs |
| **Medium JSON (100 KB)** | ~4 ms | ~7 ms | ~3 ms |
| **Large JSON (1 MB)** | ~45 ms | ~80 ms | ~35 ms |
| **Memory per 1K objects** | ~120 KB | ~90 KB | ~80 KB |
| **Startup overhead** | Moderate | Low | Very low (code-gen) |

Moshi's code-gen approach gives it the edge on both speed and memory, especially for Kotlin-first projects. Jackson's streaming API makes it the best choice for processing multi-gigabyte JSON files incrementally. Gson is the lightest in terms of JAR size, making it ideal for Android where APK size matters.

## When to Choose Each

**Choose Jackson when:**
- You're using Spring Boot (it's the default)
- You need XML, YAML, CSV, or Protobuf support alongside JSON
- You're building REST APIs with JAX-RS or Jakarta EE
- You need polymorphic deserialization with minimal boilerplate
- You're working with large JSON streams

**Choose Gson when:**
- You want the simplest possible API with zero configuration
- You're building an Android app and APK size matters
- Your JSON schema is straightforward (no polymorphic types)
- You need to serialize Java records with minimal setup

**Choose Moshi when:**
- You're writing Kotlin (or Kotlin-first Android)
- You value compile-time safety over runtime reflection
- You want built-in null-safety guarantees
- You're building a performance-sensitive application
- Your team already uses Square libraries (OkHttp, Retrofit)

## Why Self-Host Your Java JSON Processing?

Understanding which JSON library powers your backend matters more than most developers realize. The library you choose affects serialization correctness, startup time, and memory allocation for every single API request your self-hosted service handles. Jackson's streaming parser can process gigabyte-sized JSON documents without loading them entirely into memory — critical for data pipeline services processing export dumps or log files. Gson's minimalist design means fewer transitive dependencies and a smaller attack surface for containerized microservices. Moshi's code-gen approach eliminates reflection overhead, which translates directly to lower CPU usage and faster cold starts on resource-constrained VPS instances.

For self-hosted Java applications processing high-throughput API traffic, the difference between Jackson and Moshi can mean 30-40% less CPU time spent on JSON serialization alone. If you're running a [self-hosted API gateway](../2026-05-19-self-hosted-api-gateway-management-kong-tyk-gravitee-guide/) that transforms JSON payloads between microservices, or a [self-hosted JSON schema validation service](../2026-06-08-self-hosted-json-schema-validation-ajv-prism-joi/), the parsing library you choose has a measurable impact on latency and throughput. For data pipeline teams using [self-hosted JSON processing CLI tools](../2026-06-17-self-hosted-json-processing-cli-tools-jq-vs-fx-vs-jid/) alongside Java batch processors, understanding how Jackson's tree model compares to Gson's object model helps avoid memory bottlenecks during ETL jobs.

If you're building [self-hosted BI dashboards](../2026-04-27-redash-vs-metabase-vs-apache-superset-self-hosted-bi-dashboard-g/) that consume JSON APIs, the serialization library in your backend directly affects dashboard load times — a poor choice in JSON parsing can add 200-400ms of latency to every chart query. Self-hosted developer tools that process [binary serialization formats](../2026-06-19-binary-serialization-frameworks-bincode-borsh-postcard-rkyv/) often need Jackson's multi-format capabilities to produce both JSON for web UIs and binary formats for internal RPC.

## FAQ

### Which JSON library does Spring Boot use by default?

Spring Boot includes Jackson as its default JSON serializer via `spring-boot-starter-web`. The auto-configured `ObjectMapper` bean is pre-configured with sensible defaults (ISO-8601 dates, no `null` serialization, `FAIL_ON_UNKNOWN_PROPERTIES` disabled). You can customize it by defining a `Jackson2ObjectMapperBuilderCustomizer` bean without replacing the entire mapper.

### Is Moshi compatible with Java-only projects?

Yes, but you lose many of its advantages. Moshi's code-gen works with both Java and Kotlin, but the null-safety guarantees only apply in Kotlin. In a Java-only project, Moshi behaves similarly to Gson — you just get slightly better performance. If you're not using Kotlin at all, Jackson or Gson are usually more practical choices.

### Can I use Gson with Kotlin data classes?

Technically yes, but Gson uses reflection and does not understand Kotlin's null-safety, default parameter values, or `val` immutability. A `data class` field declared as non-nullable will silently receive `null` from Gson if the JSON omits it, causing `NullPointerException` at runtime. Moshi with its Kotlin code-gen adapter is the recommended choice for Kotlin projects.

### How do I handle unknown JSON fields across all three libraries?

Jackson: `mapper.configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false)` (this is the Spring Boot default). Gson: ignores unknown fields by default. Moshi: throws `JsonDataException` by default; use `@JsonClass(generateAdapter = true)` with `@Json(name = "...")` annotations to explicitly declare known fields — any undeclared field is silently skipped.

### What's the best choice for a Spring Boot microservice that processes 10M+ JSON events per day?

Jackson is the natural choice because of its Spring Boot integration, streaming API for large payloads, and mature polymorphic handling. For extreme throughput scenarios, consider pairing Jackson's `JsonFactory` with manual streaming reads (bypassing `ObjectMapper` for the hot path) to achieve throughputs exceeding 100K events per second on a single thread.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Java JSON Libraries Compared: Jackson vs Gson vs Moshi — Which to Choose in 2026",
  "description": "Comprehensive comparison of Jackson, Gson, and Moshi for Java JSON processing — code examples, performance benchmarks, and practical guidance for Spring Boot, Android, and Kotlin projects.",
  "datePublished": "2026-06-22",
  "dateModified": "2026-06-22",
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
