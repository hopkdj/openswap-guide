---
title: "Self-Hosted External DNS for Kubernetes: Complete Guide (2026)"
date: 2026-05-07
tags: ["kubernetes", "dns", "external-dns", "self-hosted", "cloud-native", "docker", "guide"]
draft: false
---

Managing DNS records for Kubernetes workloads can be tedious when done manually. The **external-dns** project from Kubernetes SIG automates this process by monitoring Kubernetes resources (Services, Ingresses, Gateways) and creating corresponding DNS records in your DNS provider — AWS Route 53, Cloudflare, Google Cloud DNS, or any RFC 2136-compatible server.

In this comprehensive guide, we cover how to deploy external-dns on self-hosted Kubernetes, configure it for multiple DNS providers, and set up reliable DNS automation for your cluster workloads.

## What Is external-dns?

external-dns is a Kubernetes controller that synchronizes Kubernetes resources with DNS providers. When you create a Service or Ingress with a specific hostname annotation, external-dns detects it and creates the corresponding DNS record in your configured provider. When the resource is deleted, the DNS record is cleaned up automatically.

**Key capabilities:**
- Monitors Services, Ingresses, Istio Gateways, and Contour HTTPProxies
- Supports 30+ DNS providers including Route 53, Cloudflare, Google Cloud DNS, Azure DNS, PowerDNS, and RFC 2136
- Automatically creates and deletes DNS records based on Kubernetes lifecycle
- Supports both A/AAAA records (for LoadBalancer IPs) and CNAME records
- Runs as a standard Kubernetes Deployment with minimal resource requirements
- 8,900+ GitHub stars under the kubernetes-sigs organization

## Why Self-Host DNS Automation?

Automating DNS management for Kubernetes workloads solves several operational challenges:

- **No manual DNS updates**: Developers create Ingress resources and DNS records are created automatically
- **Consistent naming conventions**: Enforce naming standards across all cluster DNS records
- **Reduced human error**: Eliminate typos in DNS records and forgotten orphan records
- **Multi-cluster support**: Manage DNS across multiple Kubernetes clusters from a single controller
- **Cost savings**: Avoid commercial DNS management platforms by running external-dns in-cluster

For teams managing DNS at scale, combining external-dns with a self-hosted [DNS management web UI](../2026-05-04-self-hosted-dns-management-web-ui-powerdns-admin-dnscontrol-technitium-guide/) provides full visibility and control over your DNS infrastructure.

## Supported DNS Providers

external-dns supports a wide range of DNS providers. Here are the most common self-hosted and cloud options:

| Provider | Type | Authentication | Notes |
|----------|------|---------------|-------|
| **AWS Route 53** | Cloud | IAM roles/keys | Most popular, native IRSA support |
| **Cloudflare** | Cloud | API token | Free tier includes API access |
| **Google Cloud DNS** | Cloud | Service account JSON | GKE-native integration |
| **RFC 2136** | Self-hosted | TSIG key | Works with BIND, PowerDNS, Knot |
| **PowerDNS** | Self-hosted | API key | Full PowerDNS API support |
| **Azure DNS** | Cloud | Service principal | AKS-native integration |
| **DigitalOcean** | Cloud | API token | Simple setup |
| **Infoblox** | Enterprise | Credentials | On-premises DNS management |

## Installing external-dns via Helm

The recommended way to install external-dns is via the official Helm chart:

```bash
# Add the external-dns Helm repository
helm repo add external-dns https://kubernetes-sigs.github.io/external-dns/
helm repo update

# Install with Cloudflare provider
helm install external-dns external-dns/external-dns \
  --set provider=cloudflare \
  --set cloudflare.apiToken=YOUR_API_TOKEN \
  --set txtOwnerId=my-cluster \
  --set domainFilters[0]=example.com
```

## Docker Compose Setup (for testing)

For development and testing, you can run external-dns with Docker Compose:

