---
title: "Mbed TLS vs wolfSSL vs BearSSL in 2026: Which Embedded TLS Stack Should You Ship?"
date: "2026-10-15"
description: "A practical 2026 comparison of Mbed TLS, wolfSSL and BearSSL for microcontrollers: flash and RAM footprint, TLS 1.3 and DTLS 1.3 support, FIPS options, real build commands and the certificate pitfalls that break field devices."
tags: ["embedded", "tls", "security", "cryptography", "comparison"]
draft: false
cover: "/img/screenshots/wolfssl-logo.jpg"
---

A full TLS 1.3 handshake plus an X.509 chain validation path can eat **more flash than your RTOS kernel and your application combined** on a Cortex-M0+. On a 64 KB part with an internal radio stack already claiming half the budget, the choice between Mbed TLS, wolfSSL and BearSSL is not a library preference — it is a product decision that determines whether cloud connectivity, secure OTA and certificate rotation fit in the image at all.

It also decides your maintenance exposure. wolfSSL pushed a batch of X.509 and session-cache fixes into 5.9.x releases this year; Mbed TLS restructured its configuration system around the PSA Crypto API; BearSSL has shipped no upstream release since 2018 and its own README still calls it beta-level software. Shipping a frozen TLS stack in 2026 is a legitimate engineering choice, but only if you make it deliberately.

## TL;DR: The 2026 Verdict

**Pick Mbed TLS** if you are on Zephyr, NuttX, FreeRTOS-plus-mbedTLS, or any Arm ecosystem where PSA Crypto is already in the picture — it is the default, the most widely integrated, and the easiest to shrink with the configuration script. **Pick wolfSSL** when you need FIPS-validated crypto, DTLS 1.3, a genuinely tiny build (`--enable-leantls`), or a commercial support contract you can put in front of an auditor. **Pick BearSSL** only for a frozen, allocation-free TLS 1.2 client where you can carry the security maintenance yourself — its design (no malloc, constant-time crypto, tiny footprint) is excellent, but it is not where new TLS 1.3 work should start.

If you read nothing else: Mbed TLS for ecosystem fit, wolfSSL for compliance and footprint, BearSSL for frozen legacy clients.

## Comparison Table: Mbed TLS vs wolfSSL vs BearSSL

| Dimension | Mbed TLS | wolfSSL | BearSSL |
|---|---|---|---|
| GitHub stars | **7,000** | **2,964** | mirror-only (canonical source at bearssl.org) |
| Last upstream activity | 2026-10-14 | 2026-10-15 | no release since 0.6 (2018) |
| License | Apache-2.0 OR GPL-2.0 | GPL-2.0 OR commercial | MIT |
| TLS 1.3 | Yes (configurable) | Yes (`--enable-tls13`) | **No — TLS 1.2 only** |
| DTLS | DTLS 1.2 (+ 1.3 in progress) | DTLS 1.2 and **DTLS 1.3** | DTLS 1.2 |
| Dynamic allocation | Optional (caller-provided buffers) | Optional (`WOLFSSL_SMALL_STACK`, static pools) | **Never allocates** |
| FIPS path | PSA Crypto / vendor validated builds | **FIPS 140-3 ready + `--enable-fips`** | None |
| Build system | CMake + `scripts/config.py` | autotools `./configure` or CMake, or `user_settings.h` | plain make + `conf/*.mk` |
| Smallest profile | `scripts/config.py` crypto-only builds | `--enable-leantls`, `--enable-lowresource` | smallest of the three |
| Commercial support | Via partners / Arm ecosystem | Direct vendor support available | Community only |

The star counts and timestamps above were pulled live from the GitHub API at publish time — treat the "last upstream activity" column as the one that matters for your threat model, because a TLS library's release cadence *is* its security posture.

## Decision Matrix: Use Case to Stack

| Your situation | Choose | Why |
|---|---|---|
| Zephyr / NuttX / FreeRTOS project, standard cloud MQTT over TLS | **Mbed TLS** | Ships with the RTOS, PSA Crypto API, no integration work |
| Need DTLS 1.3 or FIPS 140-3 for a regulated product | **wolfSSL** | Only one of the three with DTLS 1.3 and a FIPS track record |
| 32 KB flash budget, TLS 1.2 acceptable | **BearSSL** | No allocator, smallest code, predictable RAM |
| You need to pass a security audit with vendor paperwork | **wolfSSL** | Commercial license includes support and vulnerability handling |
| Multi-tasking firmware where the TLS context is shared | **Mbed TLS** | PSA key slots are documented and thread-safety is a first-class topic |
| Legacy product you cannot re-certify; frozen crypto is fine | **BearSSL** | Stability by design, but you own CVE triage |

## Mbed TLS — The Ecosystem Default

