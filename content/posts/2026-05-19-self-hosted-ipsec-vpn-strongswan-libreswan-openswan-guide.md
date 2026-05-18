---
title: "Self-Hosted IPsec VPN: strongSwan vs LibreSwan vs OpenSWAN (2026)"
date: "2026-05-19"
tags: ["vpn", "ipsec", "network-security", "site-to-site", "strongswan", "libreswan"]
draft: false
---

IPsec (Internet Protocol Security) remains the gold standard for site-to-site VPN connections between data centers, branch offices, and cloud environments. Unlike user-focused VPN protocols like WireGuard or OpenVPN, IPsec operates at the network layer, encrypting entire IP packets and providing transparent security for all traffic between networks.

The three major open-source IPsec implementations — **strongSwan**, **LibreSwan**, and **OpenSWAN** — share a common ancestry but have diverged significantly in features, platform support, and active development. This guide compares them across configuration complexity, protocol support, authentication methods, and production readiness.

## A Brief History of Open-Source IPsec

The original FreeS/WAN project (2000-2004) was the first open-source IPsec implementation for Linux. When FreeS/WAN development stopped, it forked into two projects:

- **OpenSWAN** continued the FreeS/WAN codebase but eventually saw reduced development activity
- **strongSwan** was created as a ground-up rewrite focusing on IKEv2, EAP authentication, and modern cryptographic algorithms

**LibreSwan** emerged in 2012 as a fork of OpenSWAN, aiming to modernize the codebase and add support for contemporary security requirements. Today, strongSwan and LibreSwan are the two actively maintained projects, while OpenSWAN is largely considered legacy.

## Feature Comparison

| Feature | strongSwan | LibreSwan | OpenSWAN |
|---------|-----------|-----------|----------|
| **IKEv1 support** | Yes | Yes | Yes |
| **IKEv2 support** | Yes (primary focus) | Yes | Yes |
| **MOBIKE (mobile IKE)** | Yes | Yes | No |
| **EAP authentication** | Extensive (EAP-TLS, EAP-MSCHAPv2, EAP-TTLS) | Limited | No |
| **X.509 certificate support** | Yes (extensive) | Yes | Yes |
| **Pre-shared keys** | Yes | Yes | Yes |
| **Virtual IP (VIP) assignment** | Yes (via pool or SQL) | Yes (via PLUTO) | Limited |
| **NAT traversal** | Yes | Yes | Yes |
| **IPv6 support** | Yes | Yes | Partial |
| **Android client support** | Yes (strongSwan app) | No | No |
| **Windows native support** | Yes (IKEv2) | Yes (IKEv2) | Limited |
| **macOS native support** | Yes (IKEv2) | Yes (IKEv2) | Limited |
| **Systemd integration** | Yes | Yes | Limited |
| **Docker container ready** | Yes | Yes | Yes (legacy) |
| **GitHub stars** | 2,869+ | 946+ | N/A (no active GH repo) |
| **Last updated** | 2026-05 | 2026-05 | 2017 (inactive) |

## Installing and Configuring strongSwan

strongSwan is available in all major Linux distributions and is the recommended IPsec implementation for most modern deployments:

```bash
# Debian/Ubuntu
apt-get install strongswan strongswan-pki

# RHEL/CentOS/Fedora
dnf install strongswan

# Arch Linux
pacman -S strongswan
```

The configuration file is `/etc/ipsec.conf`. Here is a site-to-site VPN example:

```conf
# /etc/ipsec.conf
config setup
    charondebug="ike 2, knl 2, cfg 2"
    uniqueids=no

conn site-to-site
    keyexchange=ikev2
    dpdaction=restart
    dpddelay=30s
    rekey=no
    left=%defaultroute
    leftsubnet=10.0.1.0/24
    leftid=@hq.example.com
    leftauth=pubkey
    leftcert=server-cert.pem
    right=203.0.113.50
    rightsubnet=10.0.2.0/24
    rightid=@branch.example.com
    rightauth=pubkey
    rightcert=peer-cert.pem
    auto=start
```

Authentication secrets and keys go in `/etc/ipsec.secrets`:

