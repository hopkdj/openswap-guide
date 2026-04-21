---
title: "iPXE vs netboot.xyz vs FOG Project: Self-Hosted PXE Network Boot Guide 2026"
date: 2026-04-20
tags: ["comparison", "guide", "self-hosted", "networking", "infrastructure"]
draft: false
description: "Complete guide to self-hosted PXE network boot solutions. Compare iPXE, netboot.xyz, and FOG Project for bare-metal provisioning, OS deployment, and imaging in 2026."
---

Bare-metal server provisioning and network-based OS installation remain essential skills for any homelab or enterprise infrastructure. Instead of physically swapping USB drives between machines, **Preboot eXecution Environment (PXE)** lets you boot and install operating systems entirely over the network.

This guide compares three leading open-source PXE network boot solutions: **iPXE**, **netboot.xyz**, and **FOG Project**. Whether you're deploying a [[kubernetes](https://kubernetes.io/) cluster on bare metal](../k3s-vs-k0s-vs-talos-linux-self-hosted-kubernetes-guide-2026/) or imaging dozens of workstations, the right PXE tool saves hours of manual setup.

## Why Self-Host PXE Network Boot?

Running your own PXE boot infrastructure gives you:

- **Zero-touch provisioning** — boot new machines with no physical media
- **Centralized OS management** — one server, dozens of install sources
- **Automated deployments** — unattended installs with preseed/Kickstart files
- **Disk imaging and cloning** — capture and restore full disk images over the network
- **Disaster recovery** — boot rescue environments on any network-connected machine
- **Cost savings** — no need for KVM switches, USB drives, or physical console access

PXE booting requires a **DHCP server** to hand out IP addresses and point clients to a **TFTP/HTTP server** hosting boot images. If you're already running a self-hosted [DHCP server like Kea or dnsmasq](../self-hosted-dhcp-servers-kea-dnsmasq-isc-dhcp-guide-2026/), you're halfway there.

## Quick Comparison

