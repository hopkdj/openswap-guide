---
title: "Human-Readable Formatting Libraries in 2026: go-humanize vs timeago.js vs python-humanize vs humantime"
date: "2026-10-06"
tags: ["developer-tools", "go", "python", "javascript", "rust"]
draft: false
---

`87342199` bytes. `1696510123` seconds. `0.00000000223` metres. Every backend eventually ships a UI that renders raw numbers like these, and every user-facing dashboard eventually gets a support ticket asking what "1696510123 seconds" is supposed to mean. The fix is a class of tiny libraries that convert machine units into human units: **83 MB**, **7 hours ago**, **2.23 nM**.

These libraries look trivial and are quietly one of the highest-leverage dependencies in a web stack — they sit on every list endpoint, every activity feed, and every file manager. This guide compares the four most-used open-source implementations, with live GitHub data pulled on **2026-10-06** and code taken directly from each project's official documentation.

## TL;DR — Quick Verdict

- **`go-humanize`** is the most complete formatter of the four: bytes, ordinals, commas, SI units, and relative time in one package. Pick it for any Go service.
- **`timeago.js`** is the right choice for browser and Node when all you need is "3 hours ago" — it is under 2 KB and does exactly one job.
- **`python-humanize`** is the Python default, and it handles both number formatting and natural-language dates.
- **`humantime`** is the Rust pick when you need fast, allocation-light duration parsing and formatting — including parsing strings like `15days 2min 2s` back into a `Duration`.

If you only have time for one rule: **`go-humanize` in the backend, `timeago.js` in the client, never hand-roll either.**

## Head-to-Head Comparison

All numbers were fetched live from GitHub on **2026-10-06**.

| Library | Language | GitHub Stars | License | Last Update | Scope | Typical Output |
|---|---|---|---|---|---|---|
| **go-humanize** | Go | 4,830 | MIT | 2026-09-28 | Bytes, ordinals, commas, SI, time | `83 MB`, `7 hours ago`, `193rd` |
| **timeago.js** | JavaScript (Node + browser) | 5,366 | MIT | 2026-06-30 | Relative time only | `3 hours ago` |
| **python-humanize** | Python | 761 | MIT | 2026-10-06 | Numbers, dates, files, lists | `123.5 million`, `an hour ago` |
| **humantime** | Rust | 398 | Apache-2.0 | 2026-07-13 | Durations and RFC 3339 timestamps | `53m 20s`, `2018-01-01T12:53:00Z` |

Two things stand out. First, `timeago.js` has the most stars (5,366) despite doing the *least* — that is the payoff of a sub-2 KB bundle in a frontend ecosystem obsessed with payload size. Second, `humantime` at 398 stars is the smallest community here but occupies a niche with almost no competition: fast duration parsing plus formatting in Rust.

**A note on the Python ecosystem:** the widely-linked `jmoiron/humanize` repository is frozen at its **2022-07-17** commit. Active development moved to `python-humanize/humanize`, which pushed on **2026-10-06**. If your `requirements.txt` pins a GitHub URL, check which one you actually point at — the PyPI package named `humanize` tracks the active repository.

### Scenario Decision Matrix

| Your Use Case | Recommended Tool | Why |
|---|---|---|
| Format byte sizes in a Go API response | **go-humanize** | `humanize.Bytes()` handles the whole KB/MB/GB scale |
| "3 hours ago" timestamps in a web app | **timeago.js** | Under 2 KB, with `render()` for live-updating feeds |
| Humanize numbers in a Django/Flask template | **python-humanize** | `intcomma`, `naturaltime`, and `naturalsize` built in |
| Parse a config string like `15days 2min 2s` | **humantime** | `parse_duration()` is the only one here that parses free-form durations |
| Live-updating relative timestamps on a feed | **timeago.js** | `render()` + `cancel()` re-render on an interval |
| Ordinals in Go ("1st", "2nd", "193rd") | **go-humanize** | `humanize.Ordinal()` — the other three lack it |

## go-humanize — The Most Complete Formatter

`go-humanize` reached **4,830 stars** and was last updated **2026-09-28** under the MIT license. It is the widest in scope of the four: bytes, ordinals, comma-separated integers, SI prefixes, and relative time all live in one import.

```bash
go get github.com/dustin/go-humanize
```

The examples below are lifted directly from the project README, with the output shown in the trailing comment:

```go
import (
    "fmt"
    "time"
    "github.com/dustin/go-humanize"
)

// Byte sizes
fmt.Printf("That file is %s.", humanize.Bytes(82854982))
// That file is 83 MB.

// Relative time
fmt.Printf("This was touched %s.", humanize.Time(someTimeInstance))
// This was touched 7 hours ago.

// Ordinals
fmt.Printf("You're my %s best friend.", humanize.Ordinal(193))
// You're my 193rd best friend.

// Thousands separators
fmt.Printf("You owe $%s.\n", humanize.Comma(6582491))
// You owe $6,582,491.
```

