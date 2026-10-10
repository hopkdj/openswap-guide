---
title: "ASN.1 Codec Libraries in 2026: asn1c vs rasn vs asn1tools vs ASN1js Compared"
date: "2026-10-10"
tags: ["asn1", "encoding", "serialization", "protocols", "developer-tools"]
draft: false
---

Your TLS certificate, your LDAP bind request, your SNMP trap, and the signaling messages inside a 5G core are all encoded in the same thing: **ASN.1**, a data description language from 1984 that refuses to die because nothing else encodes a schema into a predictable, standards-locked byte stream. If you write tooling that touches certificates, PKI, telecom stacks, or industrial protocols, you will eventually need an ASN.1 codec — and picking the wrong one costs you weeks.

The core decision is architectural, not cosmetic. You either **generate code from a schema at build time** (asn1c, and rasn's compiler) or **parse the schema at runtime into a generic object tree** (asn1tools, ASN1js). That single choice determines your binary size, your type safety, and how much glue code you write.

## TL;DR / Quick Verdict

- **Rust project, want compile-time types and `no_std`?** → **rasn**. Derive macros, every major codec, and a separate compiler crate for schema-driven generation.
- **C/C++ with a hard memory and flash budget (embedded, telecom, firmware)?** → **asn1c**. It emits plain C structs with no runtime dependency at all.
- **Python glue, verification scripts, test harnesses, or PE/PSA message crafting?** → **asn1tools**. One `compile_files()` call and you are encoding DER from a `.asn` file.
- **Browser or Node.js decoding untrusted certificates and PKI structures?** → **ASN1js**. Pure JavaScript BER/DER, zero native dependencies.

If you are encoding protocol messages for a 5G or RRC stack, use asn1c. If you are writing a certificate linter in Rust, use rasn. If you are scripting, use asn1tools. **Do not use a runtime-reflection library in a hot loop, and do not hand-roll DER parsing** — the canonicalization rules will bite you.

## Comparison Table

| Feature | asn1c | rasn | asn1tools | ASN1js |
|---|---|---|---|---|
| Language / output | C (code generator) | Rust (derive + generated) | Python (runtime) | JavaScript (runtime) |
| Model | Compile-time codegen | Compile-time codegen + macros | Runtime schema compile | Runtime object tree |
| BER | Yes | Yes | Yes | Yes |
| DER | Yes (via BER rules) | Yes | Yes | Yes |
| PER / UPER | Yes | Yes | Yes | No |
| OER / COER | Partial | Yes | Yes | No |
| XER / JER | Partial | Yes (JER) | Yes | No |
| Runtime dependency | None | Rust crate | Python package | npm package |
| `no_std` / embedded | C, any freestanding target | Yes | No | No |
| Schema input | `.asn1` file → C | `.asn1` → Rust (compiler crate) or macros | `.asn` / dict / text | Hand-built objects |
| License | BSD-2-Clause | MIT / Apache-2.0 | MIT | BSD-2-Clause |
| GitHub stars | **1,179** | 387 | 337 | 300 |
| Last push | 2026-06-28 | 2026-10-07 | 2026-09-01 | 2026-10-06 |
| Best for | Embedded, telecom, firmware | Rust services, cert tooling | Scripts, testing, PKI research | Browser PKI, parsers |

Star counts and last-push dates were pulled live from the GitHub API at the time of writing. **asn1c is the most-starred by a wide margin (1,179)**, but that mostly reflects its age and its lock on telecom: it has been the reference tool for 3GPP RRC and S1AP work for two decades.

## Scenario Decision Matrix

| Your situation | Pick | Reason |
|---|---|---|
| Encoding RRC / S1AP / NGAP messages in C | **asn1c** | Zero runtime, generates the structs the 3GPP sample code expects |
| Rust microservice validating X.509 from a TLS stream | **rasn** | Derive macros, `no_std`, no C FFI boundary |
| Python script that dumps a PE/PSA blob from a smartcard | **asn1tools** | `compile_files()` in three lines, CLI included |
| Browser extension inspecting certificate chains | **ASN1js** | Pure JS, runs where native code cannot |
| Firmware on a 64 KB MCU | **asn1c** | Emitted C is freestanding, no allocator required with static mode |
| Teaching or prototyping a new schema | **asn1tools** or **ASN1js** | No build step; edit the schema and re-run |
| High-throughput binary parsing with strict types | **rasn** | Zero-copy decode into typed Rust structs |
| Need PER *and* readable XER output | **asn1tools** | Broadest codec coverage in one runtime API |

## asn1c — The Embedded Workhorse

`vlm/asn1c` (1,179 stars, actively maintained, last push 2026-06-28) is a compiler, not a library. You feed it a schema and it writes C source files that encode and decode messages with **no runtime dependency whatsoever** — no heap library, no JSON layer, no allocator unless you opt in.

Build it from source:

```bash
git clone https://github.com/vlm/asn1c.git
cd asn1c
test -f configure || autoreconf -iv
./configure
make -j"$(nproc)"
sudo make install
```

Then compile a schema into C:

```bash
# Generate BER + PER decoders for a 3GPP-style schema
asn1c -fcompound-names -fno-include-deps -gen-PER -pdu=RRCConnectionRequest rrc.asn1

# Result: RRCConnectionRequest.c/.h, plus a Makefile.am.libasn1codec
ls *.c *.h | head
```

The generated API is a plain function pair per type:

```c
/* Encode a structure into a caller-provided buffer. */
asn_enc_rval_t er = der_encode_to_buffer(
    &asn_DEF_RRCConnectionRequest, /* type descriptor */
    &message,                      /* populated C struct */
    buffer, sizeof(buffer));

if (er.encoded == -1) {
    fprintf(stderr, "encode failed at %s\n", er.failed_type->name);
}
```

**Choose asn1c when binary size is a requirement, not a preference.** A generated BER decoder for a modest schema lands in the tens of kilobytes, and `-fno-constraints` trims the validation tables further. The trade-off is ergonomics: you are managing C structs, tag numbers, and `asn_TYPE_descriptor_t` pointers by hand, and a schema change means a full regeneration plus a rebuild of everything that included the header.

## rasn — Rust, Derives, and `no_std`

`librasn/rasn` (387 stars, last push 2026-10-07 — the most recently updated project here) is a **safe `#[no_std]` ASN.1 codec framework**. Instead of generating code first, you describe your structures with derive macros and let the crate implement encoding and decoding for you. A companion repository, `librasn/compiler`, generates Rust bindings from `.asn1` files when you would rather drive everything from a schema.

```toml
# Cargo.toml
[dependencies]
rasn = { version = "0.20", features = ["derive"] }
```

```rust
use rasn::prelude::*;

#[derive(AsnType, Encode, Decode, Debug)]
#[rasn(automatic_tags)]
struct Person {
    age: Option<String>,
    name: Option<String>,
}

fn main() -> Result<(), rasn::error::EncodeError> {
    let p = Person { age: Some("34".into()), name: Some("Ada".into()) };
    let der = rasn::der::encode(&p)?;      // canonical DER
    let back: Person = rasn::der::decode(&der).unwrap();
    println!("{} bytes, round-tripped: {:?}", der.len(), back);
    Ok(())
}
```

The `automatic_tags` attribute is the part worth understanding: ASN.1 distinguishes **automatic** tagging (each field gets an implicit tag assigned in order) from **explicit** tagging, and picking the wrong one silently changes the wire format. rasn makes you state the intent, which is a feature — a mismatched tag convention is the single most common cause of "the decoder accepts it but the other side rejects it" bugs.

`no_std` support means rasn drops into embedded Rust, bootloaders, and kernel-adjacent code without an allocator for fixed-size types. Microcontroller firmware in Rust is the strongest reason to prefer rasn over reaching for C.

## asn1tools — Python's Runtime Schema Compiler

`eerimoq/asn1tools` (337 stars, last push 2026-09-01) takes the opposite approach: **no code generation, just parse the schema at runtime**. Install and go:

```bash
pip install asn1tools
```

```python
import asn1tools

spec = asn1tools.compile_files('tests/files/foo.asn', 'der')
encoded = spec.encode('Question', {'id': 1, 'question': 'Is 1+1=3?'})
# bytearray(b'0\x0e\x02\x01\x01\x16\x09Is 1+1=3?')

decoded = spec.decode('Question', encoded)
# {'id': 1, 'question': 'Is 1+1=3?'}
```

Switch `'der'` to `'per'`, `'uper'`, `'oer'`, `'aper'`, `'xer'`, or `'jer'` and the exact same data structure re-encodes under a different codec — the widest codec coverage of any tool in this comparison. That makes it the natural choice for **conformance testing**: encode a message in DER, decode it, re-encode in PER, and diff the logical contents. The package also ships a CLI for one-off conversions.

The cost of runtime compilation is startup latency and weaker static typing. For a long-running service that decodes millions of messages per second, that reflection overhead is measurable; for a test harness or a one-shot extraction script, it is irrelevant.

## ASN1js — BER/DER in the Browser

`PeculiarVentures/ASN1js` (300 stars, last push 2026-10-06) is a **pure JavaScript implementation of a full ASN.1 BER decoder and encoder**. It is the parsing layer underneath PKI.js, which means it is battle-tested against the messy real-world certificates that browsers actually encounter — including ones that are technically non-conformant.

```javascript
import * as asn1js from "asn1js";

const buffer = new Uint8Array(derBytes).buffer;
const asn1 = asn1js.fromBER(buffer);

if (asn1.offset === -1) {
  console.error("Malformed DER");
} else {
  const cert = new pkijs.Certificate({ schema: asn1.result });
  console.log(cert.subject.typesAndValues.map(tv => tv.type + "=" + tv.value.valueBlock.value));
}
```

Two properties matter here. First, it runs **where native code cannot**: a browser extension inspecting the certificate chain of the current page has no other option. Second, the library exposes the raw BER structure tree, which is exactly what you want for a certificate linter or a signature-verification tool — you need to see the *original bytes* of the `tbsCertificate`, not a re-serialized approximation of them.

Do not attempt PER with ASN1js; the rules-based, bit-packed encodings are not implemented. If your workload is certificates and PKI structures, that gap will never bother you.

## Pitfalls That Cost Real Debugging Time

**DER is not "just BER".** Signature verification requires **canonical** DER: definite lengths, sorted SET OF elements, minimal integer encoding. Many libraries happily *decode* BER with indefinite lengths but silently produce non-canonical output, so a signature you computed from re-encoded bytes will fail verification against the original. Always verify a signature over the original byte range, never over a decode/re-encode round trip.

**Tagging mode changes the wire format.** Implicit, explicit, and automatic tagging all produce different bytes for the same logical structure. When a peer rejects your message with a generic "decode error", check tagging before you check anything else — especially when porting a schema from one library to another.

**Watch the schema's version drift.** Real-world protocols publish multiple schema revisions (often dozens). Generating from the wrong revision produces a decoder that fails on exactly the fields that changed. Pin the schema revision in your build, and treat regeneration as a code change that requires review.

**Allocation behavior in generated C.** asn1c's `OCTET STRING` and `SEQUENCE OF` handling can allocate per message. In embedded use, prefer the static/`-fno-...` configuration flags and pre-sized buffers, and check the `asn_enc_rval_t` return value on every call — a truncated buffer returns `-1` with `failed_type` set, and ignoring it produces silently corrupt output.

**Object identifiers are not strings.** Handle OIDs as parsed, compared structures, not as text. Two different textual spellings can denote the same OID, and string comparison will produce false mismatches in allowlists and policy checks.

## Why Use a Codec Library at All?

You might reasonably ask why anyone keeps a 1984 standard alive when CBOR, MessagePack, and Protocol Buffers all exist. The answer is the **schema is the contract**. ASN.1 decouples the wire format from any implementation: a C encoder written in 2001 and a Rust decoder written in 2026 agree byte-for-byte because both follow the same encoding rules and the same published schema. That property is why telecom, aviation, and payments standards are still specified this way.

For adjacent serialization and tooling comparisons, see our [Protocol Buffers tooling guide](../2026-05-07-self-hosted-protobuf-tools-buf-protolock-protovalidate-guide/), our [cryptographic primitive library comparison](../2026-06-20-cryptographic-primitive-libraries-libsodium-botan-hacl/), and the [JWT library deep dive](../2026-06-20-jwt-authentication-libraries-pyjwt-jsonwebtoken-jose-jjwt-golang/) if you are choosing a token format rather than a wire encoding. If your structures are tables rather than trees, [TOML parsing libraries](../2026-09-27-toml-parsing-libraries-tomllib-tomlkit-toml-rs-go-toml-comparison/) is the better reference.

## FAQ

**Which ASN.1 library should I use for parsing X.509 certificates?**
For Rust, use rasn. For browser or Node.js work, use ASN1js, which is the parsing layer under PKI.js and handles real-world, occasionally non-conformant certificates. For Python analysis scripts, asn1tools plus pyasn1 gives you a fast path to dumping a certificate's fields. Avoid hand-writing DER parsing for certificates specifically — the canonicalization rules around `tbsCertificate` bytes will break signature verification.

**Is asn1c still maintained?**
Yes. The repository shows active commits, most recently in 2026, and it remains the reference generator for 3GPP protocol stacks. Its slower release cadence reflects stability rather than abandonment: telecom vendors rely on byte-identical output across versions, which discourages churn.

**What is the difference between BER, DER, and PER?**
BER is the flexible, self-describing base encoding with optional indefinite lengths. DER is a canonical subset of BER with definite lengths and sorted sets, required wherever signatures are computed over encoded bytes. PER and UPER are packed, bit-level encodings driven entirely by schema, producing the smallest messages — with the trade-off that a schema change breaks compatibility.

**Can I use rasn without an allocator?**
Yes. rasn is a `no_std` framework, and fixed-size ASN.1 types can be encoded and decoded without dynamic allocation, which is why it is a reasonable choice for embedded Rust firmware.

**How do I convert between BER and DER reliably?**
Decode with a library that exposes the raw BER tree, then re-encode using a canonical DER encoder, and diff the resulting bytes against the source. If they differ, the input was not canonical — treat that as a finding, not a bug, especially in certificate-inspection tooling.

**Do I need asn1c if I only need PER for a telecom stack?**
That is exactly asn1c's sweet spot. Use `-gen-PER` when invoking it, generate the C, and link the produced code. rasn covers PER too, so choose based on whether your stack is C or Rust.

---

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "ASN.1 Codec Libraries in 2026: asn1c vs rasn vs asn1tools vs ASN1js Compared",
  "description": "A practical 2026 comparison of ASN.1 encoding libraries: asn1c vs rasn vs asn1tools vs ASN1js. Codec coverage, license, stars, code samples and pitfalls.",
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

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
