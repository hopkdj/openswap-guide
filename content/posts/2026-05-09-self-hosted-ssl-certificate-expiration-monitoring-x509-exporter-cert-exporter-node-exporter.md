---
title: "Self-Hosted SSL Certificate Expiration Monitoring: enix x509-certificate-exporter vs cert-exporter vs node-cert-exporter (2026)"
date: "2026-05-09"
tags: ["monitoring", "ssl", "tls", "certificates", "prometheus", "security"]
draft: false
---

SSL/TLS certificate expiration is one of the most common causes of production outages. When a certificate expires, services become unreachable, APIs fail, and users see browser security warnings. Despite being entirely preventable, expired certificates cause thousands of incidents every year across organizations of all sizes.

This guide compares three self-hosted Prometheus exporters that monitor certificate expiration dates across Kubernetes clusters, individual nodes, and arbitrary file paths: **enix x509-certificate-exporter**, **joe-elliott cert-exporter**, and **amimof node-cert-exporter**.

## Why Monitor Certificate Expiration?

Certificate expiration failures are deceptively simple to cause and devastating in impact:

- **Service outages** — Expired TLS certificates cause immediate connection failures for HTTPS, gRPC, and other TLS-secured protocols
- **Cascading failures** — A single expired certificate in a service mesh can take down dozens of interconnected microservices
- **Reputation damage** — Browser security warnings erode user trust and can impact search rankings
- **Compliance violations** — Standards like PCI DSS, SOC 2, and ISO 27001 require active certificate lifecycle management
- **Cost of emergency renewal** — Rushed certificate renewals during outages often bypass proper validation and security checks

Proactive monitoring with Prometheus exporters gives you weeks or months of advance notice before certificates expire, allowing planned renewals during maintenance windows rather than emergency firefighting at 3 AM.

## Quick Comparison

| Feature | enix x509-exporter | joe-elliott cert-exporter | amimof node-cert-exporter |
|---------|-------------------|--------------------------|--------------------------|
| **GitHub Stars** | 909+ | 386+ | 187+ |
| **Language** | Go | Go | Go |
| **Kubernetes Native** | Yes (DaemonSet + Deployment) | Yes (DaemonSet) | Yes (DaemonSet) |
| **File Path Monitoring** | Yes | Yes | Yes |
| **Kubeconfig Monitoring** | Yes | Yes | No |
| **CSR Monitoring** | Yes | Yes | No |
| **Custom Labels** | Yes | Yes | No |
| **Helm Chart** | Yes | Yes | No |
| **Docker Image** | `ghcr.io/enix/x509-certificate-exporter` | `quay.io/joeelliott/cert-exporter` | `ghcr.io/amimof/node-cert-exporter` |
| **License** | MIT | Apache 2.0 | Apache 2.0 |

## enix x509-certificate-exporter

