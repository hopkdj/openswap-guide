---
title: "Self-Hosted OpenSSL Certificate Management CLI: OpenSSL vs GnuTLS vs cfssl vs mkcert"
date: "2026-06-01"
tags: ["security", "ssl", "encryption", "linux", "self-hosted", "certificates", "pki"]
draft: false
---

## Introduction

Every self-hosted service that serves HTTPS needs certificates — but before you reach for Let's Encrypt or a public CA, you need to understand the command-line tools that create, inspect, sign, and manage those certificates. Whether you're building an internal PKI for your homelab, generating self-signed certs for development, or debugging TLS handshake failures on a production reverse proxy, certificate management CLI tools are an essential part of the self-hosted toolkit.

In this guide, we compare five certificate management tools: the ubiquitous **OpenSSL**, the GNU alternative **GnuTLS** (certtool), Cloudflare's **cfssl**, the developer-friendly **mkcert**, and the modern **step-cli**. Each excels in different scenarios — from scripting bulk certificate generation to setting up a local trust store that browsers actually accept.

## Why Self-Host Your Certificate Infrastructure?

Running your own certificate management pipeline gives you capabilities that public CAs cannot match. You can issue certificates with custom X.509 extensions, set any validity period you need (including short-lived 1-hour certs for microservices), and avoid rate limits entirely. For internal services, self-signed certificates managed through your own toolchain are more secure than public CA certs — there's no third party that could be compromised to issue fraudulent certificates for your internal hostnames.

For development environments, tools like mkcert eliminate the "your connection is not private" browser warnings that disrupt local testing. This is particularly valuable when you're running self-hosted services behind [TLS termination proxies like Traefik, Caddy, or HAProxy](../self-hosted-tls-termination-proxy-traefik-caddy-haproxy-guide-2026/) — you can test the full TLS chain locally before deploying to production.

In production, programmatic certificate management is essential for automation. If you operate a [self-hosted PKI with step-ca or EJBCA](../2026-06-20-self-hosted-certificate-lifecycle-management-step-ca-ejbca-dogtag/), CLI tools are how your CI/CD pipelines request, renew, and revoke certificates. Understanding the strengths of each tool lets you choose the right one for each pipeline stage — OpenSSL for inspection, cfssl for bulk generation, and step-cli for automated enrollment.

## Comparison Table: Certificate Management CLI Tools

| Feature | OpenSSL | GnuTLS (certtool) | cfssl | mkcert | step-cli |
|---------|---------|-------------------|-------|--------|----------|
| **Installation** | `apt install openssl` | `apt install gnutls-bin` | `go install` | `apt install mkcert` | `brew/apt install step` |
| **Key Generation** | RSA, EC, Ed25519, DSA | RSA, EC, Ed25519 | RSA, ECDSA | ECDSA P-256, RSA 2048 | RSA, EC, Ed25519, OKP |
| **CSR Generation** | Yes (verbose) | Yes (template-based) | Yes (JSON config) | Automatic | Yes (one-liner) |
| **Self-Signed Certs** | One-liner possible | Template required | JSON config | `mkcert example.com` | `step certificate create` |
| **CA Management** | Manual (index.txt) | Manual | Built-in CA tools | System trust store | Full CA support |
| **Certificate Inspection** | Excellent | Good | Basic (cfssl-certinfo) | No | Good |
| **PKCS#12 Support** | Yes | Yes (pkcs12) | No | No | Via OpenSSL |
| **OCSP** | Server & client | Via libgnutls | Server & client | No | Yes |
| **CRL Generation** | Yes | Yes | Yes | No | Yes |
| **Scripting Friendly** | Moderate | Good (templates) | Excellent (JSON) | Excellent | Excellent |
| **Active Development** | Very Active | Active | Moderate | Active | Very Active |

## Tool Deep Dives

### OpenSSL: The Universal Tool

OpenSSL is installed on virtually every Linux system and supports every certificate operation imaginable. Its strength is universality; its weakness is a famously inconsistent CLI.