```conf
# /etc/ipsec.secrets
: RSA server-key.pem
: PSK "your-pre-shared-key"
```

Start and enable the service:

```bash
systemctl enable --now strongswan-starter
ipsec status          # Check connection status
ipsec up site-to-site # Manually initiate connection
```

## Installing and Configuring LibreSwan

LibreSwan packages are available for most distributions:

```bash
# Debian/Ubuntu (universe repository)
apt-get install libreswan

# RHEL/CentOS/Fedora
dnf install libreswan

# From source (latest version)
git clone https://github.com/libreswan/libreswan.git
cd libreswan
make programs
make install
```

Configuration uses the same `/etc/ipsec.conf` format as strongSwan (both descend from FreeS/WAN):

```conf
# /etc/ipsec.conf - LibreSwan
config setup
    protostack=netkey
    logfile=/var/log/pluto.log

conn office-to-datacenter
    ike=aes256-sha2_512-modp2048!
    esp=aes256-sha2_512!
    ikelifetime=24h
    salifetime=24h
    left=198.51.100.10
    leftsubnet=172.16.1.0/24
    leftid=@office.example.com
    right=198.51.100.20
    rightsubnet=172.16.2.0/24
    rightid=@dc.example.com
    authby=secret
    auto=start
```

Pre-shared key in `/etc/ipsec.secrets`:

```conf
198.51.100.10 198.51.100.20 : PSK "your-shared-secret"
```

Start the service:

```bash
systemctl enable --now ipsec
ipsec auto --up office-to-datacenter
ipsec trafficstatus
```

## Docker Deployment

Both strongSwan and LibreSwan can run in Docker containers, making them suitable for containerized infrastructure:

```yaml
# strongSwan in Docker Compose
version: '3.8'

services:
  ipsec:
    image: strongswan:latest
    cap_add:
      - NET_ADMIN
      - SYS_MODULE
    sysctls:
      - net.ipv4.ip_forward=1
    volumes:
      - ./ipsec.conf:/etc/ipsec.conf:ro
      - ./ipsec.secrets:/etc/ipsec.secrets:ro
      - ./certs:/etc/ipsec.d:ro
    environment:
      - CHARON_NORESTART=yes
    network_mode: host
```

The `NET_ADMIN` capability is required for creating IPsec security associations and the `ip_forward` sysctl enables packet routing between the VPN endpoints.

## strongSwan vs LibreSwan: Key Differences

**strongSwan** is the more feature-rich implementation, particularly for modern use cases. Its native IKEv2 support is more mature, and it includes extensive EAP (Extensible Authentication Protocol) modules that make it suitable for remote access VPN scenarios where clients authenticate via certificates, username/password, or smart cards. The strongSwan Android app provides a polished mobile client that connects natively to IKEv2 servers.

**LibreSwan** focuses on simplicity and compatibility with the traditional IPsec toolchain. It is the default IPsec implementation on RHEL/CentOS systems and is well-integrated with NetworkManager and firewalld. Its configuration is generally simpler for basic site-to-site tunnels, and it has strong support for traditional authentication methods (pre-shared keys, X.509 certificates). However, it lacks the extensive EAP modules and mobile client support that strongSwan offers.

**OpenSWAN** is no longer actively maintained. The project's last stable release was in 2017, and most Linux distributions have replaced it with either strongSwan or LibreSwan. We do not recommend deploying OpenSWAN for new installations.

## Why Self-Host Your IPsec VPN?

Site-to-site connectivity is a fundamental networking requirement for distributed organizations. When you self-host your IPsec infrastructure using open-source implementations, you maintain complete control over encryption algorithms, key rotation policies, and access control — all without depending on proprietary vendor appliances or cloud-hosted VPN services.

Data sovereignty is increasingly regulated. Many jurisdictions require that network traffic between facilities remain within national boundaries and under direct organizational control. Self-hosted IPsec VPNs satisfy these requirements because the encryption and routing happen entirely on infrastructure you own and operate, with no intermediary processing the tunneled traffic.

Performance is another critical factor. Hardware VPN appliances from vendors like Cisco, Fortinet, and Palo Alto Networks carry significant capital costs and licensing fees. Open-source IPsec implementations running on commodity hardware can achieve comparable throughput at a fraction of the cost, with the added benefit of community-driven security audits and rapid vulnerability patches.

