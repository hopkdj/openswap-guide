---
title: "Recurrence Rule (RRULE) Libraries in 2026: rrule.js vs dateutil vs php-rrule vs rrule-go vs rust-rrule"
date: "2026-10-05"
tags: ["developer-tools", "libraries", "scheduling", "date-time", "python", "golang"]
draft: false
---

"Every second Tuesday of the month." "The last Friday before the 15th." "Weekdays, but never on holidays." If you have ever tried to express that sentence as a cron expression, you already know the pain: **cron cannot do it**. Cron handles fixed intervals, not calendar logic. The moment your product needs *"the third business day after month-end"*, you need a real recurrence engine built on **RFC 5545 RRULE** — the same standard behind iCalendar, Google Calendar, and every serious scheduling product.

This guide compares the five RRULE libraries that are actually maintained in 2026 across five languages, with live star counts, real API examples pulled from their official repositories, and the pitfalls that will bite you in production.

## Quick Verdict

If you are building in **JavaScript or TypeScript**, use **rrule.js** — it has the deepest feature set (RRuleSet, natural-language output, caching). In **Python**, use **python-dateutil** — it is the reference implementation and ships with the syntax most other tools imitate. In **PHP**, **php-rrule** is the only serious option and it is a good one. In **Go**, **rrule-go** is pragmatic and fast. In **Rust**, **rust-rrule** is the rising option, but check its iterator semantics carefully before you commit.

**Rule of thumb: if your scheduling logic has the word "except" or "every other" in it, do not reach for cron. Reach for RRULE.**

If you are still running simple periodic jobs, our [job scheduling libraries comparison](../2026-06-19-self-hosted-job-scheduling-libraries-apscheduler-robfig-cron-gocron-quartz/) and [Linux cron alternatives guide](../2026-05-23-linux-cron-job-scheduling-fcron-vs-cronie-vs-anacron-guide/) cover that layer. And when the dates that feed your rule arrive as messy strings, start with our [datetime parsing libraries roundup](../2026-06-20-self-hosted-datetime-parsing-libraries-dateparser-chrono-jodatime-dateutil/).

## The Five Libraries Compared

