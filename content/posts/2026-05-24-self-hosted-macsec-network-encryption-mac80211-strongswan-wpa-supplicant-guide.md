---
title: "Self-Hosted MACsec Network Encryption: mac80211 vs strongSwan vs wpa_supplicant"
date: "2026-05-24"
tags: ["networking", "security", "encryption", "macsec", "self-hosted", "linux"]
draft: false
---

MACsec (IEEE 802.1AE) provides layer 2 encryption for Ethernet networks, securing traffic between directly connected hosts at the data link layer. Unlike IPsec (layer 3) or TLS (layer 7), MACsec encrypts every Ethernet frame, including ARP, DHCP, and other non-IP protocols, providing comprehensive network-level security.

In this guide, we compare three open-source approaches to implementing MACsec on Linux: the kernel **mac80211/macsec** module, **strongSwan** for MACsec-over-IPsec integration, and **wpa_supplicant** for 802.1X/MACsec authentication. We cover installation, configuration, Docker-based testing, and when each approach is appropriate.

## What Is MACsec?

MACsec (Media Access Control Security) is an IEEE standard (802.1AE) that provides hop-by-hop encryption at layer 2. It operates between the MAC and PHY layers, encrypting Ethernet frames before they hit the wire.

### MACsec vs IPsec vs TLS

| Layer | Technology | Scope | Protocols Protected |
|-------|-----------|-------|-------------------|
| Layer 2 | MACsec (802.1AE) | Hop-by-hop | ALL (IP, ARP, DHCP, etc.) |
| Layer 3 | IPsec | End-to-end or gateway | IP traffic only |
| Layer 4-7 | TLS | Application-level | Specific protocols (HTTPS, etc.) |

MACsec's key advantage is **universal protocol coverage**: it encrypts everything on the wire, not just IP traffic. This makes it ideal for:

- **Data center interconnects**: Encrypting traffic between servers in the same rack or across racks.
- **Campus networks**: Securing connections between buildings without relying on higher-layer protocols.
- **Compliance environments**: Meeting encryption-at-rest requirements for all network traffic, not just application data.
- **IoT networks**: Encrypting traffic from devices that may not support IPsec or TLS.

### MACsec Architecture

MACsec uses the MACsec SecY (Security Entity) kernel component and the MKA (MACsec Key Agreement, IEEE 802.1X-2010) protocol for key management:

```
┌────────────────────────────────────────────┐
│              Application Layer              │
├────────────────────────────────────────────┤
│              TCP/IP Stack                   │
├────────────────────────────────────────────┤
│    MACsec SecY (kernel: macsec module)      │  ← Encryption/decryption
├────────────────────────────────────────────┤
│    MKA Daemon (user-space key management)    │  ← Key agreement
├────────────────────────────────────────────┤
│              Ethernet Driver                │
└────────────────────────────────────────────┘
```

## Kernel macsec Module: Native Linux MACsec

The Linux kernel includes a native MACsec implementation since version 4.6. It provides the SecY (Security Entity) as a network device, managed via the `iproute2` tools.

### Installation

```bash
# The macsec kernel module is built into modern kernels
# Verify it's available:
modprobe macsec
lsmod | grep macsec

# Install iproute2 for management
apt-get install iproute2   # Debian/Ubuntu
yum install iproute        # RHEL/CentOS
```

### Configuration with Pre-Shared Keys

```bash
# Create a macsec interface on eth0
ip link add link eth0 name macsec0 type macsec     port 1     encrypt on

# Add a receive security association (SA) on the peer
# SCI: SecY Channel Identifier (8-byte unique identifier)
# PN: Packet Number (for replay protection)
ip macsec add macsec0 rx port 1 address 00:11:22:33:44:55
ip macsec add macsec0 rx port 1 address 00:11:22:33:44:55 sa 0 pn 1     on     key 00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff

# Add a transmit security association
ip macsec add macsec0 tx port 1 address 00:11:22:33:44:55 sa 0 pn 1     key 00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff

# Bring up the interface
ip link set macsec0 up
ip addr add 10.0.0.1/24 dev macsec0
```

### Docker Compose for MACsec Testing

