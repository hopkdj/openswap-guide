---
title: "mapstructure vs mergo vs copier in 2026: Go Struct Mapping and Copying Done Right"
date: "2026-08-13"
tags: ["go", "golang", "struct-mapping", "developer-tools", "configuration"]
draft: false
cover: "/img/screenshots/mapstructure-pkg-go.jpg"
---

Every Go developer has written the same two loops a hundred times: the one that decodes a `map[string]interface{}` into a typed struct field by field, and the one that copies fields from one struct to another. Both are boring, repetitive, and a reliable source of subtle bugs — and both have battle-tested open-source solutions that most teams still reimplement by hand. **mapstructure**, **mergo**, and **copier** are the three libraries that eliminate this boilerplate, and they solve *different* problems. Here is when to reach for each.

## TL;DR / Quick Verdict

- **Pick mapstructure** for decoding dynamic data (config maps, JSON with unknown shapes, database rows) into typed structs — it is the de-facto standard, imported by over 30,000 modules.
- **Pick mergo** for merging two structs or maps into one, with fine control over zero-value and overwrite semantics.
- **Pick copier** for deep-copying values between structs with matching fields (e.g., DTOs, request/response models) without hand-writing assignment code.

## The Contenders

All three are MIT-licensed, mature, and widely adopted. They are complementary rather than competing: mapstructure converts *maps to structs*, mergo *merges values*, and copier *copies between structs*. Many production codebases use two of the three together.

| Library | GitHub Stars | Last Updated | License | Primary Job | Type Conversion | Deep Copy | Zero-Value Handling |
|---|---|---|---|---|---|---|---|
| **mapstructure** | 8,026 | 2024-06 (stable, done) | MIT | map → struct / struct → map | Yes (weak typing via reflection) | No (assigns references) | Yes (fills zero fields) |
| **mergo** | 3,105 | 2026-03 | BSD-3 | Merge struct/map into another | Partial | No | Configurable (`WithOverride`, `WithZeroValue`) |
| **copier** | 6,172 | 2026-03 | MIT | Copy fields between structs | Partial (basic) | Yes (deep copy of slices/maps) | Configurable (`IgnoreEmpty`) |

mapstructure is the oldest and most "finished" of the three: its last release (v1.5.0) dates to 2022, and its last commit to mid-2024 — which, for a library that 30,442 Go modules depend on, is a feature, not a bug. mergo has been maintained continuously since 2013 and is the workhorse for config-merge patterns. copier, from the same author as GORM, is the modern choice for model-to-model copying.

## Use Case → Recommended Tool

| Use Case | Recommended | Why |
|---|---|---|
| Decoding YAML/JSON config into typed structs | **mapstructure** | The canonical `map[string]interface{}` → struct decoder with `squash`, `remain`, and `omitempty` tag support |
| Reading a DB row or API response of unknown shape | **mapstructure** | Decode in two passes: inspect the raw map, then bind it to the right struct |
| Layering defaults + user config + env overrides | **mergo** | Merge config sources in order; zero fields get filled without clobbering |
| Merging structs where non-zero values must win | **mergo** | `mergo.MergeWithOverwrite` gives explicit control |
| DTO ↔ entity / request ↔ response conversion | **copier** | Deep-copies slices, maps, and nested structs by field name in one call |
| Copying structs with different field sets | **copier** | Fields present in both are copied; extras are ignored — perfect for API versioning |
| Avoiding reflection entirely in hot paths | **None of these** | All three use reflection; generate code with a tool if you need zero overhead |

## mapstructure — Decoding Dynamic Data into Typed Structs

**mapstructure** (8,026 stars) is the library Mitchell Hashimoto built for HashiCorp's config systems, and it remains the standard answer for "I have a `map[string]interface{}` and I want a `Config` struct." You control the mapping with `mapstructure` struct tags, including the three that most people discover the hard way: `,squash` to flatten embedded structs, `,remain` to capture unknown keys, and `,omitempty` when encoding back to a map.

