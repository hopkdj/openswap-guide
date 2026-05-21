---
title: "Self-Hosted DNS TLSA/DANE Management: hash-slinger vs ldns vs Knot DNS"
date: "2026-05-21"
tags: ["dns", "security", "tlsa", "dane", "tls", "certificates", "self-hosted"]
draft: false
---

DANE (DNS-based Authentication of Named Entities) is a protocol that uses DNSSEC-secured TLSA records to associate TLS certificates with domain names. Instead of relying solely on certificate authorities (CAs) for trust validation, DANE allows domain owners to publish certificate fingerprints directly in DNS. This eliminates the risk of rogue CA-issued certificates and gives administrators complete control over TLS trust chains. In this guide, we compare three open-source tools for managing TLSA records and DANE validation: hash-slinger, ldns (with ldns-dane), and Knot DNS.

## hash-slinger

hash-slinger is a collection of command-line tools specifically designed for TLSA record management. It provides utilities to generate, verify, and query TLSA records, making it the most focused tool for DANE operations.

**Key Features:**
- TLSA record generation from certificates (PEM, DER formats)
- Certificate-to-TLSA fingerprint conversion (SHA-256, SHA-512)
- TLSA record verification against live services
- Support for all TLSA usage and selector combinations
- DANE-TA (Trust Anchor) and DANE-EE (End Entity) modes

**Installation:**
```bash
# Debian/Ubuntu
apt-get install hash-slinger -y

# From source
git clone https://github.com/letoams/hash-slinger.git
cd hash-slinger
python3 setup.py install
```

**Generating TLSA records:**
```bash
# Generate a TLSA record for an HTTPS certificate
tlsa --create --certificate /etc/letsencrypt/live/example.com/fullchain.pem   --usage 3 --selector 1 --match 1 _443._tcp.example.com

# Generate TLSA from a live service (fetches certificate automatically)
tlsa --create --usage 3 --selector 1 --match 1   --connect example.com:443 _443._tcp.example.com

# Output for DNS zone file:
# _443._tcp.example.com. IN TLSA 3 1 1 <hash>
```

**Verifying TLSA records:**
```bash
# Verify a TLSA record against a live service
tlsa --verify --connect example.com:443 _443._tcp.example.com

# Check TLSA record in DNS
tlsa --query _443._tcp.example.com

# Verify with specific DNS resolver
tlsa --query --server 8.8.8.8 _443._tcp.example.com
```

**Docker Compose for hash-slinger container:**
```yaml
version: "3.8"
services:
  hash-slinger:
    image: docker.io/debian:bookworm-slim
    volumes:
      - ./certs:/etc/certs:ro
      - ./output:/output
    entrypoint: ["bash", "-c"]
    command:
      - |
        apt-get update && apt-get install -y hash-slinger
        tlsa --create --certificate /etc/certs/fullchain.pem           --usage 3 --selector 1 --match 1 _443._tcp.example.com           > /output/tlsa-record.txt
        cat /output/tlsa-record.txt
    restart: "no"
```

hash-slinger is purpose-built for TLSA management. It handles certificate format conversion, hash computation, and DNS record formatting automatically. The tool supports all TLSA parameter combinations defined in RFC 6698: usage (PKIX-TA, PKIX-EE, DANE-TA, DANE-EE), selector (Cert, SPKI), and matching type (Full, SHA-256, SHA-512).

## ldns (ldns-dane)

ldns is a DNS library developed by NLnet Labs that includes the `ldns-dane` command-line tool for DANE validation. While ldns is primarily a programming library, its DANE tool provides certificate validation against TLSA records.

**Key Features:**
- DANE validation for TLS connections
- Integration with ldns DNS resolution library
- Support for DNSSEC validation chain
- Certificate chain verification against TLSA records
- Batch processing for multiple domains

**Installation:**
```bash
# Debian/Ubuntu
apt-get install ldnsutils -y

# From source
git clone https://github.com/NLnetLabs/ldns.git
cd ldns
./configure --with-ssl
make
make install
```

**Validating DANE for a service:**
```bash
# Validate HTTPS certificate against TLSA record
ldns-dane -c 443 example.com

# Validate SMTP with STARTTLS
ldns-dane -c 25 -s example.com

# Validate with verbose output
ldns-dane -v -c 443 example.com

# Specify custom DNS resolver
ldns-dane -c 443 -s 8.8.8.8 example.com
```

**Generating TLSA records with ldns:**
```bash
# Generate TLSA record from a certificate file
ldns-dane -c 443 -g example.com

# Output the TLSA record for zone file insertion
ldns-dane -c 443 -g example.com >> zone-file.db
```

