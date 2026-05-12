---
title: "Self-Hosted DHCP Option Management — Kea Hook vs ISC DHCP vs Dnsmasq Custom Options"
date: "2026-05-13"
tags: ["dhcp", "network-automation", "infrastructure", "network-management"]
draft: false
---

DHCP options are the mechanism by which DHCP servers distribute configuration parameters to clients beyond just IP addresses -- things like DNS servers, NTP servers, domain names, SIP servers, and custom vendor-specific settings. Managing DHCP options across a large network infrastructure requires careful planning, validation, and monitoring. Self-hosted DHCP option management tools help administrators configure, test, and audit DHCP option distribution at scale.

## Understanding DHCP Options

The DHCP protocol (RFC 2132) defines over 150 standardized option codes, plus room for vendor-specific options (codes 128-254). Common options include:

- **Option 3** -- Router (default gateway)
- **Option 6** -- Domain Name Server
- **Option 15** -- Domain Name
- **Option 42** -- NTP Server
- **Option 66/67** -- Boot Server Name and Bootfile Name (PXE boot)
- **Option 121** -- Classless Static Routes
- **Option 150** -- TFTP Server (VoIP phones)
- **Option 252** -- Proxy Auto-Config (WPAD)

Managing these options across hundreds of subnets and thousands of clients requires robust tooling -- especially when options need to be updated, audited, or rolled back.

## ISC DHCP Server with Custom Options

ISC DHCP is the traditional DHCP server implementation that has been the default choice for Linux networks for decades. While ISC has officially moved development to Kea, ISC DHCP remains widely deployed and supports extensive option configuration through its declarative configuration file.

**Key features:**
- Mature, well-documented option syntax
- Support for all standard DHCP options plus vendor-encapsulated options
- Subnet-level and host-level option overrides
- Class-based option assignment
- Include file support for modular configuration

**Configuration example:**
```
# /etc/dhcp/dhcpd.conf
option domain-name "example.com";
option domain-name-servers 8.8.8.8, 8.8.4.4;
option ntp-servers 10.0.1.10;

# Custom vendor-specific option
option space myvendor;
option myvendor.config-code code 224 = string;
option myvendor.firmware-server code 225 = string;

subnet 10.0.1.0 netmask 255.255.255.0 {
    range 10.0.1.100 10.0.1.200;
    option routers 10.0.1.1;
    option domain-name-servers 10.0.1.10, 10.0.1.11;
    option ntp-servers 10.0.1.10;
    option myvendor.config-code "production";
    option myvendor.firmware-server "10.0.1.50";
}

# PXE boot options for specific clients
class "pxe-clients" {
    match if substring(option vendor-class-identifier, 0, 9) = "PXEClient";
    next-server 10.0.1.50;
    filename "pxelinux.0";
}
```

**Docker Compose deployment:**
```yaml
version: "3.8"
services:
  isc-dhcp:
    image: networkboot/dhcpd:latest
    container_name: isc-dhcp
    network_mode: host
    privileged: true
    volumes:
      - ./dhcpd.conf:/etc/dhcp/dhcpd.conf
      - ./dhcpd.leases:/var/lib/dhcp/dhcpd.leases
    environment:
      - DHCPD_CONF=/etc/dhcp/dhcpd.conf
    restart: unless-stopped
```

ISC DHCP is best for environments that need a proven, stable DHCP server with extensive option support and straightforward text-based configuration.

## Kea DHCP with Hook Modules

Kea DHCP is the next-generation DHCP server from ISC, designed from the ground up with modularity, performance, and extensibility in mind. Kea hook module architecture allows administrators to extend DHCP option handling with custom logic.

**Key features:**
- Modular hook architecture for custom option processing
- REST API for dynamic option management
- MySQL/PostgreSQL backend for centralized option storage
- Per-host and per-subnet option assignment via database
- Real-time statistics and monitoring
- High availability with database replication

**Docker Compose deployment:**
```yaml
version: "3.8"
services:
  kea-dhcp4:
    image: ghcr.io/isc-projects/kea:latest
    container_name: kea-dhcp4
    network_mode: host
    volumes:
      - ./kea-dhcp4.conf:/etc/kea/kea-dhcp4.conf
      - ./hooks:/usr/local/lib/kea/hooks
    restart: unless-stopped

  kea-dhcp-db:
    image: postgres:15
    container_name: kea-dhcp-db
    environment:
      - POSTGRES_DB=kea
      - POSTGRES_USER=kea
      - POSTGRES_PASSWORD=keapassword
    volumes:
      - pgdata:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  pgdata:
```

