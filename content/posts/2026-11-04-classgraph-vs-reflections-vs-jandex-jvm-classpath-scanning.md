---
title: "ClassGraph vs Reflections vs Jandex in 2026: Picking a JVM Classpath Scanner That Still Works on Modern Java"
date: "2026-11-04"
tags: ["java", "jvm", "libraries", "classpath", "reflection", "dependency-injection"]
draft: false
description: "ClassGraph 6, Reflections 0.10.2 and Jandex 3.6.0 compared in 2026: real API samples, JDK 25 constraints, build-time indexing, nested-jar scanning, native-image tradeoffs and a decision matrix."
---

You add one annotation — `@Plugin`, `@Route`, `@Extension` — and suddenly your framework needs to find every class that carries it. That is the moment a Java project discovers the classpath scanning problem: the JDK can tell you the superclass of a class you already have, but it cannot tell you "give me every class in this jar that implements `Plugin`". You either scan, or you maintain a hand-written registry that drifts out of date the first time someone adds a module.

Three libraries have owned this problem on the JVM for years: **ClassGraph**, **Reflections**, and **Jandex**. In 2026 they are no longer interchangeable. One has been re-architected for JDK 25 and split into five artifacts. One has had no commit since mid-2024 and still drags in Javassist. One abandoned runtime scanning entirely and became a build-time index format that Quarkus depends on. Picking the wrong one costs you either a startup regression or a migration project.

## TL;DR / Quick Verdict

- **Choose ClassGraph 6** if you need to scan at runtime, especially inside Spring Boot fat jars, nested jars, OSGi or custom classloaders. It is the most capable scanner, actively maintained, MIT licensed, and now JDK 25+ (use the `v5` branch for JDK 17–24). Cost: a larger dependency and an API that changed in 6.x.
- **Choose Jandex 3.6.0** if scanning happens at build time and startup latency is a product requirement. It builds a compact annotation index during the build, and runtime lookups are dictionary reads. This is why Quarkus is built on it. Cost: the index must be produced by your build, and anything added after the build is invisible.
- **Only choose Reflections 0.10.2** for legacy code you cannot migrate yet. Its API is pleasant, its star count is the highest of the three, and it is effectively unmaintained — last push June 2024, WTFPL licensed, Javassist-based.

The short version of the decision: **runtime discovery → ClassGraph, startup-sensitive framework → Jandex, existing code → Reflections until you can leave it.**

## Side-by-Side Comparison

| Dimension | ClassGraph | Reflections | Jandex |
|---|---|---|---|
| Latest release | **6.0.1** | 0.10.2 | **3.6.0** |
| Last push (GitHub) | 2026-11-02 | 2024-06-17 | 2026-10-29 |
| GitHub stars | 3,023 | **4,758** | 456 |
| License | MIT | WTFPL | Apache-2.0 |
| Core model | Runtime scan of classpath, module path, classloaders | Runtime scan via Javassist metadata | Build-time index, runtime reads |
| JDK baseline | 25+ (6.x), 17–24 (`v5` branch) | Java 8-era bytecode | Java 11+ |
| Nested / fat jars | Reads jars inside jars, any depth, no temp extraction | Partial, classloader-dependent | Index usually built per artifact |
| Loads classes? | No — parses classfiles | Configurable, can avoid loading | No |
| Handles JPMS modules | Yes, explicit module-path support | Limited | Yes (index per module/jar) |
| Extra runtime deps | None significant | Javassist + SLF4J | None |
| Startup cost | Proportional to classpath size | Proportional to classpath size | Near zero (index read) |
| Maven coordinates | `io.github.classgraph:classgraph` | `org.reflections:reflections` | `io.smallrye:jandex` |

Two numbers deserve emphasis. **ClassGraph is the only one of the three that can read a jar nested inside another jar without extracting it**, which is exactly the layout Spring Boot produces. And **Reflections' 4,758 stars are a historical artifact**: star count measures interest accumulated over a decade, not current maintenance. In 2026 a four-year-old last-push date is the signal that matters.

## Decision Matrix: Pick by Situation

