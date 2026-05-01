---
title: "Self-Hosted Circuit Breaker Patterns: Envoy vs HAProxy vs Linkerd 2026"
date: 2026-05-01
tags: ["circuit-breaker", "fault-tolerance", "envoy", "haproxy", "linkerd", "resilience", "microservices", "comparison", "guide"]
draft: false
description: "Compare self-hosted circuit breaker implementations — Envoy, HAProxy, and Linkerd. Learn how to configure outlier detection, error budgets, and automatic failover for resilient microservices with Docker configs."
---

When a downstream service starts failing, your entire application can cascade into failure. Circuit breakers prevent this by detecting unhealthy backends and short-circuiting requests before they pile up. Rather than waiting for connections to time out, a circuit breaker trips open, fails fast, and gives the failing service time to recover.

This guide compares three widely-used self-hosted circuit breaker implementations: **Envoy Proxy**, **HAProxy**, and **Linkerd**. We cover how each tool implements the circuit breaker pattern, provide Docker Compose deployment configs, and help you choose the right approach for your infrastructure.

## How Circuit Breakers Work

The circuit breaker pattern, popularized by Michael Nygard, models three states:

- **Closed** — requests flow normally. The proxy monitors success/error rates.
- **Open** — error threshold exceeded. Requests fail immediately without hitting the backend.
- **Half-Open** — after a timeout, a few test requests pass through. If they succeed, the circuit closes; if they fail, it reopens.

The key benefit is **fail-fast behavior**: instead of tying up threads waiting for an unresponsive service, the circuit breaker rejects requests immediately, preserving resources for healthy paths.

## Envoy Circuit Breaker Configuration

Envoy implements circuit breakers at the cluster level through its CircuitBreaker configuration. It tracks connection limits, request concurrency, and pending request queues.

Envoy's approach is unique because it uses **outlier detection** alongside circuit breakers. Outlier detection ejects individual unhealthy endpoints from a cluster, while circuit breakers limit aggregate resource consumption.

### Envoy Docker Compose

```yaml
version: "3.8"
services:
  envoy:
    image: envoyproxy/envoy:v1.31-latest
    ports:
      - "8080:8080"
      - "9901:9901"
    volumes:
      - ./envoy.yaml:/etc/envoy/envoy.yaml:ro
    networks:
      - app-network

  backend-a:
    image: hashicorp/http-echo
    command: ["-text", "healthy", "-listen", ":5678"]
    networks:
      - app-network

networks:
  app-network:
    driver: bridge
```

### Envoy Circuit Breaker Config

```yaml
static_resources:
  listeners:
    - name: main_listener
      address:
        socket_address:
          address: 0.0.0.0
          port_value: 8080
      filter_chains:
        - filters:
            - name: envoy.filters.network.http_connection_manager
              typed_config:
                "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
                stat_prefix: ingress
                route_config:
                  name: local_route
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
      connect_timeout: 2s
      type: STRICT_DNS
      lb_policy: ROUND_ROBIN
      load_assignment:
        cluster_name: backend_service
        endpoints:
          - lb_endpoints:
              - endpoint:
                  address:
                    socket_address:
                      address: backend-a
                      port_value: 5678
      circuit_breakers:
        thresholds:
          - priority: DEFAULT
            max_connections: 100
            max_pending_requests: 50
            max_requests: 200
            max_retries: 3
      outlier_detection:
        consecutive_5xx: 3
        interval: 10s
        base_ejection_time: 30s
        max_ejection_percent: 50
        enforcing_consecutive_5xx: 100
```

Envoy's circuit breaker tracks four key thresholds:

| Threshold | Default | Purpose |
|-----------|---------|---------|
| `max_connections` | 1024 | Max TCP connections to the cluster |
| `max_pending_requests` | 1024 | Max requests queued waiting for a connection |
| `max_requests` | 1024 | Max concurrent requests to the cluster |
| `max_retries` | 3 | Max parallel retry attempts |

When any threshold is exceeded, Envoy returns a `503 Service Unavailable` immediately — no connection attempt is made.

## HAProxy Circuit Breaker Configuration

HAProxy doesn't use the term "circuit breaker" natively, but it achieves the same outcome through **health checking plus server error tracking**. HAProxy monitors backend health with active checks and can dynamically mark servers as DOWN when they exceed error thresholds.

### HAProxy Docker Compose

