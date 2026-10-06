---
title: "JSON Patch Libraries in 2026: fast-json-patch vs evanphx/json-patch vs zjsonpatch vs jsondiffpatch"
date: "2026-10-07"
tags: ["json", "api", "libraries", "developer-tools", "comparison"]
draft: false
cover: "/img/screenshots/jsondiffpatch-visual-diff.jpg"
---

Sending a 200 KB JSON document over the wire because one field changed is the kind of waste that survives for years in an API nobody wants to touch. **JSON Patch (RFC 6902)** exists to fix exactly that: instead of the whole document, you send an ordered list of operations — `add`, `remove`, `replace`, `move`, `copy`, `test` — addressed with **JSON Pointer (RFC 6901)** paths.

The spec is small and stable. The library ecosystem around it is not. There are at least five implementations people actually deploy, and they disagree on the two things that matter: *which RFCs they support* and *whether they can generate a patch for you*.

Every star count and commit date below was read from the official repositories in **October 2026**.

## TL;DR — The Quick Verdict

- **JavaScript / TypeScript, applying patches:** use **fast-json-patch** (1,982 stars) — it applies, validates, observes and generates.
- **JavaScript / TypeScript, human-facing diffs:** use **jsondiffpatch** (5,347 stars) — its visual and console formatters are unmatched.
- **Go:** use **evanphx/json-patch** (1,231 stars). It handles RFC 6902 *and* RFC 7386 merge patches in one package.
- **JVM:** use **zjsonpatch** (586 stars), but read the 0.6.0 breaking change before you upgrade.
- **Python:** use **python-json-patch** (497 stars) — small, spec-compliant, no surprises.

The one decision that matters most: **JSON Patch (RFC 6902) and JSON Merge Patch (RFC 7386) are not interchangeable.** Pick merge patch for configuration-shaped objects and JSON Patch for anything containing arrays.

## Comparison Table

| Library | Language | Stars | Last activity | Apply RFC 6902 | Generate diff | Merge patch | Formats |
|---|---|---|---|---|---|---|---|
| jsondiffpatch | TypeScript | 5,347 | 2026-05-14 | Yes | Yes | No | JSON, visual, annotated, console |
| fast-json-patch | JavaScript | 1,982 | 2025-10-23 | Yes | Yes | No | JSON Patch ops |
| evanphx/json-patch | Go | 1,231 | 2025-12-15 | Yes | Merge only | Yes (RFC 7386) | JSON Patch ops |
| zjsonpatch | Java | 586 | 2026-10-06 | Yes | Yes (LCS) | No | JSON Patch ops |
| python-json-patch | Python | 497 | 2026-06-18 | Yes | No | No | JSON Patch ops |

## Decision Matrix

| Your problem | Pick this | Why |
|---|---|---|
| HTTP `PATCH` endpoint that applies client deltas | fast-json-patch | Validator catches malformed ops before mutation |
| Show a coloured diff of two config objects | jsondiffpatch | Built-in visual and console formatters |
| Go service syncing Kubernetes-style resources | evanphx/json-patch | Applies 6902 and 7386 from one import |
| Java API returning minimal updates over the wire | zjsonpatch | Key-based array pointers avoid index churn |
| Python worker reconciling desired vs actual state | python-json-patch | Strict RFC 6902, passes the shared test suite |

## jsondiffpatch — The Best Diff Engine and Viewer

jsondiffpatch computes a delta between two objects and can apply it back. It is roughly 16 KB minified and gzipped, works in the browser and on the server, and — critically for anything user-facing — ships multiple output formatters, including a visual HTML diff and a coloured console diff.

![jsondiffpatch visual diff showing changed and removed JSON values](/img/screenshots/jsondiffpatch-visual-diff.jpg "jsondiffpatch visual diff output: added and removed values highlighted")

