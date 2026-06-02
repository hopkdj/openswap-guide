---
title: "Self-Hosted DNSSEC Key Management: dnssec-keygen vs ldns-keygen vs Knot DNS keymgr"
date: "2026-06-02"
tags: ["dns", "dnssec", "security", "bind", "knot-dns", "ldns", "key-management"]
draft: false
---

## Introduction

DNSSEC protects DNS responses from forgery by cryptographically signing zone data. But the operational challenge isn't the signing itself — it's **key management**. Generating, rotating, and revoking DNSSEC keys securely is critical: a compromised ZSK can poison an entire domain's cache, and misconfigured KSK rollovers can make your zone unreachable. This article compares three battle-tested DNSSEC key management toolchains: **dnssec-keygen** (BIND), **ldns-keygen** (NLnet Labs), and **keymgr** (Knot DNS).

| Feature | dnssec-keygen (BIND) | ldns-keygen (ldns) | keymgr (Knot DNS) |
|---------|---------------------|-------------------|-------------------|
| **Parent Project** | ISC BIND 9 | NLnet Labs ldns | CZ.NIC Knot DNS |
| **Stars** | 743 | 352 | 306 |
| **Algorithm Support** | All (5-16) | All (5-16) | ECDSA, EdDSA, RSA |
| **Key Format** | .key/.private files | .key/.private files | PEM, PKCS#8 |
| **HSM Support** | PKCS#11 native | PKCS#11 via OpenSSL | PKCS#11 native |
| **Automated Rollover** | Manual (dnssec-settime) | Manual (scripts) | Built-in (keymgr) |
| **Algorithm Rollover** | Supported | Manual | Automatic |
| **Last Updated** | June 2026 | May 2026 | June 2026 |

## dnssec-keygen: The BIND Standard

`dnssec-keygen` is part of ISC BIND 9, the most widely deployed DNS server. It generates DNSSEC key pairs and outputs them in BIND's `.key`/`.private` file format. It supports every DNSSEC algorithm from RSA/SHA-1 (algorithm 5) to Ed25519 (algorithm 15).

### Key Generation Examples

```bash
# Generate a Zone Signing Key (ZSK) with ECDSA P-256
dnssec-keygen -a ECDSAP256SHA256 -n ZONE example.com

# Generate a Key Signing Key (KSK)
dnssec-keygen -a ECDSAP256SHA256 -n ZONE -f KSK example.com

# Generate with Ed25519 (algorithm 15)
dnssec-keygen -a ED25519 -n ZONE example.com

# Output files:
# Kexample.com.+013+12345.key    (public key)
# Kexample.com.+013+12345.private (private key)
```

### Key Rotation with dnssec-settime

BIND handles key rotation manually using `dnssec-settime`:

```bash
# Publish the new ZSK immediately but don't activate for signing yet
dnssec-settime -P now -A +2d Kexample.com.+013+12345

# After 2 days (propagation), start signing with the new key
dnssec-settime -I +30d -D +60d Kexample.com.+013+12345

# Revoke the old key after the new key's signatures have propagated
dnssec-settime -D now Kexample.com.+013+11111
```

The BIND toolchain requires careful manual orchestration of timing parameters (`-P` publish, `-A` activate, `-I` inactive, `-D` delete). A single misconfigured time window can create a DNSSEC validation gap.

### HSM Integration

```bash
# Generate key in a PKCS#11 HSM (SoftHSM2 for testing)
softhsm2-util --init-token --slot 0 --label "DNSSEC"
dnssec-keygen -a ECDSAP256SHA256 -n ZONE -E pkcs11 example.com

# The private key stays in the HSM; only the public key file is created
```

## ldns-keygen: The NLnet Labs Tool

`ldns-keygen` from NLnet Labs offers a more scriptable, Unix-philosophy approach. It's part of the `ldns` library, which provides C and Python bindings for DNS operations.

### Key Generation

```bash
# Generate ECDSA P-256 ZSK
ldns-keygen -a ECDSAP256SHA256 example.com

# Generate Ed25519 KSK
ldns-keygen -a ED25519 -k example.com

# Output RSA key with specific size
ldns-keygen -a RSASHA256 -b 2048 example.com
```

