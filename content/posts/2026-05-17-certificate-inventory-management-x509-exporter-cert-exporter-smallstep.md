---
title: "Self-Hosted Certificate Inventory Management: x509-Certificate-Exporter vs Cert-Exporter vs Smallstep"
date: "2026-05-17"
tags: ["certificate-management", "tls", "pki", "monitoring", "security"]
draft: false
---

Managing TLS certificates across a growing infrastructure is one of the most common operational challenges. Certificates expire, services go down, and teams scramble to rotate them before customers see browser warnings. This guide compares three self-hosted approaches for certificate inventory management: Enix x509-certificate-exporter (Kubernetes-native), cert-exporter (legacy certificate monitoring), and Smallstep step-ca with built-in inventory features.

## The Certificate Expiration Problem

Every organization running TLS services eventually faces certificate expiration incidents. Common scenarios include:

- Internal services using self-signed certificates with 1-year validity periods that get forgotten
- Let's Encrypt certificates auto-renewing but failing silently due to DNS or firewall changes
- Client certificates for mutual TLS that expire without notification
- Wildcard certificates covering dozens of subdomains where one service is missed during rotation

A certificate inventory system solves this by providing centralized visibility into every certificate deployed across your infrastructure, along with automated expiration alerts.

## Enix x509-Certificate-Exporter

The x509-certificate-exporter by Enix (enix-io/x509-certificate-exporter on GitHub, 250+ stars) is a Kubernetes-native Prometheus exporter that discovers TLS certificates across the cluster and exposes expiration metrics.

```yaml
version: "3.8"
services:
  x509-exporter:
    image: ghcr.io/enix-io/x509-certificate-exporter:latest
    ports:
      - "9793:9793"
    volumes:
      - /etc/kubernetes/pki:/etc/kubernetes/pki:ro
      - /var/lib/kubelet/pki:/var/lib/kubelet/pki:ro
      - ./exporter-config.yaml:/etc/x509-exporter/config.yaml
    command: ["--config=/etc/x509-exporter/config.yaml"]
    restart: unless-stopped
```

Configuration (`exporter-config.yaml`):

```yaml
watchers:
  - paths:
      - /etc/kubernetes/pki
      - /var/lib/kubelet/pki
    recursive: true
  - kubeConfig:
      enabled: true
      namespaces: []
      secrets:
        labelSelector: ""
        annotations: {}

exporter:
  listenAddress: :9793
  telemetryPath: /metrics

alerts:
  beforeExpireDays: 30
  beforeExpireCriticalDays: 7
```

The exporter discovers certificates in multiple locations:
- File system paths (mounted volumes)
- Kubernetes Secrets containing TLS certificates
- kubeconfig files
- PEM-encoded certificates in ConfigMaps

Prometheus metrics include `x509_cert_not_after` (expiration timestamp), `x509_cert_not_before` (issue date), `x509_cert_cn` (common name), and `x509_cert_san` (subject alternative names). These can be queried with PromQL to build Grafana dashboards and alerting rules.

Example PromQL alert for certificates expiring within 30 days:

```promql
(x509_cert_not_after - time()) / 86400 < 30
and
(x509_cert_not_after - time()) / 86400 > 0
```

## Cert-Exporter (Kubernetes Certificate Monitoring)

cert-exporter (joe-elliott/cert-exporter on GitHub, 150+ stars) is a Kubernetes controller that monitors certificate expiration for kubeconfigs, certificate files, and Kubernetes Secrets, sending alerts via Slack, PagerDuty, or webhook.

```yaml
version: "3.8"
services:
  cert-exporter:
    image: quay.io/joeelliott/cert-exporter:latest
    ports:
      - "8080:8080"
    volumes:
      - /etc/kubernetes:/etc/kubernetes:ro
      - /var/lib/kubelet:/var/lib/kubelet:ro
    command:
      - --check-kubelet-client-certificate=true
      - --check-kubelet-server-certificate=true
      - --secrets-label-selector=
      - --period=1h
      - --port=8080
    restart: unless-stopped
```

cert-exporter can be deployed as a Kubernetes DaemonSet to run on every node, or as a single Deployment with volume mounts pointing to certificate directories. It supports:

- Kubelet client and server certificates
- Kubernetes Secrets with TLS data
- Arbitrary file paths on the host
- Slack notifications via webhook URL
- Prometheus metrics endpoint

The tool is lightweight and focused specifically on expiration monitoring, without the broader certificate lifecycle management features of a full PKI platform.