The [enix x509-certificate-exporter](https://github.com/enix/x509-certificate-exporter) is the most feature-rich option, designed specifically for Kubernetes environments with support for monitoring certificates across the entire cluster lifecycle.

### Key Features

- **Comprehensive certificate discovery** — Scans TLS certificates in kubeconfig files, Kubernetes CSRs, and arbitrary file paths
- **Multi-mode deployment** — Run as a DaemonSet for node-level scanning or as a Deployment for control plane monitoring
- **Rich metrics** — Exposes certificate expiry timestamps, issuer details, SANs, and key types as Prometheus metrics
- **Label customization** — Add custom labels to metrics for filtering by namespace, environment, or team ownership
- **Helm chart support** — Official Helm chart for easy Kubernetes deployment
- **Grafana dashboard** — Pre-built dashboard templates for certificate expiration visualization

### Deployment via Helm

```bash
# Add the Helm repository
helm repo add enix https://enixsolutions.github.io/x509-certificate-exporter
helm repo update

# Install the exporter
helm install x509-certificate-exporter enix/x509-certificate-exporter \
  --namespace monitoring \
  --create-namespace \
  --set "nodeExporter.enabled=true" \
  --set "deployment.enabled=true"
```

### Manual Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: x509-certificate-exporter
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: x509-certificate-exporter
  template:
    metadata:
      labels:
        app: x509-certificate-exporter
    spec:
      containers:
      - name: exporter
        image: ghcr.io/enix/x509-certificate-exporter:latest
        args:
          - --listen-address=:9793
          - --search-dir=/etc/kubernetes
          - --search-dir=/etc/ssl/certs
        ports:
        - containerPort: 9793
          name: metrics
        volumeMounts:
        - name: etc-kubernetes
          mountPath: /etc/kubernetes
          readOnly: true
        - name: etc-ssl
          mountPath: /etc/ssl/certs
          readOnly: true
      volumes:
      - name: etc-kubernetes
        hostPath:
          path: /etc/kubernetes
      - name: etc-ssl
        hostPath:
          path: /etc/ssl/certs
```

### Docker Standalone

```bash
docker run -d --name x509-exporter \
  -p 9793:9793 \
  -v /etc/kubernetes:/etc/kubernetes:ro \
  -v /etc/ssl/certs:/etc/ssl/certs:ro \
  ghcr.io/enix/x509-certificate-exporter:latest \
  --listen-address=:9793 \
  --search-dir=/etc/kubernetes \
  --search-dir=/etc/ssl/certs
```

## joe-elliott cert-exporter

The [cert-exporter](https://github.com/joe-elliott/cert-exporter) by Joe Elliott is a focused, lightweight Prometheus exporter that monitors certificate expiration for both files on disk and Kubernetes secrets.

### Key Features

- **Dual monitoring modes** — Checks certificates in local files and Kubernetes secrets
- **Kubernetes secret scanning** — Monitors TLS secrets across all namespaces for expiration
- **Configurable check intervals** — Adjustable polling frequency for certificate checks
- **Lightweight footprint** — Minimal resource consumption suitable for edge deployments
- **Simple configuration** — Straightforward YAML configuration with sensible defaults

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: cert-exporter
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: cert-exporter
  template:
    metadata:
      labels:
        app: cert-exporter
    spec:
      containers:
      - name: cert-exporter
        image: quay.io/joeelliott/cert-exporter:latest
        args:
          - --check-interval=4h
          - --include-kubeconfig-glob=/etc/kubernetes/*.conf
          - --cert-dir=/etc/ssl/certs
        ports:
        - containerPort: 9112
          name: metrics
        volumeMounts:
        - name: kubernetes
          mountPath: /etc/kubernetes
          readOnly: true
        - name: ssl-certs
          mountPath: /etc/ssl/certs
          readOnly: true
      volumes:
      - name: kubernetes
        hostPath:
          path: /etc/kubernetes
      - name: ssl-certs
        hostPath:
          path: /etc/ssl/certs
```

### Docker Standalone

```bash
docker run -d --name cert-exporter \
  -p 9112:9112 \
  -v /etc/kubernetes:/etc/kubernetes:ro \
  -v /etc/ssl/certs:/etc/ssl/certs:ro \
  quay.io/joeelliott/cert-exporter:latest \
  --check-interval=4h \
  --cert-dir=/etc/ssl/certs
```

## amimof node-cert-exporter

The [node-cert-exporter](https://github.com/amimof/node-cert-exporter) is a specialized exporter focused on monitoring certificates found on individual nodes, making it ideal for bare-metal and VM-based infrastructure.

### Key Features

- **Node-focused scanning** — Optimized for monitoring certificates on individual hosts
- **Path-based discovery** — Recursively scans specified directories for PEM and DER certificates
- **Simple configuration** — Minimal setup with directory path arguments
- **Low overhead** — Designed for resource-constrained environments

### Deployment

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: node-cert-exporter
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: node-cert-exporter
  template:
    metadata:
      labels:
        app: node-cert-exporter
    spec:
      containers:
      - name: exporter
        image: ghcr.io/amimof/node-cert-exporter:latest
        args:
          - --cert.path=/etc/kubernetes
          - --cert.path=/etc/ssl/certs
        ports:
        - containerPort: 9206
          name: metrics
        volumeMounts:
        - name: etc-kubernetes
          mountPath: /etc/kubernetes
          readOnly: true
        - name: etc-ssl
          mountPath: /etc/ssl/certs
          readOnly: true
      volumes:
      - name: etc-kubernetes
        hostPath:
          path: /etc/kubernetes
      - name: etc-ssl
        hostPath:
          path: /etc/ssl/certs
```

### Docker Standalone

```bash
docker run -d --name node-cert-exporter \
  -p 9206:9206 \
  -v /etc/kubernetes:/etc/kubernetes:ro \
  -v /etc/ssl/certs:/etc/ssl/certs:ro \
  ghcr.io/amimof/node-cert-exporter:latest \
  --cert.path=/etc/kubernetes \
  --cert.path=/etc/ssl/certs
```

## Prometheus Alerting Rules

Regardless of which exporter you choose, set up Prometheus alerting rules to trigger before certificates expire:

```yaml
groups:
- name: certificate_expiry
  rules:
  # Critical alert: certificate expires in less than 7 days
  - alert: CertExpiryCritical
    expr: x509_read_cert_not_after_date - time() < 86400 * 7
    for: 1h
    labels:
      severity: critical
    annotations:
      summary: "TLS certificate expires in less than 7 days"
      description: "Certificate on {{ $labels.instance }} expires in {{ $value | humanizeDuration }}"

  # Warning alert: certificate expires in less than 30 days
  - alert: CertExpiryWarning
    expr: x509_read_cert_not_after_date - time() < 86400 * 30
    for: 6h
    labels:
      severity: warning
    annotations:
      summary: "TLS certificate expires in less than 30 days"
      description: "Certificate on {{ $labels.instance }} expires in {{ $value | humanizeDuration }}"
```

## Why Self-Host Certificate Monitoring?

**Complete visibility** — Third-party certificate monitoring services can only check publicly accessible endpoints. Self-hosted exporters monitor internal certificates across your entire infrastructure, including service mesh certificates, internal PKI, and client certificates that no external service can reach.

**No external dependencies** — Certificate monitoring should not depend on a third-party service being available. When your monitoring provider has an outage, you lose visibility into your own certificate expirations at the worst possible time.

**Custom thresholds and alerting** — Self-hosted solutions let you configure alerting thresholds that match your organization's renewal workflows. Need 90-day warnings for enterprise CA certificates but only 14-day warnings for Let's Encrypt auto-renewed certs? Self-hosted exporters support this granularity.

**Integration with existing tooling** — Prometheus-native exporters integrate seamlessly with your existing Grafana dashboards, Alertmanager routing, and PagerDuty/Opsgenie escalation policies. No additional API integrations or webhooks required.

For broader TLS security, see our [SSL/TLS scanning guide](../2026-04-22-testssl-vs-sslyze-vs-sslscan-self-hosted-ssl-tls-scanning-guide-2026/) and [certificate transparency monitoring](../2026-04-24-certstream-vs-certspotter-vs-ct-monitor-self-hosted-certificate-transparency/). If you manage certificate authorities, our [enterprise PKI comparison](../2026-04-26-ejbca-vs-dogtag-pki-vs-openxpki-self-hosted-enterprise-ca-guide/) covers CA platforms.

## FAQ

### What is the difference between these certificate exporters?

The enix x509-certificate-exporter is the most feature-complete, supporting kubeconfig files, Kubernetes CSRs, and custom labels. The joe-elliott cert-exporter focuses on file paths and Kubernetes secrets with a simpler configuration model. The amimof node-cert-exporter is the most lightweight, optimized for bare-metal node scanning with minimal resource usage.

### How far in advance should I set certificate expiration alerts?

For production services, set warning alerts at 30 days and critical alerts at 7 days before expiration. For certificates managed by automated renewal (like Let's Encrypt with cert-manager), 14-day warnings are sufficient. For manually renewed enterprise CA certificates, consider 60-day warnings to allow time for approval workflows.

### Can these exporters monitor certificates in cloud environments?

Yes. In AWS, Azure, or GCP Kubernetes clusters, deploy the exporters as DaemonSets to scan node filesystems. For cloud load balancer certificates (ALB, Cloud Load Balancer), use cloud-native monitoring instead, as those certificates are managed by the cloud provider and not accessible on node filesystems.

### Do these tools automatically renew certificates?

No. These exporters only monitor expiration dates and generate alerts. For automatic renewal, use tools like cert-manager (Kubernetes), ACME clients (certbot, lego), or enterprise CA automation (EJBCA, Dogtag PKI). Monitoring and renewal are separate concerns — monitoring tells you when to act, renewal tools perform the action.

### What Prometheus metrics do these exporters expose?

All three exporters expose `*_cert_not_after_date` metrics representing the certificate expiration timestamp as a Unix epoch. The enix exporter additionally provides issuer information, SANs, key type, and serial number as metric labels. You can calculate days until expiry using `cert_not_after_date - time()`.

### Can I monitor certificates inside Docker containers?

Yes, by mounting the container's certificate directories into the exporter container. For example, `-v /var/lib/docker/containers:/containers:ro` combined with `--search-dir=/containers/*/etc/ssl` would scan certificates inside running containers.

### Which exporter should I choose for a large Kubernetes cluster?

For clusters with 100+ nodes, the enix x509-certificate-exporter is recommended due to its optimized scanning algorithm and Helm chart support. Its ability to run both DaemonSet and Deployment modes lets you monitor node-level and control plane certificates separately.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted SSL Certificate Expiration Monitoring: enix x509-certificate-exporter vs cert-exporter vs node-cert-exporter (2026)",
  "description": "Compare three self-hosted Prometheus exporters for SSL/TLS certificate expiration monitoring in Kubernetes and bare-metal environments.",
  "datePublished": "2026-05-09",
  "dateModified": "2026-05-09",
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
