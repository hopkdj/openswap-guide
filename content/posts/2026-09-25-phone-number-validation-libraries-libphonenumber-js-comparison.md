---
title: "libphonenumber vs libphonenumber-js vs phonenumbers in 2026: Which Phone Number Library Should You Actually Use?"
date: "2026-09-25"
tags: ["phone-numbers", "developer-libraries", "data-validation", "self-hosted"]
draft: false
---

Eighteen million downloads a week. That is how often just one of the JavaScript ports of Google's `libphonenumber` is pulled from npm — **18,329,388 downloads for the week of 2026-09-15 to 2026-09-21**, to be exact. Phone number parsing looks like a solved problem, right up to the moment a real user types a number from a country you did not test, and your signup form either rejects a perfectly valid number or happily stores garbage in your database.

The good news: you never need to write that code. The bad news: there are four serious libraries in this space now, they disagree about what "valid" means, and one of the most popular Swift options had its maintenance move in 2026 — a migration most tutorials still have not caught up with.

This is a practical comparison of **Google libphonenumber**, **libphonenumber-js**, **python-phonenumbers**, and **PhoneNumberKit** — what each one actually does, how big the metadata is, how fresh it stays, and which one you should put in production in 2026.

## TL;DR — the 30-second verdict

- **JVM backend (Java/Kotlin/Scala)** → use **Google libphonenumber**. It is the upstream source of truth for everyone else.
- **Node/TypeScript, browser bundles** → use **libphonenumber-js** with the `/min` bundle for client-side and the default build on the server.
- **Python services, ETL, offline data cleanup** → use **python-phonenumbers**. It is a faithful port, works fully offline, and ships a `lite` variant for memory-constrained containers.
- **iOS/Swift apps** → use **PhoneNumberKit from the `PhoneNumberKit` GitHub organization**, not the old `marmelroy/PhoneNumberKit` repository, which is now frozen at 4.3.0 and no longer receives metadata updates.

Verdict in one line: **do not regex**. Store everything as E.164, parse with a real metadata-driven library, and validate in two stages (`isPossible` then `isValid`).

## Feature and health comparison (data pulled live on 2026-09-25)

| | **libphonenumber** | **libphonenumber-js** | **python-phonenumbers** | **PhoneNumberKit** |
|---|---|---|---|---|
| Language | Java, C++, JS | TypeScript / JS | Python 3 | Swift |
| GitHub stars | 18,287 | 2,996 | 3,773 | 5,389 (legacy repo) |
| License | Apache-2.0 | MIT | Apache-2.0 | MIT |
| Last push | 2026-09-24 | 2026-06-18 | 2026-09-24 | 2026-05-25 (legacy) / 2026-09-24 (new org) |
| Distribution | Maven Central, source build | npm (`libphonenumber-js`) | PyPI (`phonenumbers`) | Swift Package Manager |
| Metadata model | Upstream generator | Rewritten metadata, smaller | Port, tracks upstream releases | Bundled resource bundle |
| Offline capable | Yes | Yes | Yes | Yes |
| Called by | Android framework since 4.0 | React/Vue form stacks | Django/Flask/FastAPI apps | iOS apps |
| Bundle trimming | N/A (JVM) | `/min`, default, `/max` builds | `phonenumberslite` package | Module size at link time |
| Best for | Servers, Android, canonical data | Web front ends, Node APIs | Python backends, batch jobs | Native iOS input and display |

Latest published versions observed while writing: **python-phonenumbers 9.0.40 on PyPI**, and `libphonenumber-js` shipping continuously on npm (the metadata is versioned independently of the package).

## Decision matrix: pick your use case