**Docker Compose for ldns DANE validation:**
```yaml
version: "3.8"
services:
  ldns-dane:
    image: docker.io/debian:bookworm-slim
    entrypoint: ["bash", "-c"]
    command:
      - |
        apt-get update && apt-get install -y ldnsutils
        ldns-dane -v -c 443 example.com
    restart: "no"
```

ldns-dane excels at validation — it fetches the TLSA record from DNS, verifies the DNSSEC signature chain, connects to the target service, retrieves the certificate, and compares the certificate fingerprint against the TLSA record. If any step fails, it reports the specific failure point.

## Knot DNS

Knot DNS is a high-performance authoritative DNS server that includes native TLSA record support and DANE management features. While Knot DNS is primarily a nameserver, its comprehensive DNSSEC tooling makes it an excellent platform for publishing and managing TLSA records.

**Key Features:**
- Native TLSA record type support in zone files
- DNSSEC signing of TLSA records (inline signing)
- Zone file management with kzonecheck validation
- High-performance authoritative serving
- Dynamic DNS update support for TLSA records

**Installation:**
```bash
# Debian/Ubuntu
apt-get install knot knot-dnsutils -y

# Configure Knot DNS
cat > /etc/knot/knot.conf << 'KNOT'
server:
  rundir: "/run/knot"
  user: knot:knot

log:
  - any: info

template:
  - id: default
    storage: "/var/lib/knot"
    file: "%s.zone"
    dnssec-signing: on
    dnssec-ksk-size: 2048
    dnssec-zsk-size: 1024

zone:
  - domain: example.com
    file: "example.com.zone"
KNOT

# Start Knot DNS
systemctl enable --now knot
```

**Adding TLSA records to a Knot DNS zone:**
```bash
# Generate TLSA record (using hash-slinger for the hash)
TLSA_RECORD=$(tlsa --create --usage 3 --selector 1 --match 1   --connect example.com:443 _443._tcp.example.com 2>/dev/null | tail -1)

# Add the TLSA record to the zone using kdnssec
kdnssecutil zone-sign example.com

# Or manually edit the zone file
cat >> /var/lib/knot/example.com.zone << EOF
$TLSA_RECORD
EOF

# Reload the zone
knotc zone-reload example.com
```

**Verifying TLSA records in Knot DNS:**
```bash
# Query TLSA record directly from the Knot DNS server
kdig @localhost _443._tcp.example.com TLSA

# Verify DNSSEC signatures on the TLSA record
kdig +dnssec @localhost _443._tcp.example.com TLSA

# Check zone integrity
kzonecheck /var/lib/knot/example.com.zone
```

**Docker Compose for Knot DNS with TLSA support:**
```yaml
version: "3.8"
services:
  knot-dns:
    image: docker.io/cznic/knot:latest
    ports:
      - "53:53/tcp"
      - "53:53/udp"
    volumes:
      - ./knot.conf:/etc/knot/knot.conf:ro
      - ./zones:/var/lib/knot
      - ./keys:/etc/knot/keys
    restart: unless-stopped
```

Knot DNS's primary value for DANE management is its reliable DNSSEC signing pipeline. TLSA records are only trusted when they are properly signed by DNSSEC, and Knot DNS handles this automatically through its inline signing feature. This ensures that every TLSA record published by your nameserver has a valid DNSSEC chain of trust.

## Comparison Table

| Feature | hash-slinger | ldns (ldns-dane) | Knot DNS |
|---------|-------------|-------------------|----------|
| **Primary Role** | TLSA management tool | DNS library + DANE validator | Authoritative DNS server |
| **TLSA Generation** | Yes (full support) | Yes (via ldns-dane -g) | Via zone file editing |
| **TLSA Verification** | Yes (against live services) | Yes (full DANE validation) | Via kdig queries |
| **DNSSEC Signing** | No (relies on external) | Validates DNSSEC chain | Yes (inline signing) |
| **Certificate Formats** | PEM, DER, PKCS#12 | PEM, DER | Zone file format |
| **DANE Validation Modes** | DANE-TA, DANE-EE | Full DANE validation | DNSSEC validation only |
| **Batch Processing** | Yes (shell scripts) | Yes (ldns-dane) | Via zone reload |
| **Dynamic DNS Update** | No | No | Yes (nsupdate) |
| **Performance Focus** | CLI utility | Library | High-performance server |
| **GitHub Stars** | 55+ (letoams/hash-slinger) | 350+ (NLnetLabs/ldns) | 305+ (CZ-NIC/knot) |
| **Last Updated** | Active (2026) | Active (2026) | Active (2026) |
| **Container Support** | Manual Dockerfile | Manual Dockerfile | Official image |

