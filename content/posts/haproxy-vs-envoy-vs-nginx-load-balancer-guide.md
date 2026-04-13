---
title: "HAProxy vs Envoy vs Nginx: Best Self-Hosted Load Balancer 2026"
date: 2026-04-13
tags: ["comparison", "guide", "self-hosted", "docker", "network", "infrastructure"]
draft: false
description: "Compare HAProxy, Envoy, and Nginx as self-hosted load balancers. Complete Docker setup guides, feature comparison, and performance benchmarks for 2026."
---

## Why You Need a Self-Hosted Load Balancer

A load balancer sits in front of your services and distributes incoming traffic across multiple backend instances. For self-hosted infrastructure, this is essential:

- **High Availability**: If one backend goes down, traffic routes to healthy instances automatically.
- **Horizontal Scaling**: Add more application instances behind the balancer without changing your DNS or client configuration.
- **SSL/TLS Termination**: Offload certificate management to a single point, reducing complexity across your services.
- **Health Checking**: Automatically detect and remove unhealthy backends from the pool.
- **Traffic Management**: Route requests based on path, headers, weight, or geolocation.

While a reverse proxy (covered in our [Nginx Proxy Manager vs Traefik vs Caddy guide](/posts/reverse-proxy-comparison/)) focuses on routing and security, a load balancer specializes in distributing load and maintaining service availability. Many tools do both — the distinction is about where the emphasis lies.

If you run anything beyond a single hobby service — a self-hosted SaaS, a team API platform, or a multi-instance media server — a dedicated load balancer becomes a critical piece of infrastructure.

## HAProxy vs Envoy vs Nginx: Quick Comparison

| Feature | HAProxy | Envoy | Nginx |
|---------|---------|-------|-------|
| **Type** | Dedicated LB | Cloud-native proxy | Web server + LB |
| **Protocol Support** | TCP/HTTP/HTTP2/HTTP3 | TCP/HTTP/HTTP2/HTTP3/gRPC | TCP/HTTP/HTTP2/HTTP3 |
| **Load Balancing** | Round-robin, leastconn, uri, hdr, random | Round-robin, random, weighted, ring hash, maglev | Round-robin, leastconn, ip_hash, hash |
| **Health Checks** | ✅ Active + Passive | ✅ Active + Passive (outlier detection) | ✅ Active (plus module) |
| **Dynamic Config** | Runtime API | xDS API (hot reload) | Requires reload |
| **Observability** | Stats page, Prometheus exporter | Built-in stats, Prometheus, tracing, logging | Stub_status, basic metrics |
| **gRPC Support** | ✅ (since 2.0) | ✅ Native | ✅ |
| **Service Discovery** | DNS resolvers, Lua | DNS, xDS, EDS, CDS | Limited (resolver directive) |
| **Rate Limiting** | Stick tables | Local + global rate limit | limit_req, limit_conn |
| **Configuration** | Simple, declarative | Complex, hierarchical | Declarative (nginx.conf) |
| **Learning Curve** | Low-Medium | High | Medium |
| **Performance** | Excellent | Very Good | Excellent |
| **Best For** | Traditional LB, simplicity | Kubernetes, microservices | Web serving + LB combined |

## HAProxy: The Battle-Tested Choice

HAProxy has been the gold standard for software load balancing since 2001. It powers some of the largest websites on the internet and is known for its rock-solid stability and excellent performance under heavy load.

### Key Strengths

- **Performance**: Handles millions of concurrent connections with minimal memory overhead. Consistently tops independent benchmarks for raw throughput.
- **Simplicity**: The configuration file is intuitive. A basic load balancer setup takes fewer than 20 lines.
- **Layer 4 + Layer 7**: Full support for both TCP (Layer 4) and HTTP (Layer 7) load balancing in a single binary.
- **Runtime API**: Change backend server weights, enable/disable servers, and view stats without reloading the process.
- **Stick Tables**: Powerful rate limiting and abuse prevention using in-memory key-value stores.

### HAProxy Docker Setup

Here's a production-ready Docker Compose configuration for HAProxy load balancing a web application across three backend instances:

```yaml
version: "3.9"

services:
  haproxy:
    image: haproxy:3.1
    container_name: haproxy
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
      - "8404:8404"  # Stats page
    volumes:
      - ./haproxy.cfg:/usr/local/etc/haproxy/haproxy.cfg:ro
      - ./certs:/etc/haproxy/certs:ro
    networks:
      - lb-network

  app1:
    image: myapp:latest
    container_name: app-backend-1
    restart: unless-stopped
    environment:
      - INSTANCE_ID=1
    networks:
      - lb-network

  app2:
    image: myapp:latest
    container_name: app-backend-2
    restart: unless-stopped
    environment:
      - INSTANCE_ID=2
    networks:
      - lb-network

  app3:
    image: myapp:latest
    container_name: app-backend-3
    restart: unless-stopped
    environment:
      - INSTANCE_ID=3
    networks:
      - lb-network

networks:
  lb-network:
    driver: bridge
```

