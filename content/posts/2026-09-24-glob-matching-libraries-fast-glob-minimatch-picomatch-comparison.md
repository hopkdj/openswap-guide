---
title: "fast-glob vs minimatch vs picomatch in 2026: Which Glob Library Is Fastest and Safest?"
date: "2026-09-24"
tags: ["glob", "javascript", "golang", "python", "developer-tools", "libraries"]
draft: false
---

**`minimatch` was downloaded 519,665,999 times in the single week ending 2026-09-21.** `picomatch` was fetched 361,062,120 times. `fast-glob` 114,523,958 times. Those numbers come straight from the npm registry, and they should make you slightly uncomfortable: nearly every build tool, test runner, bundler and linter you run ships a glob matcher you have never inspected — and if any of those tools let a user supply a pattern, a badly built matcher is a denial-of-service bug with a friendly UI.

This is a comparison of the three Node matchers that dominate the download charts, plus the Go and Python options, based on their current repositories and their own documentation.

## TL;DR — Quick Verdict

- **Walking a real directory tree →** **fast-glob (2,826★)**. It owns the filesystem traversal, so you get one async call instead of a matcher plus your own recursive walk.
- **Matching a string in a hot loop →** **picomatch (1,295★)**. Zero dependencies, and it is the engine other libraries build on — its own README lists Jest, Astro, Storybook, Chokidar, Rollup and Docusaurus among its dependents.
- **Canonical Bash-like semantics for a CLI, with the widest compatibility →** **minimatch (3,521★)**. Different license, larger surface, half a billion weekly downloads.
- **Go →** **doublestar (717★)**. It is a drop-in replacement for `path.Match` and `filepath.Match` with `**` support added.
- **Python →** **wcmatch (168★)**. An enhanced `fnmatch`, `glob` and `pathlib` with `**` and extended globbing, using Bash as its behaviour reference.

## The Five Contenders

| Library | Platform | Stars | License | Adoption signal | Last repo activity |
|---|---|---|---|---|---|
| **minimatch** | Node.js | 3,521 | Blue Oak Model License 1.0.0 | 519.7M npm downloads/week | 2026-07-27 |
| **picomatch** | Node.js | 1,295 | MIT | 361.1M npm downloads/week | 2026-09-23 |
| **fast-glob** | Node.js | 2,826 | MIT | 114.5M npm downloads/week | 2026-09-22 |
| **doublestar** | Go | 717 | MIT | Standard `**` matcher in Go projects | 2026-09-20 |
| **wcmatch** | Python | 168 | MIT | On PyPI as a `fnmatch`/`glob` upgrade | 2026-08-14 |

npm figures are the registry's own counts for the week of 2026-09-15 to 2026-09-21; star counts and dates were read from GitHub on 2026-09-24. Notice what the table says about the ecosystem: the most-downloaded matcher is not the most-starred project, and the newest commits are not on the most-popular library. Download rank, star rank and maintenance rank are three different lists.

## Decision Matrix

| Your job | Pick | Why |
|---|---|---|
| Find files under a directory by pattern | fast-glob | Directory traversal is built in |
| Test one string against many patterns in a loop | picomatch | Compile the matcher once, reuse the function |
| Replace shell `*.log` style filtering in a CLI | minimatch | Closest to classic shell semantics |
| Add `**` to Go's standard matching | doublestar | Drop-in for `path.Match`/`filepath.Match` |
| Upgrade Python's `fnmatch`/`glob` | wcmatch | Same API shape, more syntax |
| Match untrusted, user-supplied patterns | None, unguarded | See the hardening section below |

## picomatch — The Zero-Dependency Matcher Everyone Else Uses

picomatch's repository description claims support for "standard and extended Bash glob features, including braces, extglobs, POSIX brackets, and regular expressions" and lists its dependents as GraphQL, Jest, Astro, Storybook, Chokidar, Rollup, Docusaurus, fast-glob and globby, among "more than 5 million projects".

The API is a single callable you keep around:

```js
const pm = require('picomatch');
const isMatch = pm('*.js');

console.log(isMatch('abcd')); //=> false
console.log(isMatch('a.js')); //=> true
console.log(isMatch('a.md')); //=> false
console.log(isMatch('a/b.js')); //=> false
```

That last line is the important one for anyone coming from shell habits: `*.js` does not cross a path separator. Extglobs work the same way they do in Bash:

```js
const picomatch = require('picomatch');
// picomatch(glob[, options]);
const isMatch = picomatch('*.!(*a)');
console.log(isMatch('a.a')); //=> false
```