```bash
# Generate a self-signed certificate in one command
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem \
  -days 365 -nodes -subj "/CN=myservice.local"

# Inspect a certificate's details
openssl x509 -in cert.pem -text -noout

# Check certificate expiration date
openssl x509 -in cert.pem -noout -enddate

# Verify a certificate chain
openssl verify -CAfile ca.pem -untrusted intermediate.pem server.pem

# Convert between formats
openssl pkcs12 -export -out bundle.p12 -inkey key.pem -in cert.pem
openssl rsa -in key.pem -out key-plain.pem  # Remove passphrase

# Generate a CSR with SANs
openssl req -new -key key.pem -out csr.pem \
  -subj "/CN=example.com" \
  -addext "subjectAltName=DNS:example.com,DNS:www.example.com"

# Test TLS connection to a server
openssl s_client -connect example.com:443 -servername example.com
```

For CA operations, OpenSSL requires manual index management:

```bash
# Initialize a CA
mkdir -p demoCA/newcerts
touch demoCA/index.txt
echo 1000 > demoCA/serial

# Create CA certificate
openssl req -x509 -newkey rsa:4096 -keyout ca-key.pem -out ca-cert.pem \
  -days 3650 -nodes -subj "/CN=My Internal CA"

# Sign a certificate request
openssl ca -in csr.pem -out signed.pem -keyfile ca-key.pem -cert ca-cert.pem
```

### GnuTLS (certtool): The GNU Alternative

GnuTLS offers a cleaner template-based approach. Instead of chaining dozens of CLI flags, you define certificate parameters in a template file and feed it to `certtool`.

```bash
# Install
sudo apt install gnutls-bin

# Generate a private key
certtool --generate-privkey --outfile key.pem --rsa

# Create a certificate template: cert.cfg
cat > cert.cfg << 'EOF'
organization = "My Org"
cn = "myservice.local"
dns_name = "myservice.local"
dns_name = "www.myservice.local"
expiration_days = 365
tls_www_server
encryption_key
signing_key
EOF

# Generate self-signed certificate from template
certtool --generate-self-signed --load-privkey key.pem \
  --template cert.cfg --outfile cert.pem

# Inspect a certificate
certtool --certificate-info --infile cert.pem

# Verify against a CA
certtool --verify --load-ca-certificate ca.pem --infile cert.pem
```

The template system makes GnuTLS especially suited for automated certificate generation in scripts where you generate the template programmatically and feed it to certtool.

### cfssl: Cloudflare's PKI Toolkit

Cloudflare's cfssl (CloudFlare SSL) is built around JSON configuration — ideal for infrastructure-as-code and programmatic certificate management. It comes with a built-in CA server (`cfssl serve`) for production use.

```bash
# Install
go install github.com/cloudflare/cfssl/cmd/...@latest

# CA configuration: ca-config.json
cat > ca-config.json << 'EOF'
{
  "signing": {
    "default": { "expiry": "8760h" },
    "profiles": {
      "server": {
        "expiry": "8760h",
        "usages": ["signing", "key encipherment", "server auth"]
      },
      "client": {
        "expiry": "8760h",
        "usages": ["signing", "key encipherment", "client auth"]
      }
    }
  }
}
EOF

# CSR configuration: csr.json
cat > csr.json << 'EOF'
{
  "CN": "myservice.local",
  "hosts": ["myservice.local", "www.myservice.local"],
  "key": { "algo": "rsa", "size": 2048 },
  "names": [{ "O": "My Organization" }]
}
EOF

# Generate certificate and key
cfssl gencert -ca ca.pem -ca-key ca-key.pem \
  -config ca-config.json -profile server csr.json | cfssljson -bare cert

# Inspect a certificate
cfssl certinfo -cert cert.pem

# Start a CA server
cfssl serve -ca ca.pem -ca-key ca-key.pem -config ca-config.json
```

### mkcert: Zero-Configuration Local Development Certificates

`mkcert` creates locally-trusted certificates by installing a local CA into your system and browser trust stores. Certificates it generates are accepted by Chrome, Firefox, and system tools without any manual security exception clicks.