## Smallstep Step-CA with Inventory Features

Smallstep (smallstep/certificates on GitHub, 3,600+ stars) is a private PKI and certificate authority that includes built-in certificate inventory through its admin API and CLI tooling.

```yaml
version: "3.8"
services:
  step-ca:
    image: smallstep/step-ca:latest
    ports:
      - "9000:9000"
    volumes:
      - step-ca-data:/home/step
    environment:
      - DOCKER_STEPCA_INIT_NAME=OpenSwap CA
      - DOCKER_STEPCA_INIT_DNS_NAMES=ca.example.com
      - DOCKER_STEPCA_INIT_ADDRESS=:9000
      - DOCKER_STEPCA_INIT_PROVISIONER_NAME=admin
      - DOCKER_STEPCA_INIT_PROVISIONER_PASSWORD=provisioner-password
    restart: unless-stopped

volumes:
  step-ca-data:
```

Step-CA provides certificate inventory through:

```bash
# List all certificates issued by the CA
step ca certificate list --provisioner admin

# Check expiration of a specific certificate
step certificate inspect /path/to/cert.crt

# Export certificate inventory as JSON
step ca certificate list --provisioner admin --output-format json
```

Step-CA also supports automated renewal through the `step-renew` daemon, which runs on client machines and automatically renews certificates before expiration. This eliminates the need for manual rotation entirely.

Step-CA's admin API returns detailed certificate metadata including serial number, subject, SANs, issue date, expiration date, and provisioning information. This data can be integrated with external inventory systems or monitoring dashboards.

## Comparison Table

| Feature | x509-Certificate-Exporter | Cert-Exporter | Smallstep Step-CA |
|---------|--------------------------|---------------|-------------------|
| **Stars** | 250+ | 150+ | 3,600+ |
| **License** | MIT | Apache 2.0 | Apache 2.0 |
| **Primary Role** | Monitoring/Exporting | Monitoring/Alerting | Full PKI + Inventory |
| **Kubernetes Native** | Yes (DaemonSet/Deployment) | Yes (DaemonSet) | Yes (Deployment) |
| **Prometheus Metrics** | Yes | Yes | Via admin API |
| **Alerting** | Via Prometheus/Alertmanager | Slack, PagerDuty, webhook | Via step-renew daemon |
| **Certificate Issuance** | No (read-only) | No (read-only) | Yes (full CA) |
| **Auto-Renewal** | No | No | Yes (step-renew) |
| **Web UI** | No (Grafana dashboards) | No | No (CLI + API) |
| **External Cert Discovery** | Yes (filesystem, Secrets) | Yes (filesystem, kubeconfigs) | No (tracks only issued certs) |
| **Docker Image Size** | ~30 MB | ~20 MB | ~50 MB |

## Why Self-Host Certificate Inventory?

**Prevent Outages**: Certificate expiration is one of the most common causes of avoidable outages. A centralized inventory system ensures every certificate is tracked with expiration dates, responsible teams, and renewal status.

**Compliance Requirements**: Many regulatory frameworks (PCI DSS, SOC 2, HIPAA) require documented certificate inventory and rotation procedures. Self-hosted inventory tools provide auditable records without sending certificate metadata to third-party services.

**Multi-Cloud Visibility**: Organizations running across AWS, GCP, and Azure need a unified view of all certificates regardless of cloud provider. Self-hosted inventory tools discover certificates from filesystem paths and Kubernetes clusters independently of cloud APIs.

**Cost Avoidance**: Third-party certificate management platforms charge per certificate or per endpoint. Self-hosted solutions scale with your infrastructure at zero additional licensing cost.

**Integration Flexibility**: Self-hosted tools integrate with your existing monitoring stack (Prometheus, Grafana, Alertmanager) and notification channels (Slack, PagerDuty, email) without vendor lock-in.

For certificate automation workflows, see our [TLS certificate automation guide](../2026-04-19-cert-manager-vs-lego-vs-acme-sh-self-hosted-tls-certificate-automation-guide-2026/). For PKI infrastructure setup, our [enterprise CA comparison](../2026-04-26-ejbca-vs-dogtag-pki-vs-openxpki-self-hosted-enterprise-ca-guide/) covers EJBCA, Dogtag, and OpenXPKI. For OCSP and revocation checking, check our [OCSP responder guide](../2026-05-06-self-hosted-ocsp-responder-certificate-revocation-cfssl-smallstep-ejbca-crl/).

## Choosing the Right Certificate Inventory Tool

