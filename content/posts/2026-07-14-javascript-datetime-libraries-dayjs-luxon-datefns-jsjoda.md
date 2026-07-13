---
title: "JavaScript Date/Time Library Comparison: Day.js vs Luxon vs date-fns vs js-joda"
date: "2026-07-14"
tags: ["javascript", "date-time", "dayjs", "luxon", "date-fns", "npm", "frontend"]
draft: false
---

Working with dates and times in JavaScript has a notorious reputation. The native `Date` object, introduced in ECMAScript 1, is mutable, has an inconsistent API, and lacks basic functionality like timezone manipulation or date arithmetic. Over the years, a rich ecosystem of third-party libraries has emerged to fill these gaps. In this article, we compare four of the most popular JavaScript date/time libraries — **Day.js**, **Luxon**, **date-fns**, and **js-joda** — examining their APIs, bundle sizes, timezone support, and ideal use cases.

## Quick Comparison

| Feature | Day.js | Luxon | date-fns | js-joda |
|---------|--------|-------|----------|---------|
| **GitHub Stars** | ~48K | ~15K | ~35K | ~1.6K |
| **Bundle Size (min+gzip)** | ~2KB | ~15KB | Tree-shakable (~2-5KB per function) | ~43KB |
| **Immutability** | Yes (chain + clone) | Yes | Yes (pure functions) | Yes |
| **Timezone Support** | Plugin (`timezone`) | Built-in (via Intl) | Companion (`date-fns-tz`) | Built-in (via `@js-joda/timezone`) |
| **Tree Shaking** | Plugin-based | Limited | Full (function-level) | Limited |
| **Moment.js Compatible** | Yes (API-aligned) | No (successor) | No | No (JSR-310 inspired) |
| **Parsing** | `dayjs(str)` | `DateTime.fromISO()` etc. | `parse(str, format, ref)` | `LocalDate.parse(str)` |
| **i18n** | Plugin | Built-in (Intl) | Import locale | Built-in |

## Day.js: The Lightweight Moment.js Replacement

Day.js has become the most popular date library in the JavaScript ecosystem by executing a simple strategy: replicate Moment.js's API with a 2KB immutable core and a robust plugin system. If you're migrating from Moment.js (which is now in maintenance mode), Day.js is the closest drop-in replacement.

### Installation and Basic Usage

```bash
npm install dayjs
```

```javascript
import dayjs from 'dayjs';

// Basic date creation and formatting
const now = dayjs();
console.log(now.format('YYYY-MM-DD HH:mm:ss')); // 2026-07-14 10:30:00

// Immutable operations — each method returns a new instance
const nextWeek = now.add(7, 'day');
console.log(now.format('YYYY-MM-DD'));  // Still 2026-07-14
console.log(nextWeek.format('YYYY-MM-DD')); // 2026-07-21

// Relative time with plugin
import relativeTime from 'dayjs/plugin/relativeTime';
dayjs.extend(relativeTime);
console.log(dayjs('2026-07-10').fromNow()); // "4 days ago"
```

### Plugin Ecosystem

Day.js's power comes from its plugins. You only load what you need, keeping bundle size minimal:

```javascript
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import timezone from 'dayjs/plugin/timezone';
import customParseFormat from 'dayjs/plugin/customParseFormat';
import advancedFormat from 'dayjs/plugin/advancedFormat';

dayjs.extend(utc);
dayjs.extend(timezone);
dayjs.extend(customParseFormat);
dayjs.extend(advancedFormat);

// Parse custom formats
const d = dayjs('14/07/2026', 'DD/MM/YYYY');

// Timezone conversion
console.log(dayjs().tz('America/New_York').format('HH:mm'));
console.log(dayjs().tz('Asia/Shanghai').format('HH:mm'));

// Ordinal formatting
console.log(dayjs().format('Do [of] MMMM')); // "14th of July"
```

### Pros and Cons

**Pros:**
- Tiny 2KB core — ideal for performance-sensitive applications
- Drop-in Moment.js replacement for most use cases
- 30+ official plugins covering i18n, timezone, duration, calendar, and more
- Mature, well-maintained with 48K+ GitHub stars

**Cons:**
- Plugins are globally registered via `dayjs.extend()`, which can cause issues in multi-package monorepos
- Timezone plugin requires the full IANA database, adding ~30KB
- Some edge cases in custom format parsing differ from Moment.js

## Luxon: The Modern Successor

Luxon was created by Isaac Cambron, a maintainer of Moment.js, as a clean-slate implementation leveraging modern JavaScript features. It wraps the `Intl.DateTimeFormat` API for timezone and locale support, meaning it doesn't ship its own timezone data.

