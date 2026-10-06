---
title: "zxcvbn Ports Compared in 2026: Password Strength Estimation in JS, Rust, Python, Java and PHP"
date: "2026-10-07"
tags: ["security", "passwords", "libraries", "developer-tools", "comparison"]
draft: false
cover: "/img/screenshots/zxcvbn-ts-demo.jpg"
---

Open the official zxcvbn demo, type the most famous passphrase on the internet — `correct horse battery staple` — and it returns **score 0 / 4** with the warning *"Your password was exposed by a data breach on the Internet."* That single result explains why this family of libraries replaced the password rules everybody used to write: **`P@ssw0rd1` passes a complexity policy, and a four-word passphrase fails it.** Character-class rules are wrong in both directions.

zxcvbn approaches the problem the way a password cracker does — pattern matching against real dictionaries, keyboard walks, dates, repeats and l33t substitutions — and then reports a conservative estimate of how many guesses an attacker needs. The original is JavaScript, but the algorithm has been ported to nearly every language you deploy. Here is how the ports compare, with star counts and commit dates read from the official repositories in **October 2026**.

## TL;DR — The Quick Verdict

- **Browser or Node.js:** use **zxcvbn-ts** (1,228 stars, TypeScript). It is the actively maintained rewrite and the only port with a breach-list matcher built in.
- **Do not start new projects on dropbox/zxcvbn.** It still has 16,067 stars, but its last commit was August 2024 and the upstream maintainers point at the TypeScript rewrite.
- **Rust:** **zxcvbn-rs** (273 stars, last pushed June 2026). **Python:** **zxcvbn** by dwolfhub (718 stars). **PHP:** **zxcvbn-php** (872 stars). **Ruby:** **zxcvbn-ruby** (354 stars).
- **Avoid zxcvbn-go for new work** — 393 stars but no commits since June 2022.

If you take one thing away: **score alone is a weak gate.** The breach check is the stronger signal, which is exactly what the demo above demonstrates by scoring a high-entropy passphrase at zero.

## Comparison Table

| Port | Language | Stars | Last activity | Dictionaries | user_inputs | Localized feedback | Breach check |
|---|---|---|---|---|---|---|---|
| dropbox/zxcvbn | JavaScript | 16,067 | 2024-08-19 | 30k+ | Yes | No | No |
| zxcvbn-ts | TypeScript | 1,228 | 2026-09-22 | 40k+ + language packs | Yes | Yes (i18n) | Yes |
| zxcvbn-php | PHP | 872 | 2025-02-24 | 10k | Yes | No | No |
| zxcvbn (Python) | Python | 718 | 2026-04-13 | 30k+ | Yes | No | No |
| zxcvbn-go | Go | 393 | 2022-06-06 | 30k+ | Yes | No | No |
| zxcvbn4j | Java | 364 | 2024-07-15 | 30k+ | Yes | Localizable | No |
| zxcvbn-ruby | Ruby | 354 | 2026-07-11 | v4 compatible | Yes | No | No |
| zxcvbn-rs | Rust | 273 | 2026-06-01 | 30k | Yes | No | No |

## Decision Matrix

| Your situation | Pick this | Why |
|---|---|---|
| Signup form that scores as the user types | zxcvbn-ts | Debounce helper, lazy-loaded dictionaries, i18n |
| Rust API validating credentials server-side | zxcvbn-rs | Serde-friendly result types, no runtime deps |
| Django or FastAPI backend | zxcvbn (dwolfhub) | Simple dict result, actively maintained |
| WordPress or Laravel plugin | zxcvbn-php | Composer-native, entropy-based scoring |
| Java service with a rule-free registration flow | zxcvbn4j | Only mature JVM port, localizable feedback |
| Rejecting passwords found in breaches | zxcvbn-ts pwned matcher | No other port ships a breach matcher |

## zxcvbn-ts — The Maintained Rewrite

The TypeScript port is a complete rewrite that splits the package into a core module and optional language packs. That structure matters: the dictionaries are large, and in a browser you do not want to ship every locale on first paint.

![zxcvbn-ts demo showing a password scored 0 out of 4 by the pwned matcher](/img/screenshots/zxcvbn-ts-demo.jpg "zxcvbn-ts demo: the pwned matcher recognises a breached passphrase and collapses the score")

```bash
npm install @zxcvbn-ts/core @zxcvbn-ts/language-common @zxcvbn-ts/language-en
```

```js
import { zxcvbn, zxcvbnOptions } from '@zxcvbn-ts/core'
import * as common from '@zxcvbn-ts/language-common'
import * as en from '@zxcvbn-ts/language-en'

zxcvbnOptions.setOptions({
  dictionary: { ...common.dictionary, ...en.dictionary },
  graphs: common.adjacencyGraphs,
  translations: en.translations,
})

const result = zxcvbn('correct horse battery staple')

console.log(result.score)             // 0..4
console.log(result.guessesLog10)      // log10 of estimated guesses
console.log(result.feedback.warning)  // human-readable warning
console.log(result.crackTimesDisplay) // per-attack-scenario timings
```