```yaml
version: "3.8"
services:
  external-dns:
    image: registry.k8s.io/external-dns/external-dns:v0.15.0
    command:
      - --source=service
      - --source=ingress
      - --provider=rfc2136
      - --rfc2136-host=192.168.1.100
      - --rfc2136-port=53
      - --rfc2136-zone=example.com
      - --rfc2136-tsig-secret=secret-key
      - --rfc2136-tsig-secret-alg=hmacsha256
      - --rfc2136-tsig-keyname=external-dns
      - --rfc2136-tsig-axfr
      - --txt-owner-id=external-dns
    restart: unless-stopped
```

## Provider-Specific Configurations

### Cloudflare Configuration

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: external-dns
spec:
  template:
    spec:
      containers:
      - name: external-dns
        image: registry.k8s.io/external-dns/external-dns:v0.15.0
        args:
        - --source=service
        - --source=ingress
        - --provider=cloudflare
        - --domain-filter=example.com
        - --txt-owner-id=my-cluster
        env:
        - name: CF_API_TOKEN
          valueFrom:
            secretKeyRef:
              name: cloudflare-api-token
              key: token
```

### RFC 2136 (BIND/PowerDNS) Configuration

For self-hosted DNS servers, RFC 2136 is the standard protocol:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: rfc2136-tsig
type: Opaque
data:
  tsig-secret: <base64-encoded-secret>
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: external-dns
spec:
  template:
    spec:
      containers:
      - name: external-dns
        image: registry.k8s.io/external-dns/external-dns:v0.15.0
        args:
        - --source=ingress
        - --provider=rfc2136
        - --rfc2136-host=10.0.0.53
        - --rfc2136-port=53
        - --rfc2136-zone=example.com
        - --rfc2136-tsig-keyname=external-dns
        - --rfc2136-tsig-secret-alg=hmacsha256
        - --rfc2136-tsig-axfr
        - --txt-owner-id=k8s-cluster-1
```

## Ingress Example

Once external-dns is running, simply annotate your Ingress resources:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: my-app
  annotations:
    external-dns.alpha.kubernetes.io/hostname: app.example.com
    external-dns.alpha.kubernetes.io/ttl: "300"
spec:
  rules:
  - host: app.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: my-app
            port:
              number: 80
