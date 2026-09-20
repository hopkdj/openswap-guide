---
title: "Leiningen vs tools.build vs Boot in 2026: Which Clojure Build Tool Should You Actually Use?"
date: "2026-09-20"
tags: ["clojure", "build-tools", "jvm", "developer-tools"]
draft: false
cover: "/img/screenshots/clojure-build-tools-cover.jpg"
description: "Leiningen, tools.build and Boot compared for Clojure builds in 2026: real project.clj and build.clj configs, star counts, maintenance status and a migration path."
---

Clojure has three build tools, and only one of them is still growing. **Leiningen** — the tool that made Clojure projects reproducible back in 2011 — still carries **7,296 GitHub stars**, but its primary repository moved to Codeberg and the GitHub copy now describes itself as "a temporary convenience mirror." **Boot**, once the hip alternative with a REPL-driven pipeline model, has not seen a commit since **April 2021** and is pinned at 1,749 stars. Meanwhile **tools.build**, the official Clojure-contributed library, sits at **230 stars** with a release only months old — far fewer stars, but it is the only one wired directly into the `clj` CLI that every new Clojure project already uses.

That mismatch — popularity versus momentum — is exactly why the wrong pick costs you a quarter of maintenance pain later. Here is the honest breakdown, built from each project's own repository at the time of writing.

## TL;DR: Quick Verdict

**Use Leiningen if you maintain an existing project** — the `project.clj` format still has the best plugin ecosystem for one-off tasks like `lein uberjar` and `lein cljsbuild`. **Use tools.build (with deps.edn) if you are starting something new** — you get official Clojure maintenance, a plain Clojure build script instead of a DSL, and zero extra tooling on top of the `clj` CLI. **Do not start a new project on Boot** — its pipeline abstraction is elegant but the project is dormant, and its `build.boot` files have no migration tooling.

## Feature Comparison at a Glance

| Dimension | Leiningen | tools.build | Boot |
|---|---|---|---|
| GitHub stars | 7,296 | 230 (plus 434 for tools.deps.alpha) | 1,749 |
| Last repository activity | 2026-06-08 (mirror; primary on Codeberg) | 2026-05-28 | **2021-04-22 (dormant)** |
| Current version line | 2.12.0 (development), 2.x stable | v0.10.14 | 2.8.x, frozen |
| Config file | `project.clj` (EDN DSL) | `deps.edn` + `build.clj` (plain Clojure) | `build.boot` (Clojure DSL) |
| Dependency resolution | Maven/Aether, with its own lock-free model | `tools.deps` (Maven + git + local, transitive graph) | Managed through Boot's own tasks |
| License | EPL-1.0 | EPL-1.0 | EPL-1.0 |
| Jar / uberjar | `lein jar`, `lein uberjar` (built in) | `b/jar`, `b/uber` (explicit API calls) | `(jar)`, `(uber)` tasks |
| Plugin ecosystem | Very large, decade-old | Small: you write build logic yourself | Moderate, mostly unmaintained |
| Learning curve | Low at first, surprising later | Low if you know Clojure, explicit | Steepest of the three |
| Best fit | Legacy and polyglot-adjacent builds | New projects, CI pipelines, libraries | Nothing new in 2026 |

## Decision Matrix: Pick by Use Case

| Your situation | Recommended tool | Why |
|---|---|---|
| New Clojure service or library in 2026 | **tools.build + deps.edn** | Official maintenance, `clj -T:build` runs from the same CLI, no plugin resolution step |
| Existing app with a working `project.clj` | **Leiningen** | Migration buys you nothing if the build is green; plugin coverage for exotic tasks is still better |
| AOT-compiled CLI jar that ships to servers | **Leiningen** or **tools.build** | `lein uberjar` is one command; tools.build's `b/uber` gives identical output with more control |
| Monorepo pulling deps from git tags | **tools.build + tools.deps** | Git coordinate support in `deps.edn` is first-class; Leiningen needs plugins or checkouts |
| Build logic shared across many repos | **tools.build** | A `build.clj` can be a dependency and reused; `project.clj` middleware is harder to share |
| A project still on `build.boot` | **tools.build**, gradually | No automatic conversion exists; port task by task while keeping the old build runnable |
| Team that fights the classpath monthly | Either Leiningen or tools.build, but pin versions | The problem is unpinned deps, not the tool |

## Leiningen: The Battle-Tested Default

Leiningen's model is a single `project.clj` that declares dependencies, entry points and profiles. The skeleton below comes straight from the project's own `doc/TUTORIAL.md`:

```clojure
(defproject my-stuff "0.1.0-SNAPSHOT"
  :description "FIXME: write description"
  :url "https://example.com/FIXME"
  :license {:name "Eclipse Public License"
            :url "https://www.eclipse.org/legal/epl-v10.html"}
  :dependencies [[org.clojure/clojure "1.11.4"]]
  :main ^:skip-aot my-stuff.core
  :target-path "target/%s"
  :profiles {:uberjar {:aot :all}})
```