Its array diffing uses longest-common-subsequence matching, but there is one requirement that trips everyone up the first time: **to match objects inside an array you must supply an `objectHash` function.** Without it, arrays are matched positionally and a single inserted element makes the entire delta useless.

```js
import * as jsondiffpatch from 'jsondiffpatch';

const left  = { name: 'Argentina', capital: 'Buenos Aires', tags: ['a', 'b'] };
const right = { name: 'Argentina', capital: 'Cordoba',      tags: ['a', 'b', 'c'] };

const delta = jsondiffpatch.diff(left, right);
const restored = jsondiffpatch.patch(left, delta);

// Reverse the delta, or un-patch entirely
const undone = jsondiffpatch.reverse(delta);
jsondiffpatch.unpatch(right, delta);
```

There is a CLI for inspecting deltas without writing a script:

```bash
npx jsondiffpatch left.json right.json
```

![jsondiffpatch console output showing a coloured delta between two JSON files](/img/screenshots/jsondiffpatch-console.jpg "jsondiffpatch CLI: coloured console delta between two JSON documents")

**Why it wins:** the formatters. No other library in this comparison gives you a visual diff and a console diff out of the box. **Where it loses:** it emits its own delta format by default, so if you need strict RFC 6902 on the wire you must select the JSON Patch formatter explicitly.

## fast-json-patch — The Safest Applier

`fast-json-patch` is the leaner JS implementation focused on the *apply* path. Its API surface is broader than it first appears: apply, validate, observe, generate and compare.

```bash
npm install fast-json-patch --save
```

```js
const jsonpatch = require('fast-json-patch');

const document = { name: 'Jane', age: 24, tags: ['admin'] };

const patch = [
  { op: 'replace', path: '/age', value: 25 },
  { op: 'add',     path: '/tags/-', value: 'ops' },
];

// validate before mutating: throws on malformed operations
jsonpatch.validate(patch);

const result = jsonpatch.applyPatch(document, patch).newDocument;
console.log(result); // { name: 'Jane', age: 25, tags: ['admin', 'ops'] }

// Generate a patch by comparing two documents
console.log(jsonpatch.compare({ a: 1 }, { a: 1, b: 2 }));
```

Watch the `path: '/tags/-'` syntax — the `-` token means "end of array" and is the spec's answer to "append without knowing the index".

**Why it wins:** `validate()` runs before your application state is touched, and prototype-modification guard rails are on by default. **Where it loses:** no merge-patch support, and the project's last commit was October 2025 — it is maintenance-mode stable.

## evanphx/json-patch — Go's Two-RFC Package

The Go library is unusual because it covers **both** patch formats in one import: RFC 6902 JSON Patch and RFC 7386 JSON Merge Patch. If your service reconciles resources, that saves you a dependency.

```bash
go get -u github.com/evanphx/json-patch/v5
```

```go
package main

import (
	"fmt"

	jsonpatch "github.com/evanphx/json-patch/v5"
)

func main() {
	original := []byte(`{"name":"John","age":24,"tags":["a"]}`)

	// RFC 6902 — decode an ordered operation list, then apply it
	patch, err := jsonpatch.DecodePatch([]byte(`[{"op":"replace","path":"/age","value":25}]`))
	if err != nil {
		panic(err)
	}
	modified, err := patch.Apply(original)
	if err != nil {
		panic(err)
	}
	fmt.Println(string(modified))
}
```

It also creates merge patches from two documents, which is the feature most people come for:

```go
target := []byte(`{"name":"Jane","age":24}`)
mergePatch, err := jsonpatch.CreateMergePatch(original, target)
// then apply it elsewhere
result, err := jsonpatch.MergePatch(original, mergePatch)
```

Behaviour is controlled by `jsonpatch.ApplyOptions`: `AllowMissingPathOnRemove` ignores `remove` operations whose target no longer exists, `EnsurePathExistsOnAdd` creates intermediate objects on `add`, and `jsonpatch.AccumulatedCopySizeLimit` caps the total growth caused by `copy` operations — a real defence against amplification attacks.