```

external-dns will automatically create an A record pointing `app.example.com` to the Ingress controller's load balancer IP.

## Managing Multiple Clusters

For multi-cluster environments, use unique `--txt-owner-id` values per cluster to prevent DNS record conflicts:

| Cluster | TXT Owner ID | DNS Zone |
|---------|-------------|----------|
| production | prod-cluster | prod.example.com |
| staging | staging-cluster | staging.example.com |
| development | dev-cluster | dev.example.com |

## Troubleshooting

**DNS records not being created:**
- Check external-dns logs: `kubectl logs deployment/external-dns`
- Verify the provider credentials are correct
- Ensure the Ingress/Service has the correct hostname annotation
- Check that the DNS zone is configured in `--domain-filter`

**Records not being deleted:**
- Verify `--txt-owner-id` matches the cluster that created the records
- Check for ownership TXT records that prevent deletion of records owned by other clusters

**Permission denied errors:**
- For cloud providers, verify IAM roles or API tokens have DNS management permissions
- For RFC 2136, verify the TSIG key has update permissions for the target zone

## Performance and Scaling

external-dns is lightweight and can handle thousands of DNS records:

- **Memory**: ~50-100 MB for typical clusters
- **CPU**: Minimal — runs reconciliation every 1 minute by default
- **DNS API rate limits**: Configure `--interval` to reduce API call frequency for providers with rate limits
- **Batch operations**: external-dns batches DNS changes to minimize API calls

For teams building comprehensive Kubernetes infrastructure, external-dns pairs well with [Kubernetes monitoring operators](../2026-04-30-k8s-monitoring-operators-kube-prometheus-victoriametrics-opentelemetry-guide/) for full cluster observability.

## FAQ

### What DNS records does external-dns create?

external-dns creates A/AAAA records (pointing to LoadBalancer IPs or NodePort addresses) and CNAME records (pointing to cloud load balancer hostnames). It also creates TXT records for ownership tracking, which prevent multiple external-dns instances from conflicting over the same DNS records.

### Can external-dns work with on-premises Kubernetes clusters?

Yes. For on-premises clusters, use the RFC 2136 provider to update self-hosted DNS servers like BIND, PowerDNS, or Knot DNS. You can also use the webhook provider to integrate with custom DNS APIs. The controller itself runs inside the cluster regardless of where the DNS provider is hosted.

### How does external-dns handle DNS record conflicts?

external-dns uses TXT records to track ownership. When it creates a DNS record, it also creates a corresponding TXT record with the configured `--txt-owner-id`. If another external-dns instance tries to modify a record it doesn't own, it will skip it. This prevents clusters from accidentally deleting each other's DNS records.

### Is external-dns compatible with cert-manager?

Yes. external-dns and cert-manager serve different purposes and work together seamlessly. external-dns manages DNS records for your Services and Ingresses, while cert-manager provisions TLS certificates for those same Ingresses. They are commonly deployed together in Kubernetes clusters.

### What is the reconciliation interval?

By default, external-dns reconciles every 1 minute (`--interval=1m`). This means it checks for new or deleted Kubernetes resources and updates DNS records accordingly. You can adjust this interval based on your needs — shorter intervals create DNS records faster but increase API calls to your DNS provider.

### Can external-dns manage wildcard DNS records?

Yes. You can create wildcard DNS records by annotating an Ingress with a wildcard hostname: `external-dns.alpha.kubernetes.io/hostname: "*.example.com"`. external-dns will create a wildcard A or CNAME record in your DNS provider. Note that not all DNS providers support wildcard records equally.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted External DNS for Kubernetes: Complete Guide (2026)",
  "description": "Complete guide to deploying and configuring external-dns for Kubernetes. Covers Cloudflare, Route 53, RFC 2136, multi-cluster setups, and troubleshooting.",
  "datePublished": "2026-05-07",
  "dateModified": "2026-05-07",
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

## Advanced Configuration Patterns

### Using external-dns with Istio Gateways

If you are running Istio service mesh, external-dns can sync DNS records from Istio Gateway resources instead of standard Ingress:

```yaml
args:
- --source=istio-gateway
- --source=istio-virtualservice
- --provider=cloudflare
- --domain-filter=example.com
```

This allows external-dns to read hostname configuration from Istio Gateway CRDs and create DNS records pointing to the Istio ingress gateway load balancer.

### TXT Registry for Ownership Management

external-dns uses TXT records to track which cluster owns which DNS records. The `--txt-owner-id` flag sets a unique identifier per cluster:

```bash
# Each cluster gets a unique TXT owner ID
external-dns --txt-owner-id=cluster-prod-us-east-1
external-dns --txt-owner-id=cluster-prod-eu-west-1
```

This prevents clusters from deleting each other's DNS records during reconciliation. The ownership TXT record is stored alongside the actual DNS record and is checked before any modification.

### DNS Record TTL Configuration

You can control TTL values per-record via annotations or globally via the `--txt-ttl` flag:

```yaml
metadata:
  annotations:
    external-dns.alpha.kubernetes.io/ttl: "60"  # 60 seconds for fast updates
```

For production services, use higher TTL values (300-3600 seconds) to reduce DNS query load. For development environments, lower TTL values enable faster DNS propagation during testing.

### Upstream DNS Provider Performance

When choosing a DNS provider for external-dns, consider API rate limits and propagation speed:

| Provider | API Rate Limit | Propagation Speed | Cost |
|----------|---------------|-------------------|------|
| Cloudflare | 1,200 requests/5 min | ~5 seconds | Free tier available |
| AWS Route 53 | 5 requests/second | ~60 seconds | $0.50/zone/month |
| Google Cloud DNS | Unlimited (with quotas) | ~30 seconds | $0.40/zone/month |
| RFC 2136 (BIND) | Unlimited | Immediate | Free (self-hosted) |
| PowerDNS | API configurable | ~1 second | Free (self-hosted) |

For self-hosted deployments, RFC 2136 with BIND or PowerDNS provides the best performance and zero cost. For cloud deployments, Cloudflare offers the best balance of speed, reliability, and cost.