| Feature | iPXE | netboot.xyz | FOG Project |
|---|---|---|---|
| **Type** | Boot firmware | Boot menu aggregator | Imaging & management platform |
| **Language** | C | Jinja/Shell | PHP |
| **GitHub Stars** | 1,927 | 11,638 | 1,546 |
| **Last Updated** | 2026-04-17 | 2026-04-20 | 2026-04-15 |
| **Web UI** | No | No | Yes |
| **Disk Imaging** | No | No | Yes |
| **OS Support** | Any (custom scripts) | 100+ live ISOs | Linux, Windows, macOS |
| **Unattended Install** | Via iPXE scripts | Via autoinstall files | Via task scheduling |
| **Self-Hosted** | Yes | Yes (local mirror) | Yes |
| **[docker](https://www.docker.com/) Support** | No | Community images | No |
| **Best For** | Firmware-level control | Quick OS testing | Mass deployment & imaging |

## iPXE: Open-Source PXE Boot Firmware

[iPXE](https://ipxe.org/) is a drop-in replacement for traditional PXE ROM firmware. It extends the basic PXE protocol with HTTP, iSCSI, FCoE, WoWLAN, and FCoE boot capabilities, plus a powerful scripting engine.

### Key Features

- **HTTP/HTTPS/iSCSI boot** — boot directly from web servers or SAN storage
- **Scripting engine** — chainload, menus, variables, and conditional logic
- **Wireless support** — boot over WiFi with WoWLAN
- **EFI and legacy BIOS** — supports both firmware types
- **Embedded scripts** — bake your boot config directly into the ROM

### How iPXE Works

iPXE replaces or chainloads from your network card's built-in PXE ROM. When a machine boots, iPXE fetches a boot script (via HTTP or TFTP) that decides what to load next: a Linux kernel, a Windows PE image, or a live ISO.

### Installation: Compile iPXE from Source

```bash
# Install build dependencies
apt-get update && apt-get install -y git build-essential binutils-dev liblzma-dev

# Clone the repository
git clone https://github.com/ipxe/ipxe.git
cd ipxe/src

# Build iPXE for standard NICs (undionly.kpxe works for most cards)
make bin/undionly.kpxe EMBED=boot.ipxe

# Build for Intel NICs specifically
make bin/ipxe.usb
make bin-x86_64-efi/ipxe.efi
```

### iPXE Boot Script Example

Create a `boot.ipxe` script that presents a boot menu:

```ipxe
#!ipxe

set menu-timeout 5000
set submenu-timeout ${menu-timeout}

:start
menu iPXE Boot Menu
item --gap -- -------------------------
item ubuntu       Install Ubuntu 24.04 LTS
item debian       Install Debian 12
item ubuntu-live  Boot Ubuntu Live (RAM)
item fog          Chainload FOG Project
item shell        iPXE Shell

choose --timeout ${menu-timeout} --default shell target && goto ${target}

:ubuntu
kernel http://archive.ubuntu.com/ubuntu/dists/noble/main/installer-amd64/current/legacy-images/netboot/ubuntu-installer/amd64/linux
initrd http://archive.ubuntu.com/ubuntu/dists/noble/main/installer-amd64/current/legacy-images/netboot/ubuntu-installer/amd64/initrd.gz
imgargs linux auto=true priority=critical locale=en_US keymap=us
boot || goto failed

:debian
kernel http://deb.debian.org/debian/dists/bookworm/main/installer-amd64/current/images/netboot/debian-installer/amd64/linux
initrd http://deb.debian.org/debian/dists/bookworm/main/installer-amd64/current/images/netboot/debian-installer/amd64/initrd.gz
imgargs linux auto=true priority=critical locale=en_US keymap=us
boot || goto failed

:ubuntu-live
kernel http://releases.ubuntu.com/24.04/ubuntu-24.04-desktop-amd64.iso
boot || goto failed

:fog
chain http://${fog-server}/fog/service/ipxe/boot.php?mac=${net0/mac} || goto failed

:shell
shell || goto failed

:failed
echo Boot failed, returning to menu
sleep 3
goto start
```

### DHCP Configuration for iPXE

Configure your DHCP server to point PXE clients to iPXE. Here's a **dnsmasq** configuration:

```bash
# /etc/dnsmasq.d/pxe.conf

# Enable TFTP
enable-tftp

# Set TFTP root directory
tftp-root=/var/lib/tftpboot

# DHCP options for PXE boot
dhcp-boot=undionly.kpxe,,192.168.1.10

# For UEFI clients
dhcp-match=set:efi-x86_64,option:client-arch,7
dhcp-boot=tag:efi-x86_64,ipxe.efi,,192.168.1.10

# For BIOS clients
dhcp-match=set:bios,option:client-arch,0
dhcp-boot=tag:bios,undionly.kpxe,,192.168.1.10
```

For a production setup with Kea DHCP, use this configuration:

```json
{
  "Dhcp4": {
    "interfaces-config": {
      "interfaces": ["eth0"]
    },
    "subnet4": [
      {
        "subnet": "192.168.1.0/24",
        "pools": [{ "pool": "192.168.1.100 - 192.168.1.200" }],
        "option-data": [
          {
            "name": "domain-name-servers",
            "data": "192.168.1.1"
          },
          {
            "name": "boot-file-name",
            "data": "undionly.kpxe"
          },
          {
            "name": "next-server",
            "data": "192.168.1.10"
          }
        ]
      }
    ]
  }
}
```

## netboot.xyz: 100+ Operating Systems in One Boot Menu

[netboot.xyz](https://netboot.xyz/) is a network bootable aggregator built on top of iPXE. It provides a single bootable ISO, USB, or PXE image that gives you access to over 100 operating system installers and live environments — all served from their CDN or your own self-hosted mirror.

### Key Features

- **100+ OS options** — Ubuntu, Debian, Fedora, Arch, Proxmox, TrueNAS, and more
- **Live environments** — boot directly into RAM without disk installation
- **Self-hosted mirror** — run your own local copy for air-gapped networks
- **Built on iPXE** — inherits all iPXE scripting and protocol support
- **Multiple boot methods** — ISO, USB, PXE, or cloud-init

### How netboot.xyz Works

netboot.xyz provides a pre-built iPXE binary that boots to a menu. When you select an OS, it fetches the kernel and initrd directly from upstream mirrors (or your local mirror) and boots them. No local storage of ISOs is required unless you run a self-hosted mirror.

### Self-Hosting netboot.xyz

To run netboot.xyz locally, you need an HTTP server to host the menu assets and a TFTP server for the iPXE binary.

##[nginx](https://nginx.org/)ep 1: Set up the HTTP server

```bash
# Install Nginx
apt-get update && apt-get install -y nginx

# Create document root
mkdir -p /var/www/netboot.xyz

# Download netboot.xyz assets
cd /var/www/netboot.xyz
wget https://github.com/netbootxyz/netboot.xyz/releases/latest/download/netboot.xyz.tar.gz
tar xzf netboot.xyz.tar.gz

# Configure Nginx
cat > /etc/nginx/sites-available/netboot.xyz << 'NGINX_EOF'
server {
    listen 80;
    server_name netboot.local;
    root /var/www/netboot.xyz;

    location / {
        autoindex on;
        try_files $uri $uri/ =404;
    }
}
NGINX_EOF

ln -s /etc/nginx/sites-available/netboot.xyz /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
```

#### Step 2: Configure TFTP for PXE boot

```bash
apt-get install -y tftpd-hpa

# Copy iPXE binary to TFTP root
mkdir -p /srv/tftp
wget -O /srv/tftp/netboot.xyz.kpxe \
  https://github.com/netbootxyz/netboot.xyz/releases/latest/download/ipxe.kpxe

# Set TFTP directory
sed -i 's|TFTP_DIRECTORY=.*|TFTP_DIRECTORY="/srv/tftp"|' /etc/default/tftpd-hpa
systemctl restart tftpd-hpa
```

#### Step 3: Self-hosted iPXE menu configuration

For a fully self-hosted setup, create a custom iPXE script pointing to your local mirror:

```ipxe
#!ipxe

set base_url http://192.168.1.10/netboot.xyz

# Ubuntu 24.04 LTS
:ubuntu-2404
kernel ${base_url}/ubuntu/dists/noble/main/installer-amd64/current/legacy-images/netboot/ubuntu-installer/amd64/linux
initrd ${base_url}/ubuntu/dists/noble/main/installer-amd64/current/legacy-images/netboot/ubuntu-installer/amd64/initrd.gz
imgargs linux auto=true priority=critical locale=en_US
boot

# Debian 12
:debian-12
kernel ${base_url}/debian/dists/bookworm/main/installer-amd64/current/images/netboot/debian-installer/amd64/linux
initrd ${base_url}/debian/dists/bookworm/main/installer-amd64/current/images/netboot/debian-installer/amd64/initrd.gz
imgargs linux auto=true priority=critical locale=en_US
boot

# Proxmox VE
:proxmox
kernel ${base_url}/proxmox/linux26
initrd ${base_url}/proxmox/initrd.img
boot
```

### Using the netboot.xyz ISO

For quick testing, download the ISO and boot a VM or physical machine:

```bash
# Download the latest ISO
wget -O netboot.xyz.iso \
  https://github.com/netbootxyz/netboot.xyz/releases/latest/download/netboot.xyz.iso

# Boot in QEMU/KVM
qemu-system-x86_64 -cdrom netboot.xyz.iso -boot d -m 2048 -enable-kvm

# Write to USB for physical machines
dd if=netboot.xyz.iso of=/dev/sdX bs=4M status=progress && sync
```

## FOG Project: Complete Imaging & Deployment Platform

[FOG Project](https://fogproject.org/) is a full-featured open-source computer imaging and deployment system. Unlike iPXE and netboot.xyz which focus on booting, FOG provides a **complete lifecycle management platform** with a web interface for capturing, deploying, and managing disk images across your network.

### Key Features

- **Web management interface** — manage hosts, images, and tasks from a browser
- **Disk imaging** — capture and deploy full disk images (single-cast and multi-cast)
- **Snapin deployment** — push software packages, scripts, and files to clients
- **Inventory management** — auto-discover hardware specs from deployed hosts
- **Wake-on-LAN** — remotely power on machines for scheduled deployments
- **Active Directory integration** — auto-join domain after imaging
- **Plugin system** — extend functionality with custom plugins

### Architecture

FOG uses a client-server model:
- **FOG Server** — Ubuntu/Debian/CentOS server with web UI, TFTP, DHCP, NFS, and MySQL
- **FOG Client** — Windows/Linux agent running on deployed machines for post-deployment tasks
- **Storage Nodes** — optional secondary servers for multi-site image distribution

### Installation

FOG Project provides an automated installer script:

```bash
# Download the latest stable release
apt-get update && apt-get install -y git
git clone https://github.com/FOGProject/fogproject.git
cd fogproject/bin

# Run the installer (interactive)
./installfog.sh

# Or for non-interactive install, create a config file first:
cat > /opt/fog/.fogsettings << 'EOF'
ipaddress='192.168.1.10'
interface='eth0'
routeraddress='192.168.1.1'
plainrouter='192.168.1.1'
dnsaddress='192.168.1.1'
username='fog'
password='yourpassword'
osid='2'
osname='Debian'
dodhcp='n'
bldhcp='0'
installlang='0'
storageLocation='/images'
fogupdateloaded='1'
EOF

./installfog.sh -X
```

### Post-Installation Configuration

After installation, access the web interface at `http://<fog-server>/fog/`.

1. **Default login**: `fog` / `password` (change immediately)
2. **Configure storage node**: Settings → FOG Configuration → Storage Nodes
3. **Add host**: Hosts → Create New Host → enter MAC address
4. **Create image**: Images → Create New Image → select OS type
5. **Schedule task**: Hosts → Select Host → Task → Deploy/Capture

### Multi-Cast Image Deployment

For deploying a single image to multiple machines simultaneously:

```bash
# Via the web UI:
# 1. Go to Host Management → Select multiple hosts
# 2. Actions → Multi-Cast Deploy
# 3. Select image, set client count, schedule time

# Via FOG API (requires API token):
curl -X POST "http://fog-server/fog/host/task" \
  -H "Content-Type: application/json" \
  -H "fog-api-token: your-api-token" \
  -d '{
    "taskTypeID": 8,
    "hostID": [1, 2, 3, 4, 5],
    "imageID": 1,
    "shutdown": false
  }'
```

### FOG PXE Boot Menu Customization

FOG automatically configures iPXE boot menus. You can customize the default boot behavior by editing `/tftpboot/default.ipxe`:

```ipxe
#!ipxe

set fog-ip 192.168.1.10
set fog-webroot fog

:MENU
menu
item --gap FOG Project Boot Menu
item fog.local Boot from hard disk
item fog.memtest Run Memtest86+
item fog.reg Quick Registration and Inventory
item fog.deploy Image Deploy
item fog.capture Image Capture
choose --default fog.local --timeout 5000 target && goto ${target}

:fog.local
sanboot --no-describe --drive 0x80 || goto MENU

:fog.memtest
kernel ${boot-url}/memtest.bin || goto MENU
boot || goto MENU

:fog.reg
login
params
param mac0 ${net0/mac}
param arch ${arch}
param username ${username}
param password ${password}
param qihost 1
imgfetch ${boot-url}/fog/service/ipxe/boot.php##params || goto MENU
boot || goto MENU

:fog.deploy
login
params
param mac0 ${net0/mac}
param arch ${arch}
param username ${username}
param password ${password}
imgfetch ${boot-url}/fog/service/ipxe/boot.php##params || goto MENU
boot || goto MENU

:fog.capture
login
params
param mac0 ${net0/mac}
param arch ${arch}
param username ${username}
param password ${password}
param qihost 1
imgfetch ${boot-url}/fog/service/ipxe/boot.php##params || goto MENU
boot || goto MENU
```

## Choosing the Right PXE Solution

| Scenario | Recommended Tool | Why |
|---|---|---|
| Boot firmware replacement | **iPXE** | Direct NIC firmware, HTTP/iSCSI boot |
| Testing multiple OSes quickly | **netboot.xyz** | 100+ installers in one menu |
| Deploying 10+ identical machines | **FOG Project** | Multi-cast imaging, web UI, AD join |
| Bare-metal Kubernetes cluster | **iPXE + custom scripts** | Unattended install with preseed files |
| Lab/education environment | **netboot.xyz** | No local storage needed, quick setup |
| Enterprise workstation imaging | **FOG Project** | Inventory, snapins, scheduling |
| Air-gapped network | **netboot.xyz mirror** | Self-hosted ISOs, no internet needed |
| Dual-boot firmware (UEFI + BIOS) | **iPXE** | Compiles for both architectures |

## When to Combine Tools

These tools are complementary, not mutually exclusive. Common combinations:

- **iPXE → netboot.xyz**: Chainload iPXE into netboot.xyz for the best of both worlds
- **iPXE → FOG Project**: Use iPXE as the firmware, FOG as the imaging backend
- **FOG + custom iPXE scripts**: FOG handles imaging, iPXE handles custom boot menus

## Deployment Best Practices

1. **Separate DHCP from PXE** — if your router runs DHCP, configure it to point to your PXE server via the `next-server` option
2. **Use HTTP over TFTP** — iPXE supports HTTP fetching, which is significantly faster than TFTP for large kernels
3. **VLAN isolation** — keep PXE boot traffic on a dedicated VLAN to avoid interfering with production DHCP
4. **Backup your images** — FOG Project images are large; store them on a separate disk or NAS
5. **Test with VMs first** — always validate boot scripts in a VM (VirtualBox, KVM) before deploying to physical hardware
6. **Document your MAC addresses** — FOG requires MAC addresses for host registration; maintain a spreadsheet or CMDB

For related reading, see our [Proxmox vs XCP-ng virtualization comparison](../proxmox-ve-vs-xcp-ng-vs-ovirt-self-hosted-virtualization-guide-2026/) for bare-metal hypervisor options to provision via PXE, and our [complete overlay networks guide](../self-hosted-overlay-networks-zerotier-nebula-netmaker-guide-2026/) for connecting remote sites to your PXE infrastructure.

## FAQ

### What is PXE boot and how does it work?

PXE (Preboot eXecution Environment) is a standard that allows a computer to boot from a network interface rather than a local disk. The process works in stages: the client's network card broadcasts a DHCP request, the DHCP server responds with an IP address and the location of a boot file (usually via the `next-server` and `filename` options), the client fetches the boot file via TFTP, and the bootloader (like iPXE) loads the operating system kernel and initrd.

### Can I use PXE boot over WiFi?

Traditional PXE requires an Ethernet connection. However, **iPXE** supports WoWLAN (Wake on Wireless LAN) and can boot over WiFi if your network card supports it. For most deployments, a wired Ethernet connection is more reliable and recommended.

### Do I need a DHCP server for PXE boot?

Yes. PXE boot requires a DHCP server to assign IP addresses and provide the boot file location (`next-server` and `filename` DHCP options). You can use your existing router's DHCP server (by configuring options 66 and 67), or run a dedicated DHCP server like **dnsmasq**, **Kea**, or **ISC DHCP** on your PXE server.

### Is netboot.xyz safe to use in production?

netboot.xyz is widely used and open-source. For production or air-gapped environments, you should run a **self-hosted mirror** of the boot assets rather than relying on the public CDN. This ensures availability even without internet access and gives you full control over the boot images served to your clients.

### Can FOG Project image Windows machines?

Yes. FOG Project supports Windows imaging using the `ntfsclone` or `partclone` imaging engines. After deploying a Windows image, the FOG Client can handle post-deployment tasks like Active Directory domain join, driver injection, and hostname configuration. Note that Windows licensing compliance is your responsibility.

### How fast is multi-cast imaging with FOG?

Multi-cast imaging speed depends on your network bandwidth and the number of clients. On a 1 Gbps network, deploying a 50 GB image to 20 machines simultaneously takes approximately 8-10 minutes (similar to single-cast, since the data is sent once and received by all clients). On 10 Gbps networks, the same deployment completes in under 2 minutes.

### What's the difference between iPXE and standard PXE?

Standard PXE (defined in the Intel PXE specification) only supports TFTP for downloading boot files. **iPXE** is an open-source implementation that extends PXE with support for HTTP, HTTPS, iSCSI, FCoE, and WoWLAN, plus a built-in scripting language. Most modern systems use iPXE either as a replacement for the built-in PXE ROM or chainloaded from it.

### Can I chainload iPXE from my existing PXE ROM?

Yes. Configure your DHCP server to serve `undionly.kpxe` (the iPXE binary that works with any PXE ROM) as the boot filename. The built-in PXE ROM loads iPXE, which then provides full HTTP, scripting, and menu support. This is the most common iPXE deployment method.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "iPXE vs netboot.xyz vs FOG Project: Self-Hosted PXE Network Boot Guide 2026",
  "description": "Complete guide to self-hosted PXE network boot solutions. Compare iPXE, netboot.xyz, and FOG Project for bare-metal provisioning, OS deployment, and imaging in 2026.",
  "datePublished": "2026-04-20",
  "dateModified": "2026-04-20",
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