`humanize.Time()` is the workhorse: hand it a `time.Time` and it picks the right phrasing for the distance, from "just now" through "7 hours ago" to an absolute date for anything more than a month old. There is also `humanize.SI(0.00000000223, "M")`, which returns `2.23 nM` — useful for scientific dashboards where hand-writing prefix logic is a waste of an afternoon.

**Verdict:** if your service is written in Go, this is not a close call. It is the most complete, most maintained option, and its API is stable enough that upgrade risk is negligible.

## timeago.js — Two Kilobytes That Do One Thing

`timeago.js` carries **5,366 stars** and was last updated **2026-06-30**. It is a nano library — the project advertises **under 2 KB** — that converts a date into a relative-time string. That is the entire feature set, and the size is the point.

```bash
npm install timeago.js
```

Import the four functions it exports and format a timestamp:

```ts
import { format, render, cancel, register } from 'timeago.js';

// format the time with a locale
format('2016-06-12', 'en_US');   // "3 years ago"
```

For live feeds — comments, activity streams, notification lists — `render()` scans the DOM for elements carrying a datetime attribute and updates them, then re-checks on an interval:

```html
<time class="timeago" datetime="2026-10-06T12:00:00Z"></time>

<script src="//unpkg.com/timeago.js"></script>
<script>
  timeago.render(document.querySelectorAll('.timeago'));
  // call timeago.cancel() when the component unmounts
</script>
```

The library also ships localized strings; `register('zh_CN', myLocale)` lets you add or override a language pack. It includes the usual set out of the box, so most projects never touch `register` at all.

**Verdict:** the correct default for frontend relative timestamps. Reach for it before writing your own `timeAgo()` helper — that helper is always longer than 2 KB and always has a bug at the "yesterday" boundary.

## python-humanize — Numbers and Dates in One Import

`python-humanize` was last pushed on **2026-10-06** — the freshest commit in this comparison — and sits at **761 stars** under the MIT license. Its breadth is its selling point: it humanizes integers, floats, file sizes, dates, times, and lists.

```bash
python3 -m pip install --upgrade humanize
```

Number formatting is the entry point, and the README examples are short enough to memorize:

```pycon
>>> import humanize
>>> humanize.intcomma(12345)
'12,345'
>>> humanize.intword(123455913)
'123.5 million'
>>> humanize.intword(12345591313)
'12.3 billion'
>>> humanize.apnumber(4)
'four'
>>> humanize.apnumber(41)
'41'
```

Date and time humanization lives in the same module and covers the phrasing that is otherwise annoying to get right:

```pycon
>>> import humanize, datetime as dt
>>> humanize.naturalday(dt.datetime.now())
'today'
>>> humanize.naturaldelta(dt.timedelta(seconds=1001))
'16 minutes'
>>> humanize.naturalday(dt.datetime.now() - dt.timedelta(days=1))
'yesterday'
>>> humanize.naturaltime(dt.datetime.now() - dt.timedelta(seconds=3600))
'an hour ago'
```

Note `intword(12345591313)` returning `12.3 billion` rather than a raw integer: that single function replaces the custom `format_big_number()` helper that otherwise gets copy-pasted across five services.

**Verdict:** the default for Python web apps and dashboards, especially Django templates where a one-line filter beats a custom utility module.

## humantime — Fast Durations for Rust

`humantime` sits at **398 stars**, was last updated **2026-07-13**, and is licensed **Apache-2.0**. It does two things: parse and format durations, and parse and format RFC 3339 timestamps. The README describes the duration format as free-form — `15days 2min 2s` parses, and output looks like `2years 2min 12us`.

Install it as a normal crate dependency:

```toml
[dependencies]
humantime = "2"
```

Formatting a `Duration` into compact human text:

```rust
use std::time::Duration;
use humantime::format_duration;

fn main() {
    let d = Duration::from_secs(3200);
    println!("{}", format_duration(d));   // 53m 20s
}
```

And parsing a user-supplied config value back into a typed `Duration`:

```rust
use humantime::parse_duration;

fn main() {
    let d = parse_duration("15days 2min 2s").unwrap();
    println!("{}", d.as_secs());   // 1297322
}
```

The README also documents RFC 3339 handling — `humantime::format_rfc3339(SystemTime::now())` produces `2018-01-01T12:53:00Z`, and the crate advertises nanosecond precision plus micro-benchmarks in the tens-of-nanoseconds range for the fixed-format paths. Timestamp parsing is fast precisely because the format is fixed, which is a fair trade for log processing.

**Verdict:** the right Rust crate when you need both directions — formatting for display and parsing for configuration. If you only need "3 hours ago" in Rust, check `chrono-humanize` first, since it targets relative time specifically.

## Pitfalls and Gotchas

**Relative time is not a substitute for a timestamp.** "3 hours ago" is unreadable to a screen reader and unindexable by search engines. Always render the absolute date in a `<time datetime="...">` attribute — that is exactly what `timeago.js`'s `render()` expects, and it doubles as machine-readable markup.