```go
package main

import (
    "fmt"

    "github.com/mitchellh/mapstructure"
)

type Config struct {
    Name    string                 `mapstructure:"name"`
    Port    int                    `mapstructure:"port"`
    Feature map[string]interface{} `mapstructure:",remain"` // capture unknown keys
}

func main() {
    raw := map[string]interface{}{
        "name":    "api-server",
        "port":    8080,
        "debug":   true, // unknown key -> lands in Feature
        "verbose": false,
    }

    var cfg Config
    if err := mapstructure.Decode(raw, &cfg); err != nil {
        panic(err)
    }

    fmt.Printf("%+v\n", cfg) // {Name:api-server Port:8080 Feature:map[debug:true verbose:false]}
}
```

Embedded structs can be flattened with `,squash`:

```go
type Database struct {
    Host string `mapstructure:"host"`
    Port int    `mapstructure:"port"`
}

type AppConfig struct {
    Database `mapstructure:",squash"` // no "database" nesting in the input
    Debug    bool                     `mapstructure:"debug"`
}

// input: map[string]interface{}{"host": "localhost", "port": 5432, "debug": true}
```

Two details matter in production. First, decoding is **weakly typed by default**: `"8080"` (string) decodes into an `int` field without error, which is convenient but hides type bugs — set `ErrorUnused: true` and `WeaklyTypedInput: false` in a `DecoderConfig` when you want strict behavior. Second, unknown keys are silently dropped unless you use `,remain` or `ErrorUnused`. For a config loader, you almost always want one of those on.

```bash
go get github.com/mitchellh/mapstructure
```

## mergo — Merging Structs and Maps with Explicit Semantics

**mergo** (3,105 stars, updated **March 2026**) answers a different question: "I have two values of the same type, how do I combine them?" The default `Merge` fills only zero-valued fields in the destination, which is exactly the semantics you want when layering defaults over user config — the user's explicitly set values are never clobbered.

```go
package main

import (
    "fmt"

    "github.com/imdario/mergo"
)

type ServerConfig struct {
    Host    string
    Port    int
    Timeout int
}

func main() {
    defaults := ServerConfig{Host: "0.0.0.0", Port: 8080, Timeout: 30}
    user := ServerConfig{Port: 9090} // user only overrides the port

    merged := defaults
    if err := mergo.Merge(&merged, user); err != nil {
        panic(err)
    }

    fmt.Printf("%+v\n", merged) // {Host:0.0.0.0 Port:9090 Timeout:30}
}
```

When the source's zero values *should* win, flip the behavior with `mergo.Merge(&dst, src, mergo.WithOverride)`. mergo also handles maps (`mergo.Map(&dst, src)`), slices, and nested structs, and it supports `WithAppendSlice` and `WithTypeCheck` options for stricter merging. The one rule to internalize: **mergo merges, it does not deep-copy** — after a merge, shared nested pointers can alias, so treat merged configs as immutable downstream.

```bash
go get github.com/imdario/mergo
```

## copier — Deep-Copying Between Structs

**copier** (6,172 stars, updated **March 2026**) is the GORM author's answer to the endless DTO-conversion boilerplate. It copies values between structs by matching field names, and — unlike mapstructure or mergo — it deep-copies slices, maps, and nested structs, so the result is a fully independent value.

```go
package main

import (
    "fmt"

    "github.com/jinzhu/copier"
)

type User struct {
    Name  string
    Email string
    Tags  []string
}

type UserResponse struct {
    Name  string
    Email string
    Tags  []string
}

func main() {
    user := User{
        Name:  "jinzhu",
        Email: "jinzhu@gorm.io",
        Tags:  []string{"go", "orm"},
    }

    var resp UserResponse
    if err := copier.Copy(&resp, &user); err != nil {
        panic(err)
    }

    // Deep copy: mutating resp.Tags does not affect user.Tags
    resp.Tags[0] = "changed"
    fmt.Println(user.Tags) // [go orm]
    fmt.Println(resp.Tags) // [changed orm]
}
```

copier's matching rules are pragmatic: fields match by name, and it converts between compatible types (e.g., `string` to a `string`-backed custom type) automatically. Options include `copier.IgnoreEmpty` (skip empty source fields), custom converters via `copier.WithConverters`, and `copier.WithDeepCopy` for copy-on-write semantics. Its sweet spot is request/response mapping and entity-to-DTO conversion where both sides are typed structs.

```bash
go get github.com/jinzhu/copier
```

## Performance and Maintenance Notes