**Kea configuration with custom options:**
```json
{
    "Dhcp4": {
        "interfaces-config": {
            "interfaces": ["eth0"]
        },
        "option-data": [
            {
                "name": "domain-name-servers",
                "data": "10.0.1.10, 10.0.1.11"
            },
            {
                "name": "ntp-servers",
                "data": "10.0.1.10"
            }
        ],
        "option-def": [
            {
                "name": "vendor-specific-info",
                "code": 43,
                "type": "string",
                "space": "vendor-encapsulated-options-space"
            }
        ],
        "subnet4": [
            {
                "subnet": "10.0.1.0/24",
                "pools": [{"pool": "10.0.1.100 - 10.0.1.200"}],
                "option-data": [
                    {"name": "routers", "data": "10.0.1.1"},
                    {"name": "domain-name-servers", "data": "10.0.1.10"}
                ]
            }
        ],
        "hooks-libraries": [
            {
                "library": "/usr/local/lib/kea/hooks/libdhcp_lease_cmds.so"
            }
        ]
    }
}
```

Kea is the recommended choice for new deployments, especially in environments that need database-backed configuration, REST API management, or custom option processing through hooks.

## Dnsmasq for Lightweight Option Management

Dnsmasq is a lightweight DNS forwarder and DHCP server that excels in smaller deployments, lab environments, and edge networks. While simpler than Kea or ISC DHCP, it supports extensive DHCP option configuration through its straightforward configuration syntax.

**Key features:**
- Combined DNS and DHCP server in a single process
- Very lightweight resource footprint
- Simple, well-documented option syntax
- PXE/TFTP boot server support built in
- Tag-based option assignment for complex scenarios
- No external database dependencies

**Configuration example:**
```
# /etc/dnsmasq.conf
# Basic DHCP options
dhcp-option=option:router,10.0.1.1
dhcp-option=option:dns-server,10.0.1.10,10.0.1.11
dhcp-option=option:ntp-server,10.0.1.10
dhcp-option=option:domain-name,example.com

# Vendor-specific options for VoIP phones
dhcp-option=vendor:PXEClient,66,10.0.1.50
dhcp-option=vendor:PXEClient,67,pxelinux.0

# Tag-based options for specific device types
dhcp-option=tag:voip,option:tftp-server,10.0.1.50
dhcp-option=tag:voip,option:bootfile-name,phone.cfg

# Classless static routes
dhcp-option=option:classless-static-route,10.0.2.0/24,10.0.1.254,0.0.0.0/0,10.0.1.1

# Host-specific options
dhcp-host=aa:bb:cc:dd:ee:ff,10.0.1.50,server01,option:ntp-server,10.0.1.20
```

**Docker Compose deployment:**
```yaml
version: "3.8"
services:
  dnsmasq:
    image: jpillora/dnsmasq:latest
    container_name: dnsmasq
    network_mode: host
    cap_add:
      - NET_ADMIN
    volumes:
      - ./dnsmasq.conf:/etc/dnsmasq.conf
      - ./hosts:/etc/hosts
    restart: unless-stopped
```

Dnsmasq is ideal for smaller networks, home labs, and edge deployments where a lightweight combined DNS/DHCP server with straightforward option configuration is preferred over a full-featured DHCP platform.

## Comparison Table

| Feature | ISC DHCP | Kea DHCP | Dnsmasq |
|---------|----------|----------|---------|
| Configuration Format | Text (declarative) | JSON | Text (key-value) |
| DHCP Options | Full RFC 2132 support | Full plus custom via hooks | Full standard options |
| Database Backend | No | MySQL/PostgreSQL | No |
| REST API | No | Yes (via hooks) | No |
| High Availability | Manual failover | Database replication | Manual failover |
| Combined DNS and DHCP | No | No | Yes |
| PXE and TFTP | Via external TFTP | Via external TFTP | Built-in |
| Vendor Options | Encapsulated options | Custom option definitions | Vendor-class matching |
| Resource Usage | Moderate | Higher (DB required) | Very low |
| Best For | Legacy deployments, stability | New deployments, automation | Small networks, edge |
| License | MPL 2.0 | MPL 2.0 | GPL v2 |

