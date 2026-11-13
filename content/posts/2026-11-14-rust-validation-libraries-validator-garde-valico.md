---
title: "Rust Validation Libraries in 2026: validator vs garde vs valico"
date: "2026-11-14"
tags: ["rust", "validation", "api-development", "developer-tools"]
draft: false
description: "validator, garde, and valico compared for Rust in 2026 — annotation-driven struct validation versus JSON Schema, with real code and the error-shape traps that break API clients."
---

# Rust Validation Libraries in 2026: validator vs garde vs valico

Validation is the part of an API everyone writes twice. First pass: a handful of `if` statements at the top of each handler. Second pass, three months later: the same checks, subtly different, copied into four handlers because the payload shape changed and nobody remembered to update the original. The bug is not that validation is missing — it is that validation drifted, and a field that used to be capped at 25 characters now accepts 25,000 and lands in your database.

A validation library exists to make drift impossible: one declaration per type, one error shape, enforced everywhere. In Rust the choice is narrower than it looks, and the three candidates are not even in the same category — **validator** and **garde** attach rules to your structs via derive macros, while **valico** validates `serde_json::Value` against a JSON Schema document. Picking between those two philosophies matters more than picking between the two derive macros.

## TL;DR

**Use validator** for the typical Rust web service. It is the most-used crate in this space by a wide margin (77M+ downloads), the annotation syntax is compact, and its `ValidationErrors` type maps directly onto an API error body. Version 0.21.0, last pushed July 2026.

**Use garde** if you need validation that is aware of context, borrowed data, or enums as first-class validatable types — or if you want the newer of the two APIs. It is smaller (6.3M downloads) but has the better story for non-trivial rules, and its `report` API is a genuine step forward.

**Use valico only if your contract is already JSON Schema.** For schema-driven validation of untrusted JSON — including coercion — it works. But it was last pushed in March 2024, its README still advertises version 2 while crates.io serves 4.0.0, and it does not know anything about your structs. For new code in 2026, that staleness is disqualifying unless you specifically need draft-v7 JSON Schema semantics.

## Comparison at a Glance

| Dimension | validator | garde | valico |
|---|---|---|---|
| Latest version | **0.21.0** | 0.23.0 | 4.0.0 |
| crates.io downloads | **77.3M** | 6.29M | 23.1M |
| GitHub stars | **2,529** | 913 | 306 |
| Last push | 2026-07-27 | 2026-07-31 | **2024-03-07** |
| Validation model | Derive on structs | Derive on structs + enums | JSON Schema on `serde_json::Value` |
| Error type | `ValidationErrors` (nested map) | `Report` (structured, ordered) | Schema error list |
| Enum support | No | **Yes** (`Valid<T>` wrapper) | N/A — validates values |
| Context / stateful rules | Custom functions only | **`Validate` with context** | No |
| Nested structs | `#[validate(nested)]` | `#[garde(dive)]` | Schema `$ref` |
| Feature-gated rules | Limited | **Yes** (`email`, `url`, …) | Built in |
| License | MIT | MIT | MIT |
| Maintenance signal | Active | Active | Inactive |

Read the download column carefully. validator's 77M and valico's 23M are cumulative and heavily inflated by transitive dependencies — valico's number is legacy from the era when REST frameworks pulled it in. GitHub push dates are the honest signal here, and they say: two maintained crates and one that stopped in 2024.

## Which One for Which Job

| Use case | Pick | Why |
|---|---|---|
| REST handler input structs | **validator** | Compact annotations, predictable error shape |
| Domain types with invariants enforced on construction | **garde** | Context-aware rules + enum support |
| Untrusted JSON from a third party | **valico** | JSON Schema is the actual contract |
| Config file validation at startup | **garde** | Borrowed `&str` fields avoid clones |
| Validating a struct you do not own | **valico** | Schema binds at runtime, not compile time |
| Multi-tenant rules (limits per plan) | **garde** | Context parameter carries tenant state |
| Legacy code already returning `ValidationErrors` | **validator** | Migration buys little |