### Scripting Key Rotation

ldns-keygen doesn't have built-in rollover scheduling, but its clean output format makes scripting easy:

```bash
#!/bin/bash
# Automated ZSK rotation script for ldns
DOMAIN="example.com"
KEYDIR="/etc/dns/keys"

# Create new ZSK
NEWKEY=$(ldns-keygen -a ECDSAP256SHA256 "$DOMAIN")
echo "New ZSK: $NEWKEY"

# Wait for DNS propagation (TTL × 2)
sleep 7200

# Sign zone with both keys
ldns-signzone -n -o "$DOMAIN" "$DOMAIN.zone" "$NEWKEY" "$CURRENT_KSK"

# Mark old key for deletion after signature expiry
CURRENT_EPOCH=$(date +%s)
EXPIRY=$((CURRENT_EPOCH + 2592000))
echo "Old key expires at: $(date -d @$EXPIRY)"

# Schedule removal via cron
echo "0 0 $(date -d @$EXPIRY +%d) $(date -d @$EXPIRY +%m) * rm $KEYDIR/$OLDKEY.*" >> /etc/crontab
```

### Docker Compose for Testing

```yaml
version: "3.8"
services:
  dnssec-lab:
    image: ubuntu:24.04
    command: >
      sh -c "apt-get update && apt-get install -y ldnsutils bind9-dnsutils knot-dnsutils &&
             ldns-keygen -a ECDSAP256SHA256 test.example &&
             cat Ktest.example.*"
```

## Knot DNS keymgr: Automated Key Management

Knot DNS's `keymgr` takes a declarative approach: you define a policy, and it handles generation, rotation, and cleanup automatically. This is the most operationally mature solution for teams that want minimal DNSSEC key management overhead.

### Policy-Based Key Management

```bash
# Define a DNSSEC policy
keymgr example.com init

# Configure policy in Knot's configuration
cat >> /etc/knot/knot.conf << 'EOF'
policy:
  - id: default
    algorithm: ecdsap256sha256
    ksk-lifetime: 365d
    zsk-lifetime: 30d
    zsk-rollover: 14d

zone:
  - domain: example.com
    dnssec-signing: on
    dnssec-policy: default
EOF

# keymgr automatically generates and rotates keys
keymgr example.com status
# Output:
# KSK: active (ID: abc123, expires in 340d)
# ZSK: active (ID: def456, expires in 28d, rollover in 12d)
```

### Automated Rollover

Knot handles the entire ZSK rollover process without manual intervention:

```
Day 0:  ZSK1 active (signing)
Day 16: ZSK2 published (not yet signing)
Day 20: ZSK2 active (signing) + ZSK1 published
Day 30: ZSK1 removed, ZSK2 active
```

```bash
# Force immediate rollover for emergency key compromise
keymgr example.com ds-generate
keymgr example.com rollover

# Check rollover status
keymgr example.com status --verbose
```

### HSM Integration

```bash
# PKCS#11 HSM configuration
cat >> /etc/knot/knot.conf << 'EOF'
keystore:
  - id: hsm
    backend: pkcs11
    config: "pkcs11:token=DNSSEC;pin-value=secret /usr/lib/softhsm/libsofthsm2.so"

policy:
  - id: hsm-policy
    keystore: hsm
    algorithm: ecdsap256sha256
EOF
```

## Security Comparison

| Aspect | dnssec-keygen | ldns-keygen | keymgr |
|--------|--------------|-------------|--------|
| **Private key storage** | Filesystem (0600) | Filesystem (0600) | Filesystem or HSM |
| **HSM support** | PKCS#11 | Via OpenSSL engine | Native PKCS#11 |
| **Algorithm deprecation** | Manual | Manual | Automatic (policy) |
| **Key compromise recovery** | Emergency manual rollover | Emergency script | `keymgr rollover` command |
| **Audit logging** | System logs | Shell history | Structured JSON logs |