## Why Self-Host DHCP Option Management?

DHCP options directly control how network clients configure themselves -- from DNS resolution to boot image selection. Misconfigured options can cause widespread connectivity issues, security vulnerabilities, or service disruptions across your entire network. Self-hosting DHCP option management ensures that configuration changes are made within your controlled environment, validated before deployment, and auditable for compliance purposes.

For organizations managing VoIP phone networks, PXE boot infrastructure, or IoT device provisioning, DHCP options are the primary mechanism for distributing device configuration. Self-hosted tools give you full visibility into which options are being served to which clients, and allow you to test changes in isolated subnets before rolling them out network-wide.

Additionally, DHCP option configuration often contains sensitive infrastructure details -- internal server IPs, boot server paths, and network topology information. Keeping this configuration within your network boundary prevents exposure of internal infrastructure details to external DHCP management services.

For broader DHCP management, see our [Kea dashboard guide](../2026-05-10-self-hosted-dhcp-monitoring-kea-dashboard-exporter-guide/). For DHCP high availability, check our [Kea HA vs Failover comparison](../2026-05-09-self-hosted-dhcp-high-availability-kea-ha-vs-isc-failover-guide/). For network device inventory, our [Nautobot vs NetBox comparison](../2026-04-28-racktables-vs-nautobot-vs-opendcim-self-hosted-inventory-management/) covers infrastructure documentation.

## FAQ

### What are DHCP vendor-specific options and when should I use them?

Vendor-specific options (option code 43) allow DHCP servers to send configuration parameters specific to a particular device type or manufacturer. They are commonly used for VoIP phones (to configure SIP servers), network switches (for auto-provisioning), and IoT devices (for firmware update servers). You define the option format in your DHCP server configuration, and devices that recognize the vendor class will interpret the data accordingly.

### How do I test DHCP option changes before deploying to production?

The safest approach is to use a dedicated test subnet with a small range of IP addresses. Configure your DHCP server to serve different options to this subnet, then connect a test client and verify the received options using tools like dhclient with the verbose flag or tcpdump on ports 67 and 68. Kea REST API also allows you to query what options would be served to a specific client before making changes live.

### Can DHCP options be used for network security?

DHCP options themselves are not encrypted or authenticated, so they should not be used to distribute sensitive information like passwords or encryption keys. However, they can support security infrastructure by distributing the addresses of authentication servers, certificate authorities, or secure boot servers. Options like 802.1X credentials should be distributed through more secure channels like RADIUS or certificate enrollment protocols.

### What is the maximum number of DHCP options I can configure?

The DHCP protocol supports option codes 1 through 254, with codes 128 through 254 reserved for vendor-specific use. The total size of all options in a single DHCP response is limited by the maximum DHCP message size (typically 576 bytes for the initial request, expandable via client requests). In practice, most deployments use fewer than 20 distinct options per subnet.

### How do I migrate DHCP options from ISC DHCP to Kea?

Kea provides a migration tool (kea-admin lease-upgrade) for converting ISC DHCP configuration to the JSON format. However, manual review is recommended since the configuration paradigms differ -- ISC uses a declarative text format while Kea uses structured JSON. Pay special attention to vendor-specific option definitions, which need to be redefined using the option-def syntax.

### Can I use DHCP options to deploy custom scripts to clients?

DHCP options can distribute URLs or server addresses that clients use to fetch configuration scripts (for example, option 66 and 67 for PXE boot), but the options themselves should not contain script content. The recommended approach is to use DHCP to point clients to a configuration server, then use secure protocols like HTTPS or SCP to transfer the actual scripts.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted DHCP Option Management -- Kea Hook vs ISC DHCP vs Dnsmasq Custom Options",
  "description": "Compare self-hosted DHCP option management approaches using ISC DHCP, Kea hooks, and Dnsmasq. Includes configuration examples and Docker deployment guides.",
  "datePublished": "2026-05-13",
  "dateModified": "2026-05-13",
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