All three libraries rely on reflection, so their cost shows up in throughput-sensitive code — typically microseconds per call, which is irrelevant for config loading and HTTP handlers but measurable in tight loops. If a copy or decode runs millions of times per second, the standard advice applies: batch it, cache the result, or switch to generated code. For everything else, these libraries are the difference between 20 lines of repetitive reflection-adjacent code and one readable call.

Also note the maintenance contrast: mapstructure is deliberately frozen (v1.5.0, last touched 2024) and still the ecosystem standard — a good sign of a stable API. mergo and copier are actively developed, so pin versions and read release notes on upgrade. None of the three has had a security advisory affecting its core decoding path as of August 2026.

## Common Pitfalls and How to Avoid Them

1. **mapstructure silently drops unknown keys.** Without `,remain` or `ErrorUnused: true`, typos in config files pass silently. For user-facing config, always collect unused keys and warn.
2. **Weak typing hides bugs.** `mapstructure.Decode` will happily turn `"8080"` into `8080`. If you want strictness, build a `DecoderConfig` with `WeaklyTypedInput: false` — and be ready for legitimate string-vs-number mismatches in real configs.
3. **mergo's zero-value semantics surprise people.** `Merge(&dst, src)` does *not* overwrite non-zero destination fields. If you expect "source wins," you must pass `mergo.WithOverride`. The default is "destination wins unless it is zero."
4. **Merging nested structs creates aliasing.** mergo assigns nested pointers rather than cloning them. If either side mutates shared nested values, both change. Use copier to deep-copy when isolation matters.
5. **copier matches by name, not by tag.** Unlike mapstructure, copier has no per-field tag rename by default — if your DTO fields differ in name, add explicit converters or rename the fields. Two structs with the same names but different meanings (e.g., `ID` as string vs int64) need a custom converter.
6. **Unexported fields are skipped.** All three libraries operate via reflection and cannot set unexported fields. If your struct has private fields that must survive a copy, you need explicit methods instead.
7. **Don't stack all three in one hot path.** It is tempting to decode with mapstructure, merge with mergo, then copy with copier in a single request flow. Each hop is a full reflection pass. Collapse the pipeline where you can.

For more Go ecosystem deep dives, see our [Go environment configuration libraries comparison](../2026-06-23-go-environment-config-libraries-caarlos0-env-cleanenv-envconfig/), the [Go testing frameworks roundup](../2026-07-22-go-testing-frameworks-testify-goconvey-ginkgo/), and the [Go CLI library shootout](../2026-06-22-go-cli-libraries-cobra-urfave-cli-bubble-tea-promptui/).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "mapstructure vs mergo vs copier in 2026: Go Struct Mapping and Copying Done Right",
  "description": "Deep comparison of the three essential Go struct-handling libraries: mapstructure for map-to-struct decoding, mergo for merging, and copier for deep copying between structs, with code examples and pitfalls.",
  "datePublished": "2026-08-13",
  "dateModified": "2026-08-13",
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

## FAQ

**Can I use mapstructure with YAML instead of JSON?**
Yes. mapstructure works on `map[string]interface{}` regardless of the source format — decode your YAML into a generic map first (e.g., with `yaml.v3`), then call `mapstructure.Decode`. This is exactly how many config loaders are built.

**Does mergo work on maps?**
Yes. `mergo.Merge` and `mergo.Map` both handle `map[string]interface{}` and typed maps, merging keys recursively. Use `mergo.WithOverride` when source keys should replace destination keys.

**Is copier safe for structs with different types for the same field?**
Only for compatible types. copier converts between basic compatible types and supports custom converters via `copier.WithConverters`. If the types are unrelated (e.g., a flat `string` vs a nested struct), you must provide a converter or map the field manually.

**Which library should I use for config file parsing in a CLI tool?**
mapstructure for the decode step, combined with a flags library for overrides — then mergo to layer defaults, file config, environment variables, and CLI flags in that order. This is the pattern used by many production CLI tools.

**Are these libraries safe for untrusted input?**
mapstructure's decode is allocation-based and does not execute code from the input; there are no known code-execution issues in its decoding path as of August 2026. Still, treat decoding as a parsing step: validate the resulting struct before using it, and never feed unbounded maps without size limits.

**Do any of these support struct tags for renaming like encoding/json?**
mapstructure uses `mapstructure:"name"` tags for renaming, squashing, remainder, and omitempty. copier does not support renaming tags by default — field names must match or you need converters. mergo merges by field name with no tag renaming.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