## validator: The Default, and It Earns It

validator's model is annotation-driven and deliberately boring, which is what you want in a validation layer. Installation:

```toml
[dependencies]
validator = { version = "0.21", features = ["derive"] }
```

The crate's own README example is the best summary of what it covers:

```rust
use serde::Deserialize;
use validator::{Validate, ValidationError};

#[derive(Debug, Validate, Deserialize)]
struct SignupData {
    #[validate(email)]
    mail: String,
    #[validate(url)]
    site: String,
    #[validate(length(min = 1), custom(function = "validate_unique_username"))]
    #[serde(rename = "firstName")]
    first_name: String,
    #[validate(range(min = 18, max = 20))]
    age: u32,
    #[validate(range(exclusive_min = 0.0, max = 100.0))]
    height: f32,
}

fn validate_unique_username(username: &str) -> Result<(), ValidationError> {
    if username == "xXxShad0wxXx" {
        return Err(ValidationError::new("terrible_username"));
    }
    Ok(())
}
```

Three details make this practical. **`custom(function = ...)`** lets you bolt on business rules without leaving the declarative model — and because it takes `&str`, it composes with async-free validation nicely. **`exclusive_min`** exists specifically because "height must be greater than zero" is a different rule from "greater than or equal to zero," and getting that wrong in a hand-written check is a classic off-by-epsilon bug. **Nested structs** are handled explicitly rather than implicitly:

```rust
#[derive(Debug, Validate, Deserialize)]
struct SignupData {
    #[validate(nested)]
    contact_details: ContactDetails,
    #[validate(nested)]
    preferences: Vec<Preference>,
    #[validate(required)]
    allow_cookies: Option<bool>,
}
```

The error type is the part that decides how much code you write in your API layer. validator returns a `ValidationErrors` structure that serializes into a nested map of field name to messages — which is exactly the shape most frontends expect for inline field errors:

```rust
#[derive(Debug, Serialize, Clone, PartialEq)]
#[serde(untagged)]
pub enum ValidationErrorsKind {
    Struct(Box<ValidationErrors>),
    List(BTreeMap<usize, Box<ValidationErrors>>),
    Field(Vec<ValidationError>),
}
```

The weakness is visible in that enum: `List(BTreeMap<usize, ...>)` indexes errors by position in a vector, so if your frontend renders `preferences[2].name`, it must agree with Rust's ordering. That is fine for a stable payload and annoying for a form where rows can be reordered client-side.

## garde: Context, Enums, and a Better Report

garde takes the same derive approach but assumes you will eventually need something validator cannot express. Install with the full rule set:

```bash
cargo add garde -F full
```

The basic shape is familiar, but note the borrowed field types — `&'a str` rather than `String`, which means validating a request body parsed from a borrowed buffer costs no allocations:

```rust
use garde::Validate;

#[derive(Validate)]
struct User<'a> {
    #[garde(ascii, length(min=3, max=25))]
    username: &'a str,
    #[garde(length(min=15))]
    password: &'a str,
}

let user = User {
    username: "test",
    password: "not_a_very_good_password",
};

if let Err(e) = user.validate() {
    println!("invalid user: {e}");
}
```

Where garde pulls ahead is enums. validator's derives apply to structs; garde validates enum variants directly, including per-variant rules on tuple fields and struct fields:

```rust
use garde::{Validate, Valid};

#[derive(Validate)]
enum Data {
    Struct {
        #[garde(range(min=-10, max=10))]
        field: i32,
    },
    Tuple(
        #[garde(ascii)]
        String
    ),
}

let data = Data::Struct { field: 100 };
if let Err(e) = data.validate() {
    println!("invalid data: {e}");
}
```

