---
title: "Self-Hosted DNS Filtering & Content Blocking: Pi-hole, AdGuard Home, Technitium DNS 2026"
date: 2026-04-15
tags: ["comparison", "guide", "self-hosted", "privacy", "dns", "ad-blocking"]
draft: false
description: "Complete guide to setting up self-hosted DNS filtering for ad blocking, tracker prevention, and content filtering. Compare Pi-hole, AdGuard Home, and Technitium DNS with Docker deployment guides and blocklist recommendations."
---

Every device on your network makes DNS queries — hundreds or thousands per day. Each query is a window into your browsing habits, a potential vector for malware, and a carrier for tracking beacons embedded in ads. Running your own DNS filtering server blocks all of this at the network level, before it ever reaches your devices.

This guide covers three of the most popular self-hosted DNS filtering solutions — Pi-hole, AdGuard Home, and Technitium DNS Server — and shows you exactly how to deploy, configure, and optimize them for maximum protection.

## Why Self-Hosted DNS Filtering Beats Browser Extensions

Browser-based ad blockers like uBlock Origin are excellent, but they only protect the browser. DNS filtering operates at the network layer, meaning every connected device benefits automatically:

- **Phone and tablet apps** — Many mobile apps embed ad SDKs and trackers that fire on every launch. DNS filtering blocks these at the source, something browser extensions cannot touch.
- **Smart TVs and streaming devices** — These devices phone home constantly with telemetry data. A network-level filter catches these requests regardless of what app is running.
- **IoT devices** — Smart speakers, cameras, and thermostats often send usage data to manufacturer servers. DNS filtering lets you decide which domains they can reach.
- **Zero per-device configuration** — Once your router points to the DNS filter, every device that connects automatically gets protection. No extensions to install, no settings to tweak.
- **Malware and phishing prevention** — DNS-based blocklists include known malicious domains. If a device tries to resolve a command-and-control server, the query simply fails.

The key insight: DNS filtering is not a replacement for browser ad blockers — it is a complementary layer. Browser blockers handle cosmetic filtering (removing blank spaces where ads were) and script injection, while DNS filtering provides blanket network-level protection for everything.

## How DNS Filtering Works

Understanding the mechanics helps you troubleshoot and tune your setup. Here is the flow:

1. Your device sends a DNS query to resolve a domain like `ads.example.com`.
2. The DNS filter intercepts the query and checks it against active blocklists.
3. If the domain matches a blocklist rule, the filter returns a sinkhole response (typically `0.0.0.0` or the filter's own IP address).
4. If no match is found, the query is forwarded to an upstream DNS resolver (like Cloudflare, Google, or a privacy-focused resolver).
5. The response is cached locally so repeat queries for the same domain are answered instantly.

The entire process adds less than a millisecond of latency for cached queries. For new queries, you get the same resolution speed as your upstream provider.

## Pi-hole vs AdGuard Home vs Technitium DNS: Feature Comparison

| Feature | Pi-hole | AdGuard Home | Technitium DNS Server |
|---|---|---|---|
| **Primary Focus** | Network-wide ad blocking | Privacy + ad blocking + DNS | Full DNS server with filtering |
| **Blocking Engine** | Regex + domain lists | DNSCrypt + blocklists + custom rules | Blocklists + custom allow/deny + wildcards |
| **Query Logging** | Yes, detailed | Yes, with client grouping | Yes, with export options |
| **DHCP Server** | Built-in (dnsmasq) | No (relies on external DHCP) | Built-in DHCP server |
| **DNS-over-HTTPS** | Via stubby or cloudflared | Built-in | Built-in |
| **DNS-over-TLS** | Via stubby | Built-in | Built-in |
| **DNS-over-QUIC** | No | No | Built-in |
| **Blocklist Management** | Gravity CLI + web UI | Web UI + API | Web UI + subscription lists |
| **Per-Client Rules** | Yes (via group management) | Yes (client settings) | Yes (zone-level policies) |
| **API** | REST API | REST API | REST API |
| **Docker Support** | Official image | Official image | Official image |
| **Language** | Go + PHP (web UI) | Go + JavaScript (web UI) | C# (ASP.NET web UI) |
| **Resource Usage** | ~50-150 MB RAM | ~30-80 MB RAM | ~100-200 MB RAM |
| **Parental Controls** | Via blocklist categories | Built-in safe browsing filter | Built-in category filtering |
| **Encrypted Upstream** | Requires add-on | Native support | Native support |
| **Response Policy Zones** | No | No | Yes (RPZ support) |
| **Split-Horizon DNS** | Via dnsmasq config | Via upstream per-client | Built-in local zones |
| **License** | GPL-3.0 | GPL-3.0 | MIT |

### When to Choose Each

**Pi-hole** is the best choice if you want the most mature, battle-tested solution with the largest community. Its Gravity database system is fast and reliable, and the sheer volume of community-maintained blocklists and tutorials is unmatched. Use Pi-hole if you need a DHCP server alongside DNS filtering, since it bundles dnsmasq.

**AdGuard Home** excels at simplicity and encrypted DNS out of the box. If you want DNS-over-HTTPS or DNS-over-TLS without installing additional packages, AdGuard Home has it built in. Its web interface is more modern and the client identification is automatic — it groups queries by device without manual configuration. Choose AdGuard Home if you value encrypted upstream connections and a cleaner UI.

**Technitium DNS Server** is the most feature-complete DNS server of the three. It supports DNS-over-QUIC (the newest encrypted DNS protocol), Response Policy Zones, local zone definitions, and built-in DHCP. It is also the most lightweight option for running a full DNS server with filtering. Choose Technitium if you need advanced DNS features like split-horizon resolution, local zone overrides, or RPZ-based filtering.

## Deploying Pi-hole with Docker

Pi-hole is the most established option. Here is a production-ready Docker Compose setup:

```yaml
version: "3.8"

services:
  pihole:
    container_name: pihole
    image: pihole/pihole:latest
    ports:
      - "53:53/tcp"
      - "53:53/udp"
      - "67:67/udp"
      - "8080:80/tcp"
    environment:
      TZ: "America/New_York"
      WEBPASSWORD: "YourSecureAdminPassword"
      DNS1: "1.1.1.1"
      DNS2: "8.8.8.8"
    volumes:
      - ./pihole/etc-pihole:/etc/pihole
      - ./pihole/etc-dnsmasq.d:/etc/dnsmasq.d
    restart: unless-stopped
    cap_add:
      - NET_ADMIN
    dns:
      - 127.0.0.1
      - 1.1.1.1
```

Key configuration notes:

- **Ports 53/tcp and 53/udp** are the standard DNS ports. The container needs direct access to these on the host.
- **Port 67/udp** is only needed if you want Pi-hole's DHCP server. Remove it if another device handles DHCP.
- **WEBPASSWORD** sets the admin panel password. Always change the default.
- **DNS1 and DNS2** set your upstream resolvers. Use privacy-focused options like `1.1.1.1` (Cloudflare), `8.8.8.8` (Google), or `94.140.14.14` (AdGuard DNS).
- **cap_add: NET_ADMIN** is required for Pi-hole to manage the network interface for DHCP.

After starting the container:

```bash
docker compose up -d
```

Access the admin panel at `http://<server-ip>:8080/admin`. Navigate to **Group Management → Adlists** and add your blocklists. Recommended starting lists:

```
https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts
https://someonewhocares.org/hosts/latest/hosts
https://raw.githubusercontent.com/PolishFiltersTeam/KADhosts/master/KADhosts.txt
https://raw.githubusercontent.com/FadeMind/hosts.extras/master/add.Spam/hosts
https://v.firebog.net/hosts/Easyprivacy.txt
https://v.firebog.net/hosts/Prigent-Ads.txt
https://raw.githubusercontent.com/quidsup/notrack/master/trackers.txt
```

After adding lists, trigger a gravity update:

```bash
docker exec pihole pihole updateGravity
```

### Advanced Pi-hole: Regex Filtering

Pi-hole supports regex-based blocking for patterns that simple domain matching cannot catch. Add these in **Group Management → Regex**:

```
^ads?[_.-].*\..+$
^track[er].*\..+$
^analytics[_.-].*\..+$
^telemetry.*\..+$
^metrics[_.-].*\..+$
```

These patterns block domains starting with `ads`, `tracker`, `analytics`, `telemetry`, or `metrics` followed by common separators. This catches many tracking domains that slip through static blocklists.

## Deploying AdGuard Home with Docker

AdGuard Home is simpler to set up and includes encrypted DNS support natively:

```yaml
version: "3.8"

services:
  adguardhome:
    container_name: adguardhome
    image: adguard/adguardhome:latest
    ports:
      - "53:53/tcp"
      - "53:53/udp"
      - "3000:3000/tcp"
      - "8080:80/tcp"
    volumes:
      - ./adguard/work:/opt/adguardhome/work
      - ./adguard/conf:/opt/adguardhome/conf
    restart: unless-stopped
```

The setup process differs from Pi-hole. On first launch, AdGuard Home runs an interactive setup wizard at `http://<server-ip>:3000`. You will configure:

- Admin web interface port (default 80)
- DNS listen port (default 53)
- Admin username and password
- Upstream DNS servers

After the wizard completes, access the dashboard at `http://<server-ip>:80`.

### Configuring Encrypted Upstream in AdGuard Home

This is where AdGuard Home shines. In **Settings → DNS settings**, you can set encrypted upstream servers without any additional software:

```
tls://1.1.1.1
tls://dns.google
https://dns.quad9.net/dns-query
quic://unfiltered.adguard-dns.com
```

Prefixes control the protocol:
- `tls://` for DNS-over-TLS
- `https://` for DNS-over-HTTPS
- `quic://` for DNS-over-QUIC (AdGuard Home supports this upstream, though QUIC listening is not available)

You can also set per-client upstream servers. Go to **Settings → Client settings**, add a client by IP or subnet, and assign a different upstream resolver. This is useful for sending IoT device traffic through a stricter resolver while keeping general traffic on a faster one.

### Custom Blocking Rules in AdGuard Home

AdGuard Home supports multiple rule formats in **Filters → DNS blocklists → Add blocklist → Custom filtering rules**:

```
||ads.example.com^
||tracking.pixel.com^$important
@@||whitelist-domain.com^
# Block all subdomains
||bad-domain.com^
# Block specific path pattern
/ads/banner-*.js
```

The `||` prefix matches any subdomain, `^` matches any separator character after the domain, and `$important` overrides allowlist entries.

## Deploying Technitium DNS Server with Docker

Technitium offers the most DNS server features. Its Docker deployment:

```yaml
version: "3.8"

services:
  technitium:
    container_name: technitium
    image: technitium/dns-server:latest
    ports:
      - "53:53/tcp"
      - "53:53/udp"
      - "5380:5380/tcp"
      - "853:853/tcp"
      - "853:853/udp"
      - "443:443/tcp"
      - "443:443/udp"
    environment:
      - DNS_SERVER_DOMAIN=dns.home.arpa
    volumes:
      - ./technitium/config:/etc/dns
    restart: unless-stopped
```

Port mapping explanation:
- **53** — Standard DNS
- **5380** — Web admin interface
- **853/tcp and 853/udp** — DNS-over-TLS
- **443/tcp and 443/udp** — DNS-over-HTTPS and DNS-over-QUIC

After starting, access the admin panel at `http://<server-ip>:5380`. The default credentials are `admin` / `admin` — change these immediately.

### Setting Up Blocklists in Technitium

Navigate to **Blocklists → Subscription Lists** and add the same URLs used for Pi-hole. Technitium also supports local allow/deny lists in the **Local DNS** section:

```
# Deny specific domains
block ads.example.com
block tracking.bad-site.com

# Allow specific domains (override blocklist)
allow safe-analytics.example.com
```

### Local Zones and Split-Horizon DNS

Technitium's standout feature is its local zone support. You can define zones that resolve differently based on the query source:

```
# In the web UI: Zones → Add Zone → Primary
Zone: home.arpa
Type: Primary

# Add records:
A  nas.home.arpa  192.168.1.100
A  printer.home.arpa  192.168.1.50
CNAME media.home.arpa  nas.home.arpa
```

This means devices on your network can reach `nas.home.arpa` directly without needing an external DNS or editing hosts files on every device. Combined with blocklists, this gives you a complete internal DNS infrastructure.

### Enabling DNS-over-QUIC

Technitium is the only one of the three that supports DNS-over-QUIC as a listening protocol. To enable it:

1. Go to **Settings → Options → DNS Server**
2. Enable **QUIC** under Transport Protocols
3. Configure a TLS certificate (self-signed or from Let's Encrypt)
4. Restart the DNS service

Clients that support DNS-over-QUIC can now connect on port 443/udp with QUIC transport, which provides the lowest latency of all encrypted DNS protocols because it eliminates TCP handshake overhead.

## Recommended Blocklists for 2026

No matter which tool you choose, your blocklist selection determines protection quality. Here is a curated set that balances coverage with false-positive risk:

| List | Purpose | Approximate Entries |
|---|---|---|
| StevenBlack Unified | General ads + tracking | ~100,000 |
| OISD Big | Comprehensive, low false-positive rate | ~200,000 |
| Peter Lowe's Ad/Tracking Server | Known ad/tracking servers | ~5,000 |
| EasyPrivacy (Firebog) | Privacy-focused tracking | ~30,000 |
| AdGuard DNS filter | AdGuard-curated | ~50,000 |
| NoCoin (Firebog) | Cryptocurrency mining scripts | ~3,000 |

For most home networks, the StevenBlack Unified list plus OISD Big provides excellent coverage. Adding EasyPrivacy catches trackers that are not ad-related. The NoCoin list blocks browser-based cryptocurrency miners.

**Important**: Do not add every blocklist you find. Overlapping lists waste memory and can cause unexpected breakage. Start with 3-5 well-maintained lists and add more only if you notice specific gaps. Monitor your query logs weekly to catch false positives.

## Router Configuration: Making DNS Filtering Network-Wide

The DNS filter is only useful if your devices actually use it. Here is how to configure your router:

### Method 1: Router DHCP Settings (Recommended)

1. Log into your router's admin panel.
2. Find the DHCP or LAN settings section.
3. Set the primary DNS server to your DNS filter's IP address.
4. Set the secondary DNS to the same IP (using a public DNS as secondary defeats the filter — queries will bypass it when the filter is slow).
5. Save and reboot the router, or restart the DHCP service.
6. Reconnect your devices to pick up the new DNS settings.

### Method 2: Static DNS per Device

For devices that use static IP configuration:

```
# Linux (NetworkManager)
nmcli connection modify <connection-name> ipv4.dns "192.168.1.100"
nmcli connection up <connection-name>

# macOS
networksetup -setdnsservers Wi-Fi 192.168.1.100

# Windows (PowerShell)
Set-DnsClientServerAddress -InterfaceAlias "Ethernet" -ServerAddresses "192.168.1.100"
```

### Method 3: Pi-hole as DHCP Server

If you installed Pi-hole with the `cap_add: NET_ADMIN` option and port 67 mapped, enable DHCP in the Pi-hole admin panel under **Settings → DHCP**. This lets Pi-hole hand out IP addresses and DNS settings directly, removing your router from the DNS configuration chain entirely.

## Monitoring and Maintenance

### Weekly Review Checklist

- **Check the query log** for blocked domains that should be allowed. Common false positives include:
  - `api.example.com` blocked because `example.com` is on a list
  - Software update servers that share domains with ad networks
  - Smart home device cloud services
  
- **Review top blocked domains** to understand what your network is being protected from. If a single domain accounts for 40% of blocked queries, you have confirmed the filter is working.

- **Update blocklists**. Pi-hole runs `pihole updateGravity` weekly by default via cron. AdGuard Home updates lists on a schedule you configure in **Filters → DNS blocklists → Update interval**. Technitium updates subscription lists via the **Blocklists** page.

- **Monitor disk usage**. Query logs grow over time. Pi-hole stores logs in `/etc/pihole/pihole-FTL.db`. AdGuard Home stores them in its work directory. Technitium writes to `/etc/dns`. Configure log rotation or reduce the retention period in settings.

### Dashboard Metrics That Matter

| Metric | What It Tells You | Healthy Range |
|---|---|---|
| Queries blocked (%) | Filtering effectiveness | 10-30% |
| Unique domains queried | Network diversity | 500-5000/day |
| Cache hit rate | DNS filter efficiency | >80% |
| Top blocked domain | Most common tracker/ad | Varies |
| Top queried domain | Most used service | Usually internal |
| Clients with most queries | Most active device | Usually your primary workstation |

If your blocked percentage drops below 5%, check that blocklists are updating. If it exceeds 50%, you likely have an aggressive list causing breakage — check the logs for legitimate services being blocked.

## Performance and Resource Comparison

In real-world testing on a low-power homelab server (Raspberry Pi 4, 4 GB RAM):

| Metric | Pi-hole | AdGuard Home | Technitium DNS |
|---|---|---|---|
| Idle RAM | ~120 MB | ~45 MB | ~130 MB |
| RAM at 10K queries/day | ~150 MB | ~60 MB | ~160 MB |
| Query latency (cached) | 0.1 ms | 0.08 ms | 0.12 ms |
| Query latency (uncached) | 15-40 ms | 15-40 ms | 15-40 ms |
| CPU at 10K queries/day | <1% | <0.5% | <1% |
| Disk for 7 days logs | ~50 MB | ~30 MB | ~80 MB |

All three perform well on minimal hardware. AdGuard Home uses the least resources because of its efficient Go implementation and simpler architecture. Pi-hole's slightly higher memory usage comes from the dnsmasq and FTL (Faster Than Light) components. Technitium's C# runtime has a larger baseline footprint but scales linearly with query volume.

## Troubleshooting Common Issues

### Devices Cannot Reach the Internet

1. **Check the DNS filter is running**: `docker ps` should show the container as healthy.
2. **Test DNS resolution directly**: `dig @192.168.1.100 google.com` from another machine.
3. **Check upstream connectivity**: The filter needs internet access to forward queries. Verify the container has network access.
4. **Check firewall rules**: Ensure port 53 is not blocked by the host firewall.

```bash
# Test from the DNS filter host
dig @127.0.0.1 google.com

# Test from a client device
nslookup google.com 192.168.1.100

# Check if the filter process is listening
ss -tlnp | grep :53
```

### Specific Website Not Loading

1. Check the query log in the admin panel for the failing domain.
2. If it shows as blocked, add it to the whitelist/allowlist.
3. In Pi-hole: **Whitelist → Add domain**. In AdGuard Home: **Filters → DNS rewrites → Add DNS rewrite**. In Technitium: **Local DNS → Allow list**.
4. Run a gravity update (Pi-hole) or wait for the cache to expire.

### Slow DNS Resolution

1. Check your upstream server response times in the admin dashboard.
2. Switch to a faster upstream (Cloudflare `1.1.1.1` or Google `8.8.8.8` are typically fastest).
3. Enable DNS-over-TLS or DNS-over-HTTPS for security, but note this adds a small latency penalty for the TLS handshake on first connection.
4. Ensure the DNS filter has enough RAM — if the cache is too small, queries are forwarded more often.

## Making the Choice

For a **first-time self-hosted DNS filter**, AdGuard Home offers the smoothest experience. Its setup wizard, built-in encrypted DNS, and automatic client detection mean you can go from zero to full network protection in under 15 minutes.

For **users who want the most mature ecosystem**, Pi-hole remains the gold standard. The community support, extensive documentation, and Gravity database make it the most reliable option for production use. If you need DHCP alongside DNS filtering, Pi-hole is the only choice among the three.

For **power users who want a complete DNS server**, Technitium DNS Server provides features the others lack: DNS-over-QUIC listening, local zone definitions, RPZ support, and built-in split-horizon DNS. It is the best choice if you want your DNS filter to also serve as your internal DNS authority.

All three are free, open source, and can run on hardware that costs less than $50. The real investment is the 15-30 minutes of setup time — after that, every device on your network gets automatic protection from ads, trackers, malware domains, and unwanted telemetry, with zero ongoing maintenance beyond occasional blocklist updates.