| Use case | Recommended | Why |
|---|---|---|
| Signup form in a React SPA | libphonenumber-js `/min` bundle | Smallest client payload, as-you-type formatting, no server round trip |
| Node/Express API validating inbound JSON | libphonenumber-js (default build) | Full metadata, `isValid()` plus type detection, pure TS types |
| Spring Boot / Kotlin service | libphonenumber (JVM) | Reference implementation, exact metadata parity, battle-tested |
| Python ETL cleaning a 5M-row CRM export | python-phonenumbers | Fast enough in-process, offline, `phonenumberslite` for tight memory |
| Django admin field | python-phonenumbers + form widget | `is_possible_number()` for input, `is_valid_number()` for commit |
| iOS app with a country-code picker | PhoneNumberKit (`PhoneNumberKit/PhoneNumberKit`, 5.x) | `AsYouTypeFormatter` plus `PhoneNumberTextField` UI module |
| One-off script to normalize a contact list | python-phonenumbers | `pip install phonenumbers`, zero infrastructure |
| Verifying numbers are *reachable* | None of these | They validate format + range, not existence — see the pitfalls section |

## Google libphonenumber — the upstream everyone else copies

This is where the metadata is generated. Google's library parses, formats, and validates international numbers for the Java, C++, and JavaScript worlds, and its metadata has shipped inside the Android framework since Android 4.0 (Ice Cream Sandwich). The repository was still being pushed the day before this article was written.

The JVM API is verbose but explicit — parsing is locale-aware, and you must handle `NumberParseException`:

```java
import com.google.i18n.phonenumbers.PhoneNumberUtil;
import com.google.i18n.phonenumbers.PhoneNumberUtil.PhoneNumberFormat;
import com.google.i18n.phonenumbers.Phonenumber.PhoneNumber;

PhoneNumberUtil util = PhoneNumberUtil.getInstance();

try {
    PhoneNumber number = util.parse("+1 650 253 0000", "US");
    System.out.println(util.isValidNumber(number));                 // true
    System.out.println(util.getNumberType(number));                 // FIXED_LINE_OR_MOBILE
    System.out.println(util.format(number, PhoneNumberFormat.E164));
    System.out.println(util.format(number, PhoneNumberFormat.INTERNATIONAL));
} catch (NumberParseException e) {
    // e.getErrorType() tells you exactly which of ~15 failure modes fired
}
```

Maven coordinates are `com.googlecode.libphonenumber:libphonenumber`; releases land on Maven Central frequently because the metadata regeneration is automated upstream.

Two behaviours are worth internalizing. First, `parse()` without a leading `+` depends on the region hint you pass, so the hint must come from the user's profile, not from a hardcoded default. Second, the Java library intentionally exposes both `isPossibleNumber()` and `isValidNumber()`: the first is a cheap length/prefix plausibility check, the second does full range verification.

The repository also contains a document that should be required reading before anyone writes validation logic: `FALSEHOODS.md` — a catalogue of wrong assumptions about phone numbers, from "phone numbers are unique per subscriber" to "a number always has one country". If your team argues about validation, cite that file and end the argument.

## libphonenumber-js — the right choice for web stacks

`libphonenumber-js` is not a bindings layer. It is a **rewrite** in TypeScript with its own, deliberately smaller metadata pipeline, and that is why it can ship to a browser at all.

```bash
npm install libphonenumber-js --save
```

```js
import parsePhoneNumberFromString, { isValidPhoneNumber } from 'libphonenumber-js'

// Cheap check for form validation on every keystroke
isValidPhoneNumber('+12133734253')            // true
isValidPhoneNumber('+12133734253', 'US')      // region hint version

const phoneNumber = parsePhoneNumberFromString('+12133734253')
phoneNumber.country                // 'US'
phoneNumber.countryCallingCode     // '1'
phoneNumber.nationalNumber         // '2133734253'
phoneNumber.formatInternational()  // '+1 213 373 4253'
phoneNumber.formatNational()       // '(213) 373-4253'
phoneNumber.getType()              // 'FIXED_LINE_OR_MOBILE'
```

The library exposes three builds, and picking the right one is the difference between a 20 KB and a 100 KB bundle:

```js
// 1. Smallest: possible-length metadata only (best for client-side hints)
import { parsePhoneNumberFromString } from 'libphonenumber-js/min'

// 2. Default: standard metadata, good balance for Node APIs
import parsePhoneNumberFromString from 'libphonenumber-js'

// 3. Max: includes example numbers for every region — the one to use in tests
import parsePhoneNumberFromString from 'libphonenumber-js/max'
```

