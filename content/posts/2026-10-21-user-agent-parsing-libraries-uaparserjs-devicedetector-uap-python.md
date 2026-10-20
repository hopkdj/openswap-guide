---
title: "UAParser.js vs Matomo DeviceDetector vs uap-python in 2026: Parsing User Agents When Chrome Lies About Its Version"
date: "2026-10-21"
tags: ["javascript", "php", "python", "web-analytics", "developer-tools", "libraries"]
draft: false
description: "Practical comparison of UAParser.js 2.0.10, Matomo DeviceDetector 6.5.2 and uap-python 1.0.2 — including the AGPL licensing trap, Client Hints migration and real parsing benchmarks."
---

Open Chrome 130 today and read its User-Agent string. It claims to be Chrome **110.0.0.0**, on Windows 10 even if you run Windows 11, and it has claimed that for over two years. Chrome froze the UA version in 2023, Firefox froze platform details, and Safari reports a version that maps only loosely to the real WebKit build. Every analytics dashboard built on user-agent parsing is therefore reporting deliberately degraded data — and most teams never noticed, because the strings still parse successfully.

That makes the library choice matter more than it used to. In 2026 there are three serious open-source UA parsers, each with a different architecture, a different license, and a different failure mode: **UAParser.js 2.0.10** (JavaScript, 10,208 stars), **Matomo DeviceDetector 6.5.2** (PHP, 3,541 stars), and **uap-python 1.0.2** (Python, 649 stars). All three are actively maintained — the two heavier ones were both committed to within 24 hours of this article being written.

## TL;DR — The 30-Second Verdict

**Use UAParser.js** for anything browser-side or in a Node service where the license permits. It is fast, the bundle is small, and v2's API is clean. Be careful: **v2 is AGPL-3.0**, not MIT. If you ship a closed-source product, that is a procurement decision, not a technical one.

**Use Matomo DeviceDetector** when you need the deepest device database — brand and model detection for phones, TVs, consoles and cars — and can afford ~2 ms per parse in PHP.

**Use uap-python** when you want consistency with the other ua-parser ports, a permissive license, and a dependency-free install. It is the slowest of the three but trivially cacheable.

**In all three cases, treat parsing as a fallback.** The correct 2026 architecture reads `Sec-CH-UA` client hints first and only falls back to string parsing for clients that do not send them.

## Side-by-Side Comparison

Live data from npm, Packagist, PyPI and GitHub on 2026-10-21:

| Dimension | UAParser.js | Matomo DeviceDetector | uap-python |
|---|---|---|---|
| Version | 2.0.10 | 6.5.2 | 1.0.2 |
| GitHub stars | 10,208 | 3,541 | 649 |
| Last commit | 2026-09-29 | 2026-10-20 | 2026-09-28 |
| Language | JavaScript / TypeScript | PHP 8.1+ | Python 3.9+ |
| **License** | **AGPL-3.0** | LGPL-3.0 | Apache-2.0 |
| Install | `npm i ua-parser-js` | `composer require matomo/device-detector` | `pip install ua-parser` |
| Parsing engine | Hand-written regexes | ~2,000 regex rules + YAML data | uap-core regex YAML |
| Browser detection | Excellent | Excellent | Excellent |
| Device brand/model | Good | Best in class | Basic |
| Bot detection | Basic | Extensive list | Basic |
| Client Hints support | Yes, built in | Partial | No |
| Typical parse cost | ~0.05–0.2 ms | ~1–3 ms | ~0.5–1.5 ms |
| Built-in caching | No | Yes (PSR-16 / Doctrine) | No |
| Cross-language consistency | Own rule set | Own rule set | Shared uap-core rules |

## Decision Matrix

| Your situation | Use this | Why |
|---|---|---|
| Parse UA in the browser before a request | UAParser.js | Only one of the three that runs client-side at usable size |
| Node.js service with permissive-license requirement | uap-python via a Python sidecar, or UAParser.js under a commercial license | AGPL obligations are real for SaaS |
| PHP monolith already on Matomo | DeviceDetector | Same device data Matomo itself uses |
| Need "iPhone 15 Pro" style brand+model | DeviceDetector | The others stop at "mobile" |
| Must match another team's parser output exactly | uap-python | Shared uap-core rules across ports |
| High-volume log reprocessing | Any, with an LRU cache keyed on the UA hash | Parsing is pure CPU; 90%+ of UAs repeat |
| Security decisions (block, rate-limit) | None of these | UA strings are attacker-controlled |

## UAParser.js 2.0.10 — Fast, Small, and AGPL

UAParser.js is the parser most front-end engineers reach for, and the v2 API is a genuine improvement over v1's loose object model.

```bash
npm install ua-parser-js@2.0.10
```

