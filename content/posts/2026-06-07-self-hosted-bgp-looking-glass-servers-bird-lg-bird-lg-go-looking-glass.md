---
title: "Self-Hosted BGP Looking Glass Servers: bird-lg vs bird-lg-go vs Looking Glass (PHP)"
date: "2026-06-07"
tags: ["bgp", "networking", "looking-glass", "routing", "network-monitoring", "bird", "self-hosted"]
draft: false
---

A BGP Looking Glass is a publicly accessible web interface that allows anyone to query a router's BGP routing table, run ping/traceroute tests, and inspect route advertisements — all without requiring direct router access. For network operators, hosting providers, and enterprises, a self-hosted looking glass offers transparency into your network's routing decisions and serves as a valuable troubleshooting tool for both internal teams and customers.

## Why Self-Host Your BGP Looking Glass?

Commercial BGP monitoring platforms bundle looking glass functionality into expensive network observability suites. Running your own looking glass gives you complete control over what routes are visible, eliminates per-seat licensing costs, and lets you customize the interface for your specific use case. For ISPs and hosting providers, a public looking glass builds trust — customers can verify route propagation themselves without opening a support ticket.

Beyond transparency, a self-hosted looking glass serves as an operational troubleshooting tool. When a prefix isn't reachable from certain networks, your NOC team can query BGP tables across multiple routers simultaneously to pinpoint where the route is being dropped or filtered. This dramatically reduces mean time to resolution (MTTR) compared to SSH'ing into individual routers and running manual commands.

For network engineers studying for certifications or labbing complex topologies, a looking glass deployed alongside BIRD or FRRouting in a lab environment provides visibility into how route propagation works in practice. You can inject test prefixes and watch how they propagate through your simulated AS topology.

Security is another consideration — commercial looking glass services route your queries through third-party infrastructure. A self-hosted instance keeps all query data within your own network, which matters when you're troubleshooting internal prefixes or sensitive routing configurations.

For more on BGP routing fundamentals, see our [BGP routing comparison guide](../2026-04-19-frrouting-vs-bird-vs-openbgpd-self-hosted-bgp-routing-guide-2026/). If you're building out monitoring infrastructure, our [network monitoring comparison](../2026-05-04-self-hosted-bgp-monitoring-looking-glass-exabgp-bgpalerter-looking-glass-guide/) covers ExaBGP and BGPalerter for route monitoring and alerting.

## Comparison: bird-lg vs bird-lg-go vs Looking Glass (PHP)

| Feature | bird-lg (Python) | bird-lg-go | Looking Glass (PHP) |
|---------|-----------------|------------|---------------------|
| **Language** | Python 3 + Flask | Go | PHP |
| **GitHub Stars** | ~330 | ~200 | ~530 |
| **Last Updated** | 2023 | May 2026 | May 2026 |
| **Deployment** | Flask app + uWSGI | Single binary | Apache/Nginx + PHP |
| **BIRD Version** | BIRD 1.x & 2.x | BIRD 2.x | BIRD 1.x & 2.x |
| **Multi-Router** | Yes | Yes | Yes |
| **Ping/Traceroute** | Yes (via proxy) | Yes (native) | Yes |
| **IPv6 Support** | Yes | Yes | Yes |
| **Authentication** | Basic auth proxy | Built-in | None (nginx proxy) |
| **Docker Support** | Community images | Official Dockerfile | Community images |
| **WHOIS Integration** | Limited | Yes | Yes |
| **AS-Path Visualization** | No | No | Yes |
| **BGP Community Display** | Yes | Yes | Yes |
| **REST API** | No | No | No |

### bird-lg (Python)

bird-lg is the original Python-based looking glass implementation, designed by the OpenStack community for their infrastructure. It uses a proxy architecture: a lightweight agent (`bird-proxy`) runs alongside each BIRD instance and exposes BIRD's control socket over HTTP, while a central Flask web application queries all proxies and renders results. This proxy model means the web server doesn't need direct filesystem access to BIRD's socket.