### Installation and Usage

```bash
npm install luxon
```

Luxon's API is class-based and explicitly different from Moment.js. Dates are created through named factory methods rather than a single constructor:

```javascript
import { DateTime, Duration, Interval } from 'luxon';

// Explicit creation methods — no guessing
const now = DateTime.now();
const fromISO = DateTime.fromISO('2026-07-14T10:30:00');
const fromFormat = DateTime.fromFormat('14/07/2026', 'dd/MM/yyyy');
const fromJSDate = DateTime.fromJSDate(new Date());

// Timezone support via Intl — no extra data required
const ny = DateTime.now().setZone('America/New_York');
const tokyo = DateTime.now().setZone('Asia/Tokyo');

console.log(ny.toFormat('yyyy-MM-dd HH:mm:ss ZZZZ'));
// "2026-07-13 22:30:00 Eastern Daylight Time"

// Duration arithmetic
const dur = Duration.fromObject({ hours: 3, minutes: 45 });
console.log(now.plus(dur).toISO());

// Date intervals
const start = DateTime.fromISO('2026-07-01');
const end = DateTime.fromISO('2026-07-14');
const interval = Interval.fromDateTimes(start, end);
console.log(interval.length('days')); // 13
```

### Key Differentiators

Luxon's biggest advantage is **native timezone support without additional data**. Since it uses `Intl.DateTimeFormat`, timezone names and offsets come from the browser or Node.js runtime. This is both a strength and a limitation — you rely on the runtime's ICU data, which is usually excellent in modern browsers but may be incomplete in some server environments.

### Pros and Cons

**Pros:**
- Built-in timezone support via Intl — no extra data payload
- Clean, explicit API with named factory methods
- Robust `Duration` and `Interval` classes for date math
- Created by a Moment.js maintainer with deep domain knowledge

**Cons:**
- Larger bundle (~15KB min+gzip) compared to Day.js
- Relies on runtime Intl support (limited in React Native and some older browsers)
- Not API-compatible with Moment.js — requires a full migration

## date-fns: The Functional Toolkit

date-fns takes a fundamentally different approach: instead of a monolithic date object, it provides 200+ pure, tree-shakeable functions. Each function takes a date as input and returns a new value, making it naturally immutable and functional-programming friendly.

### Installation and Usage

```bash
npm install date-fns
```

```javascript
import { format, addDays, differenceInDays, parseISO } from 'date-fns';

// Functional — no mutation, no chaining
const today = new Date(2026, 6, 14);
const nextWeek = addDays(today, 7);
console.log(format(nextWeek, 'yyyy-MM-dd')); // "2026-07-21"

// Date math
const start = parseISO('2026-07-01');
const end = parseISO('2026-07-14');
console.log(differenceInDays(end, start)); // 13

// Tree-shaking: only imported functions are bundled
// import { format } from 'date-fns' adds only ~2KB
```

### Timezone Handling

date-fns itself does not include timezone support. You use the companion package `date-fns-tz`:

```javascript
import { format, utcToZonedTime, zonedTimeToUtc } from 'date-fns-tz';

const pattern = "yyyy-MM-dd HH:mm:ssXXX";
const timeZone = 'America/New_York';

// Convert UTC to a zoned time
const zonedDate = utcToZonedTime(new Date('2026-07-14T14:30:00Z'), timeZone);
console.log(format(zonedDate, pattern, { timeZone }));
// "2026-07-14 10:30:00-04:00"

// Convert zoned time back to UTC
const utcDate = zonedTimeToUtc('2026-07-14 10:30:00', timeZone);
console.log(utcDate.toISOString());
// "2026-07-14T14:30:00.000Z"
```

### Ecosystem

date-fns shines with its ecosystem of specialized packages:
- **date-fns-tz**: IANA timezone support
- **date-fns/locale**: 50+ locale packages for i18n formatting
- **date-fns/fp**: Curried functional programming variants of all functions

### Pros and Cons

**Pros:**
- Tree-shakeable — you only pay for what you import
- Pure functions compatible with React, Redux, and functional patterns
- Largest feature set: 200+ functions covering nearly every date operation
- Active maintenance with regular releases

**Cons:**
- Verbose for complex date chains — no fluent API
- Timezone support requires a separate companion package
- Functions expect native `Date` objects (mutable input, immutable output)

## js-joda: Java's JSR-310 for JavaScript

js-joda is a JavaScript port of Java's `java.time` (JSR-310) API. It provides a comprehensive, immutable date/time library with classes like `LocalDate`, `LocalTime`, `LocalDateTime`, `ZonedDateTime`, `Duration`, and `Period`. If you come from a Java or Kotlin background, this API will feel immediately familiar.

