---
title: "Self-Hosted Split-Horizon DNS: Pi-hole vs dnsmasq vs CoreDNS vs BIND 9 Guide 2026"
date: 2026-04-24
tags: ["comparison", "guide", "self-hosted", "dns", "networking", "security"]
draft: false
description: "Complete guide to setting up split-horizon DNS for self-hosted environments. Compare Pi-hole, dnsmasq, CoreDNS, and BIND 9 with Docker configs and real-world deployment patterns."
---

Split-horizon DNS — also known as split-brain DNS or split-view DNS — is a configuration where a DNS server returns different answers depending on who is asking. Internal clients on your local network get private IP addresses (like `192.168.1.50`), while external queries from the internet receive public IP addresses (like `203.0.113.10`). This is one of the most powerful techniques for self-hosters who want to use the same domain names both inside and outside their network.

In this guide, we compare four popular open-source tools for implementing split-horizon DNS, with Docker Compose configurations, step-by-step setup instructions, and real-world deployment patterns.

## Why Self-Hosted Split-Horizon DNS Matters

When you run self-hosted services — a Nextcloud instance, a Gitea forge, a Jellyfin media server — you typically want to access them using the same domain name whether you're on your home network or browsing from a coffee shop. Without split-horizon DNS, you face a choice: use the public IP everywhere (wasting bandwidth by routing local traffic through the internet) or use the private IP locally and the public IP remotely (managing two separate hostnames for the same service).

Split-horizon DNS eliminates this problem. It's the foundation of a proper homelab network, enabling:

- **Consistent domain names** — `nextcloud.example.com` resolves correctly from everywhere
- **Reduced latency** — local traffic stays local, no hairpin NAT required
- **Improved security** — internal infrastructure details stay hidden from external queries
- **Service availability** — services remain accessible locally even when the public internet connection is down

For related reading on DNS fundamentals, check out our [self-hosted DNS resolver guide](../self-hosted-dns-resolvers-unbound-dnsmasq-bind-coredns-guide-2026/) and [DNS firewall and RPZ configuration tutorial](../2026-04-21-self-hosted-dns-firewall-rpz-unbound-powerdns-bind9-knot-guide-2026/).

## Comparison: Split-Horizon DNS Solutions

| Feature | Pi-hole | dnsmasq | CoreDNS | BIND 9 |
|---|---|---|---|---|
| **Split-horizon method** | Custom DNS records + DHCP | Conditional forwarding per interface | Plugin chain with rewrite | Views (ACL-based zones) |
| **Complexity** | Low (web UI) | Low (config file) | Medium (YAML plugins) | High (named.conf) |
| **Web UI** | Yes (built-in) | No | Yes (optional dashboard) | No |
| **Ad blocking** | Yes | No | Via plugins | No |
| **Docker support** | Official image | Community images | Official image | Official image |
| **Kubernetes ready** | No | No | Yes (native) | No |
| **Query logging** | Yes (web dashboard) | Syslog only | Yes (log plugin) | Yes (named logs) |
| **IPv6 support** | Yes | Yes | Yes | Yes |
| **DNSSEC validation** | Via forwarder | Yes | Yes | Yes |
| **Performance** | Good (lightweight) | Excellent (minimal) | Good (Go-based) | Good (C-based) |
| **Learning curve** | Beginner | Beginner | Intermediate | Advanced |
| **Best for** | Home users, homelabs | Embedded, routers | Kubernetes, cloud | Enterprise DNS |

Pi-hole currently has **57,679 stars** on GitHub and was last updated on 2026-04-22. It's the most popular choice for home users because the web interface makes configuration straightforward, and the split-horizon setup leverages its built-in "Local DNS" records feature combined with DHCP-provided DNS.

## Configuring Pi-hole for Split-Horizon DNS

Pi-hole handles split-horizon DNS through a combination of local DNS records and conditional forwarding. When internal clients query a domain that exists in your Local DNS configuration, Pi-hole returns the private IP. For everything else, queries are forwarded upstream.

