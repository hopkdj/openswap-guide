---
title: "networknt vs Everit vs java-json-tools: The Best JSON Schema Validator for Java in 2026"
date: "2026-11-10"
tags: ["java", "json-schema", "api-validation", "openapi", "jvm", "api-design"]
draft: false
cover: "/img/screenshots/json-schema-walk-flow.jpg"
description: "A 2026 comparison of the three JSON Schema validators Java teams actually use — networknt 3.0.9, Everit 1.14.6 and java-json-tools 2.2.14 — with real code, draft-support facts and the SSRF trap nobody mentions."
---

JSON Schema draft 2020-12 has been the current specification for years, OpenAPI 3.1 embeds it, and yet one of the most-starred Java validators — **java-json-tools/json-schema-validator, 1,636 stars** — still tops out at **draft-4**. That is not a trivia item. It is the difference between validating the payload your API gateway actually receives and validating a decade-old approximation of it, silently ignoring `$defs`, `unevaluatedProperties`, and every `prefixItems` tuple rule you wrote. If your service validates JSON on the hot path, the validator you import in `pom.xml` is a contract decision.

Three libraries dominate the JVM: **networknt** (1,087 stars, 3.0.9), **Everit** (900 stars, 1.14.6) and **java-json-tools** (1,636 stars, 2.2.14). They differ in draft support, JSON object model, dependency weight and — most importantly — whether the project is still moving.

## TL;DR: The 30-Second Verdict

**Use networknt** for anything new: it supports draft-4 through 2020-12, works directly on Jackson `JsonNode`, and shipped 3.0.9 in November 2026. **Use Everit** only if your codebase is already built around `org.json.JSONObject` and you are staying on draft-4/6/7. **Use java-json-tools only to maintain legacy draft-4 schemas** — its last commit was July 2024 and it cannot parse modern drafts at all. In a Spring Boot service that already has Jackson on the classpath, networknt adds essentially nothing to your dependency tree.

## Side-by-Side Comparison

| Dimension | networknt | Everit | java-json-tools |
|---|---|---|---|
| Stable version | **3.0.9** | **1.14.6** | 2.2.14 |
| GitHub stars | 1,087 | 900 | **1,636** |
| License | Apache-2.0 | Apache-2.0 | Dual LGPL-3.0 / Apache-2.0 |
| Last commit | **2026-11-09** | 2025-08-01 | 2024-07-17 |
| Draft 4 | Yes | Yes | Yes |
| Draft 6 | Yes | Yes | No |
| Draft 7 | Yes | Yes | No |
| 2019-09 | **Yes** | No | No |
| 2020-12 | **Yes** | No | No |
| JSON model | Jackson `JsonNode` | `org.json.JSONObject` | Jackson `JsonNode` |
| Extra runtime deps | Jackson (databind, YAML), SLF4J | org.json | Jackson, Guava, jopt-simple |
| YAML schemas | Yes (jackson-dataformat-yaml) | No | No |
| Remote `$ref` resolution | Yes (must be locked down) | Yes | Yes |
| Maven coordinates | `com.networknt:json-schema-validator` | `com.github.erosb:everit-json-schema` | `com.github.java-json-tools:json-schema-validator` |
| Best fit | New services, OpenAPI 3.1 | org.json codebases | Legacy draft-4 only |

## Decision Matrix: Pick in 10 Seconds

| Your situation | Recommended | Why |
|---|---|---|
| Validating request bodies in a Spring Boot API | **networknt** | Jackson-native, no conversion, Spring-friendly beans |
| Schema authored as draft 2020-12 or bundled into OpenAPI 3.1 | **networknt** | The only one of the three that parses it |
| Existing code already builds `org.json.JSONObject` | **Everit** | Avoids a full tree conversion on every request |
| Maintaining a 2019-era service with draft-4 schemas | **java-json-tools** | It is already wired in; do not rewrite what works |
| Need YAML schemas alongside JSON | **networknt** | `jackson-dataformat-yaml` support is built in |
| Validating on every request with sub-millisecond budgets | **networknt** (compiled schema, cached) | Pre-compiled `JsonSchema` + `InputFormat` reuse |
| Starting a greenfield project in 2026 | **networknt** | Active releases and modern draft coverage |

## networknt 3.0.9 — Modern Drafts, Jackson-Native

```xml
<dependency>
  <groupId>com.networknt</groupId>
  <artifactId>json-schema-validator</artifactId>
  <version>3.0.9</version>
</dependency>
```

The core pattern is: build a registry once at startup, load the schema once, validate many payloads. Loading a schema per request is the single most common performance mistake with this library.

```java
import com.networknt.schema.Error;
import com.networknt.schema.InputFormat;
import com.networknt.schema.Schema;
import com.networknt.schema.SchemaRegistry;
import com.networknt.schema.SpecificationVersion;

import java.nio.charset.StandardCharsets;
import java.util.List;

public final class OrderValidator {
    private static final Schema SCHEMA;

    static {
        SchemaRegistry registry = SchemaRegistry.withDefaultDialect(SpecificationVersion.DRAFT_2020_12);
        String schemaData = new String(
                OrderValidator.class.getResourceAsStream("/schemas/order.json").readAllBytes(),
                StandardCharsets.UTF_8);
        SCHEMA = registry.getSchema(schemaData, InputFormat.JSON);
    }

    public static List<Error> validate(String json) {
        return SCHEMA.validate(json, InputFormat.JSON);   // empty list == valid
    }
}
```