```yaml
version: "3.8"
services:
  haproxy:
    image: haproxy:3.0-alpine
    ports:
      - "8080:8080"
      - "8404:8404"
    volumes:
      - ./haproxy.cfg:/usr/local/etc/haproxy/haproxy.cfg:ro
    networks:
      - app-network

  backend-a:
    image: hashicorp/http-echo
    command: ["-text", "healthy", "-listen", ":5678"]
    networks:
      - app-network

  backend-b:
    image: hashicorp/http-echo
    command: ["-text", "standby", "-listen", ":5678"]
    networks:
      - app-network

networks:
  app-network:
    driver: bridge
```

### HAProxy Health Check Config

```
global
    log stdout format raw local0
    maxconn 4096

defaults
    log     global
    mode    http
    option  httplog
    timeout connect 5s
    timeout client  30s
    timeout server  30s
    retries 2

frontend http_front
    bind *:8080
    default_backend web_servers

backend web_servers
    balance roundrobin
    option httpchk GET /health
    http-check expect status 200
    default-server inter 5s fall 3 rise 2

    server backend-a backend-a:5678 check
    server backend-b backend-b:5678 check backup

    stats enable
    stats uri /stats
    stats refresh 10s
```

HAProxy's circuit breaker behavior comes from these directives:

| Directive | Purpose |
|-----------|---------|
| `inter 5s` | Health check interval (every 5 seconds) |
| `fall 3` | Mark server DOWN after 3 consecutive check failures |
| `rise 2` | Mark server UP after 2 consecutive check successes |
| `backup` | Only route traffic when primary servers are DOWN |
| `retries 2` | Retry failed connections up to 2 times before giving up |

Unlike Envoy's per-request thresholds, HAProxy's approach is **server-state based** — it tracks the health of individual backends rather than aggregate connection limits.

## Linkerd Circuit Breaker Configuration

Linkerd, as a service mesh, implements circuit breaking through its **retry budget** and **failure accrual** policies. Unlike Envoy or HAProxy which run as standalone proxies, Linkerd injects sidecar proxies into each pod, providing per-service circuit breaker controls.

### Linkerd Installation

```bash
# Install Linkerd CLI
curl -sL https://run.linkerd.io/install | sh

# Install the control plane
linkerd install | kubectl apply -f -

# Verify installation
linkerd check
```

### Linkerd Retry and Circuit Breaker Config

```yaml
apiVersion: policy.linkerd.io/v1beta1
kind: HTTPRoute
metadata:
  name: backend-route
  namespace: default
spec:
  parentRefs:
    - name: backend-service
      kind: Service
  rules:
    - matches:
        - path:
            type: PathPrefix
            value: /
      filters:
        - type: RequestRetry
          requestRetry:
            retries: 3
            retryOn:
              - "500"
              - "502"
              - "503"
              - "504"
              - "connect-failure"
              - "retriable-4xx"
            backoff:
              maxMs: 3000
              jitterRatio: 0.5
---
apiVersion: linkerd.io/v1alpha2
kind: ServiceProfile
metadata:
  name: backend-service.default.svc.cluster.local
  namespace: default
spec:
  retryBudget:
    retryRatio: 0.2
    minRetriesPerSecond: 10
    ttl: 10s
  routes:
    - name: GET /api
      condition: "GET /api/.*"
      isRetryable: true
```

Linkerd's retry budget ensures retries don't amplify failures:

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `retryRatio` | 0.2 | Max 20% of original requests can be retried |
| `minRetriesPerSecond` | 10 | Minimum retry rate regardless of ratio |
| `ttl` | 10s | Budget window duration |
| `retries` | 3 | Max retry attempts per request |

## Comparison: Circuit Breaker Features

| Feature | Envoy | HAProxy | Linkerd |
|---------|-------|---------|---------|
| Circuit breaker type | Connection/request thresholds | Health check-based ejection | Retry budget + failure accrual |
| Outlier detection | Yes (consecutive errors, success rate) | Yes (active health checks) | Yes (via ServiceProfile) |
| Per-priority limits | Yes (DEFAULT, HIGH) | No | No |
| Ejection algorithm | Consecutive 5xx, success rate, failure percentage | Fall/rise counters | Retry budget ratio |
| Half-open state | Yes (automatic via ejection timeout) | Yes (via rise count) | Yes (budget refreshes over TTL) |
| Kubernetes native | Via xDS/gateway API | Via Kubernetes CRDs | Native (sidecar injection) |
| Configuration format | YAML/protobuf | HAProxy config file | Kubernetes CRDs |
| GitHub stars | 27,903 | 6,512 | 11,380 |
| Last updated | 2026-05-01 | 2026-04-30 | 2026-05-01 |

## When to Use Each Approach