### Docker Compose Setup

```yaml
services:
  pihole:
    image: pihole/pihole:latest
    container_name: pihole
    restart: unless-stopped
    environment:
      TZ: "America/New_York"
      WEBPASSWORD: "your-admin-password"
      ServerIPv4: "192.168.1.10"
    volumes:
      - "./etc-pihole:/etc/pihole"
      - "./etc-dnsmasq.d:/etc/dnsmasq.d"
    ports:
      - "53:53/tcp"
      - "53:53/udp"
      - "80:80/tcp"
    cap_add:
      - NET_ADMIN
    networks:
      pihole-net:
        ipv4_address: 192.168.1.10

networks:
  pihole-net:
    driver: macvlan
    driver_opts:
      parent: eth0
    ipam:
      config:
        - subnet: 192.168.1.0/24
          gateway: 192.168.1.1
```

### Split-Horizon Configuration via dnsmasq.d

Pi-hole uses dnsmasq under the hood. Add custom split-horizon rules by creating files in the mounted `/etc/dnsmasq.d` volume:

```bash
# /etc-dnsmasq.d/02-split-horizon.conf

# Override internal services to use local IPs
address=/nextcloud.example.com/192.168.1.50
address=/gitea.example.com/192.168.1.51
address=/jellyfin.example.com/192.168.1.52

# Conditional forwarding for the entire internal domain
server=/example.com/192.168.1.1

# Tag-based split DNS — different responses per client subnet
# Clients on 10.0.0.0/8 get internal IPs
server=/internal.example.com/192.168.1.1

# DHCP integration — Pi-hole provides DNS to DHCP clients
dhcp-range=192.168.1.100,192.168.1.200,255.255.255.0,24h
```

With this setup, any internal client using Pi-hole as its DNS server will resolve `nextcloud.example.com` to `192.168.1.50`. External clients querying your public DNS (not Pi-hole) will resolve it to your public IP via your authoritative DNS server.

## Configuring dnsmasq for Split-Horizon DNS

dnsmasq is the lightweight DNS and DHCP server that powers Pi-hole and many router firmware projects. Running it standalone gives you a minimal, highly efficient split-horizon setup without the web UI overhead.

### Docker Compose Setup

```yaml
services:
  dnsmasq:
    image: jpillora/dnsmasq:latest
    container_name: dnsmasq
    restart: unless-stopped
    ports:
      - "53:53/tcp"
      - "53:53/udp"
    volumes:
      - "./dnsmasq.conf:/etc/dnsmasq.conf:ro"
      - "./hosts:/etc/hosts:ro"
    cap_add:
      - NET_ADMIN
    networks:
      - host

networks:
  host:
    external: true
```

### Configuration File

```ini
# /etc/dnsmasq.conf — Split-horizon setup

# Listen on all interfaces (or specify: interface=eth0)
listen-address=0.0.0.0
interface=eth0
except-interface=lo

# Upstream DNS servers
server=8.8.8.8
server=1.1.1.1

# Split-horizon: override specific domains for internal clients
address=/app.example.com/192.168.1.100
address=/wiki.example.com/192.168.1.101
address=/git.example.com/192.168.1.102

# Override the entire internal domain
server=/internal.example.com/192.168.1.1

# Read additional host mappings from /etc/hosts
addn-hosts=/etc/hosts

# Enable DHCP with DNS server assignment
dhcp-range=192.168.1.50,192.168.1.150,12h
dhcp-option=option:dns-server,192.168.1.10

# Log queries for debugging
log-queries
log-dhcp
```

The dnsmasq approach is ideal when you want a simple, single-config-file solution. The `addn-hosts` directive lets you maintain a standard `/etc/hosts` file alongside dnsmasq rules, which is useful for managing dozens of internal services.

## Configuring CoreDNS for Split-Horizon DNS

CoreDNS takes a fundamentally different approach: it's a plugin-based DNS server written in Go. Each feature (forwarding, caching, rewriting, logging) is a separate plugin chained together in a Corefile. This makes it extremely flexible for complex split-horizon scenarios, especially in Kubernetes environments.