**Rounding is where these libraries disagree.** `humantime` prints compact forms like `53m 20s`; `python-humanize` writes `16 minutes`; `timeago.js` says `3 hours ago`. If a test asserts an exact string, pin the library version and expect breakage on upgrade. Assert on structure, not on the literal phrase.

**Time zones silently corrupt relative times.** `humanize.Time()` and `naturaltime()` compute distance from *now*, so a naive timestamp interpreted in the wrong zone produces "in 5 hours" for an event that just happened. Normalize to UTC at the boundary and only humanize at the last moment before rendering.

**Locale coverage is uneven.** `timeago.js` ships language packs; `go-humanize` and `humantime` are English-only by design. A multilingual product should plan for a translation layer rather than assuming the library will handle it.

**Don't humanize data you will sort or compare.** Rounding `87342199` to `83 MB` is fine for display; it is a correctness bug if that string ever reaches a database column, a sort key, or an API filter.

**The stale-fork trap in Python.** Installing from a GitHub URL that points at the archived `jmoiron/humanize` repository gets you a 2022 codebase. Use the PyPI package name and let the index resolve to the maintained repository.

## Where This Fits in a Self-Hosted Stack

Formatting libraries are the presentation layer of observability and admin UIs: file managers, log viewers, activity feeds, and storage dashboards all live or die on whether the numbers make sense at a glance. If you are building that layer, our comparison of [Rust datetime libraries — chrono, jiff, time and hifitime](../2026-09-21-rust-datetime-libraries-chrono-jiff-time-hifitime-comparison/) covers the type systems these formatters sit on, and the [Python datetime libraries guide covering arrow, pendulum and dateutil](../2026-08-10-python-datetime-libraries-arrow-pendulum-dateutil/) explains the parsing side for Python services.

On the client, the choice of date engine determines how much work your formatter has to do — the [JavaScript datetime libraries comparison: Day.js, Luxon, date-fns and js-joda](../2026-07-14-javascript-datetime-libraries-dayjs-luxon-datefns-jsjoda/) is the natural companion to `timeago.js`. And for the parsing edge cases that break every formatter at least once, see the [self-hosted datetime parsing libraries guide](../2026-06-20-self-hosted-datetime-parsing-libraries-dateparser-chrono-jodatime-dateutil/).

A sane default stack: parse and store UTC, format typed values with `go-humanize` or `python-humanize` on the server, and let `timeago.js` handle only the "3 hours ago" layer in the browser.

## FAQ

**Which library should I use to format file sizes?**

For Go, `humanize.Bytes()` in `go-humanize` converts a byte count straight into `83 MB`. In Python, `humanize.naturalsize()` does the same job, including decimal and binary unit modes. In JavaScript, no single library here covers bytes — `timeago.js` is relative-time only — so use `pretty-bytes` or `filesize` alongside it. The Rust crate `humansize` fills the equivalent niche.

**Is timeago.js still maintained in 2026?**

Yes. The repository received commits as recently as **2026-06-30** and the library remains the standard sub-2 KB option for relative timestamps. Its age is a feature: the API has been stable for years, so upgrading is a non-event. The companion React package `timeago-react` covers component-based usage.

**Why does python-humanize have fewer stars than the old repository?**

Because the project migrated organizations. The original `jmoiron/humanize` repository (1,704 stars) has been frozen since **2022-07-17**, while active development continues at `python-humanize/humanize` (761 stars, pushed **2026-10-06**). Star counts accumulate over a repository's life, so the newer home shows fewer — it does not indicate less activity.

**Can humantime parse arbitrary duration strings?**

It parses free-form durations such as `15days 2min 2s`, `2years`, and combinations of the two, along with RFC 3339 timestamps. That flexibility is unusual; most formatters in this comparison only format and cannot parse back. It is the reason `humantime` shows up in config loaders and CLI argument parsers despite having the smallest star count here.

**Should I format relative times on the server or the client?**

On the client, whenever the value must stay accurate as the page stays open. A server-rendered "3 hours ago" is wrong the moment the user leaves the tab open overnight. Render an absolute timestamp into the `<time>` element on the server, then let `timeago.js` `render()` refresh it in place — you get correct machine-readable markup and correct human text at the same time.

**Do these libraries handle localization?**

`timeago.js` does, with bundled locale packs and a `register()` function for custom ones. `python-humanize` installs translations with the package and follows the active locale. `go-humanize` and `humantime` are English-only by design, so a multilingual Go or Rust product needs its own translation layer on top.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Human-Readable Formatting Libraries in 2026: go-humanize vs timeago.js vs python-humanize vs humantime",
  "description": "Comparison of open-source human-readable formatting libraries for Go, JavaScript, Python and Rust, covering byte sizes, relative time, ordinals and duration parsing.",
  "datePublished": "2026-10-06",
  "dateModified": "2026-10-06",
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
