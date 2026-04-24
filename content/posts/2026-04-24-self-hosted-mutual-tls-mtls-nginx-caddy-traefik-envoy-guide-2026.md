---
title: "Self-Hosted Mutual TLS (mTLS) Setup Guide: nginx vs Caddy vs Traefik vs Envoy 2026"
date: 2026-04-24
tags: ["security", "guide", "self-hosted", "mtls", "nginx", "caddy", "traefik", "envoy"]
draft: false
description: "Complete guide to setting up mutual TLS (mTLS) for self-hosted services. Compare nginx, Caddy, Traefik, and Envoy mTLS configurations with Docker examples."
---

Mutual TLS (mTLS) is the gold standard for service-to-service authentication in self-hosted infrastructure. Unlike standard TLS, which only verifies the server's identity, mTLS requires **both the client and server to present and validate certificates** — ensuring that only authorized services can communicate with each other.

Whether you're securing microservices, protecting internal APIs, or building a zero-trust network on bare metal, this guide walks through mTLS setup across four popular self-hosted proxies: **nginx**, **Caddy**, **Traefik**, and **Envoy**. Each offers different tradeoffs in complexity, automation, and ecosystem fit.

Here's how the four tools compare in terms of community adoption:

| Project | GitHub Stars | Last Updated | Primary Language |
|---------|-------------|--------------|-----------------|
| [Caddy](https://github.com/caddyserver/caddy) | 71,787 | April 2026 | Go |
| [Traefik](https://github.com/traefik/traefik) | 62,846 | April 2026 | Go |
| [nginx](https://github.com/nginx/nginx) | 30,051 | April 2026 | C |
| [Envoy](https://github.com/envoyproxy/envoy) | 27,884 | April 2026 | C++ |

## Why Self-Host mTLS

Running your own mTLS infrastructure gives you complete control over certificate lifecycle, trust anchors, and access policies — without depending on external certificate authorities or service mesh vendors. Here's why self-hosted mTLS matters:

- **Zero-trust architecture**: Every service must prove its identity before any data is exchanged. Network perimeter security is no longer sufficient.
- **Regulatory compliance**: Standards like PCI DSS, HIPAA, and SOC 2 increasingly require mutual authentication for sensitive data flows.
- **Cost control**: Commercial service mesh platforms (Istio, Linkerd) add operational overhead. Simple mTLS via a reverse proxy handles most use cases without the complexity.
- **Private CA control**: You manage the root of trust. Certificates never leave your infrastructure, and revocation is immediate.
- **Defense in depth**: Even if an attacker gains network access, they cannot impersonate a service without a valid client certificate signed by your CA.

For related reading on securing self-hosted infrastructure, see our [web application firewall comparison](../2026-04-18-bunkerweb-vs-modsecurity-vs-crowdsec-self-hosted-waf-guide-2026/) and [TLS termination proxy guide](../self-hosted-tls-termination-proxy-traefik-caddy-haproxy-guide-2026/).

## How mTLS Works

Before diving into configurations, here's a quick overview of the mTLS handshake:

1. **Client connects** to the server and requests a TLS session.
2. **Server presents its certificate** to the client (standard TLS).
3. **Server requests the client's certificate** via the `CertificateRequest` message.
4. **Client presents its certificate** to the server.
5. **Both sides validate** each other's certificates against their trusted CA bundles.
6. **Encrypted communication begins** — only if both certificates are valid and trusted.

The key difference from standard TLS is step 3-5: the server actively requests and validates the client's certificate. If the client has no certificate, or its certificate isn't signed by a trusted CA, the connection is rejected.

### Certificate Infrastructure You'll Need

Every mTLS setup requires three certificate components:

- **Root CA**: A self-signed certificate authority that signs both server and client certificates.
- **Server certificate**: Issued by the Root CA, presented by the proxy to clients.
- **Client certificates**: Issued by the Root CA, presented by each service or user connecting to the proxy.

For automated certificate management, check our [cert-manager vs Lego vs ACME.sh comparison](../2026-04-19-cert-manager-vs-lego-vs-acme-sh-self-hosted-tls-certificate-automation-guide-2026/).

## Prerequisites: Generate a Root CA and Certificates

Before configuring any proxy, you need a certificate authority. Here's how to generate one with OpenSSL:

```bash
# 1. Generate Root CA private key
openssl genrsa -out ca.key 4096

# 2. Generate Root CA certificate (valid for 10 years)
openssl req -x509 -new -nodes -key ca.key -sha256 -days 3650 \
  -out ca.crt -subj "/C=US/ST=California/O=SelfHosted/CN=SelfHosted Root CA"

# 3. Generate server private key
openssl genrsa -out server.key 2048

# 4. Generate server CSR (Certificate Signing Request)
openssl req -new -key server.key -out server.csr \
  -subj "/C=US/ST=California/O=SelfHosted/CN=localhost"

# 5. Sign server certificate with CA
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key \
  -CAcreateserial -out server.crt -days 365 -sha256 \
  -extfile <(printf "subjectAltName=DNS:localhost,IP:127.0.0.1")

# 6. Generate client private key
openssl genrsa -out client.key 2048

# 7. Generate client CSR
openssl req -new -key client.key -out client.csr \
  -subj "/C=US/ST=California/O=SelfHosted/CN=service-a"

# 8. Sign client certificate with CA
openssl x509 -req -in client.csr -CA ca.crt -CAkey ca.key \
  -CAcreateserial -out client.crt -days 365 -sha256
```

You now have: `ca.crt` (trusted by both sides), `server.crt`/`server.key` (for the proxy), and `client.crt`/`client.key` (for connecting services).

## nginx mTLS Configuration

nginx is the most battle-tested option with straightforward mTLS directives. It's ideal when you need simple, reliable mutual authentication without additional dependencies.

### Docker Compose Setup

```yaml
services:
  nginx-mtls:
    image: nginx:1.27-alpine
    container_name: nginx-mtls
    ports:
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./server.crt:/etc/nginx/ssl/server.crt:ro
      - ./server.key:/etc/nginx/ssl/server.key:ro
      - ./ca.crt:/etc/nginx/ssl/ca.crt:ro
    restart: unless-stopped
```

### nginx Configuration

```nginx
events {
    worker_connections 1024;
}

http {
    server {
        listen 443 ssl;
        server_name localhost;

        # Server certificate
        ssl_certificate     /etc/nginx/ssl/server.crt;
        ssl_certificate_key /etc/nginx/ssl/server.key;

        # Require client certificate (mTLS)
        ssl_client_certificate /etc/nginx/ssl/ca.crt;
        ssl_verify_client on;

        # TLS settings
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;
        ssl_prefer_server_ciphers on;

        location / {
            # Pass client certificate info to backend
            proxy_set_header X-Client-CN $ssl_client_s_dn;
            proxy_set_header X-Client-Verify $ssl_client_verify;

            # Backend service
            proxy_pass http://backend:8080;
        }

        # Optional: Allow specific endpoints without mTLS
        location /health {
            ssl_verify_client off;
            return 200 "OK";
        }
    }

    upstream backend {
        server app:8080;
    }
}
```

### Testing nginx mTLS

```bash
# With valid client certificate — should succeed
curl --cacert ca.crt --cert client.crt --key client.key https://localhost

# Without client certificate — should fail with 400
curl --cacert ca.crt https://localhost

# With wrong CA — should fail
curl --cacert /dev/null --cert client.crt --key client.key https://localhost
```

## Caddy mTLS Configuration

Caddy stands out for its automatic TLS and mTLS capabilities with minimal configuration. Its native `tls` directive handles both server certificates and client verification in just a few lines.

### Docker Compose Setup

```yaml
services:
  caddy-mtls:
    image: caddy:2.9-alpine
    container_name: caddy-mtls
    ports:
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - ./ca.crt:/etc/caddy/ssl/ca.crt:ro
      - caddy_data:/data
    restart: unless-stopped

volumes:
  caddy_data:
```

### Caddyfile Configuration

```caddy
{
    # Optional: use your own ACME CA or disable automatic HTTPS
    # auto_https off
}

localhost {
    tls /etc/caddy/ssl/server.crt /etc/caddy/ssl/server.key {
        client_auth {
            mode require_and_verify
            trusted_ca_cert_file /etc/caddy/ssl/ca.crt
        }
    }

    reverse_proxy app:8080

    # Log client certificate details
    log {
        output stdout
        format json
    }
}
```

### Caddy with Automatic Client Certificate Issuance

For advanced use cases, Caddy can also act as the CA and issue client certificates on demand using the [On-Demand TLS](https://caddyserver.com/docs/on-demand-tls) feature combined with a custom CA module:

```caddy
localhost {
    tls internal {
        ca_root ca.crt
        client_auth {
            mode require_and_verify
            trusted_ca_cert_file ca.crt
            trusted_leaf_cert_file /etc/caddy/issued-clients/
        }
    }

    reverse_proxy app:8080
}
```

Caddy's simplicity makes it ideal for teams that want mTLS without managing OpenSSL manually. It handles certificate rotation automatically when paired with its built-in ACME support for the server certificate.

## Traefik mTLS Configuration

Traefik provides mTLS through its TLS options system, making it a natural fit for Docker and Kubernetes environments where dynamic service discovery is essential.

### Docker Compose Setup

```yaml
services:
  traefik-mtls:
    image: traefik:v3.3
    container_name: traefik-mtls
    ports:
      - "443:443"
      - "8080:8080"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./traefik.yaml:/etc/traefik/traefik.yaml:ro
      - ./tls-config.yaml:/etc/traefik/tls-config.yaml:ro
      - ./server.crt:/etc/traefik/ssl/server.crt:ro
      - ./server.key:/etc/traefik/ssl/server.key:ro
      - ./ca.crt:/etc/traefik/ssl/ca.crt:ro
    restart: unless-stopped

  whoami:
    image: traefik/whoami
    labels:
      - "traefik.http.routers.whoami.rule=Host(`localhost`)"
      - "traefik.http.routers.whoami.tls=true"
      - "traefik.http.routers.whoami.tls.options=mtls@file"
```

### traefik.yaml (Main Configuration)

```yaml
entryPoints:
  websecure:
    address: ":443"

providers:
  docker:
    exposedByDefault: false
  file:
    filename: /etc/traefik/tls-config.yaml

api:
  dashboard: true
  insecure: true
```

### tls-config.yaml (mTLS Options)

```yaml
tls:
  options:
    mtls:
      minVersion: VersionTLS12
      clientAuth:
        caFiles:
          - /etc/traefik/ssl/ca.crt
        clientAuthType: RequireAndVerifyClientCert

  stores:
    default:
      defaultCertificate:
        certFile: /etc/traefik/ssl/server.crt
        keyFile: /etc/traefik/ssl/server.key
```

Traefik's label-based routing means you can enable or disable mTLS per-service by adding or removing the `tls.options` label. This granular control is valuable when migrating a mixed environment — some services require mTLS while others remain on standard TLS during a transition period.

## Envoy mTLS Configuration

Envoy is the most powerful option for mTLS, offering deep traffic management, observability, and advanced certificate validation. It's the foundation of many service mesh data planes (Istio, Linkerd).

### Docker Compose Setup

```yaml
services:
  envoy-mtls:
    image: envoyproxy/envoy:v1.32
    container_name: envoy-mtls
    ports:
      - "443:443"
      - "9901:9901"
    volumes:
      - ./envoy.yaml:/etc/envoy/envoy.yaml:ro
      - ./server.crt:/etc/envoy/ssl/server.crt:ro
      - ./server.key:/etc/envoy/ssl/server.key:ro
      - ./ca.crt:/etc/envoy/ssl/ca.crt:ro
    restart: unless-stopped
```

### envoy.yaml Configuration

```yaml
static_resources:
  listeners:
    - name: listener_0
      address:
        socket_address:
          address: 0.0.0.0
          port_value: 443
      filter_chains:
        - transport_socket:
            name: envoy.transport_sockets.tls
            typed_config:
              "@type": type.googleapis.com/envoy.extensions.transport_sockets.tls.v3.DownstreamTlsContext
              common_tls_context:
                tls_certificates:
                  - certificate_chain:
                      filename: /etc/envoy/ssl/server.crt
                    private_key:
                      filename: /etc/envoy/ssl/server.key
                validation_context:
                  trusted_ca:
                    filename: /etc/envoy/ssl/ca.crt
              require_client_certificate: true
          filters:
            - name: envoy.filters.network.http_connection_manager
              typed_config:
                "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
                stat_prefix: ingress_http
                route_config:
                  name: local_route
                  virtual_hosts:
                    - name: local_service
                      domains: ["*"]
                      routes:
                        - match:
                            prefix: "/"
                          route:
                            cluster: backend_service
                http_filters:
                  - name: envoy.filters.http.router
                    typed_config:
                      "@type": type.googleapis.com/envoy.extensions.filters.http.router.v3.Router

  clusters:
    - name: backend_service
      type: STRICT_DNS
      load_assignment:
        cluster_name: backend_service
        endpoints:
          - lb_endpoints:
              - endpoint:
                  address:
                    socket_address:
                      address: app
                      port_value: 8080
```

Envoy's `require_client_certificate: true` enforces mTLS at the transport layer. The configuration is more verbose than nginx or Caddy, but it unlocks advanced features like certificate-based routing, SPIFFE/SPIRE identity integration, and fine-grained access control policies.

## mTLS Comparison: Choosing the Right Tool

| Feature | nginx | Caddy | Traefik | Envoy |
|---------|-------|-------|---------|-------|
| **Configuration complexity** | Low | Very Low | Medium | High |
| **mTLS directives** | `ssl_verify_client` | `client_auth` block | `clientAuth` in TLS options | `DownstreamTlsContext` |
| **Per-route mTLS** | Yes (via location blocks) | Yes (via site blocks) | Yes (via labels) | Yes (via filter chains) |
| **Automatic cert issuance** | No (manual or certbot) | Built-in (ACME) | Via ACME/Let's Encrypt | No |
| **Docker integration** | Basic | Basic | Native (Docker provider) | Basic |
| **Kubernetes support** | Ingress controller | Limited | Ingress controller | Service mesh data plane |
| **Certificate rotation** | Manual reload | Automatic | Hot reload | Hot reload |
| **Observability** | Access logs | Structured JSON logs | Metrics + dashboard | Prometheus + detailed stats |
| **Best for** | Simple, reliable setups | Quick deployment, small teams | Docker/K8s environments | Service mesh, advanced routing |

### When to Use Each

**Choose nginx** when you need a proven, lightweight solution with straightforward configuration. It's the most widely deployed and has the largest community for troubleshooting.

**Choose Caddy** when simplicity is the priority. Its declarative Caddyfile handles mTLS in under 10 lines, and automatic certificate management reduces operational overhead.

**Choose Traefik** when you're running containerized workloads and want mTLS with dynamic service discovery. Its label-based configuration pairs naturally with Docker Compose and Kubernetes.

**Choose Envoy** when you need advanced traffic management, observability, or plan to integrate with a service mesh. It's the most powerful but requires the most configuration expertise.

For deeper infrastructure security, also consider our [service mesh guide](../self-hosted-service-mesh-consul-linkerd-istio-guide/) and [fail2ban vs Crowdsec comparison](../2026-04-24-fail2ban-vs-sshguard-vs-crowdsec-self-hosted-intrusion-prevention-2026/).

## Client Certificate Management at Scale

Managing individual client certificates becomes unwieldy beyond a handful of services. Here are practical strategies for production:

### Certificate Naming Convention

Use the certificate Common Name (CN) or Subject Alternative Name (SAN) to encode service identity:

```bash
# Format: CN=<service-name>.<environment>.<domain>
openssl req -new -key client.key -out client.csr \
  -subj "/C=US/ST=California/O=SelfHosted/CN=payments.prod.internal"
```

### Certificate Expiry Monitoring

Set up automated checks for expiring client certificates:

```bash
# Check certificate expiration date
openssl x509 -enddate -noout -in client.crt
# Output: notAfter=Apr 24 12:00:00 2027 GMT

# Alert if cert expires within 30 days
openssl x509 -checkend $((30 * 86400)) -noout -in client.crt
# Exit code 1 = expires within 30 days
```

### Revocation

When a service is decommissioned or compromised, revoke its certificate. You have two options:

1. **CRL (Certificate Revocation List)**: Maintain a list of revoked serial numbers. All proxies check this list on every connection.
2. **Short-lived certificates**: Issue certificates with 24-hour validity and rotate automatically. No revocation needed — expired certs are rejected.

For short-lived certificates, consider using [step-ca](https://smallstep.com/certificates/) or Vault's [PKI secrets engine](https://developer.hashicorp.com/vault/docs/secrets/pki) as an internal CA with built-in renewal APIs.

## FAQ

### What is the difference between TLS and mTLS?

Standard TLS (Transport Layer Security) only authenticates the server to the client — this is what secures HTTPS websites. mTLS (Mutual TLS) adds a second layer: the server also verifies the client's certificate. Both sides prove their identity before any data is exchanged.

### Can I use Let's Encrypt certificates for mTLS?

Let's Encrypt only issues server certificates, not client certificates. For mTLS, you need your own Certificate Authority (CA) to sign client certificates. You can still use Let's Encrypt for the server certificate while using a self-signed CA for client authentication.

### Do I need to restart nginx after adding or revoking client certificates?

If you add or remove entries from the CA bundle (`ssl_client_certificate`), you need to reload nginx with `nginx -s reload`. However, if you're using CRL-based revocation, you can update the CRL file and reload without regenerating the CA bundle. Caddy and Traefik support hot-reloading of TLS configuration without restart.

### How do I test mTLS without a real backend service?

You can use a simple echo server to verify mTLS is working. Run `python3 -m http.server 8080` as a backend, or use the `traefik/whoami` Docker image which returns request headers — useful for verifying that `X-Client-CN` headers are being forwarded correctly.

### Is mTLS enough for complete service-to-service security?

mTLS provides authentication and encryption in transit, but a complete zero-trust architecture also needs authorization (what each service is allowed to do), auditing (logging all connections), and potentially encryption at rest. Consider pairing mTLS with API authorization middleware, centralized logging, and network segmentation for defense in depth.

### Can I disable mTLS for specific endpoints?

Yes. In nginx, use `ssl_verify_client off;` inside specific `location` blocks. In Caddy, create a separate site block or matcher without `client_auth`. In Traefik, apply different TLS options per-route using labels. In Envoy, configure separate filter chains with different `require_client_certificate` settings.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Mutual TLS (mTLS) Setup Guide: nginx vs Caddy vs Traefik vs Envoy 2026",
  "description": "Complete guide to setting up mutual TLS (mTLS) for self-hosted services. Compare nginx, Caddy, Traefik, and Envoy mTLS configurations with Docker examples.",
  "datePublished": "2026-04-24",
  "dateModified": "2026-04-24",
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