| Library | Language | Stars | Last Push | License | RRuleSet (union/exclude) | Natural language | Timezone/DST aware |
|---|---|---|---|---|---|---|---|
| [rrule.js](https://github.com/jkbrzt/rrule) | JS / TS | 3,742 | active 2026 | BSD-3 | Yes (full `RRuleSet`) | Yes (`toText()`) | Yes (`tzid` option) |
| [python-dateutil](https://github.com/dateutil/dateutil) | Python | 2,638 | 2026-09-26 | Apache-2.0 / BSD-3 | Yes (`rruleset`, `rrule`) | No | Yes (`tzinfo`) |
| [php-rrule](https://github.com/rlanvin/php-rrule) | PHP | 711 | active 2026 | MIT | Yes (`RRuleSet`) | Yes (`humanReadable()`) | Yes (via `DateTimeZone`) |
| [rrule-go](https://github.com/teambition/rrule-go) | Go | 383 | active 2026 | MIT | Yes (`Set`) | No | Partial (fixed offsets) |
| [rust-rrule](https://github.com/fmeringdal/rust-rrule) | Rust | 95 | active 2026 | MIT | Partial | No | Yes (via `chrono-tz`) |

Numbers pulled live from the GitHub API at publish time. Star count is not a quality score — it is a proxy for "how many people will answer your Stack Overflow question."

## Use-Case Decision Matrix

| Your situation | Pick | Why |
|---|---|---|
| Generating calendar-style schedules in a browser | **rrule.js** | Ships as an ES module, tree-shakeable, and can render human-readable text for previews |
| Backend batch job that computes next runs on a schedule | **python-dateutil** | `rrulestr()` parses RFC 5545 strings directly; no hand-built option objects |
| PHP SaaS with recurring billing or bookings | **php-rrule** | Composer install, immutable objects, clean `RRuleSet` exclusions |
| High-throughput Go service scheduling reminders | **rrule-go** | Iterator-based API avoids allocating full date lists |
| Rust service where correctness and zero-cost abstractions matter | **rust-rrule** | Native `Iterator` implementation, integrates with `chrono` |

## rrule.js — The Reference JavaScript Implementation

Install:

```bash
npm install rrule
# or
yarn add rrule
```

The core API builds a rule from a plain options object. This example — straight from the project README — produces **every fifth week, on Monday and Friday**, five times:

```js
import { RRule } from 'rrule';

const rule = new RRule({
  freq: RRule.WEEKLY,
  interval: 5,
  byweekday: [RRule.MO, RRule.FR],
  dtstart: new Date(Date.UTC(2026, 1, 1, 10, 30)),
  count: 5
});

console.log(rule.all());
console.log(rule.toText()); // "every 5 weeks on Monday and Friday"
```

What makes rrule.js stand out is **`RRuleSet`**, which lets you union several rules and then subtract exceptions. This is exactly how a real booking system expresses *"every Monday, except public holidays"*:

```js
import { RRule, RRuleSet, rrulestr } from 'rrule';

const set = new RRuleSet();

// Every Monday
set.rrule(new RRule({ freq: RRule.WEEKLY, byweekday: RRule.MO, count: 10 }));

// ...plus the first of every month
set.rrule(new RRule({ freq: RRule.MONTHLY, bymonthday: 1, count: 3 }));

// ...minus a specific holiday
set.exdate(new Date(Date.UTC(2026, 11, 25)));

console.log(set.all().length);
```

The one caveat: `rule.all()` without `count` or `until` will **throw** rather than loop forever — which is a feature, not a bug. Always bound your rules.

## python-dateutil — The Reference Implementation

Install:

```bash
pip install python-dateutil
```

`dateutil.rrule` is the implementation that most other languages were ported *from*, and it is the most forgiving about input. You can build rules programmatically:

```python
from dateutil.rrule import rrule, WEEKLY, MO, FR
from datetime import datetime

rule = rrule(
    WEEKLY,
    interval=5,
    byweekday=(MO, FR),
    dtstart=datetime(2026, 2, 1, 10, 30),
    count=5,
)

for occurrence in rule:
    print(occurrence)
```

Or — far more useful in practice — parse a raw RFC 5545 string that came from a calendar client:

```python
from dateutil.rrule import rrulestr

text = "FREQ=WEEKLY;INTERVAL=5;BYDAY=MO,FR;COUNT=5"
rule = rrulestr(text, dtstart=datetime(2026, 2, 1, 10, 30))

print(rule.after(datetime(2026, 3, 1)))   # next occurrence after a date
print(list(rule)[:3])                      # first three occurrences
```

The `after()` and `before()` helpers are the ones you will actually use in production: they let a scheduler ask *"what is the next run after now?"* without materialising the whole series. The trade-off is that dateutil has **no human-readable output** — if you need "every 5 weeks on Monday" in the UI, you generate that yourself.

## php-rrule — Composer-Native Recurrence

Install:

```bash
composer require rlanvin/php-rrule
```

The API mirrors the RFC directly, which makes it easy to round-trip values that came from a front-end calendar widget:

```php
use RRule\RRule;
use RRule\RRuleSet;

$rule = new RRule([
    'FREQ' => 'WEEKLY',
    'INTERVAL' => 5,
    'BYDAY' => ['MO', 'FR'],
    'DTSTART' => new DateTime('2026-02-01 10:30:00'),
    'COUNT' => 5,
]);

foreach ($rule as $occurrence) {
    echo $occurrence->format('Y-m-d H:i:s') . PHP_EOL;
}

// Parse straight from an RFC 5545 string
$fromString = RRule::createFromRfcString('FREQ=WEEKLY;INTERVAL=5;BYDAY=MO,FR');
```

php-rrule's `RRuleSet` and its `humanReadable()` method give it feature parity with rrule.js — rare for PHP libraries, and the reason it is the default choice for PHP booking engines. Note that `humanReadable()` output is English-oriented; if you serve multiple locales you will still want your own translation layer.

## rrule-go — Iterators for High-Throughput Services

Install:

```bash
go get github.com/teambition/rrule-go
```

The Go port uses an option struct and returns an iterator, which matters when you are computing thousands of schedules per second:

```go
package main

import (
	"fmt"
	"time"

	"github.com/teambition/rrule-go"
)

func main() {
	start := time.Date(2026, 2, 1, 10, 30, 0, 0, time.UTC)

	r, err := rrule.NewRRule(rrule.ROption{
		Freq:      rrule.WEEKLY,
		Interval:  5,
		Byweekday: []rrule.Weekday{rrule.MO, rrule.FR},
		Dtstart:   start,
		Count:     5,
	})
	if err != nil {
		panic(err)
	}

	for _, d := range r.All() {
		fmt.Println(d)
	}

	// Or stream without building a slice:
	it := r.Iterator()
	for it.Next() {
		fmt.Println(it.Value())
	}
}
```

The `Iterator()` path is the one to use in services: `All()` allocates a slice for the entire series, while the iterator stops as soon as you break out of the loop. `rrule-go` also exposes `Set` for union/exclusion, though its timezone story is thinner than rrule.js — it works best when you normalise everything to UTC at the edge.

## rust-rrule — Native Iterators in the Rust Ecosystem

Install:

```bash
cargo add rrule
```

The Rust implementation leans on `chrono` types and implements `Iterator` directly:

```rust
use chrono::{TimeZone, Utc};
use rrule::{Frequency, RRule, RRuleProperties, Weekday};

fn main() {
    let start = Utc.with_ymd_and_hms(2026, 2, 1, 10, 30, 0).unwrap();

    let props = RRuleProperties {
        freq: Frequency::Weekly,
        interval: 5,
        by_weekday: vec![
            Weekday::Mon.into(),
            Weekday::Fri.into(),
        ],
        dt_start: start.into(),
        count: Some(5),
        ..Default::default()
    };

    let rule = RRule::new(props).expect("valid rule");

    for date in rule.into_iter().take(5) {
        println!("{date}");
    }
}
```

Be deliberate about which entry point you use: `RRule::new()` sets up validation, while the iterator variants differ in whether `dt_start` itself is yielded first. If your first generated date is off by one, that is the knob to check — not your timezone conversion.

## Common Pitfalls and Migration Notes

**1. DST will silently shift your wall-clock times.** `FREQ=DAILY;BYHOUR=9` should fire at 09:00 local time every day. If you build the rule in UTC with a fixed `HH:MM`, it will drift to 08:00 or 10:00 twice a year. Always anchor `DTSTART` in the target timezone (via `tzid` in rrule.js, `tzinfo` in dateutil, `DateTimeZone` in PHP, `chrono-tz` in Rust) rather than converting UTC yourself.

**2. Unbounded rules are a production incident waiting to happen.** Never call `all()` without `count` or `until`. Prefer `after()`/`before()`/`between()` so the computation is bounded by your query window.

**3. `EXDATE` removes occurrences; `RDATE` adds them.** They are not symmetric with `RRULE`. If you are storing "skipped meetings", append to `EXDATE`. If you are storing "extra one-off sessions", append to `RDATE` — never encode one-off dates by editing the base rule.

**4. `BYSETPOS` is how you express ordinals.** "Last Friday of the month" is `FREQ=MONTHLY;BYDAY=FR;BYSETPOS=-1`. Reaching for `INTERVAL` will not get you there.

**5. Migration trap.** If you are porting from cron to RRULE, there is no automatic mapping: cron's step syntax (`*/5`) has no ordinal equivalent, and RRULE's `BYDAY` semantics differ from cron's day-of-week field. Write a mapping table for your existing schedules and test both engines side by side for a full month before you cut over.

## FAQ

**Which RRULE library should I use in JavaScript?**
Use **rrule.js**. It has the most complete RFC 5545 coverage among JavaScript options, including `RRuleSet`, `EXDATE`/`RDATE`, and human-readable output through `toText()`.

**Can I use cron instead of RRULE?**
Only if your schedule is a fixed interval. Cron cannot express ordinals like "the third Tuesday" or "the last business day of the month." That is exactly the class of problem RRULE exists to solve.

**Does python-dateutil support parsing RFC 5545 strings?**
Yes. `rrulestr()` accepts a raw rule string such as `FREQ=WEEKLY;INTERVAL=5;BYDAY=MO,FR;COUNT=5` and returns a callable rule object, which makes it ideal for consuming calendar data from external clients.

**How do I exclude holidays from a recurrence rule?**
Add the dates to the rule's exclusion list: `set.exdate(...)` in rrule.js, `exdate` in dateutil and php-rrule, and the exclusion helpers on Go's `Set` and Rust's rule set. Do not try to bend `BYDAY` into expressing holidays.

**Why does my rule generate an infinite loop?**
Because you did not bound it. A rule with neither `COUNT` nor `UNTIL` is infinite by definition — most libraries expose a bounded `after()`/`before()` API specifically so you never materialise the whole series.

**How do I get "last Friday of the month" in RRULE?**
Use `BYSETPOS=-1` together with `BYDAY=FR`: `FREQ=MONTHLY;BYDAY=FR;BYSETPOS=-1`. Negative set positions count backwards from the end of the period.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Recurrence Rule (RRULE) Libraries in 2026: rrule.js vs dateutil vs php-rrule vs rrule-go vs rust-rrule",
  "description": "A practical 2026 comparison of RFC 5545 RRULE libraries across JavaScript, Python, PHP, Go and Rust, with real API examples, star counts and production pitfalls.",
  "datePublished": "2026-10-05",
  "dateModified": "2026-10-05",
  "author": { "@type": "Organization", "name": "OpenSwap Guide" },
  "publisher": {
    "@type": "Organization",
    "name": "OpenSwap Guide",
    "logo": { "@type": "ImageObject", "url": "https://hopkdj.github.io/openswap-guide/logo.png" }
  }
}
</script>

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
