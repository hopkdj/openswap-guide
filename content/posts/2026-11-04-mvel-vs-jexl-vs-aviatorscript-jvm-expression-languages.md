---
title: "MVEL vs Apache JEXL vs AviatorScript in 2026: Embedded Expression Engines for the JVM"
date: "2026-11-04"
tags: ["java", "jvm", "expression-language", "rules", "libraries"]
draft: false
cover: "/img/screenshots/jexl-expression-language.jpg"
description: "MVEL, Apache Commons JEXL and AviatorScript compared for embedding expressions in Java applications in 2026: code samples, compilation models, sandboxing and a decision matrix."
---

The moment a Java application lets a non-developer change behaviour, you inherit an expression language problem. Pricing rules, discount thresholds, alert conditions, feature gates, routing decisions — someone always wants to edit them without a deploy. The first version of that feature is always `if (tier.equals("gold") && total > 300)` buried in a service class. The fifth version is a `switch` statement nobody dares touch, and the sixth version is an expression engine.

Three JVM libraries have been the default answers for that problem for years: MVEL, Apache Commons JEXL, and AviatorScript. They overlap so much that choosing one feels arbitrary — and they differ so much in compilation model, sandboxing and syntax that picking wrong costs you either performance or a security incident.

## TL;DR / Quick Verdict

**Need maximum expression throughput and a permissive, C-like dialect? Pick MVEL.** It compiles expressions to JVM bytecode, it is what Drools and JBoss Rules grew up on, and it is extremely fast for repeated evaluation — provided you compile once and cache. It is also the easiest of the three to misuse dangerously.

**Need something boring, Apache-governed, and safe by default? Pick Apache JEXL.** It is an interpreter, not a compiler, so it is slower per evaluation, but it has the most conservative defaults, a well-defined permissions model, and the kind of release discipline you want under a regulated workload.

**Need a small scripting language inside your product — with variables, functions, lambdas, and dynamic typing — rather than just an expression evaluator? Pick AviatorScript.** It is the most language-like of the three and the most used in high-volume pricing and campaign systems.

| Dimension | MVEL | Apache Commons JEXL | AviatorScript |
|---|---|---|---|
| Repository | `mvel/mvel` | `apache/commons-jexl` | `killme2008/aviatorscript` |
| Stars | 1,205 | 243 | **5,246** |
| Last push | 2026-10-27 | 2026-10-31 | 2026-07-27 |
| Latest version | **2.5.2.Final** | **3.6.2** | **5.4.3** |
| Maven coordinates | `org.mvel:mvel2` | `org.apache.commons:commons-jexl3` | `com.googlecode.aviator:aviator` |
| Governance | Community project | **Apache Software Foundation** | Single maintainer-led |
| License | Apache 2.0 | **Apache 2.0** | No LICENSE file detected at repo root in 2026 — verify before shipping |
| Execution model | Compiles to bytecode (ASM) | Interprets an AST | Compiles to bytecode |
| Sandboxing | Weak by default; allowlist required | `JexlPermissions` (3.3+) | Feature sets / allowed-class configuration |
| Syntax | Java-like, with property navigation | JSTL-EL-like | JavaScript-like, with lambdas |
| Typical use | Rule engines, templating, data mapping | Configuration-driven conditions | Pricing, campaigns, formula fields |

## Decision Matrix

| Situation | Pick | Reason |
|---|---|---|
| Millions of evaluations per minute, fixed expressions | MVEL | Compile once, evaluate cheaply; fastest of the three |
| Expressions authored by business users, must be contained | JEXL | Conservative defaults plus an explicit permissions model |
| You need loops, lambdas, and user-defined functions | AviatorScript | It is a small language, not just an evaluator |
| Regulated environment needing vendor-neutral governance | JEXL | Apache project, clear IP provenance |
| Already using Drools or a JBoss-adjacent stack | MVEL | Same lineage and dialect as the rule engine |
| Expression text arrives from end users over HTTP | **None of them, unsandboxed** | Any of the three is remote code execution if you skip the allowlist |
| Simple property path + one comparison | Plain Java | Do not add a dependency for `a.b > 5` |

## MVEL — Bytecode Speed, With Sharp Edges

MVEL predates most of the JVM expression ecosystem and earned its place because it was fast when being fast was hard. `MVEL.compileExpression` produces bytecode via ASM, so a compiled expression is a real method call rather than a tree walk.

**1,205 stars, last pushed 2026-10-27, version 2.5.2.Final on Maven Central, Apache 2.0.**

```xml
<dependency>
  <groupId>org.mvel</groupId>
  <artifactId>mvel2</artifactId>
  <version>2.5.2.Final</version>
</dependency>
```

The one-shot form is convenient and the wrong thing to ship:

```java
import org.mvel2.MVEL;
import java.util.Map;

Map<String, Object> vars = Map.of("tier", "gold", "total", 320.0);
Object discount = MVEL.eval("tier == 'gold' && total > 300 ? 0.15 : 0.0", vars);
```