Note the 3.x API break: `JsonSchemaFactory` and `ValidationMessage` from the 2.x line are gone. Version 3 replaced them with `SchemaRegistry`, `Schema`, `InputFormat` and `List<Error>`, so tutorials written before 2026 will not compile against 3.0.9.

A draft 2020-12 schema using tuple validation and `$defs` — the exact constructs java-json-tools cannot express:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.com/schemas/order.json",
  "type": "object",
  "required": ["id", "items"],
  "properties": {
    "id": { "type": "string", "format": "uuid" },
    "items": {
      "type": "array",
      "minItems": 1,
      "items": { "$ref": "#/$defs/item" }
    },
    "shipping": {
      "type": "object",
      "unevaluatedProperties": false,
      "properties": { "country": { "type": "string", "pattern": "^[A-Z]{2}$" } }
    }
  },
  "$defs": {
    "item": {
      "type": "object",
      "required": ["sku", "qty"],
      "properties": {
        "sku": { "type": "string", "minLength": 3 },
        "qty": { "type": "integer", "minimum": 1 }
      },
      "additionalProperties": false
    }
  }
}
```

Two details that trip people up. First, **`format` is annotation-only by default** in modern drafts — `format: "uuid"` will not fail validation unless you explicitly enable format assertions:

```java
List<Error> errors = SCHEMA.validate(json, InputFormat.JSON, executionContext ->
        executionContext.executionConfig(config -> config.formatAssertionsEnabled(true)));
```

Second, **remote `$ref` resolution is enabled and that is an SSRF vector**. The library's own documentation is explicit: it loads schemas from the classpath *and* over the internet by default, and the `SchemaLoader` (in `com.networknt.schema.resource`) can be configured to block or allow specific IRIs. A schema containing `"$ref": "http://169.254.169.254/latest/meta-data/"` will make your validator issue that request server-side. In any multi-tenant or user-supplied-schema scenario, restrict the loader set to `ClasspathResourceLoader` (your own schemas only) and drop `IriResourceLoader` — never leave default URL resolution enabled when schemas can be influenced by users.

![Schema validation walk-through: how networknt resolves and evaluates a document](/img/screenshots/json-schema-walk-flow.jpg "The validation walk — schema resolution, keyword evaluation and error collection — from the networknt documentation")

## Everit 1.14.6 — The org.json Option

Everit's distinguishing feature is its data model: it validates `org.json.JSONObject` / `JSONArray`, not Jackson nodes. If your stack already uses the org.json API (common in older Android and lightweight services), this avoids a full copy of every payload.

Note the coordinates — the project migrated under the `erosb` organization, so the artifact is `com.github.erosb:everit-json-schema` at **1.14.6**, even though older tutorials still show `com.github.everit-org.json-schema`.

```xml
<dependency>
  <groupId>com.github.erosb</groupId>
  <artifactId>everit-json-schema</artifactId>
  <version>1.14.6</version>
</dependency>
```

```java
import org.everit.json.schema.Schema;
import org.everit.json.schema.ValidationException;
import org.everit.json.schema.loader.SchemaLoader;
import org.json.JSONObject;
import org.json.JSONTokener;

JSONObject rawSchema = new JSONObject(
        new JSONTokener(OrderValidator.class.getResourceAsStream("/schemas/order.json")));
Schema schema = SchemaLoader.load(rawSchema);   // load once, reuse

try {
    schema.validate(new JSONObject(payload));
} catch (ValidationException e) {
    e.getAllMessages().forEach(System.err::println);  // nested errors, all messages
}
```

**Where it hurts:** draft-7 is the ceiling. If a schema declares `"$schema": "https://json-schema.org/draft/2020-12/schema"`, Everit will not evaluate `$defs` or `unevaluatedProperties` correctly — it may accept documents your spec says are invalid. Its last commit was August 2025, so treat it as maintenance mode rather than a growth path.

## java-json-tools 2.2.14 — Powerful, and Frozen in 2014

The most-starred validator of the three is also the least future-proof. Its README states validation support for **draft v4 and v3** — full stop. No draft-6, no draft-7, no 2019-09, no 2020-12. It is dual-licensed (LGPL-3.0 or Apache-2.0), which is why GitHub's license detector reports `NOASSERTION` instead of a clean SPDX identifier.

```xml
<dependency>
  <groupId>com.github.java-json-tools</groupId>
  <artifactId>json-schema-validator</artifactId>
  <version>2.2.14</version>
</dependency>
```

```java
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.github.fge.jsonschema.main.JsonSchema;
import com.github.fge.jsonschema.main.JsonSchemaFactory;
import com.github.fge.jsonschema.core.report.ProcessingReport;