## Why Self-Host DNS TLSA/DANE Management?

The traditional TLS trust model relies on hundreds of certificate authorities worldwide. Any of these CAs can issue a certificate for your domain, creating a broad attack surface for certificate misissuance. DANE narrows this trust surface by allowing you to specify exactly which certificates are valid for your services through DNSSEC-secured TLSA records.

Self-hosting TLSA management gives you complete control over your TLS trust chain. You decide which certificates are valid, when they expire, and how trust is distributed. This is particularly important for organizations with internal PKI, private CAs, or strict compliance requirements that mandate certificate pinning.

For self-hosted services, DANE eliminates the need for public certificate authorities entirely. You can self-sign certificates, publish their fingerprints as TLSA records, and have clients validate them through DNSSEC. This reduces operational costs and removes dependency on external CA infrastructure.

The security benefits extend beyond certificate validation. DANE provides protection against man-in-the-middle attacks even if a CA is compromised, because the TLSA record must match the DNSSEC-signed zone data. An attacker would need to compromise both the CA and the DNSSEC chain to successfully forge a valid certificate.

For related reading on DNS security, see our [DNS-over-TLS resolver guide](../self-hosted-dns-over-tls-resolver-stubby-unbound-knot-2026/) and [DNS firewall with RPZ](../2026-04-21-self-hosted-dns-firewall-rpz-unbound-powerdns-bind/).

## Choosing the Right TLSA/DANE Tool

**Choose hash-slinger if:** You need a dedicated TLSA record management tool with comprehensive certificate format support. hash-slinger is the best choice for generating and verifying TLSA records across multiple services and certificate types.

**Choose ldns-dane if:** You need thorough DANE validation that checks the complete DNSSEC chain and compares certificate fingerprints. ldns-dane is ideal for automated validation pipelines and compliance checking.

**Choose Knot DNS if:** You need a production-grade authoritative DNS server with DNSSEC signing for TLSA record publication. Knot DNS is the best choice when you want to serve TLSA records to the public internet with proper DNSSEC chain of trust.

## FAQ

### What is DANE and how does it improve TLS security?
DANE (DNS-based Authentication of Named Entities) uses DNSSEC-secured TLSA records to publish certificate fingerprints for domain services. Instead of trusting any certificate authority, clients validate that the server's certificate matches the TLSA record published in DNS. This protects against rogue CA certificates and gives domain owners direct control over TLS trust.

### What are TLSA record usage types?
TLSA records have four usage types: PKIX-TA (0) validates against a trusted CA anchor, PKIX-EE (1) validates the end-entity certificate against a CA chain, DANE-TA (2) validates against a specific trust anchor in the TLSA record, and DANE-EE (3) validates the end-entity certificate fingerprint directly. Usage 3 (DANE-EE) is the most common for self-signed certificates.

### What is the difference between TLSA selector 0 and 1?
Selector 0 (Cert) matches the full certificate, while selector 1 (SPKI) matches only the Subject Public Key Info. Using SPKI (selector 1) is generally preferred because it allows certificate renewal without updating the TLSA record — as long as the public key remains the same, the TLSA record remains valid.

### Do I need DNSSEC for DANE to work?
Yes, DNSSEC is mandatory for DANE. Without DNSSEC, TLSA records in DNS can be spoofed or modified by an attacker, defeating the security purpose. Clients must verify the DNSSEC signature chain on the TLSA record before trusting it. Always sign your zones with DNSSEC before publishing TLSA records.

### Can I use DANE with self-signed certificates?
Yes, this is one of the primary use cases for DANE. With DANE-EE (usage 3), you can publish the fingerprint of a self-signed certificate as a TLSA record. Clients that support DANE will validate the server's certificate against the TLSA record, eliminating the need for a public CA. This is ideal for internal services and self-hosted infrastructure.

### Which TLSA matching type should I use?
Matching type 1 (SHA-256) is recommended for most use cases. It provides a good balance between security and record size. Matching type 2 (SHA-512) offers stronger collision resistance but produces longer TLSA records. Matching type 0 (Full) stores the entire certificate or public key, which is useful for debugging but increases DNS response size.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted DNS TLSA/DANE Management: hash-slinger vs ldns vs Knot DNS",
  "description": "Compare open-source tools for DNS TLSA/DANE management — hash-slinger, ldns-dane, and Knot DNS for certificate validation and DNSSEC-secured TLS records.",
  "datePublished": "2026-05-21",
  "dateModified": "2026-05-21",
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