**Why it wins:** one package, two RFCs, and explicit knobs for hostile input. **Where it loses:** non-standard negative array indices are enabled by default (`SupportNegativeIndices`); if you want strict spec behaviour you must disable them yourself.

## zjsonpatch — Java with Extended Pointers

zjsonpatch implements RFC 6902 for Java and adds one genuinely useful extension: **key-based array addressing**. Instead of `/users/3/email` you can write `/users/id=123/email`, which stops a single array insertion from invalidating every downstream pointer.

```xml
<dependency>
  <groupId>com.flipkart.zjsonpatch</groupId>
  <artifactId>zjsonpatch</artifactId>
  <version>0.4.16</version>
</dependency>
```

```java
JsonNode source = mapper.readTree(originalJson);
JsonNode target = mapper.readTree(modifiedJson);

// Generate the patch by diffing two documents (LCS for arrays)
JsonNode patch = JsonDiff.asJson(source, target);

// Apply it
JsonNode patched = JsonPatch.apply(patch, source);
```

Two things changed recently. The project now requires **Java 17+**, and the development branch documents a breaking change arriving in **0.6.0**, where all Jackson dependencies become optional so consumers can choose Jackson 2.x or 3.x. Projects that relied on zjsonpatch to pull Jackson in transitively will fail to compile until Jackson is declared explicitly. Note that the newest release published to Maven Central is still **0.4.16**, so plan the upgrade against the changelog rather than assuming the branch is released.

**Why it wins:** key-based pointers and a documented complexity profile (Ω(N+M) for object diffing, LCS for arrays). **Where it loses:** the 0.6.0 dependency change is a migration landmine, and combining it with HTTP `PATCH` requires you to wire the Spring or JAX-RS support yourself.

## python-json-patch — Small and Spec-Strict

The Python implementation is deliberately narrow: it applies RFC 6902 patches and does not invent its own delta format. It is validated against the shared `json-patch-tests` suite, which is the closest thing the ecosystem has to a conformance benchmark.

```bash
pip install jsonpatch
```

```python
import jsonpatch

doc = {"foo": "bar", "numbers": [1, 2, 3]}
patch = [
    {"op": "replace", "path": "/foo", "value": "baz"},
    {"op": "add", "path": "/numbers/0", "value": 0},
]

result = jsonpatch.apply_patch(doc, patch)
print(result)   # {'foo': 'baz', 'numbers': [0, 1, 2, 3]}

# Also available as an object, which supports validation
p = jsonpatch.JsonPatch(patch)
p.apply(doc, in_place=False)
```

It also exposes `make_patch(old, new)` for generating a patch from two documents, so the "generate" column in the comparison table is not empty for Python — it is just less featureful than jsondiffpatch's.

**Why it wins:** strictness. It rejects malformed operations instead of guessing. **Where it loses:** patch generation is basic, and there is no merge-patch implementation.

## Pitfalls, Migration Traps and Security Notes

**1. JSON Patch and JSON Merge Patch are different formats.** RFC 6902 sends an operation array; RFC 7386 sends a partial document where `null` means "delete this key". Merge patch cannot append to an array without rewriting it and cannot express "set this value to null" — for arrays and nulls, you need RFC 6902.

**2. `test` operations are your concurrency control.** A patch applied to a document that changed since the client read it can corrupt data silently. Emit a `test` op for the field you expect, or pair the request with `If-Match` on an ETag, so a stale patch fails loudly.

**3. JSON Pointer escaping is two characters, not one.** In a pointer, `~` is written `~0` and `/` is written `~1`. A naive path builder that does not escape keys containing a slash will address the wrong node.

**4. Array diffs are only as good as your identity function.** jsondiffpatch and zjsonpatch both need a stable way to identify array elements. Give them an `objectHash` (JS) or a key-based pointer (Java), otherwise a single insert rewrites the whole array.