It also supports a **pwned matcher**, which checks the password against a breach corpus and forces the guess count toward zero when it appears there — the behaviour visible in the screenshot. Additional matchers cover Levenshtein distance (near-misses of dictionary words) and there is a debounce helper so you are not running the estimator on every keypress.

**Why it wins:** active development, real i18n, breach matching and a lazy-loading strategy. **Where it loses:** the modular packaging means more setup than `require('zxcvbn')`, and you must decide which language packs to bundle.

## zxcvbn-rs — Rust, With Serde-Friendly Results

The Rust port recognizes around 30,000 common passwords plus census-derived names, Wikipedia vocabulary and the usual pattern classes. Results are plain structs, which makes them easy to serialize into an API response.

```toml
[dependencies]
zxcvbn = "3"
```

```rust
use zxcvbn::zxcvbn;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let estimate = zxcvbn("correct horse battery staple", &[])?;

    println!("score: {}", estimate.score());
    if let Some(feedback) = estimate.feedback() {
        println!("warning: {:?}", feedback.warning());
    }
    println!("guesses: {}", estimate.guesses());
    Ok(())
}
```

The second argument is the `user_inputs` slice — feed it the username, e-mail local part and display name so that `alice2026` is not treated as a strong password just because it is long.

**Why it wins:** no runtime dependencies and a typed result you can return directly from an API handler. **Where it loses:** English-centric dictionaries, like every port except zxcvbn-ts with extra language packs.

## zxcvbn (Python) — The Recommended Python Port

Four Python implementations exist; the one the original authors pointed at is `dwolfhub/zxcvbn-python`, which is also the most recently maintained. It returns a dictionary rather than an object, so it drops straight into a Django or FastAPI response.

```bash
pip install zxcvbn
```

```python
from zxcvbn import zxcvbn

results = zxcvbn('JohnSmith123', user_inputs=['John', 'Smith'])

print(results['score'])          # 0 (terrible) .. 4 (great)
print(results['guesses'])        # estimated guesses
print(results['feedback'])       # {'warning': ..., 'suggestions': [...]}
print(results['crack_times_display']['offline_fast_hashing_1e10_per_second'])
```

Pass `user_inputs` from the account being registered — it is the cheapest accuracy win available, because it catches passwords built from the user's own name before any dictionary lookup runs.

**Why it wins:** the widest Python version support and a plain-dict result. **Where it loses:** there is an older `dropbox/python-zxcvbn` on GitHub (259 stars) — it is not the maintained one, and mixing them up is a common mistake.

## zxcvbn4j — The JVM Option, With Caveats

The Java port is feature-complete, including customizable dictionaries, custom keyboard layouts and localizable feedback messages. The Maven coordinates are `com.nulab-inc:zxcvbn`.

```java
Zxcvbn zxcvbn = new Zxcvbn();
Result result = zxcvbn.measure(password, userInputs);

int score = result.getScore();                 // 0..4
String warning = result.getFeedback().getWarning();
```

**Why it wins:** it is the only mature JVM implementation, and the localizable feedback is useful for non-English registration flows. **Where it loses:** last commit July 2024. It works, but dictionary updates have stopped, so treat it as frozen rather than maintained.

## zxcvbn-php and zxcvbn-ruby — Framework Ports

**zxcvbn-php** (872 stars) installs with Composer and exposes an entropy-based result, which makes it natural inside a Laravel or WordPress password validator:

```bash
composer require bjeavons/zxcvbn-php
```

```php
<?php
$zxcvbn = new ZxcvbnPhp\Zxcvbn();
$result = $zxcvbn->passwordStrength('password', ['username', 'email@example.com']);

echo $result->score;                       // 0..4
echo json_encode($result->feedback);       // warning + suggestions
```

Note the dictionary size difference: this port ships roughly 10,000 common passwords against the 30,000+ in the JS and Rust implementations. It is a smaller attack surface of known-bad passwords, not a different algorithm.

**zxcvbn-ruby** (354 stars, v4-compatible) is used in production at Envato and returns a rich `Score` object with the full match sequence, which is genuinely useful when you want to explain *why* a password was rated weak:

```ruby
require 'zxcvbn'

pp Zxcvbn.test('@lfred2004', ['alfred'])
# password="@lfred2004", guesses=15000.0,
# sequence=[pattern="dictionary", token="@lfred", l33t=true, dictionary_name="user_inputs", ...]
```

