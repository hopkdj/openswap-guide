---
title: "bcrypt vs Argon2id vs scrypt in 2026: Which Password Hashing Algorithm Should You Actually Ship?"
date: "2026-10-10"
tags: ["security", "password-hashing", "cryptography", "developer-libraries", "application-security"]
draft: false
cover: "/img/screenshots/argon2-kdf-benchmark.jpg"
description: "A hands-on 2026 comparison of bcrypt, Argon2id, scrypt and PBKDF2 — OWASP parameters, working code in Python, Go, PHP and Node, migration traps and benchmark guidance."
---

Your database is one leaked backup away from being a credential dump. In 2026 the average attacker rents GPU time by the minute, and a password hash that cost 200 ms to produce on your server costs a few microseconds per guess on hardware that was designed for exactly this job. Hashing is the only control standing between a stolen table row and a working login — and the algorithm you pick decides how long that wall holds.

This is a working guide, not a theory piece. Every parameter below comes from the current OWASP Password Storage guidance, every code sample runs as written, and the star counts come from GitHub on release day.

## TL;DR: The Verdict

**Ship Argon2id for anything new** — it is OWASP's first choice, memory-hard, and its parameters are a single, well-documented dial. **Keep bcrypt if you already run it at cost ≥ 10** and need zero migration risk; just respect the 72-byte input limit. **Choose scrypt when you want memory-hardness from a library that has been audited in OpenSSL and the BSDs for a decade.** Use **PBKDF2 only when a compliance auditor demands a FIPS-validated primitive** — and then use 600,000 iterations of PBKDF2-HMAC-SHA256, not the 10,000 you remember from 2013.

## The Contenders At A Glance

Live figures pulled from GitHub on 2026-10-09/10:

| Property | Argon2id | bcrypt | scrypt | PBKDF2 |
| --- | --- | --- | --- | --- |
| Reference implementation | [P-H-C/phc-winner-argon2](https://github.com/P-H-C/phc-winner-argon2) — **5,383 ⭐**, stable since 2024 | [pyca/bcrypt](https://github.com/pyca/bcrypt) — **1,504 ⭐**, updated 2026-10-09 | [Tarsnap/scrypt](https://github.com/Tarsnap/scrypt) — **518 ⭐**, updated 2026-09-21 | Shipped inside OpenSSL, `hashlib`, Node `crypto` |
| Memory-hard | Yes — tunable `memory_cost` | No — fixed 4 KB working set | Yes — `N × r` memory | No |
| GPU/ASIC resistance | High | Medium (fast cores still help) | High | Low |
| OWASP 2026 stance | **First choice** | Acceptable, cost ≥ 10 | Acceptable, N=2^17,r=8,p=1 | Last resort, 600k iterations |
| Input length limit | None practical | **72 bytes**, silent truncation | None practical | None practical |
| Parallelism knob | `parallelism` | Implicit | `p` | None |
| Standardised | RFC 9106 | None (de facto) | RFC 7914 | RFC 8018 |
| Reference code maturity | 9 years, 3 stable releases | 12+ years, multiple audited bindings | 17 years | Decades |

A second, sharper decision:

| Your situation | Pick | Why |
| --- | --- | --- |
| New application, no legacy constraints | **Argon2id** (m=19 MiB, t=2, p=1) | OWASP first choice; strong GPU resistance; simple tuning |
| You already store bcrypt hashes and they work | **bcrypt**, cost 12 | Cost-12 is still >150 ms server-side; migration risk exceeds the marginal gain |
| Regulated environment that names a primitive | **PBKDF2-HMAC-SHA256**, 600k iterations | FIPS-validated implementations everywhere; document the trade-off |
| You need memory-hardness in a language with no Argon2 binding | **scrypt** | OpenSSL, Go, and Node ship it natively — zero new dependencies |
| You need to hash a *file* or key, not a password | **Argon2** but not `id` — use Argon2i/d per RFC 9106 §4 | Different threat model than interactive login |

## Argon2id — The Default Choice

Argon2id is the hybrid the Password Hashing Competition designed for exactly this use case: the first pass behaves like Argon2i (side-channel resistant), the rest behaves like Argon2d (maximally GPU-resistant). The winning implementation, `P-H-C/phc-winner-argon2` (**5,383 ⭐**), is the C code that every language binding calls into, and the OWASP cheat sheet's baseline parameters are **19 MiB of memory, 2 iterations, 1 degree of parallelism**.

Python with `argon2-cffi` (**733 ⭐**, updated 2026-10-01):

```python
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

ph = PasswordHasher(
    time_cost=2,          # iterations
    memory_cost=19456,    # KiB → 19 MiB, the OWASP baseline
    parallelism=1,
    hash_len=32,
    salt_len=16,
)

hashed = ph.hash("correct horse battery staple")
# $argon2id$v=19$m=19456,t=2,p=1$....$....

try:
    ph.verify(hashed, "correct horse battery staple")
except VerifyMismatchError:
    raise
```

Go's `golang.org/x/crypto/argon2` exposes the primitive directly, so you own the encoding:

```go
salt := make([]byte, 16)
if _, err := rand.Read(salt); err != nil { return err }

key := argon2.IDKey([]byte(password), salt, 2, 19*1024, 1, 32) // t=2, m=19MiB, p=1
fmt.Printf("$argon2id$v=19$m=19456,t=2,p=1$%s$%s\n",
    base64.RawStdEncoding.EncodeToString(salt),
    base64.RawStdEncoding.EncodeToString(key))
```

PHP ships it in core — no extensions, no vendor directory:

```php
$hash = password_hash($password, PASSWORD_ARGON2ID, [
    'memory_cost' => 19456,
    'time_cost'   => 2,
    'threads'     => 1,
]);
if (!password_verify($password, $hash)) { /* reject */ }
```

**When to raise the parameters:** benchmark `ph.hash()` on your smallest production instance. If it completes in under 50 ms, raise `memory_cost` (not just `time_cost`) until it lands between 100 ms and 250 ms. Memory is the whole point — doubling `time_cost` mostly helps attackers' cache behaviour, while doubling `memory_cost` forces every parallel guess to allocate 38 MiB.

## bcrypt — The Boring, Battle-Tested Option

bcrypt has one famous flaw and one famous strength. The flaw: it reads **at most 72 bytes** of input. Anything longer is silently ignored, which means a 200-character passphrase and its first 72 characters hash identically. The strength: after fifteen years of public analysis, nobody has broken it in a real deployment.

```python
import bcrypt

COST = 12  # ~250 ms on a 2026-era vCPU; never below 10

def hash_password(password: str) -> bytes:
    raw = password.encode("utf-8")[:72]        # honour the limit explicitly
    return bcrypt.hashpw(raw, bcrypt.gensalt(rounds=COST))

def check_password(password: str, hashed: bytes) -> bool:
    return bcrypt.checkpw(password.encode("utf-8")[:72], hashed)
```

Node, with the native `bcrypt` or pure-JS `bcryptjs`:

```js
const bcrypt = require('bcrypt');

const hash = await bcrypt.hash(password.slice(0, 72), 12);
const ok   = await bcrypt.compare(candidate.slice(0, 72), hash);
if (!ok) throw new Error('invalid credentials');
```

If your users type 100-character passphrases, either truncate *explicitly and consistently* — every write and every read path — or pre-hash with SHA-256 and base64-encode the digest before handing it to bcrypt. The base64 step matters: raw SHA-256 output can contain a `0x00` byte, and several bcrypt libraries treat that as a string terminator.

## scrypt — Memory-Hard and Audited

scrypt predates Argon2 and remains excellent. Its parameters are `N` (CPU/memory cost), `r` (block size) and `p` (parallelism), with memory use ≈ `128 × N × r` bytes. OWASP's 2026 baseline is **N=2^17, r=8, p=1** — about 128 MiB, which in Python requires raising `maxmem` above the 32 MiB default:

```python
import hashlib, os

def hash_scrypt(password: str) -> bytes:
    salt = os.urandom(16)
    dk = hashlib.scrypt(
        password.encode(), salt=salt,
        n=2**17, r=8, p=1,
        dklen=32,
        maxmem=256 * 1024 * 1024,   # must exceed 128*N*r
    )
    return salt + dk
```

Node's `crypto.scrypt` is the same primitive, and it is fast enough to serve interactive logins:

```js
const crypto = require('crypto');
const N = 2 ** 17, r = 8, p = 1;

crypto.scrypt(password, salt, 32, { N, r, p, maxmem: 256 * 1024 * 1024 },
  (err, key) => { if (err) throw err; /* store key */ });
```

The 128 MiB allocation is a real operational constraint: if your login service has 20 concurrent requests and 512 MiB of RAM, scrypt at OWASP parameters will exhaust it. Profile before you ship, and consider lowering `N` to 2^15 (`32 MiB`) with a correspondingly higher `p`.

## PBKDF2 — Only When Compliance Demands It

PBKDF2 is a 25-year-old key-derivation function that happens to be acceptable for passwords. It has no memory-hardness, so a GPU cluster guesses it orders of magnitude faster per dollar than Argon2id. Two reasons to keep it: FIPS 140 validation, and the fact that it is already inside every standard library on Earth.

```python
import hashlib, os

def hash_pbkdf2(password: str) -> bytes:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 600_000, dklen=32)
    return salt + dk
```

**600,000** is the 2026 OWASP number for PBKDF2-HMAC-SHA256. If you find `10000` or `100000` in your codebase, that is a migration ticket, not a tuning choice.

## Tuning Parameters Without Guessing

The published Argon2 cost model makes the trade-off visible — the official repository ships the distribution plot from the specification, which is the most useful picture in this whole debate:

![Argon2 memory-time trade-off chart from the official Argon2 specification repository](/img/screenshots/argon2-kdf-benchmark.jpg "Argon2 power distribution from the official phc-winner-argon2 repository, showing how memory cost dominates attacker advantage")

Practical targets for a 2026 login endpoint:

| Primitive | OWASP baseline | Expected server cost (modern vCPU) | Memory per concurrent login |
| --- | --- | --- | --- |
| Argon2id | m=19 MiB, t=2, p=1 | 40–90 ms | ~19 MiB |
| bcrypt | cost 12 | 200–350 ms | ~4 KB |
| scrypt | N=2^17, r=8, p=1 | 100–200 ms | ~128 MiB |
| PBKDF2-HMAC-SHA256 | 600,000 iterations | 150–400 ms | negligible |

bcrypt looks expensive per hash and cheap in memory; that is precisely the shape of its weakness. Argon2id and scrypt cost you RAM, which is the resource an attacker cannot rent at scale as cheaply as a GPU.

## Migration & Pitfalls: The Part That Bites

- **Never silently swap algorithms.** Store the algorithm identifier inside the hash string (`$argon2id$...`, `$2b$...`) and verify with the algorithm the string declares, not the one you prefer today.
- **Rehash on successful login.** When a bcrypt hash verifies and your policy is now Argon2id, derive the new hash from the plaintext you already have in memory and update the row in the same transaction. No password reset emails required.
- **Add a pepper stored outside the database.** An HMAC with a 32-byte key from your secret manager before hashing defeats a database-only leak. Keep it out of the same backup.
- **Cap input length before it reaches the KDF.** Accepting a 1 MB password is a free denial-of-service: Argon2 will happily allocate for it. Cap at 128–1024 characters and reject the rest.
- **Use constant-time comparison.** `bcrypt.checkpw` and `ph.verify` do this for you; hand-rolled `==` comparisons do not.
- **Do not roll your own "fast" scheme.** SHA-256 with a salt, repeated concatenation, or MD5-then-bcrypt "for compatibility" all reduce to something weaker than the primitive you started with.
- **Benchmark on production hardware.** A laptop with a 5 GHz core will happily tell you cost 14 is fine. Your 2-vCPU container will disagree at 3 a.m.

For a broader look at protecting the credentials around the hash, our [self-hosted password vault comparison](../2026-04-24-teampass-vs-syspass-vs-passky-self-hosted-password-vault-guide-2026/) covers the storage side, and if you want to measure how weak the *inputs* are, the [password strength library comparison](../2026-10-07-password-strength-libraries-zxcvbn-ports-comparison/) is the companion read. When you are ready to attack your own hashes before someone else does, see the [password auditing platforms guide](../2026-04-27-hashtopolis-vs-hashview-vs-hashcat-self-hosted-password-auditing-guide-2026/).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "bcrypt vs Argon2id vs scrypt in 2026: Which Password Hashing Algorithm Should You Actually Ship?",
  "description": "A hands-on 2026 comparison of bcrypt, Argon2id, scrypt and PBKDF2 with OWASP parameters, working code in Python, Go, PHP and Node, and migration pitfalls.",
  "datePublished": "2026-10-10",
  "dateModified": "2026-10-10",
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

**Is Argon2id always better than bcrypt?**
For new applications, yes — it is OWASP's first choice and resists GPU cracking far better per byte of server cost. For an existing system already storing bcrypt at cost 12, the marginal security gain does not justify a risky bulk migration; migrate lazily by rehashing on each successful login instead.

**What exactly happens when a password is longer than 72 bytes with bcrypt?**
The library silently ignores everything past the 72nd byte, so two different long passphrases can produce identical hashes. Truncate explicitly on every code path, or pre-hash with SHA-256 and base64-encode the digest before calling bcrypt.

**Can I just use SHA-256 with a salt for passwords?**
No. SHA-256 is designed to be fast, which is the opposite of what password hashing needs. A single 2026 GPU evaluates billions of SHA-256 digests per second, so a salted SHA-256 hash of an eight-character password falls in minutes. Salting only prevents rainbow tables and identical-hash detection.

**How do I choose Argon2 memory_cost versus time_cost?**
Start at the OWASP baseline of 19 MiB with two iterations, measure on your smallest production instance, and raise memory_cost first if the hash completes in under 100 ms. Memory is the parameter that scales the attacker's cost; time_cost alone mostly helps them stay in cache.

**What is a pepper, and where should it live?**
A pepper is a secret key mixed into the hash (usually an HMAC applied before the KDF) and stored outside the credential database — in a secret manager or environment-injected key. It means a stolen database dump is still useless without a second breach.

**Is scrypt still safe to use in 2026?**
Yes. It is standardised in RFC 7914, ships inside OpenSSL, Go and Node, and remains memory-hard. Its main drawback is operational: OWASP parameters allocate roughly 128 MiB per concurrent login, so size your login service's memory accordingly.

**Do I need to rehash every password when I change parameters?**
No. Increase the cost parameters for new hashes and rehash each existing hash the next time that user logs in successfully, using the plaintext already present in the request.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