### Docker Compose Setup

```yaml
services:
  coredns:
    image: coredns/coredns:latest
    container_name: coredns
    restart: unless-stopped
    command: -conf /etc/coredns/Corefile
    ports:
      - "53:53/tcp"
      - "53:53/udp"
    volumes:
      - "./Corefile:/etc/coredns/Corefile:ro"
    cap_add:
      - NET_BIND_SERVICE
    networks:
      coredns-net:
        ipv4_address: 192.168.1.20

networks:
  coredns-net:
    driver: bridge
    ipam:
      config:
        - subnet: 192.168.1.0/24
```

### Corefile Configuration

```
# Corefile — Split-horizon DNS with rewrite plugin

# Zone for the example.com domain
example.com {
    # Rewrite responses based on client source
    # Internal clients get private IPs
    rewrite name nextcloud.example.com nextcloud.internal.example.com
    rewrite name gitea.example.com gitea.internal.example.com

    # Hosts plugin for internal IP mapping
    hosts {
        192.168.1.50 nextcloud.internal.example.com
        192.168.1.51 gitea.internal.example.com
        192.168.1.52 jellyfin.internal.example.com
        fallthrough
    }

    # Cache responses for performance
    cache 30

    # Log all queries
    log

    # Forward external queries
    forward . 8.8.8.8 1.1.1.1
}

# Default zone — forward everything else
. {
    cache 300
    forward . 8.8.8.8 1.1.1.1
    log
}
```

For a more advanced split-horizon setup using the `acl` plugin to differentiate by client IP:

```
# Advanced split-horizon: different views per subnet

# Internal view (192.168.0.0/16)
example.com:53 {
    acl {
        allow 192.168.0.0/16
        block 0.0.0.0/0
    }

    hosts /etc/coredns/internal.hosts {
        fallthrough
    }

    cache 30
    log
}

# External view — forward to upstream
example.com:53 {
    forward . 8.8.8.8
    cache 30
    log
}
```

CoreDNS shines when you need programmatic DNS resolution. The `file` plugin can read zone files, the `hosts` plugin handles static mappings, and the `rewrite` plugin transforms queries on the fly — all without restarting the server.

## Configuring BIND 9 for Split-Horizon DNS

BIND 9 is the industry-standard authoritative and recursive DNS server. Its "views" feature is the most powerful split-horizon mechanism available, allowing completely different zone configurations based on the client's source IP address, network interface, or other ACL criteria.

### Docker Compose Setup

```yaml
services:
  bind9:
    image: ubuntu/bind9:latest
    container_name: bind9
    restart: unless-stopped
    environment:
      BIND9_USER: bind
      DNS_FORWARDERS: "8.8.8.8; 1.1.1.1;"
    ports:
      - "53:53/tcp"
      - "53:53/udp"
    volumes:
      - "./named.conf:/etc/bind/named.conf:ro"
      - "./named.conf.options:/etc/bind/named.conf.options:ro"
      - "./zones-internal:/etc/bind/zones-internal:ro"
      - "./zones-external:/etc/bind/zones-external:ro"
      - "./cache:/var/cache/bind"
    cap_add:
      - NET_BIND_SERVICE
    networks:
      bind9-net:
        ipv4_address: 192.168.1.30

networks:
  bind9-net:
    driver: bridge
    ipam:
      config:
        - subnet: 192.168.1.0/24
```

### named.conf with Views

```
// /etc/bind/named.conf — Split-horizon DNS using views

// ACL definitions
acl "internal" {
    192.168.0.0/16;
    10.0.0.0/8;
    172.16.0.0/12;
    localhost;
};

acl "external" {
    any;
};

// Internal view — local network gets private IPs
view "internal" {
    match-clients { internal; };
    recursion yes;

    zone "example.com" {
        type master;
        file "/etc/bind/zones-internal/db.example.com.internal";
        allow-transfer { none; };
    };

    // Forward unknown queries
    zone "." {
        type hint;
        file "/usr/share/dns/root.hints";
    };
};

// External view — internet gets public IPs
view "external" {
    match-clients { external; };
    recursion no;

    zone "example.com" {
        type master;
        file "/etc/bind/zones-external/db.example.com.external";
        allow-transfer { trusted-slaves; };
        allow-query { any; };
    };
};
```