```bash
# Install and set up local CA (do this once)
sudo apt install mkcert
mkcert -install

# Generate a certificate for local development
mkcert myservice.local localhost 127.0.0.1 ::1

# Output: myservice.local+3.pem and myservice.local+3-key.pem

# Use with a local web server
caddy reverse-proxy --from localhost:8443 --to localhost:3000 \
  --tls "$(mkcert -cert-file myservice.local+3.pem \
  -key-file myservice.local+3-key.pem 2>/dev/null)"
```

### step-cli: Modern Zero-Touch Certificate Management

`step-cli` from Smallstep combines certificate generation with automated enrollment against any ACME or step-ca server, making it the best bridge between local development and production PKI.

```bash
# Install
wget https://dl.smallstep.com/cli/docs-cli-install/latest/step-cli_amd64.deb
sudo dpkg -i step-cli_amd64.deb

# Generate a self-signed certificate (single command)
step certificate create myservice.local cert.pem key.pem \
  --profile self-signed --subtle --san myservice.local --not-after 2160h

# Inspect a certificate
step certificate inspect cert.pem

# Check certificate expiration
step certificate needs-renewal cert.pem

# Bootstrap trust with a CA
step ca bootstrap --ca-url https://ca.example.com --fingerprint <hash>

# Request a certificate from the CA
step ca certificate myservice.local cert.pem key.pem
```

## Security Considerations

When managing certificates for self-hosted services, protect your private keys. Use restrictive file permissions (`chmod 600 key.pem`) and consider hardware security modules (HSMs) or TPM-backed key storage for production CAs. For automated renewal pipelines, never hardcode key passphrases — use environment variables or secret management tools.

Certificate revocation is equally important. Maintain CRLs (Certificate Revocation Lists) or run an OCSP responder for your internal CA. Tools like OpenSSL and cfssl can generate CRLs; step-ca provides a full OCSP responder out of the box.

## FAQ

### When should I use self-signed certificates vs. Let's Encrypt?

Use Let's Encrypt (or another public CA) for publicly accessible services where browser trust matters. Use self-signed certificates (managed through these CLI tools) for internal services — backend microservices, database connections, monitoring endpoints — where you control both ends of the TLS connection and can distribute your internal CA certificate to all clients.

### Can I use mkcert certificates in production?

No. mkcert is explicitly designed for local development only. Its CA private key is stored on your local machine and is not suitable for production use. For production internal PKI, use step-ca, cfssl's CA mode, or a commercial CA.

### How do I automate certificate renewal?

For public certificates, use certbot or an ACME client. For internal certificates, script the renewal with your chosen CLI tool and a cron job. step-cli's `needs-renewal` command makes this particularly clean — check if renewal is needed, and if so, request a new certificate and reload affected services.

### What's the best tool for inspecting a certificate I received?

OpenSSL's `x509 -text -noout` gives the most comprehensive output. For quick checks — just expiration date or SANs — use `step certificate inspect` or `openssl x509 -noout -enddate`. For TLS server certificates, `openssl s_client -connect host:port` shows the entire handshake and server certificate.

### How do I handle certificate chains with intermediate CAs?

Provide the full chain (server cert first, then intermediates, then root) in a single PEM file. OpenSSL's `s_client -showcerts` shows the chain a server sends. If your server isn't sending intermediates, concatenate them manually: `cat server.pem intermediate.pem root.pem > fullchain.pem`. Both nginx (`ssl_certificate`) and Apache (`SSLCertificateFile`) support full chain files.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted OpenSSL Certificate Management CLI: OpenSSL vs GnuTLS vs cfssl vs mkcert",
  "description": "In-depth comparison of command-line certificate management tools — OpenSSL, GnuTLS certtool, Cloudflare cfssl, mkcert, and step-cli — for self-hosted PKI and TLS infrastructure.",
  "datePublished": "2026-06-01",
  "dateModified": "2026-06-01",
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

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到科技监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测科技趋势走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