**5. Treat patch input as hostile.** A `copy` operation can grow a small request into a huge document, and unguarded `add` operations can create deeply nested structures. Set a size limit (`AccumulatedCopySizeLimit` in Go) and keep prototype guards enabled in JavaScript.

**6. Read the changelog before upgrading.** zjsonpatch 0.6.0 changed its Jackson dependency scope, and Java 17 is now required. This is the kind of change that breaks a build with no code diff.

## Frequently Asked Questions

### What is the difference between JSON Patch and JSON Merge Patch?

JSON Patch (RFC 6902) is an ordered array of operations — `add`, `remove`, `replace`, `move`, `copy`, `test` — each addressed by a JSON Pointer. JSON Merge Patch (RFC 7386) is a partial JSON document that is merged into the target, where a `null` value means "delete". Merge patch is simpler to hand-write; JSON Patch can express array surgery and null assignment, which merge patch cannot.

### Which library can generate a patch automatically from two documents?

jsondiffpatch and zjsonpatch both generate diffs directly (`jsondiffpatch.diff()` and `JsonDiff.asJson()`), fast-json-patch generates one with `compare()`, and Go's evanphx/json-patch creates merge patches with `CreateMergePatch()`. Python's python-json-patch offers `make_patch()`, though with fewer options.

### How do I use JSON Patch with an HTTP PATCH request?

Send the operation array as the request body with `Content-Type: application/json-patch+json`, and have the server apply it to the stored representation. Because the patch is applied to whatever the server currently holds, include a `test` operation or an `If-Match` header so a stale client cannot overwrite newer state.

### Is it safe to apply a JSON Patch from an untrusted client?

Only with limits. Reject oversized patch arrays, cap the total growth caused by `copy` operations, disable negative array indices if you want strict spec behaviour, and keep prototype-pollution guards on in JavaScript. Applying an unvalidated patch to live application state is equivalent to letting the client write arbitrary fields.

### Why does my array diff look wrong?

Almost always because the library could not identify array elements across the two versions. jsondiffpatch needs an `objectHash` function and zjsonpatch needs a unique key, otherwise array comparison falls back to position and one inserted element shifts the entire diff.

### Can I use JSON Patch to sync configuration between services?

Yes, and it is a good fit as long as the configuration is object-shaped. For configuration maps, RFC 7386 merge patch is often simpler; for anything with ordered lists, use RFC 6902. Either way, validate the incoming patch against the shape you expect — see our [guide to JSON Schema validation with ajv, Prism and Joi](../2026-06-08-self-hosted-json-schema-validation-ajv-prism-joi/) before applying it.

## Choosing Between Them in Practice

If your API returns diffs to a browser, jsondiffpatch is the only one that solves the presentation problem as well as the data problem — inspect real payloads with [JSON Crack, JSON Hero or JSON Editor](../2026-06-15-self-hosted-json-visualization-tools-jsoncrack-jsonhero-jsoneditor/) when a delta does not look right. If your service consumes patches, pick the implementation in your language and lean on its safety switches rather than writing your own pointer arithmetic. And if you publish schemas, remember that adding or removing patchable fields is a breaking API change — the same class of change tracked by [schema-aware API diff tooling](../2026-05-24-self-hosted-api-breaking-change-detection-oasdiff-openapi-diff-azure-guide/).

JSON Patch is one of those specifications that rewards reading the RFC once. Fifteen minutes with RFC 6901 explains more production incidents than any library comparison can.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "JSON Patch Libraries in 2026: fast-json-patch vs evanphx/json-patch vs zjsonpatch vs jsondiffpatch",
  "description": "Compare the five main JSON Patch implementations across JavaScript, Go, Java and Python, including RFC 6902 vs RFC 7386 trade-offs, real code samples and security limits.",
  "datePublished": "2026-10-07",
  "dateModified": "2026-10-07",
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
