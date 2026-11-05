---
title: "Post-Quantum TLS in 2026: liboqs vs PQClean vs OpenSSL 3.5 Compared"
date: "2026-11-05"
tags: ["cryptography", "tls", "post-quantum", "openssl", "security", "self-hosted"]
draft: false
---

Your TLS traffic recorded today is already a liability. Anything encrypted with RSA-2048 or ECDSA P-256 can be stored now and decrypted later once a cryptographically relevant quantum computer exists — the "harvest now, decrypt later" scenario that pushed NIST to publish FIPS 203/204/205 in August 2024 and to draft IR 8547, which deprecates RSA and elliptic-curve cryptography after **2030** and disallows it after **2035**.

If you run your own reverse proxy, VPN, or internal CA, the migration is your problem, not your cloud provider's. The good news: ML-KEM is deployable today on ordinary x86 hardware with almost no performance penalty. The bad news: the ecosystem has four overlapping layers — liboqs, oqs-provider, PQClean, and native OpenSSL 3.5 support — and picking the wrong one wastes weeks.

## TL;DR: The Quick Verdict

**If you want post-quantum TLS on a real server this quarter, use OpenSSL 3.5's native ML-KEM with the `X25519MLKEM768` hybrid group.** It is the only path with no extra provider to load, no unpinned research code in your handshake, and a hybrid construction that keeps you safe if ML-KEM is ever broken.

**If you are prototyping, benchmarking, or need algorithms OpenSSL has not shipped yet (Falcon, HQC, Classic McEliece), use liboqs and its OpenSSL provider.** **If you are shipping firmware or embedding a single scheme into your own protocol, vendor the reference implementation from PQClean** — that is precisely what PQClean exists for.

Do not build production services directly against liboqs. The project says so itself in its own README.

## The Four Layers, Compared

| Dimension | liboqs | oqs-provider | PQClean | OpenSSL 3.5 (native) |
|---|---|---|---|---|
| GitHub stars | 3,122 | 510 | 958 | 31,193 |
| Last push | 2026-11-04 | 2026-11-02 | 2026-08-04 | 2026-11-05 |
| License | Mixed per algorithm (MIT-style) | MIT | Public domain / CC0-style per scheme | Apache-2.0 |
| What it is | C library of KEM + signature schemes | OpenSSL 3 provider wrapping liboqs | Clean, standalone reference code | Production TLS/crypto toolkit |
| ML-KEM | Yes | Yes (via liboqs) | Yes (`ml-kem-512/768/1024`) | Yes |
| ML-DSA | Yes | Yes | Yes | Yes |
| SLH-DSA | Yes | Yes | Yes | Yes |
| Extra algorithms | Falcon, HQC, McEliece, BIKE | Same as liboqs | Same as liboqs | Standardized set only |
| TLS integration | None (library) | Drop-in OpenSSL provider | None (library) | Built in |
| FIPS story | None | None | None | FIPS provider separate |
| Maintenance risk | Research-grade | Research-grade | Frozen reference code | Vendor-supported |
| Best for | Experimentation, benchmarks | Testing PQC with existing TLS stacks | Embedding one scheme | Production deployment |

The decision matrix most teams actually need:

| Your situation | Pick | Why |
|---|---|---|
| Nginx/HAProxy/Caddy in front of customer traffic | OpenSSL 3.5 + `X25519MLKEM768` | Zero new moving parts, hybrid safety, one config line |
| Need to test Falcon or McEliece handshakes | liboqs + oqs-provider | Only place those schemes are wired into OpenSSL |
| Embedded device, 40 KB of flash for crypto | PQClean (single scheme) | Per-scheme source tree, no build system dependencies |
| Benchmarking KEM performance across schemes | liboqs | Uniform `OQS_KEM` API across all algorithms |
| Must pass an audit with a supported crypto module | OpenSSL 3.5 (or vendor BoringSSL) | Third-party providers are outside most support matrices |

## liboqs — The Experimentation Layer

liboqs is the reference C library from the Open Quantum Safe project: one API (`OQS_KEM`, `OQS_SIG`) across a dozen-plus schemes, with the build able to fetch upstream implementations and compile them in. It is excellent at what it does and explicitly not a production dependency.

Build it the documented way:

```bash
sudo apt install astyle cmake gcc ninja-build libssl-dev unzip xsltproc doxygen graphviz valgrind
git clone -b main https://github.com/open-quantum-safe/liboqs.git
cd liboqs
mkdir build && cd build
cmake -GNinja -DBUILD_SHARED_LIBS=ON ..
ninja
sudo ninja install
ldconfig
```

A minimal key-encapsulation round trip looks like this:

```c
#include <stdio.h>
#include <stdlib.h>
#include <oqs/oqs.h>

int main(void) {
    OQS_KEM *kem = OQS_KEM_new(OQS_KEM_alg_ml_kem_768);
    if (kem == NULL) return 1;

    uint8_t *pk  = malloc(kem->length_public_key);
    uint8_t *sk  = malloc(kem->length_secret_key);
    uint8_t *ct  = malloc(kem->length_ciphertext);
    uint8_t *ss1 = malloc(kem->length_shared_secret);
    uint8_t *ss2 = malloc(kem->length_shared_secret);

    OQS_KEM_keypair(kem, pk, sk);       /* server side */
    OQS_KEM_encaps(kem, ct, ss1, pk);   /* client side */
    OQS_KEM_decaps(kem, ss2, ct, sk);   /* server side */

    printf("shared secrets match: %d\n", OQS_MEM_secure_bcmp(ss1, ss2, kem->length_shared_secret) == 0);
    printf("pk=%zu ct=%zu ss=%zu bytes\n", kem->length_public_key, kem->length_ciphertext, kem->length_shared_secret);

    OQS_KEM_free(kem);
    return 0;
}
```

Compile with `gcc demo.c -loqs -lcrypto -o demo`. On ML-KEM-768 you will see **pk=1184, ct=1088, ss=32** bytes — remember those numbers, because they drive every handshake-size problem later.

The API is uniform, so switching `OQS_KEM_alg_ml_kem_768` to `OQS_KEM_alg_hqc_128` is a one-line benchmark change. That is the whole point of liboqs, and it is why paper authors and protocol designers keep it installed.

## oqs-provider — Post-Quantum Algorithms Inside OpenSSL 3

`oqs-provider` is a shared library that registers liboqs algorithms as an OpenSSL 3 provider. Once loaded, `openssl` CLI commands and TLS handshakes can use ML-KEM and friends without patching OpenSSL itself. This is how most people get a working post-quantum TLS handshake on a stack that predates 2025.

Build order matters: liboqs first (shared library, installed), then:

```bash
git clone https://github.com/open-quantum-safe/oqs-provider.git
cd oqs-provider
cmake -S . -B build -DOPENSSL_ROOT_DIR=/usr/local -DCMAKE_PREFIX_PATH=/usr/local
cmake --build build
sudo cmake --install build
```

Then activate it in `/etc/ssl/openssl.cnf`:

```ini
openssl_conf = openssl_init

[openssl_init]
providers = provider_sect
ssl_conf = ssl_sect

[provider_sect]
default = default_sect
oqsprovider = oqsprovider_sect

[oqsprovider_sect]
activate = 1

[default_sect]
activate = 1

[ssl_sect]
system_default = system_default_sect

[system_default_sect]
Groups = x25519_mlkem768
```

Verify what actually loaded instead of trusting the config:

```bash
openssl list -kem-algorithms -provider oqsprovider
openssl list -signature-algorithms -provider oqsprovider
```

The provider also exposes hybrid groups, which is what you want: a classical X25519 exchange combined with ML-KEM so that a break in either algorithm alone does not sink the session. The catch is operational, not cryptographic — you now own a native library built from a research repository, and every OpenSSL upgrade can break ABI compatibility. There are prebuilt container images (`openquantumsafe/oqs-ossl3`) that sidestep the build, which is the sane way to evaluate before committing.

## PQClean — For People Who Need One Scheme, Not a Framework

PQClean is a curated collection of clean, portable, dependency-free implementations of the NIST post-quantum schemes. It is not a library you link against as a whole; it is a source tree you copy from. Each scheme builds standalone, with a stable namespaced API.

```bash
git clone https://github.com/PQClean/PQClean.git
cd PQClean
make -C crypto_kem/ml-kem-768        # produces libml-kem-768_clean.a
make -C crypto_sign/ml-dsa-65
```