```yaml
version: "3.8"
services:
  macsec-host-a:
    image: ubuntu:24.04
    privileged: true
    network_mode: host
    volumes:
      - ./setup-macsec-a.sh:/setup.sh
    command: ["/bin/bash", "/setup.sh"]

  macsec-host-b:
    image: ubuntu:24.04
    privileged: true
    network_mode: host
    volumes:
      - ./setup-macsec-b.sh:/setup.sh
    command: ["/bin/bash", "/setup.sh"]
```

```bash
#!/bin/bash
# setup-macsec-a.sh (Host A)
modprobe macsec
ip link add link eth0 name macsec0 type macsec port 1 encrypt on
ip macsec add macsec0 tx port 1 address AA:BB:CC:DD:EE:01 sa 0 pn 1     key 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
ip macsec add macsec0 rx port 1 address AA:BB:CC:DD:EE:02 sa 0 pn 1     key 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
ip link set macsec0 up
ip addr add 10.0.1.1/24 dev macsec0
```

### Monitoring MACsec

```bash
# Show MACsec interface details
ip -s macsec show macsec0

# Show statistics
ip -s link show macsec0
# RX: bytes packets errors dropped
# TX: bytes packets errors dropped

# Capture encrypted traffic (MACsec frames are still visible, just encrypted)
tcpdump -i eth0 ether proto 0x88e5 -nn
```

## strongSwan: MACsec with IKE-Based Key Management