**Use Envoy** when you need fine-grained control over connection limits, pending request queues, and per-priority thresholds. Envoy's outlier detection is the most configurable — you can eject based on consecutive errors, success rate percentage, or gateway errors. It is ideal for API gateways and service mesh data planes.

**Use HAProxy** when you want simple, battle-tested health-check-based failover. HAProxy's approach is easier to understand and configure — set your check interval, fall threshold, and rise count. It excels at traditional load balancing scenarios where you have a known set of backends and want automatic failover to backup servers.

**Use Linkerd** when you are running on Kubernetes and want circuit breaker behavior baked into your service mesh. Linkerd's retry budget approach is particularly effective at preventing retry storms — it caps retries at a percentage of original traffic, ensuring that a failing service does not get hammered by cascading retries from every caller.

## Why Self-Host Your Circuit Breaker?

Running your own circuit breaker infrastructure gives you full control over failure handling policies. When you rely on managed API gateways or cloud load balancers, you are limited to the circuit breaker options the provider exposes — often just basic health checks with fixed timeouts.

Self-hosted solutions let you tune thresholds based on your specific workload characteristics. You can set different circuit breaker policies per service, implement custom ejection algorithms, and integrate with your observability stack for real-time alerting. For teams running multi-cloud or hybrid deployments, a self-hosted circuit breaker provides consistent failure handling across all environments.

For related reading, see our [Self Hosted Mutual Tls Mtls Nginx Caddy Traefik...](../2026-04-24-self-hosted-mutual-tls-mtls-nginx-caddy-traefik-envoy-guide-2026/), and [Twemproxy Vs Mcrouter Vs Envoy Self Hosted Cach...](../2026-04-25-twemproxy-vs-mcrouter-vs-envoy-self-hosted-cache-proxy-guide-2026/).
For more on service mesh patterns, check our [Spiffe Spire Vs Istio Vs Linkerd Self Hosted Se...](../2026-04-28-spiffe-spire-vs-istio-vs-linkerd-self-hosted-service-identity-mtls-guide-2026/), and [Self Hosted Service Mesh Consul Linkerd Istio G...](../self-hosted-service-mesh-consul-linkerd-istio-guide/).

## FAQ

### What is a circuit breaker in microservices?

A circuit breaker is a design pattern that prevents cascading failures in distributed systems. It monitors requests to a downstream service and trips open when failures exceed a threshold, immediately rejecting further requests without attempting to contact the failing service. This gives the downstream service time to recover and prevents resource exhaustion in the calling service.

### How does Envoy circuit breaker differ from HAProxy?

Envoy uses connection and request thresholds (max connections, max pending requests, max concurrent requests) combined with outlier detection (consecutive errors, success rate monitoring). HAProxy uses active health checks with fall/rise counters — it marks servers as DOWN after N consecutive check failures and UP after N consecutive successes. Envoy approach is more granular per-request; HAProxy is server-state based.

### Can I use circuit breakers with Docker Compose?

Yes. Envoy and HAProxy both run as containers in a Docker Compose stack. Configure the circuit breaker settings in their respective config files (envoy.yaml or haproxy.cfg), mount them as volumes, and the proxy will enforce circuit breaker policies across all services in the compose network.

### What is outlier detection and how does it relate to circuit breakers?

Outlier detection is a complementary mechanism that ejects individual unhealthy endpoints from a load balancing pool. While circuit breakers limit aggregate resource consumption (total connections, requests), outlier detection identifies and removes specific backends that are performing poorly. Envoy supports both simultaneously — circuit breakers protect the cluster as a whole, while outlier detection protects against individual bad actors.

### Should I use a service mesh or a standalone proxy for circuit breaking?

If you are running on Kubernetes and already use a service mesh, Linkerd provides circuit breaker behavior through retry budgets and ServiceProfiles with minimal configuration overhead. If you need a standalone proxy for API gateway or edge routing use cases, Envoy or HAProxy are better choices. Envoy offers the most granular control; HAProxy offers the simplest configuration.

### What happens when a circuit breaker reopens after being open?

When a circuit breaker transitions from open to half-open, it allows a limited number of test requests through to the backend. If these test requests succeed, the circuit closes and normal traffic resumes. If they fail, the circuit reopens and waits for another timeout period. This gradual recovery prevents overwhelming a service that is still recovering from failure.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Circuit Breaker Patterns: Envoy vs HAProxy vs Linkerd 2026",
  "description": "Compare self-hosted circuit breaker implementations — Envoy, HAProxy, and Linkerd. Learn how to configure outlier detection, error budgets, and automatic failover for resilient microservices with Docker configs.",
  "datePublished": "2026-05-01",
  "dateModified": "2026-05-01",
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