Beyond `isMatch`, the library exposes `makeRe` to get the underlying regular expression and `scan` to pull the static parts out of a pattern — that second function is what makes it viable as a pre-filter when you have millions of candidate paths and only a few patterns.

**Why it wins in a hot loop:** it has no dependencies, so the supply-chain surface is one file, and a compiled matcher is a closure you can hold in a variable. If your code tests 50,000 strings against one pattern, compiling once is the difference between a build step and a stall.

**Where it loses:** it does not walk directories. Pair it with `fs` or reach for fast-glob.

## fast-glob — The One That Does the Walking

fast-glob's pitch is "very fast and efficient glob library for Node.js", and its differentiator is that it takes over the filesystem traversal rather than only the matching. The current README documents `fg.glob(patterns, [options])`:

```js
import * as fg from 'fast-glob';

const entries = await fg.glob(['.editorconfig', '**/index.js'], { dot: true });
```

Two details in that snippet are load-bearing. `dot: true` is required because glob patterns do **not** match dotfiles by default — the single most common surprise when someone's build script silently skips `.eslintrc` or a `.babelrc`-equivalent. And the pattern list is a first-class feature: combining includes and excludes in one call is what you would otherwise hand-roll with a filter.

**Why it wins for real projects:** one async call returns the entries you asked for, in the order you asked for them, with the traversal handled by the library. That is most of the work in any file-based tool.

**Where it loses:** if you only need to test a path you already have, this is the wrong dependency — you are installing a directory crawler to answer a boolean.

## minimatch — Half a Billion Downloads and a Different License

minimatch is the classic. Its repository describes it simply as "a glob matcher in javascript", and at 519,665,999 weekly downloads it is the matcher most JavaScript tooling depends on whether or not the authors know it.

The modern API is a named export and a class:

```js
// hybrid module, load with require() or import
const { minimatch } = require('minimatch')

minimatch('bar.foo', '*.foo') // true!
minimatch('bar.foo', '*.bar') // false!
minimatch('bar.foo', '*.+(bar|foo)', { debug: true }) // true, and noisy!
```

Note the named export: a great deal of code you will find in tutorials calls minimatch as a default export, which is not what the current documentation shows. Copy-paste carefully.

For repeated matching, the `Minimatch` class pre-compiles a pattern and exposes a regular expression plus helper methods:

```js
var Minimatch = require('minimatch').Minimatch
var mm = new Minimatch(pattern, options)
```

The README documents the instance members clearly: `makeRe()` builds the regex, `match(fname)` tests a name, and there is a convenience `minimatch.filter(pattern, options)` for array filtering plus `{ matchBase: true }` when you want `*.js` to behave as if it were `**/*.js`.

**The license is the underrated differentiator.** minimatch ships under the Blue Oak Model License 1.0.0, not MIT. It is a permissive license, but if your organisation runs automated license policy checks, this file will raise a flag that picomatch and fast-glob will not — and that is a perfectly good reason to pick the MIT option in some codebases.

## doublestar — `**` for Go

Go's standard library gives you `path.Match` and `filepath.Match`, and neither understands `**`. doublestar (717★, MIT, active 2026-09-20) fixes exactly that, deliberately as a drop-in:

```go
func Match(pattern, name string) (bool, error)
func PathMatch(pattern, name string) (bool, error)
func Glob(fsys fs.FS, pattern string, opts ...GlobOption) ([]string, error)
```

`Match` is the replacement for `path.Match` and assumes `/` separators; `PathMatch` is the replacement for `filepath.Match` and is the one you want on Windows because it respects the platform separator. There is also `GlobWalk` for streaming results and options such as `WithCaseInsensitive` and `WithFilesOnly` to tune what counts as a match.

**Where it wins:** it adds the one feature Go's standard library lacks without asking you to adopt a whole framework, and the API shape is familiar to anyone who has used `filepath.Glob`.

## wcmatch — Python's `fnmatch` and `glob`, Upgraded

wcmatch (168★, MIT, 2026-08-14) takes a different approach to the same problem: rather than inventing new API names, it mirrors Python's built-ins. The project describes itself as providing "an enhanced `fnmatch`, `glob`, and `pathlib`" and adds `globmatch`, which behaves like `fnmatch` but for paths. Its documentation states that **Bash is used as the guide** when deciding behaviour, which is exactly the right reference point if you have ever been surprised by Python's `fnmatch` and shell globbing disagreeing.

```bash
pip install wcmatch
```