```bash
# Install bird-lg proxy on each BIRD router
pip install bird-lg
bird-proxy --bind 0.0.0.0:8888 --socket /run/bird/bird.ctl

# Run the web frontend
git clone https://github.com/sileht/bird-lg
cd bird-lg/web
pip install -r requirements.txt
export BIRDPROXY_SERVERS="router1:8888,router2:8888"
python app.py
```

```yaml
# Docker Compose for bird-lg
version: "3.8"
services:
  birdlg:
    image: ghcr.io/example/bird-lg:latest
    ports:
      - "5000:5000"
    environment:
      - BIRDPROXY_SERVERS=router1.example.com:8888,router2.example.com:8888
      - SECRET_KEY=your-random-secret-key
    restart: unless-stopped
```

### bird-lg-go

bird-lg-go is a ground-up Go rewrite that addresses bird-lg's main pain points: Python dependency management and complex multi-process deployment. The entire application — proxy, web frontend, and CLI tools — compiles into a single statically linked binary. This eliminates Python virtual environment issues and makes deployment trivial on any Linux system. bird-lg-go also adds native ping/traceroute through Go's stdlib (no external proxy needed) and includes WHOIS lookup integration.

```bash
# Download and run — single binary, no dependencies
wget https://github.com/xddxdd/bird-lg-go/releases/latest/download/bird-lg-go_linux_amd64
chmod +x bird-lg-go_linux_amd64
./bird-lg-go_linux_amd64 --servers router1,router2 --listen :5000
```

```yaml
# Docker Compose for bird-lg-go
version: "3.8"
services:
  bird-lg-go:
    image: ghcr.io/xddxdd/bird-lg-go:latest
    ports:
      - "5000:5000"
    volumes:
      - ./servers.yaml:/etc/bird-lg-go/servers.yaml:ro
    restart: unless-stopped
```

bird-lg-go also supports a YAML configuration file for defining multiple router groups — useful for organizations with separate edge, core, and peering routers:

```yaml
servers:
  edge:
    - name: Edge Router 1
      host: edge1.example.com
      proxy_port: 8000
  core:
    - name: Core Router 1
      host: core1.example.com
      proxy_port: 8000
```

### Looking Glass (PHP)

Looking Glass is the most mature and feature-rich option, originally developed for the DN42 experimental network and now widely deployed by ISPs and hosting providers. Written in PHP, it runs behind any standard web server (Apache, Nginx, Caddy) and supports a wide range of router backends beyond BIRD — including Cisco IOS, Juniper JunOS, Quagga, FRRouting, VyOS, and MikroTik RouterOS. This multi-vendor support is its killer feature: if your network runs a mix of BIRD on Linux and JunOS on physical routers, a single Looking Glass instance can query all of them.

```bash
# Install Looking Glass
cd /var/www/html
git clone https://github.com/respawner/looking-glass
cd looking-glass
cp config.php.example config.php
# Edit config.php to add your routers
```

```php
// config.php — router configuration
$routers = [
    'router1' => [
        'host' => '192.168.1.1',
        'user' => 'lg-user',
        'password' => 'secure-password',
        'type' => 'bird',
    ],
    'router2' => [
        'host' => '192.168.1.2',
        'user' => 'lg-user',
        'type' => 'juniper',
    ],
];
```

## Deployment Architecture

A typical production deployment places the looking glass web server behind a reverse proxy (Nginx or Caddy) with TLS termination and optional authentication. Each BIRD router runs a lightweight proxy agent that the web server queries:

```
[User Browser] → [Nginx/TLS] → [Looking Glass App] → [bird-proxy on Router 1]
                                                     → [bird-proxy on Router 2]
                                                     → [bird-proxy on Router 3]
```

For security, restrict the proxy agent to listen only on localhost or a management VLAN interface, and use firewall rules to limit which IPs can connect to the proxy port. Never expose the BIRD control socket proxy directly to the public internet.

### Reverse Proxy Configuration (Nginx)