## Why Self-Host Your DNSSEC Infrastructure?

Running your own DNSSEC signing infrastructure gives you complete control over your cryptographic material. When you delegate DNSSEC to a managed DNS provider, they hold your private keys — a compromise at the provider level can poison your entire zone. Self-hosting with HSM-backed key storage ensures that only you control the signing keys, and automated monitoring can alert you to any unexpected zone changes.

The operational burden of manual DNSSEC key rotation is one of the primary reasons many organizations still avoid deploying DNSSEC. Tools like Knot DNS's keymgr eliminate this pain point by automating the entire lifecycle — from initial key generation to emergency rollover — reducing the risk of misconfiguration that can make your domain unreachable. For teams managing dozens of zones, the difference between manual BIND scripts and Knot's declarative policy approach is measured in hours of maintenance per month.

For a comprehensive comparison of authoritative DNS servers, see our [guide to PowerDNS vs BIND9 vs NSD vs Knot DNS](../2026-04-18-powerdns-vs-bind9-vs-nsd-vs-knot-self-hosted-authoritative-dns-2026/). If you're interested in DNS-layer security beyond DNSSEC, check our [guide to DNS firewall and RPZ implementation](../2026-04-21-self-hosted-dns-firewall-rpz-unbound-powerdns-bind9-knot-guide-2026/).

Understanding DNS protocol internals is essential for secure zone management. Our [DNS-over-QUIC encryption guide](../2026-04-21-knot-resolver-vs-blocky-vs-dnscrypt-proxy-self-hosted-dns-over-quic-guide-2026/) covers the latest transport-layer security improvements for DNS queries.

## FAQ

### How often should I rotate DNSSEC keys?

**ZSK**: Every 30-90 days. Frequent rotation limits the impact of key compromise. **KSK**: Every 12-24 months. KSK rotation requires updating the DS record at your registrar, so it's a more involved process.

### What happens if my DNSSEC keys expire?

DNSSEC keys don't technically "expire" — validators check signature validity periods, not key expiry. If signatures expire before new ones are published, validators will reject your zone's responses (SERVFAIL). Always ensure your signer refreshes signatures before the previous set expires.

### Can I use Ed25519 for DNSSEC signing?

Yes. Ed25519 (algorithm 15) is supported by all three tools and is the recommended algorithm for new deployments. It offers 128-bit security with smaller keys and faster signing than RSA. Major resolvers (Google Public DNS, Cloudflare, Quad9) all validate Ed25519-signed zones.

### How do I validate that my DNSSEC configuration is correct?

```bash
# Check DNSSEC chain with delv (BIND tool)
delv @8.8.8.8 +dnssec example.com

# Online validators
# https://dnsviz.net/ — visual DNSSEC chain analysis
# https://dnssec-analyzer.verisignlabs.com/ — Verisign's validator

# Local validation with ldns
ldns-verify-zone example.com.zone
```

### What's the difference between algorithm rollover and key rollover?

**Key rollover**: Replace the key but keep the same algorithm (e.g., new ECDSA P-256 key). This is routine. **Algorithm rollover**: Switch from one algorithm to another (e.g., RSA to Ed25519). This requires updating DS records, waiting for propagation, and ensuring all resolvers support the new algorithm. Knot DNS's keymgr is the only tool that handles algorithm rollovers automatically.

### Do I need a Hardware Security Module (HSM) for DNSSEC?

For most self-hosted deployments, filesystem-based key storage with strict permissions (0400) is sufficient. HSMs (including software HSMs like SoftHSM2) become important when: (a) you manage high-value domains, (b) you need compliance (PCI-DSS, FIPS), or (c) you want physical separation between your DNS server and signing keys.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted DNSSEC Key Management: dnssec-keygen vs ldns-keygen vs Knot DNS keymgr",
  "description": "Compare DNSSEC key management tools: BIND dnssec-keygen, NLnet Labs ldns-keygen, and Knot DNS keymgr. Covers key generation, rotation, HSM integration, and security best practices.",
  "datePublished": "2026-06-02",
  "dateModified": "2026-06-02",
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