| Your situation | Recommended | Why |
|---|---|---|
| Plugin system inside a Spring Boot fat jar | ClassGraph 6 | Nested-jar reading without temp extraction |
| Framework whose startup time is a selling point | Jandex | Index built at compile time, zero scan at boot |
| Quarkus extension or anything on Quarkus | Jandex | Native integration; the index already exists |
| Scanning OSGi bundles or app-server classloaders | ClassGraph 6 | `classgraph-classpath` resolves container classloaders |
| Legacy library already using `org.reflections` | Reflections (short term) | Migration cost often exceeds the benefit |
| GraalVM native image | Jandex | Closed-world build already needs a static index |
| One-off script to list annotated classes | ClassGraph 6 | Fastest path from zero to working scan |
| Need a virtual filesystem over jars/modules | ClassGraph 6 (`classgraph-vfs`) | Standalone module, usable without the scanner |

## ClassGraph 6: The Scanner That Also Became a Virtual Filesystem

ClassGraph 6 is not an incremental release. The project re-architected the codebase and **split it into five artifacts** so you depend only on what you use:

- `classgraph-base` — shared internals and the verbose log
- `classgraph-vfs` — a virtual filesystem over directories, jars, nested jars and modules
- `classgraph-classpath` — resolves the classpath and module path in classloader search order
- `classgraph` — scanning plus the class-graph API
- `classgraph-viz` — GraphViz `.dot` output

The JDK story matters more than the module split. **ClassGraph 6 targets JDK 25 and newer.** If your build is still on JDK 17 through 24, the project maintains a `v5` branch with the same API and behaviour; ClassGraph 4 (JDK 8–16) is end-of-life at 4.8.199. Plan the upgrade rather than pinning a 4.x artifact forever.

```xml
<dependency>
  <groupId>io.github.classgraph</groupId>
  <artifactId>classgraph</artifactId>
  <version>6.0.1</version>
</dependency>
```

The scan API is a builder, and nothing is scanned until you declare a source. This example finds every class annotated with `@com.xyz.Route` and reads the annotation's parameter **without loading or initializing any of the scanned classes**:

```java
String pkg = "com.xyz";
String routeAnnotation = pkg + ".Route";

try (ScanResult scanResult =
        new ClassGraph()
            .verbose()                    // log to stderr
            .enableNonSystemModules()     // scan the module path
            .enableClasspath()            // scan the classpath
            .enableClassInfo()            // read the classfiles
            .enableAnnotationInfo()       // read annotations on those classes
            .acceptPackages(pkg)          // com.xyz and subpackages
            .scan()) {

    for (ClassInfo routeClassInfo : scanResult.getClassesWithAnnotation(routeAnnotation)) {
        AnnotationInfo info = routeClassInfo.getAllAnnotationInfo(routeAnnotation);
        List<AnnotationParameterValue> params = info.getParameterValues();
        String route = (String) params.get(0).getValue();
        System.out.println(routeClassInfo.getName() + " is annotated with route " + route);
    }
}
```

`ScanResult` implements `AutoCloseable`, and closing it releases the internal caches and classloader references. Skipping `close()` in an application server is the classic way to leak a classloader on every redeploy.

Resource scanning uses the same model, and `classgraph-vfs` is where the nested-jar support lives:

```java
try (ScanResult scanResult = new ClassGraph()
        .enableNonSystemModules()
        .enableClasspath()
        .acceptPathsNonRecursive("META-INF/config")
        .scan()) {

    scanResult.getResourcesWithExtension("json")
        .forEachByteArray((Resource res, byte[] content) ->
            readJson(res.getPath(), new String(content, StandardCharsets.UTF_8)));
}
```

That `forEachByteArray` variant throws `IOException` when a resource cannot be read; the `...IgnoringIOException` variant skips unreadable entries silently. Choose deliberately — silent skipping hides a broken jar behind a working application until the missing plugin is actually needed.

The migration cost of 6.x is real: the API changed, and the project publishes a porting guide for 4.x code. If your codebase calls `new ClassGraph()` in fifty places, budget the port as a real task, not a version bump.

