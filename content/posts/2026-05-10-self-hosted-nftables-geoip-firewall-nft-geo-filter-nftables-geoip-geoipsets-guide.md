---
title: "Self-Hosted nftables GeoIP Firewall: nft-geo-filter vs nftables-geoip vs geoipsets"
date: "2026-05-10"
tags: ["nftables", "firewall", "geoip", "network-security", "self-hosted", "linux"]
draft: false
---

Geographic IP filtering is a fundamental network security practice: blocking or allowing traffic based on the country of origin of the source IP address. For self-hosted infrastructure, this means automatically maintaining nftables rulesets that block entire countries, protect services from specific regions, or whitelist traffic from trusted locations only.

In this guide, we compare three open-source tools for building and managing GeoIP-based nftables firewall rules: **nft-geo-filter**, **nftables-geoip**, and **geoipsets**. Each takes a different approach to the same problem — translating country codes into nftables sets of IP network ranges.

## Why GeoIP Firewall Filtering?

Geographic IP filtering serves several practical security and operational purposes:

**Attack Surface Reduction:** The majority of automated attacks — brute-force SSH attempts, port scans, web application exploits — originate from a small set of countries. By blocking traffic from regions where you have no legitimate users, you dramatically reduce the volume of malicious connections your infrastructure must handle.

**Compliance Requirements:** Some regulations require that certain services only be accessible from specific jurisdictions. Financial services, healthcare systems, and government applications often need geographic access controls to comply with data residency requirements.

**Bandwidth Conservation:** For services with limited bandwidth, blocking high-volume regions that do not contribute meaningful traffic can reduce costs. This is especially relevant for content delivery, API services, and torrent trackers.

**DDoS Mitigation Layer:** While GeoIP filtering is not a complete DDoS defense, it provides an effective first layer of filtering that reduces the attack surface before more sophisticated mitigation systems engage.

For related reading on firewall management, see our [comprehensive firewall management guide](../2026-05-08-self-hosted-firewall-management-firehol-shorewall-ferm-guide/) and [UFW vs firewalld vs iptables comparison](../self-hosted-firewall-ufw-firewalld-iptables/). If you need geographic data for other purposes, check our [GeoIP databases guide](../2026-04-23-self-hosted-geoip-databases-maxmind-ip2location-dbip-guide/).

## Understanding nftables Sets

Before comparing tools, it helps to understand how nftables handles IP address sets. Unlike iptables, which processes rules sequentially, nftables uses **sets** — hash-based data structures that enable O(1) lookup of IP addresses. This makes nftables ideal for GeoIP filtering, where you may need to match against thousands of IP ranges.

```bash
# Create a named set for blocked countries
nft add set inet filter geoip_block { type ipv4_addr \; flags interval \; }

# Add IP ranges to the set (example: CN and RU ranges)
nft add element inet filter geoip_block { 1.0.1.0/24, 1.0.2.0/23, ... }

# Use the set in a rule
nft add rule inet filter input ip saddr @geoip_block drop
```

The challenge is keeping these sets updated — country IP allocations change constantly. The tools we compare automate this process.

## nft-geo-filter — Simple Shell-Based GeoIP Blocking