For organizations migrating from proprietary VPN appliances, strongSwan and LibreSwan offer standards-compliant IKEv2 implementations that interoperate with existing hardware — enabling gradual migration without requiring simultaneous replacement of all endpoints.

For overlay network alternatives using different protocols, see our [ZeroTier vs Nebula vs Netmaker guide](../2026-04-17-self-hosted-overlay-networks-zerotier-nebula-netmaker-complete-guide-2026/). If you need user-facing remote access rather than site-to-site tunnels, our [OpenVPN management guide](../2026-04-25-ovpn-admin-vs-openvpn-ui-vs-openvpn-web-ui-self-hosted-vpn-management-guide-2026/) covers web-based administration options. For WireGuard management, our [WireGuard UI comparison](../2026-04-24-wg-easy-vs-wireguard-ui-vs-wg-gen-web-self-hosted-wireguard-management-guide-2026/) provides detailed options.

## FAQ

### What is the difference between IKEv1 and IKEv2?

IKE (Internet Key Exchange) is the protocol used to set up IPsec security associations. IKEv2, defined in RFC 7296, improves on IKEv1 with faster connection establishment, built-in NAT traversal, MOBIKE support (allowing clients to change IP addresses without re-establishing the tunnel), and more robust error handling. IKEv2 is recommended for all new deployments.

### Can strongSwan connect to Cisco ASA or Fortinet firewalls?

Yes. Both strongSwan and LibreSwan implement standards-compliant IKEv1 and IKEv2, making them interoperable with commercial VPN appliances from Cisco, Fortinet, Palo Alto Networks, and other vendors. The key is matching the encryption algorithms, authentication method, and Diffie-Hellman group configured on both sides.

### How do I generate certificates for IPsec authentication?

strongSwan includes the `pki` utility for certificate management:

```bash
# Generate a CA
pki --gen --type rsa --size 4096 --outform pem > ca-key.pem
pki --self --ca --in ca-key.pem --dn "CN=VPN CA" --outform pem > ca-cert.pem

# Generate a server certificate
pki --gen --type rsa --size 2048 --outform pem > server-key.pem
pki --pub --in server-key.pem | pki --issue --cacert ca-cert.pem     --cakey ca-key.pem --dn "CN=@hq.example.com"     --san @hq.example.com --flag serverAuth --outform pem > server-cert.pem
```

LibreSwan uses the `certutil` command from the NSS (Network Security Services) toolkit for similar operations.

### Which IPsec implementation should I choose for a site-to-site VPN?

For most new deployments, **strongSwan** is the recommended choice due to its active development, extensive feature set, and strong IKEv2 implementation. Choose **LibreSwan** if you are on RHEL/CentOS (where it is the default) or if you need maximum compatibility with existing OpenSWAN configurations. Avoid **OpenSWAN** for new installations — it is no longer maintained.

### How do I troubleshoot an IPsec connection that won't establish?

Start by checking the logs: `journalctl -u strongswan-starter -f` for strongSwan or `/var/log/pluto.log` for LibreSwan. Common issues include: mismatched encryption algorithms between peers, firewall rules blocking UDP ports 500 (IKE) and 4500 (NAT-T), incorrect pre-shared keys, or certificate validation failures (expired certs, wrong CN/SAN). Use `ipsec status` to check the current state of all connections.

### Does IPsec work with IPv6?

Yes, both strongSwan and LibreSwan fully support IPv6. strongSwan has more comprehensive IPv6 support, including IPv6-in-IPv6 tunneling and IPv6 address assignment for remote clients. Configure IPv6 subnets in the `leftsubnet` and `rightsubnet` parameters using the standard CIDR notation (e.g., `fd00::/64`).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted IPsec VPN: strongSwan vs LibreSwan vs OpenSWAN (2026)",
  "description": "Compare three open-source IPsec VPN implementations: strongSwan, LibreSwan, and OpenSWAN. Covers installation, configuration, Docker deployment, and site-to-site setup.",
  "datePublished": "2026-05-19",
  "dateModified": "2026-05-19",
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