This matters more than it sounds. Tagged-union payloads — `{"type": "card", ...}` versus `{"type": "bank", ...}` — are the normal shape of payment, notification, and webhook APIs. With validator you end up with per-variant structs and a manual match; with garde the rules live on the variants themselves.

Two more garde features are worth knowing before you commit. Rules are **feature-gated** (`email`, `url`, and others require the corresponding feature), so a minimal build does not drag in URL parsing. And `length` accepts an explicit mode — `simple`, `bytes`, `graphemes`, `utf16`, `chars` — which is the only correct way to enforce a user-visible character limit. `length(min=3, max=25)` on a string of emoji validates *bytes* by default, so a 7-emoji username can fail a 25-character rule that a human would count as valid. If you accept non-ASCII input and care about the limit, set the mode deliberately.

## valico: JSON Schema, and the Cost of Choosing It

valico is a different tool wearing a similar label. It validates `serde_json::Value` against a JSON Schema document (draft v7), with an additional DSL of validators and coercers:

```rust
use serde_json::Value;
use valico::json_schema;

let schema: Value = serde_json::from_str(r#"{
  "type": "object",
  "required": ["email"],
  "properties": { "email": { "type": "string", "format": "email" } }
}"#)?;
```

The appeal is real: if your contract already exists as JSON Schema — generated by an OpenAPI spec, shared with a TypeScript client, or maintained by another team — validating against it means one source of truth instead of two representations of the same rules. Coercion is the other draw: valico can turn `"42"` into `42`, which is what you want when a query string or form body arrives with everything typed as text.

The problem is timing. `s-panferov/valico` was last pushed in **March 2024**, and its README still instructs `valico = "2"` while crates.io serves 4.0.0 — a two-major-version documentation gap. JSON Schema draft 7 is now two drafts behind the current specification, and no amount of download history compensates for a crate nobody is updating. If you need schema validation today, evaluate the actively maintained alternatives in the `jsonschema` crate family, or generate a typed struct and validate it with validator or garde.

## Traps That Only Appear Once You Ship

**1. Validating input but not output.** Every library here is aimed at decoding. The inverse mistake — serializing a struct that a bug allowed into an invalid state — is worse, because now bad data is persisted. Enforce invariants in a constructor or a newtype, and let validation be the boundary check, not the only guarantee.

**2. `String` everywhere hides the real limit.** A `length(max = 255)` rule on a `TEXT` column is fiction; the database will happily store megabytes. Match the rule to the storage constraint, and remember that byte limits and character limits diverge the moment non-ASCII input arrives.

**3. The error-shape migration is a breaking API change.** validator's nested map and garde's ordered report produce different JSON. If a frontend already parses one, switching crates is a client-side breaking change, not an internal refactor. Decide the error contract once, wrap the library's error type in your own response type, and the choice becomes swappable.

**4. Losing the field path.** "Invalid input" is a useless error. Both derive crates preserve the path (`contact_details.mail`, `preferences[2].name`), but the moment you flatten errors into a single message for logging, that path disappears from the client's view. Log the structured form, return the path.

**5. Validating before deserialization.** Serde errors and validation errors are different failure modes and clients deserve to distinguish them. `{"age": "abc"}` is a type error; `{"age": 12}` is a validation error. If you collapse both into a 400 with one message, debugging becomes guesswork on the client side.

**6. Regex-based rules are a denial-of-service surface.** A `custom` rule with a pathological regex against a 100KB input can pin a core. Bound the input length *before* the rule runs, and prefer the built-in `email`/`url` validators over hand-rolled patterns.

**7. `Option<T>` plus `required` is not what you think.** On validator, `#[validate(required)]` on an `Option<bool>` rejects `None` — but if you forget it, `None` passes silently. On a PATCH endpoint that is usually the correct behavior and almost never the intended one.