The API is a namespaced variant of the reference code, which means multiple schemes can coexist in one binary without symbol collisions:

```c
#include "api.h"

uint8_t pk[PQCLEAN_MLKEM768_CLEAN_CRYPTO_PUBLICKEYBYTES];
uint8_t sk[PQCLEAN_MLKEM768_CLEAN_CRYPTO_SECRETKEYBYTES];
uint8_t ct[PQCLEAN_MLKEM768_CLEAN_CRYPTO_CIPHERTEXTBYTES];
uint8_t ss[PQCLEAN_MLKEM768_CLEAN_CRYPTO_BYTES];

PQCLEAN_MLKEM768_CLEAN_crypto_kem_keypair(pk, sk);
PQCLEAN_MLKEM768_CLEAN_crypto_kem_enc(ct, ss, pk);
```

This is the right choice for firmware, bootloaders, and shipping a scheme inside a proprietary protocol. It is the wrong choice if you expected a package manager to keep it patched — PQClean is a snapshot by design, and you are responsible for re-vendoring when the reference implementations change.

## OpenSSL 3.5 — The Boring, Correct Answer

OpenSSL 3.5 shipped native ML-KEM, ML-DSA, and SLH-DSA, and made the hybrid `X25519MLKEM768` group the default for TLS 1.3 clients. That single default is the biggest practical change in the ecosystem: an unmodified 3.5 client will negotiate post-quantum key exchange against any server that supports it.

```bash
# Generate an ML-KEM-768 keypair
openssl genpkey -algorithm ML-KEM-768 -out mlkem768.pem

# Inspect the parameters
openssl pkey -in mlkem768.pem -text -noout | head -20

# Test a hybrid handshake against a remote host
openssl s_client -connect example.com:443 -groups X25519MLKEM768 -brief </dev/null

# Run a local test server that prefers the hybrid group
openssl s_server -accept 4433 -cert cert.pem -key key.pem -groups X25519MLKEM768
```

Signing works the same way:

```bash
openssl genpkey -algorithm ML-DSA-65 -out mldsa65.pem
openssl req -new -x509 -key mldsa65.pem -subj "/CN=pqc-test" -days 30 -out pqc.crt
```

If you only need standard algorithms and you can upgrade OpenSSL, stop here. There is no reason to introduce a provider for functionality the vendor now ships — the certificate tooling, the package maintainers, and your monitoring all already understand it. If you want the broader picture of how these libraries relate to each other, our [TLS implementation libraries comparison](../2026-06-21-tls-ssl-implementation-libraries-openssl-boringssl-libressl-rustls/) covers the OpenSSL/BoringSSL/rustls split in detail.

## The Part Nobody Warns You About: Handshake Size

ML-KEM is fast. ML-KEM is not small. The numbers:

| Item | Bytes |
|---|---|
| X25519 key share (classical) | 32 |
| ML-KEM-768 encapsulation key | 1,184 |
| ML-KEM-768 ciphertext | 1,088 |
| X25519MLKEM768 client key share | 1,216 |
| Ed25519 signature | 64 |
| ML-DSA-65 signature | 3,309 |
| ML-DSA-65 public key | 1,952 |
| SLH-DSA-SHA2-128s signature | 7,856 |

A TLS 1.3 ClientHello carrying a hybrid key share grows by more than a kilobyte. That routinely pushes it past a single 1,500-byte MTU, so it fragments across two TCP segments — and a small but real population of middleboxes, load balancers, and older firewalls mishandle fragmented ClientHellos or drop them. Certificate chains get worse: three ML-DSA-65 certificates with signatures add roughly 10 KB to every full handshake, which is why session resumption and OCSP stapling stop being optimizations and start being requirements.

Two practical mitigations, in order of impact: enable TLS 1.3 session resumption aggressively so the big handshake happens once per client, and prefer the hybrid group over pure ML-KEM so you keep classical interoperability while the long tail of clients catches up.

## Migration Checklist for Self-Hosted Stacks