Three things matter in those nine lines. `^:skip-aot` keeps the entry namespace interpreted during development, which makes the REPL start faster; `:target-path "target/%s"` isolates per-profile build output so your `:uberjar` artifacts never clobber your dev classpath; and `:profiles {:uberjar {:aot :all}}` AOT-compiles only when you actually build a jar. Aliases handle everything else, for example routing tests through a different runner:

```clojure
:aliases {"test" ["run" "-m" "kaocha.runner"]}
```

Then the day-to-day commands are short:

```shell
lein deps      # resolve and download the dependency tree
lein test      # run the test suite
lein uberjar   # build target/my-stuff-0.1.0-SNAPSHOT-standalone.jar
lein repl      # start a REPL on the project classpath
```

The honest caveats in 2026: the GitHub repository is explicitly a mirror of the Codeberg original, so star counts and issue trackers understate real activity, and Leiningen's dependency handling is its own implementation rather than `tools.deps`. If your build already works, that distinction never shows. If you are debugging a diamond dependency with git coordinates, it will.

## tools.build: deps.edn and Clojure-Native Builds

tools.build deletes the DSL layer. Your dependency declaration lives in `deps.edn` — the same file the `clj` CLI reads — and your build steps are ordinary Clojure functions in `build.clj`. First, expose the build alias, exactly as the official guide shows:

```clojure
{:paths ["src"]
 :aliases
 {:build {:deps {io.github.clojure/tools.build {:git/tag "TAG" :git/sha "SHA"}}
          :ns-default build}}}
```

For a pinned artifact, the library's own README gives the coordinates directly:

```clojure
io.github.clojure/tools.build {:mvn/version "0.10.14"}
```

The build namespace is where the interesting part lives. This is the guide's standalone-jar example, unmodified:

```clojure
(ns build
  (:require [clojure.tools.build.api :as b]))

(def lib 'my/lib1)
(def version "0.1.0") ;; or source from file, etc
(def class-dir "target/classes")
(def uber-file (format "target/%s-%s-standalone.jar" (name lib) version))

;; delay to defer side effects (artifact downloads)
(def basis (delay (b/create-basis {:project "deps.edn"})))

(defn clean [_]
  (b/delete {:path "target"}))

(defn uber [_]
  (clean nil)
  (b/copy-dir {:src-dirs ["src" "resources"]
               :target-dir class-dir})
  (b/compile-clj {:basis @basis
                  :ns-compile '[my.lib.main]
                  :class-dir class-dir})
  (b/uber {:class-dir class-dir
           :uber-file uber-file
           :basis @basis
           :main 'my.lib.main}))
```

You invoke it with the same CLI you already use for the REPL:

```shell
clj -T:build clean
clj -T:build uber
java -jar target/lib1-0.1.0-standalone.jar
```

The trade-off is deliberate. Nothing is implicit: there is no `lein uberjar` shortcut that "just knows" where your main namespace is, because you declared it. That means more lines in `build.clj`, but every step is inspectable, testable Clojure. It also means a build file can be published as a library and reused across an organisation — something Leiningen middleware never made pleasant.

Note that `tools.deps.alpha` (434 stars) still appears in tutorials, but for typical projects you do not add it manually: dependency resolution is part of the `clj`/`clojure` CLI now, and the last meaningful alpha activity dates to **July 2024**. Add `tools.build` for artifacts, and nothing else.

## Boot: The Build Tool That Time Forgot

Boot's selling point was that a build was a pipeline of composable tasks evaluated in a live REPL, not a declarative file. That is genuinely nice, and it is also why porting off Boot hurts: there is no equivalent of "translate `project.clj` to `deps.edn`" because Boot's build logic is imperative Clojure.

Installation, from Boot's own README:

```shell
$ sudo bash -c "cd /usr/local/bin && curl -fsSLo boot https://github.com/boot-clj/boot-bin/releases/download/latest/boot.sh && chmod 755 boot"
```

Builds are then composed on the command line or in the REPL:

```shell
# The -- args below are optional. We use them here to visually separate the tasks.
boot -r src -d me.raynes/conch:0.8.0 -- pom -p my-project -v 0.1.0 -- jar -M Foo=bar -- install
```

```clojure
boot.user=> (set-env!
       #_=>   :resource-paths #{"src"}
       #_=>   :dependencies '[[me.raynes/conch "0.8.0"]])

boot.user=> (boot (pom :project 'my-project :version "0.1.0")
       #_=>       (jar :manifest {"Foo" "bar"})
       #_=>       (install))
```

Read those two snippets again and the migration problem is obvious: the second one is a running REPL session, not a file you can mechanically convert. With no commits since **April 2021**, Boot still works for pinned toolchains, but every Crystal-clear answer you would need in 2026 — JDK 21+ classpath handling, modern Clojure versions, native image tooling — has to come from you. Treat `build.boot` as technical debt with a clear payoff: port the build to `build.clj`, keep both working for a sprint, then delete the Boot pipeline.

## Migration Path: Leiningen to tools.build

The port is mechanical once you know the mapping. Dependencies and paths move to `deps.edn`; anything that used to be a plugin becomes a function.

