---
title: "Eclipse Collections vs fastutil vs HPPC in 2026: Which Java Collections Library Should You Use?"
date: "2026-08-13"
tags: ["java", "data-structures", "collections-framework", "developer-tools", "performance"]
draft: false
cover: "/img/screenshots/eclipse-collections-code.jpg"
---

Every Java developer hits the same wall sooner or later: `ArrayList<Integer>` boxes every single `int` into an `Integer` object, bloating memory by 3–5x and turning simple loops into garbage-collection churn. In 2026, with memory prices flat and CPU cores plentiful, the three libraries that fix this — **Eclipse Collections, fastutil, and HPPC** — are more relevant than ever, yet most teams still don't use any of them. Here is the honest, benchmark-backed breakdown of which one you should adopt.

## TL;DR / Quick Verdict

- **Pick Eclipse Collections** if you want a drop-in, API-rich replacement for the standard JDK collections with fluent iteration and parallel streams support — it is the best "developer experience" choice for application code.
- **Pick fastutil** if your goal is raw memory density and speed for large primitive datasets, and you are willing to live without `java.util` interface compatibility.
- **Pick HPPC** if you want the smallest, simplest primitive collections with zero learning curve — ideal for tight loops in search, graphics, or analytics engines.

## The Contenders

All three libraries are mature, open source, and actively maintained as of mid-2026. They solve the same core problem — Java's generics-only collections force autoboxing on primitives — but they take fundamentally different design directions:

| Library | GitHub Stars | Last Updated | License | Primitive Support | java.util Compatible | Parallel Iteration | Learning Curve |
|---|---|---|---|---|---|---|---|
| **Eclipse Collections** | 2,643 | 2026-07 | EPL-2.0 | Full (8 primitives) | Partial (MutableCollection) | Yes (parallelCollect, parallelIterate) | Medium |
| **fastutil** | 2,210 | 2026-07 | Apache-2.0 | Full (all primitives + 2D maps) | No (own hierarchy) | No (manual) | Medium |
| **HPPC** | 1,050 | 2026-08 | Apache-2.0 | Full (all primitives) | No | No (manual) | Low |

Eclipse Collections began life as the GS Collections framework Goldman Sachs open-sourced in 2012 and donated to the Eclipse Foundation in 2015. fastutil is the long-running project of Sebastiano Vigna (the author of the popular `Sux4J` and co-author of the zstd compressor), focused relentlessly on speed and compactness. HPPC — High Performance Primitive Collections — is the lightweight option from the Carrot Search team, designed to be simple enough to vendor into other projects.

## Use Case → Recommended Tool

| Use Case | Recommended | Why |
|---|---|---|
| Enterprise application code with complex query logic | **Eclipse Collections** | Fluent `select`/`collect`/`groupBy` APIs, JDK compatibility, parallel iteration |
| Caching large numeric datasets (billions of IDs) | **fastutil** | Smallest memory footprint per element, open-addressing maps, type-specialized containers |
| High-frequency trading / analytics hot loops | **HPPC** | Minimal object overhead and simplest code to reason about; trivially portable |
| Migrating an existing `List<Integer>` codebase | **Eclipse Collections** | `MutableList` extends `java.util.List`, so existing code compiles with minimal changes |
| Storing 2D arrays of primitives (matrices, grids) | **fastutil** | Dedicated 2D primitive array classes (`int[][]` wrappers with bulk operations) |
| A library that must avoid external dependencies | **HPPC** | Single small JAR, no transitive dependencies, easy to shade |

## Eclipse Collections — The Developer-Experience Champion

With **2,643 stars** and last updated in **July 2026**, Eclipse Collections is the most actively evolved of the three. Its defining feature is a rich, fluent API built around `RichIterable`: instead of `stream().filter().map().collect()`, you write `select().collect()`, and instead of a separate `Collectors` utility class, the operations are methods on the collections themselves.

```java
// Eclipse Collections — fluent, type-safe, and JDK-compatible
import org.eclipse.collections.api.list.MutableList;
import org.eclipse.collections.impl.factory.Lists;

MutableList<Integer> numbers = Lists.mutable.with(1, 2, 3, 4, 5, 6);

// Fluent filtering + transformation — no Stream API ceremony
MutableList<Integer> doubledEvens = numbers
    .select(i -> i % 2 == 0)
    .collect(i -> i * 2);

System.out.println(doubledEvens); // [4, 8, 12]

// Primitive variant that avoids boxing entirely
import org.eclipse.collections.api.list.primitive.IntList;
import org.eclipse.collections.impl.factory.primitive.IntLists;

IntList ints = IntLists.mutable.with(1, 2, 3, 4, 5, 6);
long sum = ints.sum(); // no Integer objects created
```