And the corresponding `haproxy.cfg`:

```
global
    log stdout format raw local0
    maxconn 50000
    daemon

defaults
    log     global
    mode    http
    option  httplog
    option  dontlognull
    option  forwardfor
    timeout connect 5000ms
    timeout client  50000ms
    timeout server  50000ms
    retries 3

frontend http_front
    bind *:80
    bind *:443 ssl crt /etc/haproxy/certs/
    http-request redirect scheme https unless { ssl_fc }
    
    # Rate limiting: 100 requests per 10 seconds per IP
    stick-table type ip size 100k expire 30s store http_req_rate(10s)
    http-request track-sc0 src
    http-request deny deny_status 429 if { sc_http_req_rate(0) gt 100 }

    # Path-based routing
    acl is_api path_beg /api
    acl is_static path_beg /static /assets

    use_backend api_servers if is_api
    use_backend static_servers if is_static
    default_backend app_servers

backend app_servers
    balance leastconn
    option httpchk GET /healthz
    http-check expect status 200
    server app1 app1:8080 check inter 5s fall 3 rise 2
    server app2 app2:8080 check inter 5s fall 3 rise 2
    server app3 app3:8080 check inter 5s fall 3 rise 2

backend api_servers
    balance roundrobin
    option httpchk GET /api/health
    http-check expect status 200
    server app1 app1:8080 check inter 5s fall 3 rise 2
    server app2 app2:8080 check inter 5s fall 3 rise 2
    server app3 app3:8080 check inter 5s fall 3 rise 2

backend static_servers
    balance roundrobin
    server app1 app1:8080 check
    server app2 app2:8080 check
    server app3 app3:8080 check

listen stats
    bind *:8404
    stats enable
    stats uri /stats
    stats refresh 10s
    stats auth admin:securepassword
```

This configuration gives you:

- **Least-connection balancing** for the main app (sends traffic to the least busy server)
- **Active health checks** every 5 seconds with automatic failover
- **Rate limiting** at 100 requests per 10 seconds per source IP
- **Path-based routing** separating API, static, and general traffic
- **A live stats dashboard** at port 8404

### HAProxy Runtime Management

One of HAProxy's best features is the ability to modify backends without downtime:

```bash
# Connect to the runtime API via socat
echo "show stat" | socat stdio /var/run/haproxy.sock

# Disable a backend server for maintenance
echo "disable server app_servers/app2" | socat stdio /var/run/haproxy.sock

# Set a server weight to 50%
echo "set server app_servers/app1 weight 50%" | socat stdio /var/run/haproxy.sock

# Graceful reload (zero downtime)
echo "add server app_servers/app4 10.0.0.4:8080 check" | socat stdio /var/run/haproxy.sock
```

## Envoy: The Cloud-Native Powerhouse

Envoy was originally built at Lyft and donated to the CNCF. It has become the backbone of modern service mesh architectures (Istio uses Envoy as its data plane). Envoy's strength lies in its dynamic configuration model — it can receive live updates from a control plane without ever dropping connections.

### Key Strengths

- **xDS Protocol**: Dynamic service discovery, configuration, and health reporting via a standardized API. Works seamlessly with Kubernetes and service meshes.
- **Outlier Detection**: Automatically ejects unhealthy hosts from the load balancing pool and gradually reintroduces them.
- **Rich Observability**: Built-in support for distributed tracing (Jaeger, Zipkin), metrics (Prometheus, StatsD), and structured access logging.
- **gRPC Native**: First-class gRPC support including load balancing, health checking, and transcoding.
- **Extensible**: WebAssembly (Wasm) filters let you write custom logic in any language that compiles to Wasm.

### Envoy Docker Setup

Envoy's configuration is more complex but significantly more powerful. Here's a Docker Compose setup:

```yaml
version: "3.9"

services:
  envoy:
    image: envoyproxy/envoy:v1.32
    container_name: envoy
    restart: unless-stopped
    ports:
      - "80:10000"
      - "443:10001"
      - "9901:9901"  # Admin/stats
    volumes:
      - ./envoy.yaml:/etc/envoy/envoy.yaml:ro
      - ./certs:/etc/envoy/certs:ro
    networks:
      - lb-network

  app1:
    image: myapp:latest
    container_name: app-backend-1
    networks:
      - lb-network

  app2:
    image: myapp:latest
    container_name: app-backend-2
    networks:
      - lb-network

  app3:
    image: myapp:latest
    container_name: app-backend-3
    networks:
      - lb-network

networks:
  lb-network:
    driver: bridge
```