```nginx
server {
    listen 443 ssl http2;
    server_name lg.example.com;

    ssl_certificate /etc/letsencrypt/live/lg.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/lg.example.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Rate limiting to prevent abuse
        limit_req zone=lookinglass burst=10 nodelay;
    }
}

# Rate limit zone (in http block)
limit_req_zone $binary_remote_addr zone=lookinglass:10m rate=5r/s;
```

## Choosing the Right Looking Glass

**Choose bird-lg (Python)** if you want a proven, battle-tested solution and are comfortable managing Python dependencies. The OpenStack community has used it in production for years, and the proxy architecture is well-understood.

**Choose bird-lg-go** if you want the simplest possible deployment — a single binary you can drop onto any server. The Go rewrite is actively maintained (updated May 2026), adds native traceroute and WHOIS, and supports the same multi-router configuration as the original. Ideal for quick deployments and environments where Python dependency management is a friction point.

**Choose Looking Glass (PHP)** if you operate a multi-vendor router environment (BIRD + Cisco + Juniper + MikroTik) or need advanced features like AS-path visualization and comprehensive WHOIS integration. It's the most mature project with the largest feature set, but requires a PHP web server stack.

## FAQ

### What exactly does a BGP Looking Glass show?

A BGP Looking Glass lets you query a router's BGP table through a web interface. You can look up how a specific IP prefix is routed — which AS path it takes, what communities are attached, and which next-hop the router has selected. You can also run ping and traceroute from the router's perspective, which is invaluable for troubleshooting reachability issues from different points in your network.

### Do I need to run BIRD to use these looking glass tools?

bird-lg and bird-lg-go are specifically designed for BIRD (versions 1.x and 2.x). Looking Glass (PHP) supports BIRD plus 15+ other router platforms including Cisco IOS, Juniper JunOS, FRRouting, Quagga, VyOS, MikroTik RouterOS, and OpenBGPd. If you're running a multi-vendor network, Looking Glass (PHP) is the clear choice.

### Is it safe to expose a looking glass to the public internet?

Yes, with proper precautions. The looking glass web application should run behind a reverse proxy with rate limiting. The bird-proxy agent should only listen on localhost or a management VLAN — never expose it directly. Use a read-only BIRD user for the proxy connection so that even if the web app is compromised, an attacker cannot modify your BGP configuration. Some operators also limit which prefixes can be queried to prevent reconnaissance of internal routing.

### Can I use these in a Kubernetes environment?

Yes. All three tools can be containerized. bird-lg-go is particularly well-suited for Kubernetes because of its single-binary design and health check endpoints. Deploy it as a Deployment with a Service and Ingress, and configure the router list via a ConfigMap. The stateless design means you can scale horizontally behind a load balancer.

### How does this differ from BGP monitoring tools like BGPalerter?

A looking glass is for **on-demand queries** — someone actively looks up a prefix or runs a traceroute. BGP monitoring tools like BGPalerter, ExaBGP, and ARTEMIS **continuously watch** BGP updates and alert on anomalies like hijacks, route leaks, or unexpected AS path changes. They serve complementary roles: monitoring catches problems automatically, while the looking glass helps diagnose them. For a full BGP operations stack, you typically run both.

---

**💰 Want to test your market judgment? I use [Polymarket](https://polymarket.com/?r=fc8a0) for prediction market trading — the world's largest prediction market platform, where you can bet on everything from election outcomes to tech regulation timelines. Unlike gambling, this is a real information market: the more you know, the better your odds. I've earned quite a bit predicting tech-related events. Sign up with my referral link: [Polymarket.com](https://polymarket.com/?r=fc8a0)**

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted BGP Looking Glass Servers: bird-lg vs bird-lg-go vs Looking Glass (PHP)",
  "description": "Compare three open-source BGP looking glass servers — bird-lg (Python), bird-lg-go, and Looking Glass (PHP) — for self-hosting network route visibility tools. Includes Docker Compose configurations, Nginx reverse proxy setup, and deployment best practices.",
  "datePublished": "2026-06-07",
  "dateModified": "2026-06-07",
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