Mbed TLS is a C library implementing X.509 certificate manipulation plus the TLS and DTLS protocols, and it is the reference implementation of the PSA Crypto API. Its README states the design goal plainly: a small code footprint suitable for embedded systems. In practice, the configuration system is what makes it embedded-friendly — the build is controlled by a header file that `scripts/config.py` can rewrite programmatically.

```sh
# Clone and prepare host-side dependencies (Python 3 is required for codegen)
git clone https://github.com/Mbed-TLS/mbedtls.git
cd mbedtls
python3 -m pip install --user -r scripts/basic.requirements.txt

# Shrink the library for a TLS 1.3-only client build
python3 scripts/config.py set MBEDTLS_SSL_PROTO_TLS1_3
python3 scripts/config.py unset MBEDTLS_SSL_PROTO_TLS1_2
python3 scripts/config.py unset MBEDTLS_SSL_SRV_C

# Build statically; skip the test suites on a constrained CI runner
cmake -B build -DENABLE_TESTING=Off -DUSE_SHARED_MBEDTLS_LIBRARY=Off
cmake --build build
```

The client setup path is the one you will write first:

```c
mbedtls_ssl_config conf;
mbedtls_ssl_context ssl;

mbedtls_ssl_config_init(&conf);
mbedtls_ssl_config_defaults(&conf,
                            MBEDTLS_SSL_IS_CLIENT,
                            MBEDTLS_SSL_TRANSPORT_STREAM,
                            MBEDTLS_SSL_PRESET_DEFAULT);

/* Never ship MBEDTLS_SSL_VERIFY_NONE outside of bring-up */
mbedtls_ssl_conf_authmode(&conf, MBEDTLS_SSL_VERIFY_REQUIRED);
mbedtls_ssl_conf_ca_chain(&conf, &ca_chain, NULL);

mbedtls_ssl_init(&ssl);
mbedtls_ssl_setup(&ssl, &conf);
mbedtls_ssl_set_bio(&ssl, &net_ctx, send_cb, recv_cb, NULL);
mbedtls_ssl_handshake(&ssl);
```

When mbedtls is wired into an RTOS with more than one task touching the crypto layer, the PSA key-slot state machine becomes the thing you debug at 2 a.m.:

![Mbed TLS PSA key slot state transitions](/img/screenshots/mbedtls-psa-keyslots.jpg "Mbed TLS documentation diagram of PSA key slot state transitions")

If your firmware runs a mesh stack, the RTOS integration order matters as much as the TLS library — see our [embedded RTOS comparison of Zephyr, NuttX and RIOT](../2026-09-23-embedded-rtos-zephyr-nuttx-riot-os-comparison/) for how each one wires in a TLS port.

## wolfSSL — Compliance and the Smallest Practical Build

wolfSSL describes itself as a small, fast, portable TLS/SSL implementation for embedded devices through to the cloud, supporting TLS 1.3 and DTLS 1.3. Two things separate it from the other two options in this article: a FIPS-validated crypto core, and *profile flags that genuinely change the binary size*.

```sh
./autogen.sh
./configure \
  --enable-tls13 \
  --enable-dtls \
  --enable-leantls \
  --enable-static \
  --disable-shared \
  CFLAGS="-Os -DWOLFSSL_SMALL_STACK"
make -j"$(nproc)"
sudo make install
```

`--enable-leantls` and `--enable-lowresource` are the flags worth reading about before you size your flash budget — they drop optional protocol features rather than trimming code blindly. Recent 5.9.x releases also trimmed TLS 1.3-only builds so the handshake transcript state is smaller (the TLS 1.2 transcript and SHA-512 transcript are omitted unless explicitly enabled), which is exactly the kind of change that decides whether a feature fits on a 512 KB part.

Client bring-up is the OpenSSL-shaped API many firmware engineers already know:

```c
wolfSSL_Init();

WOLFSSL_CTX* ctx = wolfSSL_CTX_new(wolfTLSv1_3_client_method());
wolfSSL_CTX_load_verify_locations(ctx, ca_pem, NULL);

WOLFSSL* ssl = wolfSSL_new(ctx);
wolfSSL_set_fd(ssl, sock);
int rc = wolfSSL_connect(ssl);   /* rc must be SSL_SUCCESS */
```

The CVE history in the README is long and very specific — including an X.509 name-constraint enforcement flaw in 5.9.2 and earlier, an OCSP/CRL interaction that could accept a revoked certificate, and a session-cache issue where a TLS 1.2 session handle could be resolved against another server's master secret. All of these are fixed in current releases, but two operational lessons follow: **pin your dependency and read the advisories every quarter**, and be aware that a poisoned session cache lives in a process-global structure, so a long-running device may need its `WOLFSSL_CTX` torn down, not just the library upgraded.

## BearSSL — Excellent Design, Frozen Feature Set

BearSSL is the odd one out and worth understanding before you dismiss it. Its README is refreshingly honest: BearSSL is considered beta-level software, the MIT license is explicit, and using it in production is "a relatively bold but not utterly crazy move." The design choices are what people come for:

- **No dynamic allocation, ever.** RAM usage is decided at build time by buffer size constants, which is a gift for MISRA-style reviews.
- **Constant-time crypto throughout.** BearSSL was written by a cryptographer and its timing characteristics are documented rather than incidental.
- **TLS 1.2 only.** There is no TLS 1.3 and no DTLS 1.3, which in 2026 is the deciding limitation for anything new.
- **Plain makefiles, no CMake and no autotools.** Platform profiles live in `conf/` — for example `conf/Unix.mk` for a host build and `conf/samd20.mk` for an Arm Cortex-M0+ target — and the top-level Makefile selects one.

That last point is why BearSSL is a legitimate pick for an allocation-free client on a tiny part with a bounded, well-understood protocol surface. It is also why we do not recommend starting new TLS 1.3 projects on it: the upstream release line stopped at 0.6 in 2018, so every CVE affecting TLS 1.2 cipher suites or X.509 parsing becomes your patch to write and carry.

## Pitfalls That Break TLS in the Field

**No clock, no certificates.** X.509 validity checking needs wall-clock time. A device that boots with an unset RTC will reject valid chains or, worse, have `MBEDTLS_SSL_VERIFY_NONE`-style shortcuts bolted on to "fix" it. Sniff the time from the TLS handshake itself or a signed time source before validating.

**Entropy is not optional.** On a board with no TRNG, a handshake that randomly fails every few hundred connections is almost always a DRBG seeded from an uninitialised source. WolfSSL's and Mbed TLS's entropy callbacks must be wired to real hardware entropy.

**Trust anchor bloat.** A full public CA root store is hundreds of kilobytes of flash. Pin the one or two roots your backend actually uses, and plan certificate rotation as an OTA concern, not an afterthought.

**Buffer sizes change late.** TLS record buffers decide peak RAM. Adjusting them after the product ships is a memory-map change; decide them during bring-up and record them next to your [embedded filesystem](../2026-10-15-embedded-filesystems-littlefs-vs-spiffs-vs-fatfs/) budget, since both compete for the same flash.

**Session resumption caches.** Both major stacks support session/ticket resumption. In constrained devices the cache is often global and never validated against the peer, which is how cross-server session confusion bugs appear. Disable resumption unless you have a concrete power budget that requires it — which matters most for battery devices that also run an [MQTT client over TLS](../2026-06-26-mqtt-client-libraries-cpp-paho-mqttcpp-pahoc/).

**Test with the same tools your attackers use.** Run `testssl.sh` against a device acting as a TLS server, and check the negotiated protocol version explicitly — "it connects" is not evidence that TLS 1.3 is actually being negotiated.

## FAQ

### Which embedded TLS library should I choose in 2026?

Choose Mbed TLS if you use Zephyr, NuttX or any Arm ecosystem with PSA Crypto; choose wolfSSL if you need FIPS validation, DTLS 1.3, or the smallest tunable build with commercial support; choose BearSSL only for frozen, allocation-free TLS 1.2 clients you are prepared to maintain yourself.

### Does BearSSL support TLS 1.3?

No. BearSSL implements TLS 1.2 and DTLS 1.2 only, and its upstream release line has been stable at 0.6 since 2018. If TLS 1.3 is a requirement, BearSSL is out of scope — use Mbed TLS or wolfSSL.

### How much flash does an embedded TLS stack need?

It depends almost entirely on configuration, not the library name. A client-only, single-cipher-suite build can land in the tens of kilobytes, while a full server build with a large root CA store can exceed a megabyte. Mbed TLS shrinks via `scripts/config.py`, wolfSSL via configure profile flags such as `--enable-leantls` and `--enable-lowresource`. Always measure your own configuration.

### Is wolfSSL free for commercial firmware?

wolfSSL is dual-licensed: GPL-2.0, or a commercial license. Static linking into a closed-source product generally requires the commercial license — the same reasoning that applies to OpenBLT's GPL/commercial split. Budget for it early if your product is proprietary.

### How do I handle certificate validation without a real-time clock?

Establish time before validation: sync from the TLS connection itself, an authenticated time service, or a signed RTC value, then configure the stack's time callback. If time is unknown, fail closed rather than disabling verification — a device that accepts any certificate is worse than one that refuses to connect.

### Can I use these libraries with an RTOS?

All three are RTOS-agnostic C libraries with no mandatory OS dependencies. Mbed TLS has the deepest RTOS integration story because it ships inside Zephyr and NuttX, and its PSA key-slot documentation covers multi-tasking access patterns explicitly.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Mbed TLS vs wolfSSL vs BearSSL in 2026: Which Embedded TLS Stack Should You Ship?",
  "description": "Practical 2026 comparison of Mbed TLS, wolfSSL and BearSSL for embedded systems: footprint, TLS 1.3 and DTLS support, FIPS options, build commands and certificate pitfalls.",
  "datePublished": "2026-10-15",
  "dateModified": "2026-10-15",
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