- **Kubernetes clusters needing visibility** into all deployed certificates should use x509-certificate-exporter. It provides comprehensive Prometheus metrics and integrates with existing Grafana dashboards.
- **Teams needing simple expiration alerts** without Prometheus infrastructure should use cert-exporter. Its Slack and PagerDuty integrations work out of the box.
- **Organizations building a private PKI** should deploy Smallstep step-ca, which provides certificate issuance, inventory, and automated renewal in a single platform.

## Deployment Architecture for Certificate Monitoring

A robust certificate inventory deployment requires careful integration with your existing monitoring and infrastructure management stack. The following architectural patterns are commonly used in production environments.

### Centralized Monitoring Architecture

Deploy the certificate exporter as a DaemonSet across all Kubernetes worker nodes, with each instance scanning local filesystem paths and node-level TLS certificates. Configure Prometheus to scrape exporter metrics via ServiceMonitor or PodMonitor custom resources. Set up Alertmanager routing rules to direct certificate expiration alerts to on-call rotation channels.

For non-Kubernetes infrastructure, deploy the exporter as a systemd service on each host, configured to scan standard certificate directories (`/etc/ssl/certs`, `/etc/pki/tls`, `/opt/certificates`). Use Prometheus node exporter's textfile collector or pushgateway to aggregate metrics from hosts not directly reachable by Prometheus.

### Integration with Existing PKI Infrastructure

When running a private certificate authority (CA) alongside an inventory system, establish clear boundaries of responsibility. The CA handles certificate issuance, policy enforcement, and revocation. The inventory system handles discovery, monitoring, and alerting for all certificates regardless of issuing authority. This separation allows the inventory to track certificates from Let's Encrypt, internal CAs, and third-party providers in a single dashboard.

Configure the inventory system to correlate discovered certificates with CA issuance records. When a certificate appears in the inventory but has no corresponding CA issuance record, it indicates an externally-provisioned certificate that should be reviewed for compliance with organizational security policies.

### Scaling Considerations

For large organizations managing thousands of certificates across hundreds of Kubernetes clusters:

- Deploy separate x509-certificate-exporter instances per cluster with federated Prometheus scraping
- Use label-based filtering to exclude certificates that do not require monitoring (e.g., short-lived workload identity certificates)
- Configure alert thresholds based on certificate type: 90-day warning for manually-rotated certificates, 7-day warning for auto-renewed certificates
- Implement certificate tagging conventions (labels, annotations) to track ownership, criticality, and renewal responsibility

## FAQ

### What is the difference between certificate inventory and certificate management?

Certificate inventory tracks and monitors existing certificates across your infrastructure — it discovers, catalogs, and alerts on expiration dates. Certificate management (or PKI) includes inventory plus the ability to issue, renew, and revoke certificates. x509-certificate-exporter and cert-exporter provide inventory only; Smallstep step-ca provides both.

### Can x509-certificate-exporter discover certificates outside Kubernetes?

Yes. By mounting host filesystem paths into the exporter container, it can scan any directory for PEM-encoded certificates. This includes certificates on bare-metal servers, VMs, or network appliances accessible via NFS mounts.

### Does cert-exporter support email notifications?

Not natively. cert-exporter supports Slack, PagerDuty, and generic webhooks. For email alerts, configure a webhook that forwards to an email service, or use Prometheus Alertmanager with email receivers.

### How often does x509-certificate-exporter scan for certificates?

The exporter watches filesystem paths using inotify (Linux file system events) and checks Kubernetes Secrets via the Kubernetes API watch mechanism. Changes are detected in near-real-time without periodic polling.

### Can Smallstep step-ca import certificates issued by other CAs?

Step-CA tracks only certificates it has issued. For external certificates, pair step-ca with x509-certificate-exporter to get complete coverage across both internally-issued and externally-provisioned certificates.

### What happens when a certificate expires in the inventory?

The inventory tool itself does not take action — it reports and alerts. x509-certificate-exporter exposes metrics that Prometheus Alertmanager evaluates to fire alerts. cert-exporter sends direct notifications to Slack or PagerDuty. Smallstep step-ca's step-renew daemon attempts automatic renewal before expiration.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Certificate Inventory Management: x509-Certificate-Exporter vs Cert-Exporter vs Smallstep",
  "description": "Compare self-hosted certificate inventory management tools for tracking TLS certificate expiration across infrastructure. Includes Docker Compose configs and Prometheus integration.",
  "datePublished": "2026-05-17",
  "dateModified": "2026-05-17",
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