## Pitfalls, Migration Traps and Accuracy Limits

**1. A score of 4 is not a guarantee.** zxcvbn estimates guesses, not cryptographic strength. A password that happens to be absent from every dictionary can still be weak against a targeted attacker who knows the user's habits. Use the estimate as UX guidance and pair it with a length floor.

**2. Breach checking beats scoring.** The demo screenshot in this article is the whole argument: a 28-character passphrase scores zero because it appears in breach corpora. If your port supports a pwned matcher, enable it; if it does not, check the password against a breach corpus yourself before accepting it.

**3. Crack-time displays rest on assumptions.** Every port renders "10^10 guesses per second, offline attack" style figures. Those numbers are illustrative. Users read them as promises, so present them as rough magnitudes rather than guarantees.

**4. client-side estimation is not validation.** A browser can be bypassed trivially. Run the same estimator — or at least a minimum length and breach check — on the server, and reject there.

**5. Non-English passwords score badly.** Dictionaries are English-centric. A strong passphrase built from words in another language will be under-rated, and a weak one built from common words in that language may be over-rated. zxcvbn-ts language packs are the only real answer among these ports.

**6. Check the maintenance status before you commit.** `zxcvbn-go` has had no commits since 2022, `zxcvbn4j` since 2024, and `dropbox/zxcvbn` since 2024. None of them stopped working — but dictionary content ages, and an unmaintained port slowly stops recognizing new common passwords.

**7. Do not run the estimator on every keystroke.** zxcvbn is deliberately expensive. Debounce input (zxcvbn-ts ships a helper) or you will burn main-thread time on fast typists.

## Frequently Asked Questions

### Is zxcvbn better than traditional password complexity rules?

For most products, yes. Complexity rules reject strong passphrases and accept predictable substitutions like `P@ssw0rd1`. zxcvbn scores by estimating guesses against real dictionaries and patterns, so it rewards length and unpredictability instead of character classes. The usual recommendation is a minimum length plus a zxcvbn score threshold plus a breach check.

### Should I use dropbox/zxcvbn or zxcvbn-ts?

Use zxcvbn-ts for new work. The Dropbox original still has by far the most stars and works perfectly well in a browser, but its last commit was in August 2024, and the TypeScript rewrite is where the ecosystem is moving — it adds modular language packs, extra matchers and i18n.

### How accurate are zxcvbn's crack-time estimates?

They are order-of-magnitude estimates based on an assumed attacker model and a fixed guesses-per-second rate. They are useful for comparing two passwords and for steering users toward stronger ones, but they are not a measurement of cryptographic strength and should not be presented as such.

### Can zxcvbn check whether a password has been breached?

Only the zxcvbn-ts port ships a breach matcher out of the box (the "pwned" matcher visible in its demo). Other ports do not, so you need a separate breach-corpus lookup. Given that breached passwords collapse to score 0 regardless of their entropy, this check is often more valuable than the score itself.

### Do these libraries work for non-English passwords?

Weakly. Every port leans on English dictionaries with some additional country-specific word lists. Passphrases built from other languages can be under-rated, and attacker-specific common passwords in those languages may be missing. zxcvbn-ts is the only port in this comparison with pluggable language packs.

### Is it safe to run password strength estimation in the browser?

Yes, and it is good practice for feedback — but never trust it as a gate. Anyone can skip client-side JavaScript. Always re-check on the server before the password is stored, using the same estimator or at minimum a length and breach rule.

## Where This Fits in an Identity Stack

A strength estimator is one layer of a password policy that should also include breach checking, per-account rate limiting and a store that is hard to crack in the first place. If your users' credentials live in a self-hosted vault, see the [Teampass, sysPass and Passky comparison](../2026-04-24-teampass-vs-syspass-vs-passky-self-hosted-password-vault-guide-2026/) for the storage side, and the [Hashcat, Hashtopolis and Hashview guide](../2026-04-27-hashtopolis-vs-hashview-vs-hashcat-self-hosted-password-auditing-guide-2026/) if you want to verify your own hashing parameters by attacking them. For directory-backed sign-in flows, the [LDAP self-service password tools](../2026-05-10-ldap-self-service-password-ltb-ssp-kanidm-fusiondirectory-guide/) cover the reset path that most strength meters sit in front of.

Replace your complexity regex with a length floor, a score threshold and a breach check — and pick the port that is still being maintained in your language.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "zxcvbn Ports Compared in 2026: Password Strength Estimation in JS, Rust, Python, Java and PHP",
  "description": "A comparison of zxcvbn password strength estimation ports across JavaScript, TypeScript, Rust, Python, Java, PHP and Ruby, with real code samples, GitHub activity data and accuracy caveats.",
  "datePublished": "2026-10-07",
  "dateModified": "2026-10-07",
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