The `envoy.yaml` configuration:

```yaml
admin:
  address:
    socket_address:
      address: 0.0.0.0
      port_value: 9901

static_resources:
  listeners:
    - name: http_listener
      address:
        socket_address:
          address: 0.0.0.0
          port_value: 10000
      filter_chains:
        - filters:
            - name: envoy.filters.network.http_connection_manager
              typed_config:
                "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
                stat_prefix: ingress_http
                access_log:
                  - name: envoy.access_loggers.stdout
                    typed_config:
                      "@type": type.googleapis.com/envoy.extensions.access_loggers.stream.v3.StdoutAccessLog
                http_filters:
                  - name: envoy.filters.http.router
                    typed_config:
                      "@type": type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
                route_config:
                  name: local_route
                  virtual_hosts:
                    - name: backend
                      domains: ["*"]
                      routes:
                        - match:
                            prefix: "/api"
                          route:
                            cluster: api_cluster
                            timeout: 30s
                        - match:
                            prefix: "/"
                          route:
                            cluster: app_cluster
                            retry_policy:
                              retry_on: "5xx,connect-failure"
                              num_retries: 3
                              per_try_timeout: 10s

    - name: https_listener
      address:
        socket_address:
          address: 0.0.0.0
          port_value: 10001
      filter_chains:
        - transport_socket:
            name: envoy.transport_sockets.tls
            typed_config:
              "@type": type.googleapis.com/envoy.extensions.transport_sockets.tls.v3.DownstreamTlsContext
              common_tls_context:
                tls_certificates:
                  - certificate_chain:
                      filename: /etc/envoy/certs/fullchain.pem
                    private_key:
                      filename: /etc/envoy/certs/privkey.pem
          filters:
            - name: envoy.filters.network.http_connection_manager
              typed_config:
                "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
                stat_prefix: ingress_https
                http_filters:
                  - name: envoy.filters.http.router
                    typed_config:
                      "@type": type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
                route_config:
                  name: local_route_https
                  virtual_hosts:
                    - name: backend
                      domains: ["*"]
                      routes:
                        - match:
                            prefix: "/"
                          route:
                            cluster: app_cluster

  clusters:
    - name: app_cluster
      connect_timeout: 5s
      type: STRICT_DNS
      lb_policy: LEAST_REQUEST
      health_checks:
        - timeout: 3s
          interval: 5s
          unhealthy_threshold: 3
          healthy_threshold: 2
          http_health_check:
            path: /healthz
            expected_statuses:
              start: 200
              end: 300
      outlier_detection:
        consecutive_5xx: 3
        interval: 10s
        base_ejection_time: 30s
        max_ejection_percent: 50
      load_assignment:
        cluster_name: app_cluster
        endpoints:
          - lb_endpoints:
              - endpoint:
                  address:
                    socket_address:
                      address: app1
                      port_value: 8080
              - endpoint:
                  address:
                    socket_address:
                      address: app2
                      port_value: 8080
              - endpoint:
                  address:
                    socket_address:
                      address: app3
                      port_value: 8080

    - name: api_cluster
      connect_timeout: 5s
      type: STRICT_DNS
      lb_policy: ROUND_ROBIN
      health_checks:
        - timeout: 3s
          interval: 5s
          unhealthy_threshold: 3
          healthy_threshold: 2
          http_health_check:
            path: /api/health
            expected_statuses:
              start: 200
              end: 300
      load_assignment:
        cluster_name: api_cluster
        endpoints:
          - lb_endpoints:
              - endpoint:
                  address:
                    socket_address:
                      address: app1
                      port_value: 8080
              - endpoint:
                  address:
                    socket_address:
                      address: app2
                      port_value: 8080
              - endpoint:
                  address:
                    socket_address:
                      address: app3
                      port_value: 8080
```

Envoy's configuration uses protobuf-style JSON/YAML which is verbose but extremely precise. The key advantages visible here:

- **Outlier detection** with automatic ejection after 3 consecutive 5xx errors
- **Retry policies** with per-try timeouts
- **Health checks** with configurable thresholds
- **Least-request load balancing** (sends to the backend with fewest active requests)

### Envoy with Dynamic Service Discovery

For Kubernetes or dynamic environments, Envoy can use xDS to discover backends automatically. With the Envoy Control Plane (or a service mesh like Istio), you never need to edit configuration files — backends register and deregister themselves:

```bash
# Deploy the Envoy control plane alongside Envoy
docker run -d --name envoy-control-plane \
  -p 8081:8081 \
  envoyproxy/go-control-plane:latest

# Envoy connects to the control plane and receives:
# - CDS: Cluster Discovery Service (what backends exist)
# - EDS: Endpoint Discovery Service (where they are)
# - LDS: Listener Discovery Service (what ports to listen on)
# - RDS: Route Discovery Service (how to route traffic)
```

## Nginx: The Versatile All-Rounder

Nginx is the world's most popular web server, and its load balancing capabilities are a natural extension. If you're already running Nginx as a reverse proxy or web server, adding load balancing requires minimal additional configuration.

### Key Strengths

- **Ubiquity**: Nginx is everywhere. Documentation, tutorials, and community support are unmatched.
- **Performance**: Excellent at serving static content and proxying simultaneously. Low memory footprint even under heavy load.
- **Familiarity**: If you know Nginx configuration, you already know its load balancing syntax.
- **HTTP/3**: Native QUIC and HTTP/3 support in recent versions.
- **Ecosystem**: Massive module ecosystem (though many require recompilation).

### Nginx Docker Setup

```yaml
version: "3.9"

services:
  nginx:
    image: nginx:1.27
    container_name: nginx-lb
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/nginx/certs:ro
      - ./conf.d:/etc/nginx/conf.d:ro
    networks:
      - lb-network

  app1:
    image: myapp:latest
    container_name: app-backend-1
    networks:
      - lb-network

  app2:
    image: myapp:latest
    container_name: app-backend-2
    networks:
      - lb-network

  app3:
    image: myapp:latest
    container_name: app-backend-3
    networks:
      - lb-network

networks:
  lb-network:
    driver: bridge
```

The `nginx.conf`:

```nginx
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 10240;
    multi_accept on;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    log_format main '$remote_addr - $remote_user [$time_local] '
                    '"$request" $status $body_bytes_sent '
                    '"$http_referer" "$http_user_agent" '
                    'rt=$request_time';

    access_log /var/log/nginx/access.log main;

    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;

    # Rate limiting zone: 10 requests per second per IP
    limit_req_zone $binary_remote_addr zone=req_limit:10m rate=10r/s;
    limit_conn_zone $binary_remote_addr zone=conn_limit:10m;

    # Upstream group with least connections balancing
    upstream app_backend {
        least_conn;
        server app1:8080 max_fails=3 fail_timeout=30s;
        server app2:8080 max_fails=3 fail_timeout=30s;
        server app3:8080 max_fails=3 fail_timeout=30s backup;
    }

    # Upstream group with IP hash for session persistence
    upstream api_backend {
        ip_hash;
        server app1:8080;
        server app2:8080;
        server app3:8080;
    }

    # HTTP → HTTPS redirect
    server {
        listen 80;
        server_name _;
        return 301 https://$host$request_uri;
    }

    # HTTPS server
    server {
        listen 443 ssl http2;
        server_name example.com;

        ssl_certificate /etc/nginx/certs/fullchain.pem;
        ssl_certificate_key /etc/nginx/certs/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;
        ssl_prefer_server_ciphers on;
        ssl_session_cache shared:SSL:10m;
        ssl_session_timeout 10m;

        # Apply rate limiting
        limit_req zone=req_limit burst=20 nodelay;
        limit_conn conn_limit 100;

        # Path-based routing
        location /api/ {
            proxy_pass http://api_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_next_upstream error timeout http_500 http_502 http_503;
            proxy_connect_timeout 5s;
            proxy_read_timeout 30s;
        }

        location / {
            proxy_pass http://app_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_next_upstream error timeout http_500 http_502 http_503;
            proxy_connect_timeout 5s;
            proxy_read_timeout 60s;
        }

        # Health check endpoint (requires ngx_http_stub_status_module)
        location /nginx-health {
            stub_status on;
            access_log off;
            allow 127.0.0.1;
            deny all;
        }
    }
}
```

Nginx's load balancing features demonstrated:

- **`least_conn`**: Sends new requests to the server with fewest active connections
- **`ip_hash`**: Consistent hashing by client IP for session persistence
- **`backup`**: Designates app3 as a backup server (only used when primary servers fail)
- **`max_fails` / `fail_timeout`**: Marks a server as unavailable after 3 failures for 30 seconds
- **`proxy_next_upstream`**: Automatically retries failed requests on the next available server
- **Rate limiting** with burst handling

### Nginx Active Health Checks

The open-source version of Nginx only supports passive health checking (marking servers as down after failed requests). For active health checks (proactively pinging backends), you need Nginx Plus (commercial) or the `nginx-upstream-healthcheck` module:

```bash
# Install the health check module (open-source alternative)
# Using the open-source nginx-http-upstream-check module:

# In your upstream block:
upstream app_backend {
    server app1:8080;
    server app2:8080;
    server app3:8080;

    # Active health check every 5 seconds
    check interval=5000 rise=2 fall=3 timeout=3000 type=http;
    check_http_send "GET /healthz HTTP/1.0\r\n\r\n";
    check_http_expect_alive http_2xx http_3xx;
}
```

## Performance Benchmarks

Based on independent testing with 10,000 concurrent connections and 1 million HTTP requests:

| Metric | HAProxy 3.1 | Envoy 1.32 | Nginx 1.27 |
|--------|------------|-----------|-----------|
| **Requests/sec** | ~380,000 | ~290,000 | ~350,000 |
| **p99 Latency** | 2.1ms | 4.8ms | 2.5ms |
| **Memory at 10k conns** | ~80MB | ~220MB | ~95MB |
| **CPU (single core)** | ~65% | ~78% | ~70% |
| **Config reload time** | <1ms (zero-downtime) | <1ms (zero-downtime) | ~50ms (brief pause) |
| **TCP throughput** | ~95 Gbps | ~85 Gbps | ~90 Gbps |

**Note**: These are synthetic benchmarks under ideal conditions. Real-world performance depends heavily on your specific workload, SSL configuration, and compression settings. For most self-hosted setups, all three tools will far exceed your traffic requirements — the choice comes down to features and operational preferences, not raw speed.

## How to Choose

### Choose HAProxy if:
- You want the simplest, most battle-tested load balancer
- You need advanced Layer 4 (TCP/UDP) load balancing alongside HTTP
- You value runtime configuration changes without any process restart
- You want the best raw performance with minimal resource usage
- Your team prefers simple, readable configuration files

### Choose Envoy if:
- You're running a microservices architecture or Kubernetes cluster
- You need dynamic service discovery (xDS protocol)
- Distributed tracing and deep observability are requirements
- You're building or using a service mesh (Istio, Consul Connect)
- You need gRPC load balancing with native support
- You want WebAssembly extensibility for custom filters

### Choose Nginx if:
- You're already running Nginx as a web server or reverse proxy
- You need to serve static files and load balance in the same process
- You want the largest community and most available documentation
- You need HTTP/3 support with mature, stable implementations
- Your team already has operational experience with Nginx

## Recommended Architecture: Load Balancer + Reverse Proxy

For production self-hosted setups, the best pattern is to combine a load balancer with a reverse proxy:

```
Internet
    │
    ▼
┌─────────────────┐
│   HAProxy /     │  ← Layer 4/7 Load Balancer
│   Envoy / Nginx │     (distributes traffic, health checks)
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌────────┐
│ Caddy  │ │ Caddy  │  ← Reverse Proxy (SSL, routing per service)
└───┬────┘ └───┬────┘
    │          │
    ▼          ▼
  Services   Services  ← Your actual applications
```

This gives you the high availability and scaling of a load balancer with the routing flexibility and SSL management of a reverse proxy.

## Monitoring Your Load Balancer

Regardless of which tool you choose, set up monitoring to catch issues early:

```bash
# HAProxy: Export metrics to Prometheus
docker run -d --name haproxy-exporter \
  -p 9101:9101 \
  quay.io/prometheus/haproxy-exporter \
  --haproxy.scrape-uri="http://admin:password@haproxy:8404/stats;csv"

# Envoy: Built-in Prometheus endpoint
# Already available at :9901/stats/prometheus
# Just add to your prometheus.yml:
#   - job_name: 'envoy'
#     static_configs:
#       - targets: ['envoy:9901']

# Nginx: Use the stub_status module + nginx-prometheus-exporter
docker run -d --name nginx-exporter \
  -p 9113:9113 \
  nginx/nginx-prometheus-exporter:latest \
  --nginx.scrape-uri=http://nginx:80/nginx-health
```

## Final Thoughts

All three tools are production-grade, open-source, and capable of handling enterprise-scale traffic. For most self-hosted enthusiasts starting out, **HAProxy** offers the best balance of simplicity and power. If you're already invested in the cloud-native ecosystem with Kubernetes and service meshes, **Envoy** is the natural choice. And if you need a web server that also load balances, **Nginx** remains the versatile default.

The self-hosting advantage? You control every layer of the stack. No vendor lock-in, no hidden costs, and the ability to tune every parameter for your specific workload. Pick the tool that matches your operational comfort level and scale it as your infrastructure grows.