### Internal Zone File

```
; /etc/bind/zones-internal/db.example.com.internal
$TTL 86400
@       IN      SOA     ns1.example.com. admin.example.com. (
                        2026042401  ; Serial
                        3600        ; Refresh
                        1800        ; Retry
                        604800      ; Expire
                        86400 )     ; Minimum TTL

        IN      NS      ns1.example.com.
ns1     IN      A       192.168.1.30

; Internal services — private IPs
@       IN      A       192.168.1.50
nextcloud IN    A       192.168.1.50
gitea   IN      A       192.168.1.51
jellyfin IN     A       192.168.1.52
wiki    IN      A       192.168.1.53
```

### External Zone File

```
; /etc/bind/zones-external/db.example.com.external
$TTL 86400
@       IN      SOA     ns1.example.com. admin.example.com. (
                        2026042401  ; Serial
                        3600        ; Refresh
                        1800        ; Retry
                        604800      ; Expire
                        86400 )     ; Minimum TTL

        IN      NS      ns1.example.com.
ns1     IN      A       203.0.113.10

; External services — public IPs
@       IN      A       203.0.113.10
nextcloud IN    A       203.0.113.10
gitea   IN      A       203.0.113.11
jellyfin IN     A       203.0.113.12
wiki    IN      A       203.0.113.13
```

BIND 9 views are the most powerful split-horizon mechanism because they allow completely independent zone files for internal and external clients. This means you can have entirely different DNS records, different SOA serials, and different NS delegations for each view.

## Deployment Patterns

### Pattern 1: Pi-hole as Primary DNS with DHCP Integration

The simplest setup for a homelab. Configure your router's DHCP server to hand out Pi-hole's IP as the DNS server. Add all internal service IPs via Pi-hole's Local DNS Records (or the `dnsmasq.d` method shown above). External clients continue to use your domain registrar's DNS or your authoritative nameserver.

```
Internet → Your Router → Pi-hole (192.168.1.10)
                                  ├── nextcloud.example.com → 192.168.1.50
                                  ├── gitea.example.com → 192.168.1.51
                                  └── All other → Forward to 8.8.8.8
```

### Pattern 2: CoreDNS as Kubernetes DNS Gateway

In Kubernetes deployments, CoreDNS runs as the cluster DNS by default. Configure the `rewrite` and `hosts` plugins to handle split-horizon resolution for services that need to be accessible from both inside and outside the cluster.

```yaml
# Ingress with internal DNS override
apiVersion: v1
kind: ConfigMap
metadata:
  name: coredns
  namespace: kube-system
data:
  Corefile: |
    .:53 {
        errors
        health
        rewrite name myservice.example.com myservice.default.svc.cluster.local
        kubernetes cluster.local in-addr.arpa ip6.arpa {
            pods insecure
            fallthrough in-addr.arpa ip6.arpa
        }
        forward . /etc/resolv.conf
        cache 30
        loop
        reload
        loadbalance
    }
```

### Pattern 3: BIND 9 Views for Enterprise DNS

For organizations with multiple office locations, BIND 9 views can be extended to provide geographic-aware DNS. Each office network gets its own view with optimized server selections.

```
view "office-newyork" {
    match-clients { 10.1.0.0/16; };
    // Zone files with NY-local server IPs
};

view "office-london" {
    match-clients { 10.2.0.0/16; };
    // Zone files with London-local server IPs
};

view "office-tokyo" {
    match-clients { 10.3.0.0/16; };
    // Zone files with Tokyo-local server IPs
};
```

## Troubleshooting Common Issues