If you are comparing across ecosystems, our [Go validation libraries guide](../2026-06-22-go-validation-libraries-goplayground-ozzo-govalidator-guide/) shows how `go-playground/validator` handles the same struct-tag model, and the [Java validation comparison](../2026-07-04-java-validation-libraries-hibernate-validator-jakarta-yavi-valiktor/) covers Jakarta Bean Validation, where the annotation approach originated. For the runtime-typed end of the spectrum, the [Python validation libraries comparison](../2026-07-26-python-validation-libraries-pydantic-cerberus-jsonschema/) covers Pydantic and the JSON-Schema-driven tools that valico is closest to in spirit.

## Where Validation Belongs in a Rust Service

The library choice matters less than the layer you put it in, and Rust makes the wrong layering unusually painful because of ownership.

**Validate at the deserialization boundary, once.** A handler receives bytes, deserializes to a request struct, calls `validate()`, and passes a *validated* type inward. If downstream functions accept the raw struct, nothing stops a future caller from skipping the check. The fix is a newtype — `Validated<SignupData>` — so the type system enforces what the annotation promised.

**Keep business rules out of the annotation layer.** `length(min = 3, max = 25)` is a payload constraint. "Username must not be taken" is a database query and does not belong in a derive macro. validator's `custom(fn)` invites you to blur that line; resist it, or your validation becomes an implicit I/O layer that is impossible to unit test without a database.

**Return one error contract for the whole service.** Wrap the library error in an `ApiError` enum with `From<ValidationErrors>` and `From<serde_json::Error>`, so every handler returns the same JSON shape. This is also what makes a future crate migration survivable.

**Test the boundaries, not the annotations.** Asserting that `validate()` rejects a 2-character username tests the library. Asserting that your handler returns 422 with `{"field": "username"}` tests your service. Write the second kind.

## FAQ

### Is validator or garde faster?

Both compile rules into ordinary Rust expressions, so validation itself is nanoseconds against a payload you already parsed. garde's edge is avoiding allocations by validating borrowed `&str` fields; validator's is a smaller, more mature error type. Neither difference survives contact with a real request that does any I/O. Benchmark only if validation is measurably hot in your profile.

### Can I use validator or garde with `serde_json::Value` instead of typed structs?

Not really — both are derive macros that need compile-time type information. If your payload shape is only known at runtime, that is exactly the case where valico (or a maintained JSON Schema crate) is the right tool. The general rule: typed input → derive; dynamic input → schema.

### Why does valico show 23M downloads if it is unmaintained?

Cumulative download counts never decrease, and valico spent years as a transitive dependency of REST frameworks. It is a museum piece of a healthy past, not evidence of present suitability. Check the last-push date and the version in the README against crates.io before trusting any download number — the README saying `valico = "2"` while the registry serves 4.0.0 tells you everything about the maintenance cadence.

### How do I validate a struct with a field of `Vec<T>`?

validator handles it with `#[validate(nested)]` on the vector, and reports errors as a map keyed by index. garde uses `#[garde(dive)]` on the container, with an optional `inner` modifier for the element type. Either way, remember that an empty vector passes — add a `length(min = 1)` rule if the field is mandatory.

### Does validation belong in the handler or the domain model?

Both, with different jobs. The handler validates *shape* (types, lengths, formats) so malformed input never reaches your logic. The domain validates *invariants* (a refund cannot exceed the original charge) in constructors, so no code path can create an invalid entity. Trying to do invariant checks in the derive macro pushes database and business state into a place that cannot access it.

### Can these libraries validate nested generics or recursive types?

validator's `nested` recurses through vectors and boxed fields but does not validate generic parameters automatically. garde's `dive` is more explicit about containers. Recursive structures need a depth limit regardless of the library — unbounded recursion during validation is a stack-overflow vector on hostile input.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Rust Validation Libraries in 2026: validator vs garde vs valico",
  "description": "validator, garde, and valico compared for Rust in 2026 — struct-derive validation versus JSON Schema, with real code and error-shape traps.",
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