1. **Inventory what terminates TLS.** Reverse proxies, mail servers, VPN concentrators, internal CA, and anything with a pinned certificate. Post-quantum key exchange is negotiated per connection; if one hop is classical, the session is classical.
2. **Upgrade the terminator, not the app.** Nginx, HAProxy, Caddy, and Envoy inherit whatever OpenSSL (or BoringSSL) they link against. Check with `openssl version -a` and your package's build flags before planning provider hacks.
3. **Test fragmentation explicitly.** Run handshakes through your real load balancer with `openssl s_client -groups X25519MLKEM768` and watch for retries. A handshake that works on localhost and fails through a cloud LB is a middlebox problem, not a crypto problem.
4. **Keep classical fallback enabled.** Disabling X25519 entirely breaks older clients and gives you no security benefit today.
5. **Plan the signature migration separately.** Key exchange can be hybridized today with zero client changes; certificate signatures require every verifier in the chain to understand ML-DSA. Do key exchange first, signatures later.
6. **Record your timeline.** If NIST IR 8547 holds, RSA and ECDSA are deprecated after 2030. Internal CAs with ten-year roots are already overdue for a rotation plan — pair this work with the automation described in our [certificate automation guide](../2026-04-19-cert-manager-vs-lego-vs-acme-sh-self-hosted-tls-certificate-automation-guide-2026/) and the [mTLS deployment patterns](../2026-04-24-self-hosted-mutual-tls-mtls-nginx-caddy-traefik-envoy-guide-2026/) used for service-to-service traffic.

## Common Pitfalls

- **Treating liboqs as production-ready.** Its own README frames it as a prototyping and experimentation library. Shipping it as your only crypto layer means you own the audit.
- **Forgetting the provider is a shared object.** A distro OpenSSL upgrade that changes ABI will silently disable oqs-provider, and your handshake falls back to classical without an obvious error. Alert on negotiated group, not on "TLS works".
- **Assuming FIPS compliance carries over.** Neither liboqs nor oqs-provider is FIPS-validated. If you need a validated module, native OpenSSL with its FIPS provider is the only path.
- **Benchmarking on a laptop and extrapolating.** ML-KEM's cost is dominated by polynomial arithmetic and is genuinely cheap, but the real regression in production is bytes on the wire, not CPU cycles.
- **Mixing certificate and key-exchange migrations.** They have different client-support requirements; bundling them doubles the blast radius.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Post-Quantum TLS in 2026: liboqs vs PQClean vs OpenSSL 3.5 Compared",
  "description": "A practical comparison of liboqs, oqs-provider, PQClean and native OpenSSL 3.5 post-quantum support, with ML-KEM deployment commands, handshake size analysis and a migration checklist.",
  "datePublished": "2026-11-05",
  "dateModified": "2026-11-05",
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

### Is ML-KEM safe to deploy in production in 2026?

Yes, with the hybrid group. ML-KEM (FIPS 203) has been standardized since August 2024, and `X25519MLKEM768` combines it with a classical exchange so that a future break in either primitive alone does not compromise recorded sessions. Pure ML-KEM-only deployments are the risky configuration, not hybrid ones.

### Do I need liboqs if OpenSSL 3.5 already supports ML-KEM?

No. liboqs matters when you need algorithms OpenSSL has not shipped (Falcon, HQC, Classic McEliece), when you are benchmarking schemes with a uniform API, or when you cannot upgrade the OpenSSL your TLS terminator links against. For standard ML-KEM/ML-DSA on a modern stack, native OpenSSL is simpler and supported.

### How much slower is post-quantum TLS?

Key encapsulation is not the bottleneck — ML-KEM-768 encapsulation and decapsulation take microseconds on commodity x86. The measurable cost is bandwidth and latency from larger handshakes: roughly 1.2 KB extra per ClientHello and up to ~10 KB extra for a full ML-DSA certificate chain, which mostly hurts the first connection and is amortized by session resumption.

### Can I use post-quantum certificates with ordinary clients today?

Mostly no. Browsers and operating-system trust stores are still rolling out ML-DSA support, so a certificate signed only with ML-DSA will fail verification for many clients. The practical 2026 approach is post-quantum key exchange now (transparent to clients), post-quantum signatures when your client population supports them.

### What about embedded devices with tight flash budgets?

Use PQClean and vendor exactly one scheme. Its per-scheme source trees have no build-system dependencies beyond a C compiler, and the namespaced API lets several schemes coexist. Expect a few tens of kilobytes of code plus the key sizes above — ML-KEM-768's 1,184-byte public key is often the binding constraint, not the code size.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