The production form compiles once and reuses the result. `compileExpression` returns a `Serializable`, which means you can cache it in a `ConcurrentHashMap` keyed by the rule text — or even persist it:

```java
import org.mvel2.MVEL;
import java.io.Serializable;

Serializable rule = MVEL.compileExpression(
    "tier == 'gold' && total > 300 ? 0.15 : 0.0");

double discount = (double) MVEL.executeExpression(rule, vars);
```

MVEL's property navigation is what makes it pleasant for domain objects: given a `Customer` with `getAddress().getCountry()`, you write `customer.address.country == 'DE'` and it resolves through the getters. It also supports inline collections and projections, which is why templating and data-mapping layers adopted it.

**The edges.** MVEL's default evaluation context is powerful — it can call methods on objects it reaches, and historically it allowed static method access, which is a code-execution primitive. If the expression text can be influenced by a user, you must configure a `ParserContext` with an import/class allowlist and read the security section of the docs before anything reaches production. The project is community-maintained with a small contributor base; do not expect a security advisory process comparable to an Apache project.

## Apache JEXL — The Conservative Choice

JEXL is the expression language that Apache ships, and its design reflects that: JSTL-style syntax familiar to anyone who has written a JSP, an engine object that is explicit about caching, strict versus silent mode, and — since 3.3 — a permissions model for introspection.

**243 stars, last pushed 2026-10-31, version 3.6.2, Apache 2.0.** The star count understates adoption: JEXL is a transitive dependency in a very large number of enterprise Java stacks.

![Apache Commons JEXL — the ASF expression language for the JVM](/img/screenshots/jexl-expression-language.jpg "Apache Commons JEXL logo")

```xml
<dependency>
  <groupId>org.apache.commons</groupId>
  <artifactId>commons-jexl3</artifactId>
  <version>3.6.2</version>
</dependency>
```

```java
import org.apache.commons.jexl3.*;

JexlEngine jexl = new JexlBuilder()
        .cache(512)
        .strict(true)     // unknown variables throw instead of returning null
        .silent(false)
        .create();

JexlExpression expr = jexl.createExpression("tier == 'gold' and total > 300");

JexlContext ctx = new MapContext();
ctx.set("tier", "gold");
ctx.set("total", 320.0);

Object result = expr.evaluate(ctx);
```

Note `and` rather than `&&` — both work, but the word forms are idiomatic and less error-prone in rule text edited by non-developers.

The `JexlEngine` is expensive to build and thread-safe once built: create one per application, not per request. `cache(512)` keeps 512 parsed expressions in an internal cache, which is the correct way to get performance out of an interpreter — the parse cost disappears and you pay only the tree walk.

Sandboxing in JEXL 3.3+ is expressed through `JexlPermissions`. The strictest useful configuration restricts which classes an expression may touch at all:

```java
import org.apache.commons.jexl3.introspection.JexlPermissions;

JexlEngine sandboxed = new JexlBuilder()
        .permissions(JexlPermissions.RESTRICTED)
        .strict(true)
        .create();
```

`JexlPermissions.RESTRICTED` blocks access to arbitrary classes while still allowing the data you put in the context. If your expressions are user-authored, this is the minimum bar, and you should pair it with a timeout on evaluation because a pathological expression can still be slow.

**The trade-off:** JEXL interprets, so per-evaluation cost is higher than MVEL or Aviator. For ten thousand evaluations a second on a cached expression, that difference is easily absorbed. For a million per second inside a pricing hot path, it is not.

## AviatorScript — A Language, Not Just an Evaluator

AviatorScript started as a high-performance expression evaluator for Java and grew into a small scripting language: variables, `if`/`for`/`while`, functions, closures, `lambda`, string interpolation, and a module system. It is heavily used in Chinese e-commerce and risk-control systems, which is why its star count dwarfs the other two despite far less Western blog coverage.

**5,246 stars, last pushed 2026-07-27, version 5.4.3.**

```xml
<dependency>
  <groupId>com.googlecode.aviator</groupId>
  <artifactId>aviator</artifactId>
  <version>5.4.3</version>
</dependency>
```

```java
import com.googlecode.aviator.AviatorEvaluator;
import com.googlecode.aviator.Expression;
import java.util.Map;

Map<String, Object> env = Map.of("tier", "gold", "total", 320.0);

// one-shot
Object discount = AviatorEvaluator.execute(
    "tier == 'gold' && total > 300 ? 0.15 : 0.0", env);

// compiled + cached (the form you actually deploy)
Expression compiled = AviatorEvaluator.compile(
    "let rate = tier == 'gold' ? 0.15 : 0.05; total * rate", true);
double amount = (double) compiled.execute(env);
```

The second argument to `compile` is `cached` — the engine keeps the compiled expression under its text as key, so repeated lookups skip compilation entirely.