The author's own guidance is refreshingly opinionated and worth following: for *input validation* on a business form, prefer `isPossible()` over `isValid()` and let the strict check happen at commit time. Rejecting a plausible number during typing because the metadata is a release behind is a worse user experience than accepting it and flagging it later.

This is the library I would default to for any Node service. It has a real TypeScript surface, it is MIT licensed, and the download volume (18M/week) means edge cases get reported fast.

## python-phonenumbers — offline, complete, boring in the best way

`python-phonenumbers` is a mechanical port of the Java code, which means **it reproduces upstream behaviour exactly**, including the metadata release cadence. Installation is a single line:

```bash
pip install phonenumbers
```

```python
import phonenumbers
from phonenumbers import geocoder, carrier, timezone

raw = "+442083661177"

num = phonenumbers.parse(raw, None)
print(phonenumbers.is_possible_number(num))   # True
print(phonenumbers.is_valid_number(num))      # True
print(phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.INTERNATIONAL))

# Where is it, and which network is it on?
print(geocoder.description_for_number(num, "en"))   # London / United Kingdom
print(carrier.name_for_number(num, "en"))
print(timezone.time_zones_for_number(num))          # ('Europe/London',)

# Normalize a messy user entry
loose = phonenumbers.parse("020 8366 1177", "GB")
print(phonenumbers.format_number(loose, phonenumbers.PhoneNumberFormat.E164))
```

Note the two-call pattern again: `is_possible_number()` before `is_valid_number()`. In Python this matters even more than in Java, because bulk normalization jobs are usually the place where a permissive first pass and a strict second pass get confused with each other.

The project also publishes **`phonenumberslite`**, a variant intended for environments where installing the full metadata package is a problem due to space or memory constraints. If you are deploying to a small container, building a Lambda-layer image, or running on constrained hardware, install `phonenumberslite` and accept the reduced feature set. Because everything is bundled locally, none of this makes outbound network calls — which is a genuine advantage if you must not leak customer phone numbers to a third-party API.

Metadata freshness is versioned with the package: the release I observed was **9.0.40**, and each release carries an upstream history file so you can see exactly which country ranges changed.

## PhoneNumberKit — Swift, with a 2026 migration trap

PhoneNumberKit is the Swift-native option, and it is the one place in this comparison where the standard advice online is now **actively wrong**.

The widely linked repository, `marmelroy/PhoneNumberKit`, carries a banner at the top of its README stating that it is **no longer maintained and frozen at 4.3.0**, with no further metadata updates. Active development moved to the **`PhoneNumberKit` GitHub organization**, split into a core package (parsing/formatting/validation, 5.0.0+) and a UI package (`PhoneNumberKitUI`, 1.0.0+) containing `PhoneNumberTextField` and the country-code picker.

If your `Package.swift` still points at the old URL, your validation data drifts a little further out of date with every release:

```swift
// Package.swift — point at the maintained organization, not the legacy repo
dependencies: [
    .package(url: "https://github.com/PhoneNumberKit/PhoneNumberKit.git", from: "5.0.0")
]
```

```swift
// The 5.x line exposes the utility entry point described as PhoneNumberUtility.
// Note the README's warning: allocation is relatively expensive because it parses
// and holds the metadata for the object's lifetime — create one and reuse it.
let utility = PhoneNumberUtility()
let number = try utility.parse("+33689555555")

number.countryCode                            // 33
let e164      = utility.format(number, toType: .e164)
let intl      = utility.format(number, toType: .international)

// For live input fields, format as the user types:
let formatter = AsYouTypeFormatter(regionCode: "FR")
formatter.inputDigit("0")
formatter.inputDigit("6")
```

The UI module is the reason to pick this over rolling your own on iOS: `PhoneNumberTextField` gives you as-you-type formatting and a country picker with correct flags and dial codes, and the 4.x → 5.x migration keeps the core class name stable enough that most parsing code needs no source changes — only the package URL and metadata do.