1. **Move `:dependencies`** into `deps.edn` under `:deps`, keeping the same version strings so you can compare classpaths before and after.
2. **Move `:paths`** (`src`, `resources`, `test`) into the `:paths` and `:aliases` entries, since `deps.edn` has no separate test path concept — you add an alias with `:extra-paths ["test"]`.
3. **Translate profiles into aliases.** A `:dev` profile becomes an alias with `:extra-deps`; an `:uberjar` profile becomes the `:build` alias plus an explicit `uber` function.
4. **Replace plugin tasks with functions.** `lein-ancient`, for instance, has no direct equivalent: you call `clj -X:deps list` or add your own check.
5. **Diff the classpaths.** Run `lein classpath` before the port and `clj -Spath` after. If the two strings are not identical, you have found a resolution difference while the old build is still there to fall back on.
6. **Switch CI last.** Local builds first, then the pipeline — a broken CI build with no working local fallback is the worst of both worlds.

Keep the `project.clj` in the repository during the transition. Two build files for one sprint is normal; two build files for a year is a trap, because dependencies drift and the results stop matching.

## Pitfalls and Gotchas

- **AOT compilation hides errors.** `^:skip-aot` in Leiningen and the explicit `:ns-compile` list in tools.build exist for a reason. Compiling everything by default slows iteration and turns reflection warnings into hard failures at build time.
- **`deps.edn` has no lockfile by default.** Both Leiningen and tools.deps resolve versions at build time. Pin library versions and, for git coordinates, pin `:git/sha` rather than only `:git/tag` — tags move, SHAs do not.
- **Resource paths are not classpath magic.** `b/copy-dir` needs both `src` and `resources`; forgetting the second is the most common "my config file is not in the jar" bug after a Boot or Leiningen port.
- **`lein` mirrors lie about activity.** Since the primary repo lives on Codeberg, a stale-looking GitHub commit date is not evidence of abandonment.
- **Boot plugins cannot be reused.** Their task protocol is Boot-specific; budget a rewrite, not a port.
- **Do not mix build tools in one repo.** A `project.clj` and a `build.clj` that both produce jars will diverge silently. Pick one as authoritative and delete the other when the migration lands.
- **CI caching is tool-specific.** Building a Maven-style `~/.m2` cache for one tool does not help the other; if you cache by tool name you will get cold builds after the port.

## FAQ

**Is Leiningen dead in 2026?**
No. Leiningen's development continues under the `leiningen` organisation on Codeberg, and the version line is at 2.12.0. The GitHub repository is an explicit convenience mirror, which is why its activity graph looks slower than reality. For existing projects with working `project.clj` files, there is no urgency to migrate.

**Should I use tools.build for a library, or only for applications?**
Both. A library usually needs `b/write-pom`, `b/copy-dir` and `b/jar` rather than `b/uber`, and the guide shows exactly that variant. The same `deps.edn` alias works for either, and publishing to Clojars needs only the version metadata you already declared.

**How long does a Boot migration take?**
Plan for a few days for a small application and one to two weeks for a service with custom tasks. The dependency and path move is quick; the imperative task pipelines are not. Keep the Boot build runnable until CI passes on the new one.

**Do I lose anything by leaving Leiningen?**
You lose plugins with no equivalent: task plugins that hook build lifecycle events, and older tooling that assumes `project.clj` exists. You gain `tools.deps` resolution, shared build logic, and a build script that is plain Clojure with no DSL to learn.

**Can I run tests the same way in both worlds?**
Yes, if you model the test path as an alias. In `deps.edn`, add `:extra-paths ["test"]` to a test alias and run the same test runner namespace you already use — for example the one described in our [Clojure testing frameworks comparison](../2026-09-06-clojure-testing-frameworks-clojure-test-kaocha-midje-comparison/). Nothing about the runner changes; only the way it is launched does.

**Which one should a team standardise on for 2026?**
tools.build plus `deps.edn`, unless a specific legacy plugin blocks it. The strongest argument is not performance or syntax — it is that build logic becomes a reusable Clojure namespace instead of configuration interpreted by a plugin system. Teams already dependent on `project.clj` can defer, but new repositories should not adopt it.

If you are also deciding which logging or JSON layer to put on top of those builds, our [Clojure logging libraries comparison](../2026-09-08-clojure-logging-libraries-timbre-tools-logging-mulog-comparison/) and [Clojure JSON libraries comparison](../2026-09-08-clojure-json-libraries-cheshire-jsonista-data-json-comparison/) cover the operational side; and if you are comparing JVM build tooling more broadly, see [Gradle vs Maven vs sbt vs Bazel](../2026-06-24-jvm-build-tools-gradle-maven-sbt-bazel/).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Leiningen vs tools.build vs Boot in 2026: Which Clojure Build Tool Should You Actually Use?",
  "description": "Leiningen, tools.build and Boot compared for Clojure builds in 2026: real project.clj and build.clj configs, star counts, maintenance status and a migration path.",
  "datePublished": "2026-09-20",
  "dateModified": "2026-09-20",
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