Where Aviator pulls ahead for product teams is expressiveness. Anything the other two would force you to model as a chain of ternaries can be written as ordinary code:

```
let tiers = seq.map(customer.orders, lambda(o) -> o.amount end);
let total = seq.reduce(tiers, 0, lambda(a, b) -> a + b end);
total > 1000 ? "vip" : "standard"
```

That is a real advantage when the people writing rules think in loops, and a real liability when the people reviewing them expect a one-line condition. Every language feature is also another thing your allowlist has to reason about.

**Licensing caveat, checked in 2026:** GitHub reports no detected license for `killme2008/aviatorscript`, and there is no `LICENSE` file at the repository root. That is not proof the project is unlicensed — but it does mean you should confirm terms with the maintainer or your legal team before embedding it in a commercial product, and it is a genuine differentiator against two Apache 2.0 alternatives.

## Sandboxing: The Only Section That Actually Matters

All three libraries execute text that can call methods, and all three have historically had ways to escape into arbitrary code. Treat any expression text that you did not author as untrusted input.

The minimum viable setup for each:

1. **Allowlist, never blocklist.** Enumerate the classes and functions expressions may reach. JEXL uses `JexlPermissions`; MVEL uses a `ParserContext` with restricted imports and class resolution; AviatorScript uses feature sets and an allowed-class configuration.
2. **Never bind a live service object into the context.** Bind value objects and primitives. If an expression can reach a `DataSource` or a `Runtime`, the sandbox is decorative.
3. **Time-box evaluation.** Compilation and evaluation both run on your request thread. A malicious or buggy expression that loops is a denial of service, and none of the three protects you from that by default.
4. **Version-pin and watch advisories.** Expression engines have had deserialization and reflection escape issues before. Pin exact versions, and subscribe to the project's release feed.
5. **Store rules as data, not as Java.** The whole point is that rule changes should not require a deploy. Keep them in a table or config service with an audit trail of who changed what.

If your expressions are really about policy decisions rather than arithmetic — "can this principal perform this action" — a purpose-built policy language will be safer than any general expression engine. Our [expression languages comparison](../2026-09-27-expression-languages-cel-go-expr-lang-jsonata-starlark-comparison/) covers CEL, Expr, Jsonata and Starlark, which are designed with exactly that constraint in mind.

If instead you are generating Java rather than evaluating expressions, the trade-offs are different — see our [JVM bytecode engineering guide](../2026-09-11-jvm-bytecode-engineering-byte-buddy-javassist-asm/) for Byte Buddy, Javassist and ASM. And if the strings you are parsing are presentation templates rather than conditions, the [template engine comparison](../2026-06-21-template-engine-libraries-jinja2-handlebars-mustache-tera/) is the closer match.

## FAQ

**Which is faster: MVEL, JEXL or AviatorScript?**

MVEL and AviatorScript both compile expressions to JVM bytecode, so a cached expression evaluates at roughly method-call speed. JEXL interprets an AST and is slower per evaluation. The ordering matters only when you evaluate the same expression at very high frequency; for configuration-style checks a handful of times per request, all three are fine.

**Is it safe to evaluate user-supplied expressions?**

Not by default, with any of the three. All of them can reach objects you put into the evaluation context, and all of them have configuration that determines how far that reach extends. Use an allowlist (JEXL's `JexlPermissions`, MVEL's `ParserContext`, AviatorScript's feature and class restrictions), bind only value objects, and add a timeout.

**Can JEXL replace MVEL in an existing Drools project?**

Not directly. Drools' rule dialect is built on MVEL semantics, including its property navigation and inline collection syntax. Rewriting dialect expressions as JEXL is possible for simple conditions but usually not worth it — either keep MVEL for the rule text or migrate the whole rule layer.

**Do these libraries work with Java records and modern JDKs?**

Yes, all three run on current JDKs and resolve record accessors through standard introspection, though the accessor naming (`value()` rather than `getValue()`) occasionally trips property navigation in older configuration. Test with your actual domain types rather than POJOs only.

**What is the difference between an expression language and a scripting language here?**

An expression language evaluates a single expression and returns a value: that is JEXL's model, and MVEL's default mode. A scripting language adds statements, control flow and functions: that is AviatorScript's model and MVEL's template/script mode. If you need `for` loops in your rules, choose accordingly rather than emulating loops with recursion.

**Should I just use JavaScript via GraalJS or Nashorn instead?**

Only if you already have GraalVM or a compatible engine and your team writes JavaScript. Those engines are heavier, have larger attack surfaces, and give you far more capability than a pricing rule needs. For embedded rule text, a small expression engine is the smaller risk.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "MVEL vs Apache JEXL vs AviatorScript in 2026: Embedded Expression Engines for the JVM",
  "description": "MVEL, Apache Commons JEXL and AviatorScript compared for embedding expressions and rules in Java applications: compilation models, sandboxing, code samples and a decision matrix.",
  "datePublished": "2026-11-04",
  "dateModified": "2026-11-04",
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