The primitive variants (`IntList`, `LongList`, `DoubleList`) give you boxing-free storage while keeping the fluent API, which makes it the most comfortable upgrade path from the JDK. Add `parallelCollect()` for cheap parallelism on large collections — something neither fastutil nor HPPC offers out of the box.

```xml
<dependency>
    <groupId>org.eclipse.collections</groupId>
    <artifactId>eclipse-collections</artifactId>
    <version>11.1.0</version>
</dependency>
```

## fastutil — The Memory-Density King

**fastutil** (2,210 stars, updated **July 2026**) extends the Java Collections Framework in a different direction: it generates type-specialized classes for every primitive type combination — including 2D maps like `Int2IntOpenHashMap` — and implements open addressing with a tuned load factor to squeeze maximum density out of memory. Its collections do **not** implement `java.util` interfaces; you use them directly.

```java
// fastutil — primitive-specialized collections with minimal memory
import it.unimi.dsi.fastutil.ints.IntArrayList;
import it.unimi.dsi.fastutil.ints.IntOpenHashSet;
import it.unimi.dsi.fastutil.ints.Int2IntOpenHashMap;

// No boxing: the backing array is int[], not Integer[]
IntArrayList ids = new IntArrayList(new int[] { 7, 42, 99, 7, 13 });

// Open-addressing hash set — ~2x smaller than HashSet<Integer>
IntOpenHashSet unique = new IntOpenHashSet(ids);

// Map from int to int without any wrapper objects
Int2IntOpenHashMap counts = new Int2IntOpenHashMap();
counts.put(7, 3);
int n = counts.getInt(7); // 3 — primitive getter, no autoboxing

System.out.println("unique=" + unique.size() + " count(7)=" + n);
```

The trade-off is real: because fastutil types are not interchangeable with `java.util.List`, you cannot pass an `IntArrayList` to a method expecting `List<Integer>` without copying. That copy usually destroys most of the memory win, so fastutil works best when it is used end-to-end inside a storage or computation layer. In benchmarks with millions of elements, fastutil's `Int2IntOpenHashMap` typically uses **30–40% less memory** than a `HashMap<Integer, Integer>` at comparable or better access speed.

```xml
<dependency>
    <groupId>it.unimi.dsi</groupId>
    <artifactId>fastutil</artifactId>
    <version>8.5.15</version>
</dependency>
```

## HPPC — The Minimalist Workhorse

**HPPC** (1,050 stars, updated **August 2026**) is the smallest of the three: one JAR, no transitive dependencies, and a deliberately tiny API surface. Classes follow the `KType` naming convention — `IntIntHashMap`, `ObjectObjectHashMap`, `IntArrayList` — and behavior is predictable: open addressing with linear probing, automatic resizing, and simple iteration with cursors or iterators.

```java
// HPPC — simple, predictable, dependency-free
import com.carrotsearch.hppc.IntIntHashMap;
import com.carrotsearch.hppc.IntArrayList;

IntIntHashMap map = new IntIntHashMap();
map.put(10, 100);
map.put(20, 200);
int v = map.get(10);      // 100

// Iteration with a reusable cursor — zero allocation per pass
var cursor = map.iterator();
while (cursor.hasNext()) {
    cursor.next();
    System.out.println(cursor.key + " -> " + cursor.value);
}

IntArrayList list = new IntArrayList();
list.add(1);
list.add(2);
list.add(3);
```

HPPC's simplicity is its superpower: the code is short enough to audit, and the JAR is small enough to shade into any library. The trade-off is that you get fewer convenience methods — no fluent filtering, no parallel helpers — so you will write the loops yourself. For teams that want a fast, boring, dependency-free primitive collection, that is exactly the right deal.

```xml
<dependency>
    <groupId>com.carrotsearch</groupId>
    <artifactId>hppc</artifactId>
    <version>0.10.0</version>
</dependency>
```

## Performance and Memory: What the Numbers Actually Say

Independent microbenchmarks (JMH-based) consistently show the same shape of results at 1M+ elements:

- **fastutil** wins raw density: an `IntOpenHashSet` with 10M entries uses roughly **45–55 MB**, versus **110–130 MB** for a `HashSet<Integer>`. Access time is flat or slightly better than the JDK.
- **HPPC** is within a few percent of fastutil on access speed but slightly heavier on insert-heavy workloads due to simpler resizing; its linear-probing maps degrade gracefully until ~60–70% load.
- **Eclipse Collections** primitive lists (`IntList`) land between the JDK and fastutil on memory — roughly 2x smaller than `ArrayList<Integer>` — while its object-based collections match the JDK's performance with a nicer API.

Two rules of thumb: (1) if your collection holds **more than ~100,000 primitives**, the boxing overhead dominates and any of the three beats the JDK by a wide margin; (2) if your collection is small, none of this matters — don't add a dependency for a 1,000-element list.

## Common Pitfalls and How to Avoid Them

1. **Mixing fastutil types with java.util interfaces.** The moment you copy an `IntArrayList` into a `List<Integer>` for a downstream API, you pay the boxing cost you were trying to avoid. Keep primitive collections contained inside your storage layer and convert only at boundaries.
2. **Default load factors and iteration order.** fastutil and HPPC both use open addressing; iteration order is *not* insertion order and is not guaranteed across resizes. Never rely on order — sort explicitly or use a linked variant if order matters.
3. **Resizing spikes.** Open-addressing maps resize by rehashing everything, which causes latency spikes in latency-sensitive paths. Pre-size with `new IntIntHashMap(expectedSize)` / `new Int2IntOpenHashMap(expectedSize)` when you know the ballpark.
4. **Forgetting that `getInt()` returns 0 for missing keys.** fastutil and HPPC primitive getters return the primitive default (0) when a key is absent — indistinguishable from a stored 0. Use `containsKey()` first, or store sentinel values.
5. **Eclipse Collections' parallel APIs change thread semantics.** `parallelCollect()` uses a shared executor; if your lambdas mutate shared state you will get races just like with parallel streams. Keep the lambdas pure.
6. **Binary size.** fastutil's type-specialization generates thousands of classes; a shaded JAR is large, and JVM startup/class-loading time grows. HPPC and EC are lighter if deployment size matters.
7. **Licensing review.** EC is EPL-2.0, fastutil and HPPC are Apache-2.0. For vendoring into a closed-source product, Apache-2.0 (fastutil/HPPC) is the least friction; EPL-2.0 is fine but triggers review in some legal departments.

For more on the Java ecosystem, see our [comparison of Java JSON libraries](../2026-06-22-java-json-libraries-jackson-gson-moshi-guide/), the [Java testing libraries roundup](../2026-07-24-java-testing-libraries-assertj-hamcrest-truth/), and the [Java dependency injection shootout](../2026-07-29-java-dependency-injection-libraries-dagger-koin-guice-guide/).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Eclipse Collections vs fastutil vs HPPC in 2026: Which Java Collections Library Should You Use?",
  "description": "Deep comparison of the three leading Java primitive collections libraries: Eclipse Collections, fastutil, and HPPC. Benchmarks, memory usage, code examples, and migration pitfalls.",
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

**Is Eclipse Collections compatible with java.util.List?**
Yes, partially. `MutableList` extends `java.util.List`, so code written against the JDK interface compiles with EC instances. Primitive variants (`IntList`) are separate types and do not implement `java.util.List` — that is by design, since generics cannot express primitives.

**Does fastutil work with Java streams?**
fastutil collections have their own iterators but do not integrate with `java.util.stream`. You can call `Arrays.stream(fastutilArray)` after converting to a primitive array (`toIntArray()`), which is zero-copy for the backing store in most cases.

**Which library is fastest for a simple int-to-int cache?**
At equal sizes, fastutil's `Int2IntOpenHashMap` and HPPC's `IntIntHashMap` are within a few percent of each other and both clearly beat `HashMap<Integer, Integer>`. Choose by fit: fastutil if you also need 2D maps and set operations, HPPC if you want the smallest codebase.

**Can I use these libraries on Android or with GraalVM native-image?**
Yes, with caveats. HPPC and EC are the smoothest on Android. For GraalVM native-image, fastutil's generated classes need reflection metadata for some serialization paths; HPPC and EC generally work without extra configuration.

**What happened to Trove?**
Trove4j is effectively unmaintained (last releases are years old) and does not support newer JDK versions cleanly. fastutil, HPPC, and EC are the modern replacements — that is why this comparison focuses on those three.

**Should I replace all my HashMap<Integer, Integer> usage?**
Only where it pays off: collections larger than ~100K elements, or hot loops measured in your profiler. For application-scale data, the JDK collections are fine, and adding a second collection framework has its own maintenance cost.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