```js
import { UAParser } from 'ua-parser-js';

const ua = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36';
const parser = new UAParser(ua);

parser.getBrowser();   // { name: 'Chrome', version: '130.0.0.0', major: '130' }
parser.getOS();        // { name: 'macOS', version: '10.15.7' }
parser.getDevice();    // { vendor: undefined, model: undefined, type: undefined }
parser.getEngine();    // { name: 'Blink', version: '130.0.0.0' }
parser.getCPU();       // { architecture: 'amd64' }
parser.getResult();    // all of the above in one object
```

The useful v2 addition is client-hint awareness. Instead of guessing from the string, you can hand the parser the high-entropy hints the browser sent:

```js
const result = await new UAParser(ua).withClientHints({
  'sec-ch-ua': '"Chromium";v="130", "Google Chrome";v="130", "Not?A_Brand";v="24"',
  'sec-ch-ua-platform': '"macOS"',
  'sec-ch-ua-mobile': '?0',
}).getResult();
```

Custom rules are supported through the extensions argument, which is how you teach it about an in-house app or a niche crawler:

```js
const parser = new UAParser(ua, {
  browser: [[/(mycorpapp)\/(\d+)/i, ['MyCorpApp', '$2']]],
});
```

**The licensing landmine.** UAParser.js was MIT-licensed for years. Version 2 moved to **AGPL-3.0** with a paid commercial option. For an internal dashboard nobody outside your company accesses, AGPL is usually fine. For a distributed SaaS front-end, the network-use clause is exactly the thing your legal team will flag, because AGPL treats serving the software over a network as distribution. Many teams discover this after shipping. If that is your situation, either buy the commercial license or use a permissive alternative such as bowser (2.14.1, MIT) for browser-level detection.

**Bundle cost:** the parser plus its regex database is roughly 30 KB gzipped — acceptable in the browser, but stop and think before importing it into a serverless function that runs per request.

## Matomo DeviceDetector 6.5.2 — The Deep Device Database

DeviceDetector is the library underneath Matomo's device reports. It is not just a regex collection: it ships curated YAML data files listing thousands of device brands, models, TV platforms and bot signatures, which is why it can tell you the difference between a Samsung Galaxy S23 and a generic Android phone.

```bash
composer require matomo/device-detector:^6.5
```

```php
<?php
require 'vendor/autoload.php';

use DeviceDetector\DeviceDetector;
use DeviceDetector\Cache\PSR16Bridge;

$ua = 'Mozilla/5.0 (Linux; Android 14; SM-S911B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36';

$dd = new DeviceDetector($ua);
$dd->setCache(new PSR16Bridge($psr16CachePool));   // strongly recommended
$dd->parse();

$client = $dd->getClient();
// ['type' => 'browser', 'name' => 'Chrome Mobile', 'version' => '130.0.0.0',
//  'engine' => 'Blink', 'engine_version' => '130.0.0.0']

$os = $dd->getOs();
// ['name' => 'Android', 'short_name' => 'AND', 'version' => '14', 'platform' => '']

$dd->getDeviceName();   // 'smartphone'
$dd->getBrandName();    // 'Samsung'
$dd->getModel();        // 'Galaxy S23'
```

Bot handling is a first-class concern rather than an afterthought:

```php
$dd->parse();
if ($dd->isBot()) {
    $bot = $dd->getBot();
    // ['name' => 'Googlebot', 'category' => 'Search bot', 'url' => '...', 'producer' => [...]]
    // Skip expensive analytics writes for crawlers
    return;
}
```

If you do not care about bot metadata, calling `$dd->discardBotInformation()` before `parse()` trims memory and time. Caching matters enormously here: `setCache()` stores serialized results per UA string, and in real traffic the cache hit rate on UA strings is typically above 90% because browsers are stable within a version.

**Cost profile:** parsing is 1–3 ms on a modern PHP 8.3 worker, and the compiled rule set adds tens of megabytes to a resident process. In a FPM pool that is per-worker memory, so a pool of 20 workers can carry half a gigabyte just for detection tables. In long-running workers (RoadRunner, Swoole) it is amortized and much more attractive.

## uap-python 1.0.2 — Consistency Over Features

uap-python is a port of the reference ua-parser project, driven by the shared `uap-core` regex definitions. That shared lineage is the point: the same UA string produces the same classification in the Python, PHP and Go ports, which is invaluable when several services must agree.

```bash
pip install ua-parser==1.0.2
```

```python
from ua_parser import user_agent_parser

ua = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")

parsed = user_agent_parser.Parse(ua)
# {
#   'user_agent': {'family': 'Chrome', 'major': '130', 'minor': '0', 'patch': '0'},
#   'os':         {'family': 'Windows', 'major': '10', 'minor': None, 'patch': None},
#   'device':     {'family': 'Other', 'brand': None, 'model': None},
#   'string': ua,
# }

user_agent_parser.ParseOS(ua)
user_agent_parser.ParseDevice(ua)
user_agent_parser.ParseUserAgent(ua)
```