Capabilities worth knowing: `**` support in glob, an alternative file crawler also called `wcmatch`, and `EXTGLOB`/`EXTMATCH` flags that enable groups of patterns aligned with regular expression groups. If you have ever written a bespoke recursive `os.walk` filter because `glob.glob` could not express your pattern, this is the library that removes that code.

## Hardening: Globs Are an Attack Surface

**Never compile an untrusted pattern into a regular expression without limits.** `makeRe()`-style compilation turns pattern complexity into regex complexity. If patterns arrive from users — ignore-file syntax, log filters, search UI — cap the pattern length, cap the path length, and treat a match failure as "no match" rather than letting the process hang. The `scan`-style pre-filter in picomatch exists precisely because matching can be short-circuited.

**Dotfiles do not match by default.** In fast-glob this is the `dot` option; in most matchers a leading `.` is excluded unless the pattern starts with one. Every "my build suddenly stopped picking up a config file" bug traces back to this.

**`**` is not a universal constant.** Depth semantics, whether `**` can match zero directories, and how it interacts with dotfiles all vary between libraries and between versions. Test the specific patterns your tool ships against the specific version you pin — especially after a major upgrade.

**Path separators are a portability trap.** Go users want `PathMatch` on Windows; Node users should normalise backslashes before matching; Python's `globmatch` exists because `fnmatch` alone is separator-blind. Cross-platform bugs in this area surface as "works on my machine" reports.

**Watch for symlink loops when walking.** Recursive traversal via a matcher-driven crawler is the classic way to build an infinite loop in CI. Cap traversal depth explicitly rather than discovering the cycle in production.

**Dependency count is a security decision.** picomatch has none. minimatch pulls in a brace-expansion dependency. Fewer moving parts is less to audit, and in a matcher that runs inside every build, that is not a theoretical concern.

If your globs are filtering a search index rather than a filesystem, the same semantics question shows up one layer up — see our [ripgrep vs ag vs ugrep comparison](../2026-06-16-code-search-tools-ripgrep-ag-silver-searcher-ugrep/) for how those tools expose glob filters. And if you are wiring globs into a watcher, [chokidar, fs-extra and graceful-fs](../2026-08-24-nodejs-filesystem-libraries-chokidar-fs-extra-graceful-fs-comparison/) is the companion read, with [watchexec vs entr vs inotify-tools](../2026-05-22-self-hosted-file-watch-tools-watchexec-vs-entr-vs-inotify-tools-guide/) covering the system-level side.

## FAQ

**Which glob library is actually the fastest?**
There is no single answer, because the two jobs are different. For repeated string matching, picomatch is built for it: zero dependencies, a compiled matcher you reuse, and a `scan` function for pre-filtering. For finding files on disk, fast-glob is the faster approach because it fuses traversal and matching in one pass instead of making you walk the tree yourself. Benchmark your own pattern set and file tree rather than trusting any generic number.

**Do glob patterns match hidden files like `.env`?**
No, not by default. Patterns starting with a wildcard skip entries that begin with a dot. fast-glob exposes this as `dot: true`; other matchers have equivalent options. This is the most common cause of "it worked yesterday" behaviour in build tooling.

**Is minimatch still maintained despite the Blue Oak license?**
Yes. The repository showed activity on 2026-07-27, carries 3,521 stars, and the package recorded 519,665,999 downloads in the week ending 2026-09-21 — the largest adoption signal in this comparison. The license is permissive; it is simply not MIT, which matters if you run automated license policy checks.

**What is the Go equivalent of `fast-glob`?**
doublestar. It extends Go's standard `path.Match` and `filepath.Match` with `**` support, adds a `Glob(fsys, pattern)` function and a `GlobWalk` streaming variant, and is designed as a drop-in replacement for the standard-library functions rather than a new API to learn.

**What should I use instead of Python's `fnmatch` or `glob.glob`?**
wcmatch. It provides enhanced `fnmatch`, `glob` and `pathlib` equivalents, adds `**` to glob, offers `globmatch` for path-aware matching, and takes Bash as its behavioural reference. Installation is a plain `pip install wcmatch`, and it keeps the familiar API shape so migration is mostly an import change.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "fast-glob vs minimatch vs picomatch in 2026: Which Glob Library Is Fastest and Safest?",
  "description": "A 2026 comparison of wildcard matching libraries: picomatch, fast-glob, minimatch, Go doublestar and Python wcmatch, with live npm download counts, real API examples and hardening advice.",
  "datePublished": "2026-09-24",
  "dateModified": "2026-09-24",
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