### Installation and Usage

```bash
npm install js-joda
npm install @js-joda/timezone  # For timezone support
```

```javascript
import { LocalDate, LocalDateTime, ZonedDateTime, ZoneId, ChronoUnit } from 'js-joda';
import '@js-joda/timezone';

// Create dates — no "just parse" convenience; explicit API
const today = LocalDate.now();
const birthday = LocalDate.of(2026, 7, 14);

// Date arithmetic
const nextWeek = today.plusDays(7);
const daysBetween = today.until(birthday, ChronoUnit.DAYS);

// Timezone handling
const zdt = ZonedDateTime.now(ZoneId.of('America/New_York'));
console.log(zdt.toString()); // "2026-07-13T22:30:00-04:00[America/New_York]"

// Formatting requires an explicit formatter
import { DateTimeFormatter } from 'js-joda';
const fmt = DateTimeFormatter.ofPattern('yyyy-MM-dd HH:mm:ss');
console.log(zdt.format(fmt));
```

### JSR-310 Design Philosophy

The JSR-310 design is intentionally strict. Unlike JavaScript's `Date` or Moment.js, js-joda:
- Has **separate types** for date-only, time-only, and date-time values
- Uses **explicit constructors** and factory methods (no "guess the format")
- Treats all values as **immutable**
- Requires an **explicit formatter** for parsing and string conversion

This rigor prevents entire categories of bugs — you can't accidentally compare a date to a datetime, or mutate a value that another part of the code depends on.

### Pros and Cons

**Pros:**
- Rigorous type system catches errors at compile time (TypeScript) or logically
- Fully compliant with the proven JSR-310 specification
- Excellent timezone support via the official `@js-joda/timezone` package
- Comprehensive API covering all date/time concepts

**Cons:**
- Largest bundle size (~43KB min+gzip)
- Verbose API — more code to write for simple operations
- Steep learning curve for developers unfamiliar with JSR-310
- Smaller community compared to Day.js or date-fns

## Choosing the Right Library

| Use Case | Recommended Library |
|----------|-------------------|
| Migrating from Moment.js with minimal changes | Day.js |
| Heavy timezone manipulation in modern browsers/Node.js | Luxon |
| Tree-shaking, functional patterns, or React ecosystem | date-fns |
| Java/Kotlin background or strict type safety | js-joda |
| Minimal bundle size constraint (~2KB) | Day.js |
| Server-side with reliable Intl support | Luxon |

For a deeper look at JavaScript tooling, see our [JavaScript build bundlers guide](../2026-06-21-javascript-build-bundlers-esbuild-rollup-parcel-swc-turbopack/) and our [JavaScript state management comparison](../2026-07-05-javascript-state-management-redux-zustand-jotai-mobx-pinia/).

## FAQ

### Which library is the best replacement for Moment.js?

Day.js is the closest drop-in replacement with an almost identical API. If you need more modern features like native timezone support and are willing to rewrite your date handling code, Luxon (created by a Moment.js maintainer) is the recommended upgrade path.

### Does date-fns mutate dates like Moment.js?

No. date-fns uses pure functions that never modify the input. Every function returns a new value. This is one of its main advantages over Moment.js and native `Date`.

### Can I use these libraries in Node.js?

Yes, all four libraries work in Node.js (v12+). Luxon relies on the `Intl` API which is available in Node.js 13+ (full ICU support in v14+). js-joda works in all environments since it includes its own timezone data.

### How do I handle recurring events (e.g., "every 2 weeks on Friday")?

None of these libraries handle recurrence natively. For recurring events, consider using `rrule` (RFC 5545) — the `rrule` package on npm handles all iCalendar recurrence rules and integrates well with all four date libraries by accepting native `Date` objects.

### Does tree-shaking actually reduce bundle size with date-fns?

Yes. In a typical React application that imports ~8 date-fns functions, you'll add only 2-5KB to your final bundle. Compare this to Moment.js (~72KB) or Luxon (~15KB), and the difference is substantial. However, ensure your bundler (Webpack, Rollup, esbuild, or Vite) is configured for tree-shaking.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "JavaScript Date/Time Library Comparison: Day.js vs Luxon vs date-fns vs js-joda",
  "description": "Comprehensive comparison of JavaScript date/time libraries — Day.js, Luxon, date-fns, and js-joda — with code examples, bundle size analysis, timezone support comparison, and migration guidance.",
  "datePublished": "2026-07-14",
  "dateModified": "2026-07-14",
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