## Deployment and operational notes

**Metadata is the product, not the code.** Every one of these libraries is a thin layer over a data table of country calling codes, national number lengths, and prefix ranges. That table changes constantly. If your team pins a two-year-old version because "the upgrade broke a test", you will silently reject numbers from ranges that were allocated after the pin. Treat a metadata upgrade like a dependency security update: routine, scheduled, and verified by a test that parses one number per market you serve.

**Validation is not verification.** None of these libraries will tell you whether a phone is switched on, reachable, or owned by the person typing it. They answer "could this string be a number in this country, and does the range currently exist?" If you need reachability, that is an SMS or voice verification flow, and it is a separate system with separate costs and abuse controls.

**Bulk jobs deserve a second pass.** In a CRM cleanup, expect a meaningful share of rows to be legitimately unparseable — extensions, internal short codes, placeholder values like `000`, test numbers. Log the `NumberParseException` error type (or the Python equivalent) instead of a generic failure, so you can distinguish "user typed a landline without an area code" from "this field contains the word 'unknown'".

**Client and server should agree.** If you validate with `libphonenumber-js/min` in the browser and the JVM library on the server, they can disagree on exotic ranges. Pick one as the authority — normally the server — and make the client check purely a user-experience hint that fails open.

**Do not try to detect number portability or ownership with this stack.** Carrier and geocoder lookups are convenience features with country-specific accuracy, and portability means the original allocation data can be wrong. Never use them for compliance decisions such as which country's tax rules apply.

For teams running the communications side of this, our guides on [self-hosted SIP phone auto-provisioning](../2026-06-03-self-hosted-sip-phone-auto-provisioning-fusionpbx-freepbx-opensips-guide/) and [self-hosted fax servers](../2026-06-03-self-hosted-fax-server-hylafax-ictfax-asterisk-guide/) cover what happens after the number is stored, and the [SCTP protocol server comparison](../2026-05-20-self-hosted-sctp-protocol-servers-kamailio-vs-lksctp-tools-vs-opensips-guide/) is useful background if you are carrying signalling yourself.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "libphonenumber vs libphonenumber-js vs phonenumbers in 2026: Which Phone Number Library Should You Actually Use?",
  "description": "Practical 2026 comparison of libphonenumber, libphonenumber-js, python-phonenumbers and PhoneNumberKit: metadata freshness, bundle sizes, validation semantics and the PhoneNumberKit repository migration.",
  "datePublished": "2026-09-25",
  "dateModified": "2026-09-25",
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

**Do I really need a library, or is a regex good enough?**
A regex can enforce "digits with optional leading plus and some separators", which is all you need if you only store the string. The moment you need to *format* a number for display, accept a national-format entry with a region hint, or know whether a range is currently allocated, you need metadata — roughly 250 regions' worth of it, regenerated continuously. That is what these libraries are.

**Which library should I use in a Node/TypeScript backend?**
`libphonenumber-js`. Use the `/min` build only in the browser, the default build on the server, and `/max` in your test suite so example numbers for every region are available. Prefer `isPossible()` while the user types and `isValid()` at submit time.

**How do I keep phone metadata up to date?**
Upgrade the package. Metadata ships inside the library: python-phonenumbers versions it (9.0.40 at the time of writing), libphonenumber-js republishes with refreshed metadata, and Google's upstream repo is pushed almost daily. Add a scheduled dependency bump and one test per market you serve.

**Can these libraries tell me if a number is actually reachable?**
No. They validate syntax and allocation, not existence, ownership, or whether the handset is online. Reachability requires an SMS or voice verification round trip through a carrier-connected service.

**Does validation work offline?**
Yes — all four bundle their metadata locally and make no network calls. That is a real privacy advantage for handling customer contact data, and it also means validation keeps working in air-gapped or batch environments.

**Should I store numbers in E.164?**
Always. Store a single normalized `+CCNNNNNNNNNN` string as the canonical value, and if you must keep the user's original typing for support purposes, put it in a separate column. Everything else — display format, national format, extensions — is derived at render time.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