## Reflections 0.10.2: Still Useful, Still Unmaintained

Reflections made annotation scanning feel natural years before anyone else did. The modern API is concise:

```java
Reflections reflections = new Reflections("com.my.project");

Set<Class<?>> subTypes =
    reflections.get(SubTypes.of(SomeType.class).asClass());

Set<Class<?>> annotated =
    reflections.get(SubTypes.of(TypesAnnotated.with(SomeAnnotation.class)).asClass());
```

Filtering is where it becomes practical, because scanning everything is rarely what you want:

```java
Reflections reflections = new Reflections(
    new ConfigurationBuilder()
        .forPackage("com.my.project")
        .filterInputsBy(new FilterBuilder()
            .includePackage("com.my.project")
            .excludePackage("com.my.project.exclude")));
```

Two behaviours in this library cause more bug reports than anything else. First: **a scanner must be configured before you can query it.** If you ask for `MethodsAnnotated` results without adding that scanner to the configuration, you get an empty result set — not an error. Defaults are `SubTypes` and `TypesAnnotated` only. Second, the library resolves metadata through Javassist, so it adds Javassist and SLF4J to your dependency graph and inherits their constraints.

The honest 2026 assessment: **Reflections is legacy.** Last push June 2024, WTFPL license (fine legally, awkward in corporate license reviews), no work on modern JDK realities. If you are starting fresh, do not pick it. If you already depend on it, the migration target is usually ClassGraph for runtime scanning or Jandex if you can move discovery to build time — and the trigger to migrate is a JDK upgrade that breaks it, not a calendar date.

## Jandex 3.6.0: Build the Index Once, Read It Forever

Jandex inverts the problem. Instead of walking the classpath at startup, it consumes class files during your build and emits a compact index. At runtime you read that index — a dictionary lookup, not a scan.

```xml
<dependency>
  <groupId>io.smallrye</groupId>
  <artifactId>jandex</artifactId>
  <version>3.6.0</version>
</dependency>
```

Building an index programmatically, for a custom build step or a test harness:

```java
Indexer indexer = new Indexer();
try (InputStream in = Files.newInputStream(Paths.get("target/classes/com/example/Plugin.class"))) {
    indexer.index(in);
}
Index index = indexer.complete();

Collection<ClassInfo> implementors =
    index.getAllKnownImplementors(DotName.createSimple("com.example.Plugin"));
```

In a normal Maven build you do not write that code — the Maven plugin does it:

```xml
<plugin>
  <groupId>io.smallrye</groupId>
  <artifactId>jandex-maven-plugin</artifactId>
  <version>3.6.0</version>
  <executions>
    <execution>
      <id>make-index</id>
      <goals><goal>jandex</goal></goals>
    </execution>
  </executions>
</plugin>
```

The output is `META-INF/jandex.idx` inside the artifact. Quarkus builds on exactly this: the augmentation phase reads indexes instead of scanning, which is why a Quarkus application can start in tens of milliseconds while a scanner-heavy Spring application spends seconds walking its classpath.

The tradeoff is closed-world thinking. **Anything that appears after the build — a plugin jar dropped into a directory at runtime, a class generated by a scripting layer — is not in the index.** If your architecture needs late discovery, Jandex is the wrong tool and ClassGraph is the right one. That is a design decision, not a benchmark result.

## Performance: What Actually Costs You Time

Most "which scanner is fastest" discussions compare the wrong thing. The dominant cost in a real application is not the parsing algorithm — it is **how many bytes get read and how many times**. Three practical rules:

1. **Scan once, cache the result.** All three libraries pay their cost on first use. Re-creating a `Reflections` or `ClassGraph` scan per request is a self-inflicted outage; a static holder initialised once is the correct pattern.
2. **Restrict the search space.** `acceptPackages(...)` in ClassGraph and `filterInputsBy(...)` in Reflections are not micro-optimisations — they cut the number of jars opened, which dominates wall-clock time on a large classpath.
3. **Move to build time if startup is a feature.** Jandex does not win because its code is faster; it wins because there is no scan. Compare like for like: index-read time against scan time, not parser against parser.