[nft-geo-filter](https://github.com/rpthms/nft-geo-filter) is a straightforward shell script that generates nftables rules to allow or deny traffic based on country-specific IP blocks. It downloads GeoIP data, converts it to nftables set format, and applies the rules directly.

### Key Features

- **Shell script simplicity:** No dependencies beyond standard Linux utilities (wget, nft)
- **Country allow/deny lists:** Specify countries to block (deny list) or allow (allow list)
- **Automatic updates:** Script can be run via cron to refresh IP ranges
- **IPv4 and IPv6 support:** Handles both address families
- **116 GitHub stars** — popular among homelab and small infrastructure operators
- **Lightweight:** Runs in seconds, minimal resource usage

### Deployment and Usage

Install and run nft-geo-filter:

```bash
# Install nft-geo-filter
git clone https://github.com/rpthms/nft-geo-filter.git
cd nft-geo-filter
chmod +x nft-geo-filter.sh

# Block traffic from specific countries
./nft-geo-filter.sh -c "CN,RU,KP,IR" -a deny

# Allow traffic only from specific countries (default deny all others)
./nft-geo-filter.sh -c "US,GB,DE,FR,JP" -a allow
```

Set up automatic updates via cron:

```bash
# /etc/cron.daily/nft-geo-filter
#!/bin/bash
/root/nft-geo-filter/nft-geo-filter.sh -c "CN,RU,KP" -a deny -r
```

The script fetches IP allocation data from public sources, converts it to nftables set syntax, and reloads the ruleset. The `-r` flag regenerates the rules from scratch.

## nftables-geoip — Python-Based GeoIP Map Generator

[nftables-geoip](https://github.com/pvxe/nftables-geoip) is a Python script that generates nftables maps (associative arrays) of IP address blocks with corresponding geolocation data. It uses the db-ip.com database, avoiding MaxMind's licensing requirements.

### Key Features

- **nftables maps (not just sets):** Associates IP ranges with country codes for more flexible filtering
- **db-ip.com data source:** No MaxMind EULA or registration required
- **Flexible output:** Generate nftables ruleset files that can be included in existing configurations
- **Country code lookup:** Query the generated map to find the country of any IP address
- **166 GitHub stars** — well-maintained with recent updates
- **No kernel dependencies:** Pure userland Python script

### Deployment and Usage

```bash
# Install dependencies
pip3 install requests

# Clone and run
git clone https://github.com/pvxe/nftables-geoip.git
cd nftables-geoip
python3 nftables-geoip.py --countries CN,RU --action drop

# Generate nftables ruleset file
python3 nftables-geoip.py \
    --countries "CN,RU,KP,IR" \
    --action drop \
    --output /etc/nftables.d/geoip-block.conf

# Include in your main nftables configuration
# /etc/nftables.conf:
# include "/etc/nftables.d/geoip-block.conf"
```

The generated ruleset creates named sets with country-specific IP ranges:

```nft
#!/usr/sbin/nft -f

table inet geoip {
    set country_cn {
        type ipv4_addr
        flags interval
        elements = {
            1.0.1.0/24,
            1.0.2.0/23,
            1.0.8.0/24,
            # ... thousands of CN ranges
        }
    }
}

# Rule to drop traffic from blocked countries
table inet filter {
    chain input {
        type filter hook input priority 0 \; policy accept \;
        ip saddr @geoip.country_cn drop
    }
}
```

## geoipsets — Country-Specific IP Sets for Multiple Firewalls

[geoipsets](https://github.com/chr0mag/geoipsets) is a Python package that generates country-specific IP network ranges consumable by **both iptables/ipset and nftables**. Unlike the other two tools, geoipsets is designed to be firewall-agnostic, producing output that works with multiple firewall backends.

### Key Features

- **Multi-firewall support:** Generate sets for iptables/ipset, nftables, and plain CIDR lists
- **Multiple data sources:** Supports MaxMind GeoLite2 and db-ip.com databases
- **Package management:** Installable via pip, integrates with system package management
- **CIDR aggregation:** Combines adjacent IP ranges to minimize set size
- **119 GitHub stars** — actively maintained with regular database updates
- **Configurable output:** Customize table names, set names, and output format

### Deployment and Usage

```bash
# Install geoipsets
pip3 install geoipsets

# Generate nftables sets for blocked countries
geoipsets --family inet --output nftables --countries CN,RU,KP \
    --table filter --set-name geoip_block

# Generate ipset output (for iptables)
geoipsets --family inet --output ipset --countries CN,RU \
    --set-name geoip_block

# Generate raw CIDR list for custom processing
geoipsets --family inet --output cidr --countries CN \
    --output-file /tmp/cn-ranges.txt
```

Cron job for automated updates:

```bash
# /etc/cron.weekly/geoipsets-update
#!/bin/bash
geoipsets --family inet --output nftables \
    --countries "CN,RU,KP,IR" \
    --table filter --set-name geoip_block \
    --output-file /etc/nftables.d/geoip.conf

# Reload nftables
nft -f /etc/nftables.d/geoip.conf
```

## Comparison Table

| Feature | nft-geo-filter | nftables-geoip | geoipsets |
|---|---|---|---|
| **Language** | Shell script | Python | Python (pip package) |
| **Data source** | Public GeoIP feeds | db-ip.com | MaxMind + db-ip.com |
| **nftables sets** | Yes | Yes | Yes |
| **nftables maps** | No | Yes | No |
| **iptables/ipset** | No | No | Yes |
| **IPv6 support** | Yes | Yes | Yes |
| **CIDR aggregation** | No | No | Yes |
| **Allow list mode** | Yes | Via output config | Via country selection |
| **Deny list mode** | Yes | Yes | Yes |
| **Cron integration** | Manual script | Manual script | pip package + cron |
| **Licensing** | Open (no registration) | Open (db-ip.com, no EULA) | MaxMind requires free registration |
| **GitHub stars** | 116 | 166 | 119 |
| **Best for** | Simple shell-based blocking | Flexible nftables maps | Multi-firewall deployments |

## Security Considerations

**GeoIP accuracy:** GeoIP databases are not 100% accurate. IP allocations change, and some IPs may be misattributed. Use GeoIP filtering as a supplementary security layer, not your only defense.

**Evasion techniques:** Attackers can use VPNs, proxies, and cloud infrastructure to appear from different countries. GeoIP filtering will not stop determined attackers using infrastructure in allowed countries.

**False positives:** Legitimate users from blocked countries will be unable to access your services. Consider implementing a whitelist mechanism for known-good IPs.

**Rule set size:** Country IP ranges can be large (China has 8,000+ IPv4 ranges). nftables handles this efficiently with set lookups, but very large sets may impact memory usage on constrained systems.

## Choosing the Right GeoIP Tool

- **Choose nft-geo-filter** if you want the simplest possible solution — a single shell script that blocks countries with minimal setup. Ideal for homelabs and small deployments.

- **Choose nftables-geoip** if you need nftables maps (not just sets) for more flexible rule matching, prefer db-ip.com data to avoid MaxMind licensing, and want generated ruleset files that integrate with existing nftables configurations.

- **Choose geoipsets** if you need multi-firewall support (both iptables and nftables), want CIDR aggregation to minimize rule set size, and prefer a pip-installable package that integrates with your system's package management.

## FAQ

### How accurate is GeoIP filtering?

GeoIP databases are typically 95-99% accurate at the country level. However, accuracy varies by country and changes over time as IP allocations shift. GeoIP filtering should be used as a supplementary security layer alongside proper authentication, rate limiting, and intrusion detection.

### Can GeoIP filtering replace a WAF or IDS?

No. GeoIP filtering is a coarse-grained network-level control. It blocks or allows entire countries but cannot inspect application-layer traffic, detect malicious payloads, or identify compromised systems in allowed countries. Use it as part of a defense-in-depth strategy.

### How often should GeoIP rules be updated?

IP allocations change daily. For most use cases, updating weekly is sufficient. High-security environments should update daily. All three tools support automated updates via cron jobs.

### What happens if the GeoIP data source is unavailable?

If the data source is down during an update, the tool should retain the previous ruleset. Always test your update process to ensure failed updates do not clear existing firewall rules. nft-geo-filter and nftables-geoip both write to temporary files before applying changes.

### Does GeoIP filtering impact network performance?

nftables set lookups are O(1) hash operations with negligible performance impact. Even with thousands of IP ranges in a set, the lookup overhead is measured in nanoseconds. The primary resource usage is memory for storing the sets, typically a few megabytes per country.

### Can I whitelist specific IPs within a blocked country?

Yes. nftables rule ordering allows you to add accept rules for specific IPs before the GeoIP drop rule. Place your whitelist rules at a higher priority in the chain:

```nft
table inet filter {
    chain input {
        ip saddr 1.2.3.4 accept  # Whitelisted IP
        ip saddr @geoip_block drop  # Block country ranges
    }
}
```

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted nftables GeoIP Firewall: nft-geo-filter vs nftables-geoip vs geoipsets",
  "description": "Compare nft-geo-filter, nftables-geoip, and geoipsets for self-hosted geographic IP filtering with nftables firewall rules.",
  "datePublished": "2026-05-10",
  "dateModified": "2026-05-10",
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
