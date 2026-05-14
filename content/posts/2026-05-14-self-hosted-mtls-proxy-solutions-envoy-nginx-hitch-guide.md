---
title: "Self-Hosted mTLS Proxy Solutions: Envoy mTLS vs NGINX Mutual TLS vs Hitch mTLS Gateway"
date: "2026-05-14"
tags: ["mtls", "tls", "authentication", "network-security", "self-hosted", "zero-trust"]
draft: false
---

Mutual TLS (mTLS) extends standard TLS by requiring both the client and server to present and verify X.509 certificates during the handshake. While standard TLS only authenticates the server, mTLS ensures that both parties in a connection are who they claim to be — providing strong, certificate-based authentication without passwords or tokens.

Deploying mTLS natively in every application is complex and often impossible for legacy systems. An mTLS proxy sits in front of your services, handling certificate verification on behalf of backend applications and forwarding authenticated requests with identity headers.

In this guide, we compare three approaches to self-hosted mTLS proxying: **Envoy's mTLS**, **NGINX Mutual TLS**, and **Hitch mTLS Gateway**. Each offers different trade-offs in complexity, performance, and ecosystem integration.

## What Is mTLS and Why Does It Matter?

Standard TLS encrypts traffic between client and server using a server certificate. The client verifies the server's identity, but the server has no way to authenticate the client beyond application-layer credentials (passwords, API keys, tokens).

mTLS adds a second certificate exchange: the server requests the client's certificate, verifies it against a trusted CA, and only proceeds if the certificate is valid. This provides:

- **Strong authentication** — Certificate-based identity is cryptographically verifiable and resistant to phishing
- **Zero-trust networking** — Every connection is authenticated, regardless of network location
- **No credential storage** — Unlike passwords, certificates don't need to be stored or transmitted for authentication
- **Automated rotation** — Certificates can be issued and rotated programmatically via ACME or internal PKI
- **Fine-grained access control** — Certificate subject fields map directly to access policies

## Why Use an mTLS Proxy?

Implementing mTLS in a proxy layer rather than in each application offers several advantages:

**Decoupled authentication** — Applications receive authenticated requests via standard headers without implementing certificate parsing logic themselves.

**Centralized policy** — Certificate revocation, CA trust chains, and access policies are managed in one place rather than duplicated across every service.

**Legacy compatibility** — Applications that don't understand mTLS can still benefit from certificate-based authentication through the proxy.

**Operational simplicity** — Certificate rotation, renewal, and revocation are handled at the proxy level, reducing the blast radius of certificate management errors.

## Comparison Table

| Feature | Envoy mTLS | NGINX Mutual TLS | Hitch mTLS |
|---------|-----------|-----------------|------------|
| **Language** | C++ | C | C |
| **GitHub Stars** | 26,300+ | 27,000+ (nginx) | 1,940+ |
| **Last Updated** | Active (2026) | Active (2026) | Active (2026) |
| **mTLS Support** | Native (SPIFFE/SPIRE) | Native (ssl_verify_client) | Native (verify-client) |
| **Certificate Rotation** | Hot reload (xDS API) | Graceful reload | SIGHUP reload |
| **SPIFFE/SPIRE** | Built-in | Via external plugin | No |
| **Service Mesh** | Istio, Linkerd | No | No |
| **gRPC Support** | Native | Limited | No |
| **HTTP/2** | Native | Native | No (TLS-only) |
| **WebSocket** | Yes | Yes | No |
| **Load Balancing** | Advanced (L4/L7) | Basic (L7) | L4 only |
| **Health Checks** | Active + passive | Active | No |
| **Configuration** | xDS / YAML | nginx.conf | hitch.conf |
| **Docker Image** | Official (envoyproxy) | Official (nginx) | Community |
| **License** | Apache-2.0 | BSD-2-clause | BSD-2-clause |

## Envoy mTLS: The Service Mesh Standard