If you do benchmark, use a proper harness rather than `System.currentTimeMillis()` around a single call — class loading, page cache and JIT warmup will all lie to you. JMH is the tool for that job, and its results are the only ones worth putting in a design document.

## Common Traps

- **Forgetting to close `ScanResult`** in a servlet container or app server leaks classloaders across redeploys. Use try-with-resources, always.
- **Assuming fat-jar support.** Only ClassGraph reliably reads jars nested inside jars. If you ship a Spring Boot jar and use a scanner that extracts to temp files, you inherit cleanup problems on read-only filesystems.
- **JDK 25 breaking ClassGraph 4.** ClassGraph 6 exists because the older architecture could not keep up with modern JDK internals. If you are pinned to 4.x and moving to JDK 25, use the `v5` branch first, then port.
- **Reflections returning empty sets.** Almost always a missing scanner in `ConfigurationBuilder`, not a broken classpath.
- **Native-image builds.** Closed-world compilation needs a static index; runtime scanning either fails or needs extensive configuration. Jandex fits the model naturally.
- **Annotation retention.** Scanning only finds annotations with `RetentionPolicy.RUNTIME` (ClassGraph and Jandex read classfile metadata; `SOURCE`-retained annotations are gone). This is a Java rule that no library can bypass.
- **Scanning test classpaths by accident.** Unit tests pick up every test-scoped jar on the classpath; a scan that takes 40 ms in production can take 4 seconds in a test suite. Restrict packages in test configuration.

## FAQ

**Is ClassGraph still maintained in 2026?**
Yes. ClassGraph 6.0.1 is the current release, with commits through November 2026. The 6.x line targets JDK 25+, the `v5` branch covers JDK 17–24 with the same API, and ClassGraph 4 (JDK 8–16) is end-of-life at 4.8.199.

**Should I use Reflections or ClassGraph for a new project?**
ClassGraph. Reflections' last commit was June 2024 and it depends on Javassist; ClassGraph is actively maintained, MIT licensed, handles nested jars and modern JPMS layouts, and does not load the classes it discovers.

**Does Jandex work without Quarkus?**
Yes. `io.smallrye:jandex` is a standalone library, and `io.smallrye:jandex-maven-plugin` builds the index in any Maven project. Quarkus is simply its most visible consumer.

**Can I use Jandex for runtime plugin discovery?**
Only for artifacts indexed at build time. Jandex reads a pre-built index; a jar added to the classpath after the build will not appear in it. For genuinely late discovery, scan at runtime with ClassGraph.

**Do these libraries load the classes they find?**
ClassGraph and Jandex parse classfile bytes and return metadata without initialising classes. Reflections can work without loading classes as well, but its Javassist-based metadata model and configuration make accidental loading easier.

**What about scanning in a GraalVM native image?**
Treat scanning as a build-time concern. Produce a Jandex index (or explicit reflection configuration) during the build; a runtime classpath walk has no classpath to walk in a closed-world binary.

For the bytecode layer underneath all of this — the libraries that read and rewrite the same classfiles — see our [JVM bytecode engineering comparison](../2026-09-11-jvm-bytecode-engineering-byte-buddy-javassist-asm/). If your scan exists to wire up a dependency-injection container, the build-tool tradeoffs in our [JVM build tools guide](../2026-06-24-jvm-build-tools-gradle-maven-sbt-bazel/) decide how fast that container starts. And when scanning is used to bind native libraries rather than classes, the [JNA vs JNR vs Panama comparison](../2026-11-04-jna-vs-jnr-vs-project-panama-java-native-interop/) covers the runtime side.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "ClassGraph vs Reflections vs Jandex in 2026: Picking a JVM Classpath Scanner That Still Works on Modern Java",
  "description": "ClassGraph 6, Reflections 0.10.2 and Jandex 3.6.0 compared: JDK 25 constraints, build-time indexing, nested-jar scanning, native-image tradeoffs and a decision matrix.",
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

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