[strongSwan](https://github.com/strongswan/strongswan) is a well-established IPsec implementation (2,876+ GitHub stars) that also supports MACsec through its `charon` daemon. While primarily known for IPsec VPNs, strongSwan can manage MACsec key agreement using IKEv2, providing automated key rotation and mutual authentication.

### Why Use strongSwan for MACsec?

The kernel macsec module requires manual key configuration. strongSwan automates key management through IKEv2, providing:

- **Automatic key rotation**: Keys are refreshed periodically without manual intervention.
- **Mutual authentication**: X.509 certificates or pre-shared keys for peer verification.
- **Scalability**: Centralized key management for multi-node deployments.
- **Integration**: Unified management with existing IPsec infrastructure.

### Installation

```bash
# Debian/Ubuntu
apt-get install strongswan strongswan-pki libcharon-extra-plugins

# From source
git clone https://github.com/strongswan/strongswan.git
cd strongswan
./configure --enable-macsec --enable-charon
make && make install
```

### strongSwan Configuration for MACsec

```ini
# /etc/swanctl/swanctl.conf
connections {
    macsec-link {
        local_addrs = 192.168.1.10
        remote_addrs = 192.168.1.20

        local {
            auth = pubkey
            certs = hostA.pem
            id = "hostA.example.com"
        }
        remote {
            auth = pubkey
            certs = hostB.pem
            id = "hostB.example.com"
        }

        children {
            macsec-child {
                mode = transport
                esp_proposals = aes256gcm128-xfrm
                macsec = yes
                macsec_integ = yes
                macsec_encrypt = yes
                macsec_replay_window = 64
            }
        }
    }
}
```

### Certificate Setup

```bash
# Generate CA
swanctl --init --type ca --subject "CN=MACsec CA" --outform pem > ca.pem

# Generate host certificate
swanctl --init --type pk --subject "CN=hostA.example.com"     --cacert ca.pem --outform pem > hostA.pem
```

### Starting the MACsec Connection

```bash
# Start strongSwan
systemctl start strongswan

# Initiate the MACsec connection
swanctl --initiate --child macsec-link

# Verify the MACsec interface was created
ip link show type macsec
ip -s macsec show
```

## wpa_supplicant: 802.1X/MACsec Authentication

wpa_supplicant, best known for Wi-Fi authentication, also supports MACsec through its 802.1X-2010 implementation. It provides MKA (MACsec Key Agreement) for dynamic key management, integrating with RADIUS servers for centralized authentication.

### Why Use wpa_supplicant for MACsec?

wpa_supplicant is ideal when MACsec needs to integrate with existing 802.1X infrastructure:

- **RADIUS integration**: Authenticate MACsec peers against a RADIUS server (FreeRADIUS).
- **802.1X port-based authentication**: Combine network access control with encryption.
- **Dynamic key distribution**: Keys are generated and distributed automatically through MKA.
- **Supplicant role**: Works as the client-side component in a MACsec deployment.

### Installation

```bash
# Debian/Ubuntu
apt-get install wpasupplicant

# Ensure MKA support is compiled in
wpa_supplicant -v | grep MACSEC
```

### wpa_supplicant Configuration for MACsec

```ini
# /etc/wpa_supplicant/wpa_supplicant-macsec.conf
ctrl_interface=/run/wpa_supplicant
ap_scan=0

# MACsec configuration
macsec_integ_only=0
mka_priority=50

network={
    key_mgmt=NONE
    macsec=<eth0>
    mka_cak=0123456789abcdef0123456789abcdef
    mka_ckn=abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789
}
```

### Docker Compose with wpa_supplicant

```yaml
version: "3.8"
services:
  macsec-client:
    image: ubuntu:24.04
    privileged: true
    network_mode: host
    volumes:
      - ./wpa_supplicant-macsec.conf:/etc/wpa_supplicant/wpa_supplicant.conf
      - ./start-macsec.sh:/start.sh
    command: ["/bin/bash", "/start.sh"]
```

```bash
#!/bin/bash
# start-macsec.sh
modprobe macsec
wpa_supplicant -i eth0 -c /etc/wpa_supplicant/wpa_supplicant.conf -B

# Wait for MKA to establish the secure channel
sleep 5
ip -s macsec show
```

### RADIUS Integration for Enterprise MACsec

For enterprise deployments, combine wpa_supplicant with a RADIUS server like [FreeRADIUS](https://freeradius.org/) for centralized authentication:

```ini
# wpa_supplicant.conf with EAP-TLS
network={
    key_mgmt=IEEE8021X
    eap=TLS
    identity="hostA@example.com"
    ca_cert="/etc/ssl/certs/ca.pem"
    client_cert="/etc/ssl/certs/hostA.pem"
    private_key="/etc/ssl/private/hostA.key"
    macsec=<eth0>
    mka_cak=0123456789abcdef0123456789abcdef
    mka_ckn=abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789
}
```

## Comparison Table

| Feature | Kernel macsec | strongSwan MACsec | wpa_supplicant MACsec |
|---------|--------------|-------------------|----------------------|
| **Key Management** | Manual (PSK) | IKEv2 (auto) | MKA (auto via 802.1X) |
| **Authentication** | None (shared key) | X.509, PSK | 802.1X/EAP, RADIUS |
| **Key Rotation** | Manual | Automatic | Automatic (MKA) |
| **Scalability** | Point-to-point | Multi-peer | Enterprise (RADIUS) |
| **Setup Complexity** | Low | Medium | High |
| **Active Development** | Yes (kernel) | Yes (2,876★) | Yes (mainline) |
| **Best For** | Simple point-to-point links | IPsec+MACsec integration | Enterprise 802.1X networks |
| **Hardware Offload** | Yes (NIC dependent) | No | No |

## Choosing the Right MACsec Approach

| Scenario | Recommended Approach |
|----------|---------------------|
| Simple server-to-server link | Kernel macsec (manual PSK) |
| Data center with automated key rotation | strongSwan (IKEv2) |
| Enterprise network with RADIUS | wpa_supplicant (802.1X) |
| Existing IPsec infrastructure | strongSwan (unified management) |
| IoT devices with minimal config | Kernel macsec (static keys) |

## Why Self-Host MACsec?

Implementing MACsec on self-hosted infrastructure provides hardware-level network encryption without relying on cloud provider features or proprietary appliances. This gives you complete control over encryption algorithms, key management, and audit policies.

**Compliance advantage**: MACsec satisfies encryption requirements for regulated data in transit at the network layer. Industries subject to PCI DSS, HIPAA, or financial regulations can deploy MACsec on self-hosted switches and servers to encrypt all inter-server traffic, meeting compliance requirements that may not be covered by application-layer encryption alone.

**Performance**: Hardware-offloaded MACsec (supported by many modern NICs from Intel, Mellanox, and Broadcom) provides line-rate encryption with zero CPU overhead. Software-based MACsec typically achieves 2-8 Gbps per core on modern hardware, sufficient for most data center interconnects.

**No vendor lock-in**: The Linux MACsec implementation is standardized (IEEE 802.1AE) and interoperable with any MACsec-capable switch or NIC. Unlike proprietary encryption solutions, MACsec keys and algorithms are portable across different hardware vendors.

For broader network security, see our [IPsec VPN gateway guide](../strongswan-vs-libreswan-vs-softether-self-hosted-vpn-gateway-guide-2026/) comparing strongSwan, LibreSwan, and SoftEther. For TLS-level encryption, our [mutual TLS guide](../2026-04-24-self-hosted-mutual-tls-mtls-nginx-caddy-traefik-envoy-guide/) covers mTLS with Nginx, Caddy, Traefik, and Envoy. For comprehensive network scanning and security assessment, check our [network port scanner comparison](../2026-04-22-nmap-vs-masscan-vs-rustscan-self-hosted-network-scanning-guide/).

## FAQ

### What is the difference between MACsec and IPsec?

MACsec operates at layer 2 (data link layer), encrypting Ethernet frames before they reach the IP stack. IPsec operates at layer 3 (network layer), encrypting IP packets. MACsec encrypts ALL protocols (ARP, DHCP, IPv4, IPv6), while IPsec only encrypts IP traffic. MACsec is hop-by-hop (each link is encrypted separately), while IPsec can be end-to-end or gateway-to-gateway.

### Does MACsec work over wireless networks?

MACsec is defined for wired Ethernet (IEEE 802.3). Wireless networks use WPA3 (802.11ax) for layer 2 encryption. The wpa_supplicant tool supports both, but the MACsec and Wi-Fi implementations use different key agreement protocols (MKA vs 4-way handshake).

### Can MACsec and IPsec be used together?

Yes. This is called MACsec-over-IPsec or IPsec-over-MACsec (depending on which layer is applied first). strongSwan supports both combinations. Layer 2 encryption (MACsec) protects against local network attacks, while layer 3 encryption (IPsec) protects against routing-level attacks across untrusted networks.

### What hardware supports MACsec offload?

Many modern NICs support MACsec hardware offload, including Intel E810 series, Mellanox ConnectX-5/6, and Broadcom NetXtreme E-Series. Check your NIC's documentation for MACsec support. Hardware offload moves encryption from the CPU to the NIC, providing line-rate performance with minimal CPU overhead.

### How does MACsec key rotation work?

With the kernel macsec module, key rotation is manual — you must update the SA keys on both peers. With strongSwan, IKEv2 handles automatic key rotation at configurable intervals (default: every hour). With wpa_supplicant, MKA (MACsec Key Agreement) automatically generates and distributes new keys through the 802.1X protocol.

### Can MACsec be used with VLANs?

Yes. MACsec operates below the VLAN layer, meaning VLAN tags are encrypted along with the payload. The MACsec header is inserted between the Ethernet header and the VLAN tag (or between the VLAN tag and the payload, depending on the configuration). Most enterprise switches support MACsec on tagged ports.

### Is MACsec suitable for encrypting traffic across the internet?

No. MACsec is designed for hop-by-hop encryption on directly connected links. It does not provide end-to-end encryption across routed networks. For internet traffic, use IPsec (strongSwan, LibreSwan) or TLS. MACsec is best suited for data center interconnects, campus networks, and direct server-to-server links.

### How do I verify that MACsec is working?

Use `tcpdump -i eth0 ether proto 0x88e5` to capture MACsec frames. Encrypted MACsec frames have EtherType 0x88E5. You can verify encryption by checking that the payload is not readable in the capture. Additionally, `ip -s macsec show` displays packet counts, errors, and replay protection statistics.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted MACsec Network Encryption: mac80211 vs strongSwan vs wpa_supplicant",
  "description": "Compare three open-source approaches to MACsec (802.1AE) network encryption on Linux: kernel macsec module, strongSwan with IKEv2, and wpa_supplicant with 802.1X authentication. Includes configuration guides and Docker deployment examples.",
  "datePublished": "2026-05-24",
  "dateModified": "2026-05-24",
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