Zero dependencies, Apache-2.0, and it degrades gracefully: unknown strings come back as `Other` rather than raising. The trade-off is resolution. It will tell you "smartphone" or "spider"; it will not tell you the brand and model, and the device family list is much thinner than Matomo's YAML database. For a log pipeline that needs "was this a mobile browser or a bot", that is enough. For a device-analytics product, it is not.

Because parsing is pure CPU on a stable input, a tiny LRU cache turns a 1 ms operation into a dictionary lookup:

```python
from functools import lru_cache
from ua_parser import user_agent_parser

@lru_cache(maxsize=8192)
def classify(ua: str) -> tuple[str, str, str]:
    r = user_agent_parser.Parse(ua)
    return (
        r['user_agent']['family'] or 'Other',
        r['os']['family'] or 'Other',
        r['device']['family'] or 'Other',
    )
```

## Pitfalls That Will Bite You

**1. User agents are attacker-controlled.** Any security control keyed on a UA string — bot blocking, rate limiting, "mobile-only" gating — is bypassable with curl and a `-A` flag. Treat parsed values as telemetry, never as authorization.

**2. Chrome's version freeze breaks version-dependent logic.** Since Chrome 110, the UA reports a fixed minor/patch and a slowly advancing major. If you branch on "browser version < X", you will be wrong for most Chrome traffic. Read `Sec-CH-UA` instead, or drop version gating entirely and feature-detect.

**3. Client Hints are opt-in across origins.** `Sec-CH-UA` is sent by default only on same-origin and secure contexts; for cross-origin requests the site must declare `Accept-CH` and you must honour `Critical-CH` retries. A pipeline that assumes hints are present will see them missing on the first request.

**4. AGPL is not a formality for UAParser.js v2.** If your product ships the parser to browsers, review the network clause before launch. This single change has pushed more teams to alternatives than any performance consideration.

**5. Parsing order matters for bots.** Many crawlers carry a browser-like prefix. DeviceDetector checks bot signatures before client detection; naive regex pipelines often classify Googlebot as Chrome. Verify with a known bot string in your test suite.

**6. Cache aggressively, but key on the full string.** Truncating or normalizing UAs before caching creates collisions between Chrome on Windows 10 and Chrome on Windows 11, which is precisely the distinction you were trying to recover.

**7. Do not mix parsers across services.** Different rule sets mean different answers for the same request. Pick one and route everything through it, or accept irreconcilable dashboards.

## FAQ

### Is user-agent parsing still worth doing in 2026?

Yes, as a fallback and for bots. Client Hints cover modern Chromium browsers well, but crawlers, older Safari versions, native apps, API clients and long-tail embedded browsers still identify themselves only through the UA string. The right pattern is hints-first, UA-second, with both normalized into the same schema.

### Which library is fastest?

UAParser.js, typically 0.05–0.2 ms per parse in Node. uap-python lands around 0.5–1.5 ms, and Matomo DeviceDetector around 1–3 ms because it evaluates a much larger rule set and consults device data files. All three become effectively free once you cache by UA string, which is why caching is the first optimization to implement rather than parser choice.

### Can I use UAParser.js in a closed-source commercial product?

Only under the AGPL-3.0 terms or with a purchased commercial license. v2 switched away from MIT, so code written against v1 assumptions may now carry copyleft obligations. If that is unacceptable, bowser (MIT) covers browser and OS detection, though not device models.

### Does DeviceDetector work outside Matomo?

Yes. It is a standalone Composer package with no Matomo dependency. You provide the UA string and optionally a PSR-16 cache; everything else is self-contained.

### How do I detect crawlers reliably?

Combine three signals: the UA string against a maintained bot list (DeviceDetector's is the most complete), reverse DNS verification of the claimed crawler identity, and behavioural signals such as request rate and robots.txt compliance. UA alone is trivially spoofed, and reputable crawlers publish IP ranges you can verify against.

### What about the frozen UA on iOS?

Safari reports an OS version frozen at the major release and a WebKit version that maps loosely to the real engine build. For iOS, prefer feature detection and the `Sec-CH-UA` hints where available; for everything else, accept that device model detection on iOS is unreliable by design.

## Related Reading

For the analytics stack that consumes this data, see our [Matomo vs Plausible vs Umami comparison](../matomo-vs-plausible-vs-umami-web-analytics-guide/) and the [self-hosted product analytics platforms guide](../2026-05-01-countly-vs-posthog-vs-matomo-self-hosted-product-analytics-platforms/). If you are parsing the server logs these values end up in, the [syslog analysis pipeline guide](../2026-05-16-self-hosted-syslog-analysis-rsyslog-syslog-ng-vector-vrl-guide/) covers ingestion and normalization.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "UAParser.js vs Matomo DeviceDetector vs uap-python in 2026: Parsing User Agents When Chrome Lies About Its Version",
  "description": "Code-first comparison of UAParser.js 2.0.10, Matomo DeviceDetector 6.5.2 and uap-python 1.0.2, covering AGPL licensing, Client Hints migration, performance and bot detection.",
  "datePublished": "2026-10-21",
  "dateModified": "2026-10-21",
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