ObjectMapper mapper = new ObjectMapper();
JsonSchemaFactory factory = JsonSchemaFactory.byDefault();
JsonSchema schema = factory.getJsonSchema(mapper.readTree(schemaStream));

ProcessingReport report = schema.validate(mapper.readTree(payload));
if (!report.isSuccess()) {
    report.forEach(msg -> System.err.println(msg.getMessage()));
}
```

It also drags in Guava and jopt-simple, which is a real cost if you are trying to keep a service image small.

**Where it hurts:** the last commit was July 2024, and the draft-4 ceiling is not a documentation gap — it is the implementation. Any schema using `$defs`, `dependentRequired`, `prefixItems` or `unevaluatedProperties` will be treated as if those keywords did not exist, which means **it silently passes documents that violate your contract**. Silent false negatives are worse than loud failures.

## Migration Notes and Production Traps

**1. Draft mismatch is silent, not loud.** Every one of these libraries will accept a schema whose `$schema` declares a newer draft than it implements; unknown keywords are simply ignored. Always assert the draft your validator actually supports, and add a contract test that feeds a known-invalid document and expects a failure.

**2. Compile schemas once, validate many times.** `JsonSchemaFactory.getSchema()` and `SchemaLoader.load()` parse and index the document. Doing it per request turns a 30 µs validation into a multi-millisecond one, and allocates heavily under load.

**3. Lock down remote `$ref`.** All three resolve `http(s)` references. If schemas ever come from tenants, plugins, or a database row someone can edit, you have built an outbound request primitive into your validator — the classic path to cloud metadata endpoints.

**4. Format assertions are opt-in.** In networknt you must enable `formatAssertionsEnabled`; in Everit, `format` validators are configurable; in java-json-tools, format checking is on but limited to draft-4 semantics. A passing test suite does not prove `format: "email"` is enforced.

**5. Error messages are part of your API.** Returning raw validator messages leaks schema internals and produces inconsistent client-facing errors. Map `ValidationMessage` into your own error envelope, with a stable code per keyword.

**6. Do not run two validators in one service "for safety".** Double validation doubles the cost and produces two different verdicts for the same payload when drafts differ. Pick one, pin the draft, and test it.

**7. Watch Jackson upgrades.** networknt 3.x is built against Jackson 2.x; Jackson 3 changes package names. If your platform moves to Jackson 3, confirm the validator release you pin supports it before upgrading the whole tree.

## Why Self-Hosting Validation Logic Still Wins

Schema validation is pure CPU-bound logic inside your own process — there is no managed service to buy and nothing to phone home. Keeping it in-process means request payloads never leave your infrastructure, which is the whole point of running your own API layer. It also means the schema file in your repository is the source of truth, reviewed in a pull request like any other contract change.

For the surrounding pieces, our [Java JSON library comparison](../2026-06-22-java-json-libraries-jackson-gson-moshi-guide/) covers the serializers these validators sit on top of, the [API contract management guide](../2026-05-19-self-hosted-api-contract-management-microcks-specmatic-spring-cloud-contract-guide/) shows how to enforce the same contracts in CI, and the [OpenAPI code generation comparison](../2026-04-30-openapi-generator-vs-swagger-codegen-vs-jhipster-self-hosted-code-generation-guide-2026/) is the natural next step once your schema is stable.

## FAQ

**Which JSON Schema validator is fastest for Java?**
networknt, in practice, because it pre-compiles schemas into a keyword graph and validates Jackson nodes without a tree conversion. But the dominant cost in real services is schema parsing per request, not the validation itself — cache the compiled `JsonSchema` and all three become fast enough.

**Does networknt support OpenAPI 3.1 schemas?**
Yes. OpenAPI 3.1 uses JSON Schema 2020-12 as its dialect, and networknt's `SpecVersion.VersionFlag.V202012` handles it. This is the main reason teams migrate off java-json-tools.

**Can Everit validate draft 2020-12?**
No. Everit supports draft-4, draft-6 and draft-7. Schemas with `$defs` or `unevaluatedProperties` will not be evaluated as the 2020-12 specification requires.

**Is java-json-tools abandoned?**
Effectively maintenance-only. The last commit was July 2024, and the implementation targets draft-4/v3. It still works for legacy schemas, but it cannot be your validator for new APIs.

**How do I stop remote `$ref` from making outbound requests?**
Configure a restricted resource loader set — classpath-only, or an allowlist of your own schema hosts. Never leave default URL resolution enabled when schemas can be influenced by users.

**Do I need a schema registry to use these?**
No. All three load schemas from a stream, file, or URL. A registry helps when many services share schemas and you need versioning, but a `schemas/` directory in the repository plus a contract test covers most teams.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "networknt vs Everit vs java-json-tools: The Best JSON Schema Validator for Java in 2026",
  "description": "A 2026 comparison of networknt 3.0.9, Everit 1.14.6 and java-json-tools 2.2.14 for validating JSON Schema in Java, including draft support, real code, and the remote $ref SSRF trap.",
  "datePublished": "2026-11-10",
  "dateModified": "2026-11-10",
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