**DNS caching problems**: When you change a split-horizon record, clients may still see the old IP due to OS-level DNS caching. On Linux, clear with `sudo systemd-resolve --flush-caches`. On macOS, use `sudo dscacheutil -flushcache`. Windows uses `ipconfig /flushdns`.

**VPN split-DNS**: When connected to a WireGuard or Tailscale VPN, your device's DNS resolver may prioritize the VPN's DNS server over local resolution. Configure your VPN to push the split-horizon DNS server as the primary DNS, or use domain-based routing (e.g., Tailscale's MagicDNS). For more on secure remote access, see our [WireGuard VPN deployment guide](../firezone-vs-pritunl-vs-netbird-self-hosted-wireguard-vpn-guide-2026/).

**NAT loopback / hairpinning**: If your router doesn't support NAT loopback, external IP resolution from inside the network will fail. Split-horizon DNS is the correct solution — always resolve to the internal IP for local clients.

**DNSSEC validation failures**: When using split views, ensure DNSSEC signatures are consistent across both views. BIND 9 handles this with inline signing; for Pi-hole, ensure your upstream forwarder validates DNSSEC properly.

## FAQ

### What is the difference between split-horizon DNS and DNS views?

Split-horizon DNS is the general concept of returning different DNS answers based on the client's location or network. DNS views are BIND 9's specific implementation of this concept — an ACL-based mechanism that selects which zone file to serve based on the client's source IP. Other tools like dnsmasq achieve the same result using `address=` directives, while CoreDNS uses the `rewrite` and `hosts` plugins.

### Can Pi-hole truly do split-horizon DNS?

Pi-hole achieves split-horizon behavior through its Local DNS Records feature combined with dnsmasq configuration files in `/etc/dnsmasq.d`. It doesn't have true "views" like BIND 9 — every client querying Pi-hole gets the same response. However, since Pi-hole is typically only queried by internal clients (configured as the DHCP DNS server), the effect is equivalent: internal clients get private IPs while external clients query your public authoritative DNS.

### Do I need split-horizon DNS if I use a VPN?

If your VPN routes all DNS queries through the tunnel, you still need split-horizon DNS to ensure internal service names resolve to private IPs. Without it, `nextcloud.example.com` might resolve to the public IP, causing traffic to leave the VPN tunnel, traverse the internet, and re-enter through your firewall — a pattern called "trombone routing" that adds latency and defeats the purpose of the VPN.

### Which tool should I choose for my homelab?

For most homelab users, **Pi-hole** is the best starting point — it provides a web interface, ad blocking, and straightforward split-horizon configuration through Local DNS records. If you need more advanced conditional forwarding or DHCP integration, **dnsmasq** running standalone is lighter and more configurable. For Kubernetes-based homelabs, **CoreDNS** integrates natively. Reserve **BIND 9** for enterprise environments requiring completely independent zone files for internal and external views.

### How do I test if split-horizon DNS is working correctly?

Use `dig` or `nslookup` from both an internal and external network to compare responses:

```bash
# From internal network
dig @192.168.1.10 nextcloud.example.com +short
# Expected: 192.168.1.50

# From external network (or using a public DNS)
dig @8.8.8.8 nextcloud.example.com +short
# Expected: 203.0.113.10
```

If both return the same IP, your split-horizon configuration needs adjustment. Also verify that `dig` shows the correct answer source with `+comments` flag enabled.

### Can I use split-horizon DNS with Docker containers?

Yes. When running DNS servers in Docker, use `macvlan` or `host` networking to ensure the DNS server is reachable on your local network IP (port 53). Standard Docker bridge networking creates a separate subnet that your LAN clients cannot reach directly. The Docker Compose examples in this guide use `macvlan` for Pi-hole and `host` networking for dnsmasq to solve this issue.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Split-Horizon DNS: Pi-hole vs dnsmasq vs CoreDNS vs BIND 9 Guide 2026",
  "description": "Complete guide to setting up split-horizon DNS for self-hosted environments. Compare Pi-hole, dnsmasq, CoreDNS, and BIND 9 with Docker configs and real-world deployment patterns.",
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