[Envoy](https://github.com/envoyproxy/envoy) is a high-performance proxy designed for cloud-native environments. Its mTLS implementation is the foundation of Istio and other service meshes, providing automatic certificate rotation via SPIFFE/SPIRE identity.

### Installation

```bash
# Docker
docker pull envoyproxy/envoy:v1.31-latest

# From source
git clone https://github.com/envoyproxy/envoy.git
cd envoy
bazel build //source/exe:envoy-static

# Package managers (some distributions)
apt-get install envoy
```

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  envoy-mtls:
    image: envoyproxy/envoy:v1.31-latest
    ports:
      - "8443:8443"
      - "9901:9901"
    volumes:
      - ./envoy.yaml:/etc/envoy/envoy.yaml:ro
      - ./certs:/etc/envoy/certs:ro
      - ./ca:/etc/envoy/ca:ro
    restart: unless-stopped
```

### Envoy mTLS Configuration

```yaml
# envoy.yaml
static_resources:
  listeners:
    - name: mtls_listener
      address:
        socket_address:
          address: 0.0.0.0
          port_value: 8443
      filter_chains:
        - transport_socket:
            name: envoy.transport_sockets.tls
            typed_config:
              "@type": type.googleapis.com/envoy.extensions.transport_sockets.tls.v3.DownstreamTlsContext
              require_client_certificate: true
              common_tls_context:
                tls_certificates:
                  - certificate_chain:
                      filename: /etc/envoy/certs/server.crt
                    private_key:
                      filename: /etc/envoy/certs/server.key
                validation_context:
                  trusted_ca:
                    filename: /etc/envoy/ca/ca.crt
          filters:
            - name: envoy.filters.network.http_connection_manager
              typed_config:
                "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
                stat_prefix: mtls
                route_config:
                  virtual_hosts:
                    - name: backend
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
      connect_timeout: 5s
      type: STRICT_DNS
      lb_policy: ROUND_ROBIN
      load_assignment:
        cluster_name: backend_service
        endpoints:
          - lb_endpoints:
              - endpoint:
                  address:
                    socket_address:
                      address: backend-app
                      port_value: 8080
```

### Key Features

- **SPIFFE/SPIRE integration** — Automatic workload identity via SPIFFE IDs embedded in certificates
- **xDS dynamic configuration** — Update mTLS policies, certificates, and routes without restart
- **Service mesh ready** — Foundation for Istio, Linkerd, and Consul Connect
- **Observability** — Built-in metrics, distributed tracing, and access logging
- **Advanced routing** — Content-based routing, retries, circuit breaking, rate limiting

## NGINX Mutual TLS: The Battle-Tested Approach

NGINX has supported mutual TLS for years through its `ssl_verify_client` directive. It's the simplest and most widely deployed mTLS solution, making it ideal for traditional web application architectures.

### Installation

```bash
# Ubuntu/Debian
sudo apt-get install nginx

# From source with OpenSSL
./configure --with-http_ssl_module
make && sudo make install

# Docker
docker pull nginx:latest
```

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  nginx-mtls:
    image: nginx:latest
    ports:
      - "8443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/nginx/certs:ro
      - ./ca:/etc/nginx/ca:ro
      - ./logs:/var/log/nginx
    restart: unless-stopped
```

### NGINX mTLS Configuration

```nginx
# nginx.conf
events {
    worker_connections 1024;
}

http {
    upstream backend {
        server backend-app:8080;
    }

    server {
        listen 8443 ssl;
        server_name mtls.example.com;

        # Server certificate
        ssl_certificate /etc/nginx/certs/server.crt;
        ssl_certificate_key /etc/nginx/certs/server.key;

        # Mutual TLS: require and verify client certificate
        ssl_verify_client on;
        ssl_client_certificate /etc/nginx/ca/ca.crt;
        ssl_verify_depth 2;

        # Pass client certificate info to backend
        location / {
            proxy_pass http://backend;
            proxy_set_header X-Client-DN $ssl_client_s_dn;
            proxy_set_header X-Client-Verify $ssl_client_verify;
            proxy_set_header X-Client-Serial $ssl_client_serial;
            proxy_set_header X-Client-Cert $ssl_client_cert;
        }
    }
}
```

### Key Features

- **Simple configuration** — A few directives enable full mTLS
- **Wide ecosystem** — Extensive documentation, community support, and third-party modules
- **Header forwarding** — Pass certificate details to backend via HTTP headers
- **CRL/OCSP support** — Certificate revocation checking via CRL files or OCSP stapling
- **Lua scripting** — OpenResty/NGINX Lua enables custom certificate validation logic

## Hitch mTLS: The High-Performance TLS Terminator

[Hitch](https://github.com/varnish/hitch) is a high-performance TLS proxy designed by the Varnish team. While primarily known as a TLS terminator, Hitch supports client certificate verification (mTLS) and can front any TCP backend with certificate-based authentication.

### Installation

```bash
# Ubuntu/Debian
sudo apt-get install hitch

# From source
git clone https://github.com/varnish/hitch.git
cd hitch
./bootstrap && ./configure && make && sudo make install

# Docker
docker pull varnish/hitch:latest
```

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  hitch-mtls:
    image: varnish/hitch:latest
    ports:
      - "8443:8443"
    volumes:
      - ./hitch.conf:/etc/hitch/hitch.conf:ro
      - ./certs:/etc/hitch/certs:ro
      - ./ca:/etc/hitch/ca:ro
    command: ["--config=/etc/hitch/hitch.conf"]
    restart: unless-stopped
```

### Hitch mTLS Configuration

```ini
# hitch.conf
frontend = {
    host = "*"
    port = "8443"
}

backend = "[backend-app]:8080"

# TLS configuration
pem-file = "/etc/hitch/certs/server.pem"

# mTLS: require client certificates
verify-client = required
ca-file = "/etc/hitch/ca/ca.crt"

# Performance tuning
workers = 4
backlog = 1024
keepalive = 300

# Logging
log-level = 2
syslog = on
```

### Key Features

- **High throughput** — Designed for maximum TLS connection throughput with minimal CPU
- **PROXY protocol** — Preserves client IP addresses through the proxy chain
- **Simple configuration** — Minimal config file with sensible defaults
- **Zero-copy TLS** — Uses sendfile() and splice() for efficient data transfer
- **OCSP stapling** — Built-in OCSP stapling for server certificate status

## Choosing the Right mTLS Proxy

| Use Case | Recommended Tool | Reason |
|----------|-----------------|--------|
| Kubernetes / service mesh | Envoy | Native SPIFFE, xDS, mesh integration |
| Traditional web apps | NGINX | Simple config, wide ecosystem |
| High-throughput TLS termination | Hitch | Maximum performance, minimal overhead |
| gRPC services | Envoy | Native gRPC support, advanced routing |
| Legacy app MFA | NGINX | Header-based identity forwarding |
| Multi-tenant certificate auth | Envoy | Per-tenant xDS configuration |

## Security Best Practices

1. **Certificate lifecycle management** — Automate certificate issuance and rotation using ACME or an internal PKI
2. **CRL/OCSP checking** — Verify that client certificates haven't been revoked
3. **Certificate pinning** — For high-security environments, pin expected certificate fingerprints
4. **Network segmentation** — Place the mTLS proxy at the network boundary between trust zones
5. **Audit logging** — Log certificate subject, issuer, and verification results for every connection
6. **Fallback planning** — Have a procedure for emergency access if certificate infrastructure fails

## Why Self-Host Your mTLS Proxy?

Running mTLS infrastructure on your own infrastructure is a cornerstone of zero-trust architecture. When you control the certificate verification layer, you maintain complete visibility into authentication decisions, certificate chains, and access patterns. This visibility is critical for security operations teams investigating suspicious access attempts or auditing compliance with identity policies.

Integration with internal PKI is seamless when the proxy runs on your infrastructure. Self-hosted mTLS proxies can connect to your internal certificate authority for real-time certificate validation, leverage your organization's OCSP responders for revocation checking, and integrate with your secrets management platform for certificate and key storage.

Performance is another significant advantage. mTLS handshakes are computationally expensive — certificate verification, chain validation, and CRL/OCSP checks add measurable latency. Running the proxy on infrastructure close to your applications minimizes network latency and allows you to provision dedicated compute resources for TLS operations.

Custom policy enforcement is the final advantage. Self-hosted mTLS proxies can enforce organization-specific certificate requirements — minimum key lengths, required subject fields, allowed issuers, and validity periods. These policies can be dynamically updated without redeploying backend applications.

For TLS termination, see our [SSL/TLS proxy guide](../2026-05-15-self-hosted-ssl-tls-proxy-stunnel-sslh-hitch-guide/). For identity platforms, check our [Logto vs SuperTokens vs Ory Kratos comparison](../2026-05-10-self-hosted-auth-platforms-logto-supertokens-ory-kratos-guide/). For secrets and certificate management, our [Vault vs SOPS vs Sealed Secrets article](../self-hosted-secrets-management-vault-sops-sealed-secrets-guide-2026/) covers credential storage.

## FAQ

### What is the difference between TLS and mTLS?

Standard TLS authenticates only the server — the client verifies the server's certificate but the server doesn't verify the client. mTLS (mutual TLS) requires both parties to present and verify certificates, providing bidirectional authentication.

### Can mTLS replace API keys and passwords?

mTLS can replace API keys for service-to-service authentication, providing stronger cryptographic guarantees. However, it's less practical for human users who would need to manage personal certificates. A hybrid approach — mTLS for services, passwords/MFA for humans — is common.

### How do I rotate client certificates without downtime?

Deploy two CA certificates (old and new) in the proxy's trust store. Issue new certificates from the new CA while old ones are still valid. Once all clients have migrated, remove the old CA from the trust store. Envoy's xDS API makes this seamless with hot reload.

### What happens when a client certificate expires?

The TLS handshake fails with a certificate_expired alert. The proxy should return a 403 Forbidden response. Applications should monitor certificate expiration dates and rotate certificates before they expire.

### Can I use mTLS with load balancers?

Yes. The mTLS proxy can sit behind a Layer 4 load balancer (TCP passthrough) or handle TLS termination itself. If using a load balancer, ensure it supports PROXY protocol to preserve client IP addresses.

### Is mTLS compatible with HTTP/2 and gRPC?

Envoy fully supports mTLS with HTTP/2 and gRPC. NGINX supports HTTP/2 with mTLS but gRPC support requires additional configuration. Hitch does not support HTTP/2 — it's a TLS-only proxy that forwards raw TCP to the backend.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted mTLS Proxy Solutions: Envoy mTLS vs NGINX Mutual TLS vs Hitch mTLS Gateway",
  "description": "Compare self-hosted mTLS proxy solutions for implementing mutual TLS authentication, zero-trust networking, and certificate-based access control.",
  "datePublished": "2026-05-14",
  "dateModified": "2026-05-14",
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
