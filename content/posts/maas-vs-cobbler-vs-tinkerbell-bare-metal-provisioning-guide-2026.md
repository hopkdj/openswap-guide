---
title: "MAAS vs Cobbler vs Tinkerbell: Bare Metal Provisioning Guide 2026"
date: 2026-04-24
tags: ["comparison", "guide", "self-hosted", "infrastructure", "bare-metal"]
draft: false
description: "Compare MAAS, Cobbler, and Tinkerbell for self-hosted bare metal server provisioning. Complete guide with deployment configs, PXE setup, and workflow automation."
---

Deploying operating systems onto physical servers by hand is one of the most time-consuming tasks in any data center or homelab. Even with modern cloud-native tooling, the physical layer still exists — and someone needs to turn bare metal into running machines. That is where **bare metal provisioning** tools come in.

In this guide, we compare the three most widely used open-source bare metal provisioning platforms — **MAAS** (Metal as a Service), **Cobbler**, and **Tinkerbell** — and walk through setting each one up from scratch.

| Feature | MAAS | Cobbler | Tinkerbell |
|---|---|---|---|
| **Language** | Python | Python | Go |
| **Stars (GitHub)** | 473 | 2,752 | 992 |
| **Last Updated** | Apr 2026 | Apr 2026 | Dec 2025 |
| **License** | AGPL-3.0 | GPL-2.0 | Apache-2.0 |
| **Boot Method** | PXE, iPXE | PXE, PXELINUX | iPXE, gRPC |
| **OS Support** | Ubuntu, CentOS, RHEL, Windows, VMware | RHEL, Fedora, SUSE, Debian, Ubuntu | Custom via workflows |
| **IPMI/IPMI Control** | Built-in (IPMI, Redfish) | Via koan (IPMI only) | Via Hegel metadata |
| **DHCP Integration** | Built-in DHCP | Built-in DHCP or external | External (dnsmasq, ISC) |
| **API** | REST API | XML-RPC + REST | gRPC |
| **Best For** | Ubuntu-centric data centers | Multi-distro Linux labs | Cloud-native bare metal |

## Why Self-Hosted Bare Metal Provisioning Matters

When you own physical servers — whether in a colocation rack, a home lab, or a private data center — the cost of manual installation compounds fast. PXE booting a single server takes 30 minutes. Multiply that by 20 new machines and you have lost an entire day. Bare metal provisioning tools solve this by automating:

- **PXE network boot** — machines discover and load their OS over the network without USB drives
- **OS installation** — unattended kickstart, preseed, or cloud-init installs
- **Hardware discovery** — inventory CPU, RAM, disks, NICs, and firmware versions automatically
- **Power management** — remote power cycling via IPMI, Redfish, or vendor-specific APIs
- **Post-install configuration** — SSH keys, network setup, and package installation

For related infrastructure reading, see our [Rancher vs Kubespray vs Kind Kubernetes management guide](../rancher-vs-kubespray-vs-kind-self-hosted-kubernetes-management-guide-2026/) for what to do after provisioning, and the [Ansible vs SaltStack vs Puppet configuration management comparison](../ansible-vs-saltstack-vs-puppet-configuration-management-2026/) for post-provisioning automation.

## MAAS (Metal as a Service)

MAAS is Canonical's bare metal provisioning platform. It treats physical servers like cloud instances — you commission them, then deploy Ubuntu or other OSes with a single command or API call. MAAS integrates tightly with Juju for application deployment and is the foundation of Canonical's Charmed OpenStack and Kubernetes offerings.

### When to Choose MAAS

- You run Ubuntu or a mix of Ubuntu and other Linux distributions
- You want out-of-the-box IPMI, Redfish, and BMC power control
- You plan to deploy Kubernetes or OpenStack on top of provisioned hardware
- You need integrated DHCP, DNS, and NTP management

### Installing MAAS on Ubuntu

MAAS is packaged as a snap on Ubuntu, making installation straightforward:

```bash
# Install MAAS
sudo snap install maas

# Initialize as a region + rack controller (all-in-one for small deployments)
sudo maas init region+rack --database-uri maas-db-region+rack:///var/snap/maas/common/maas-db.sqlite

# Create the admin user
sudo maas createadmin --username admin --password secure-password --email admin@example.com

# Generate an API key
sudo maas apikey --username admin
```

After initialization, the MAAS web UI is available at `http://<server-ip>:5240/MAAS/`.

### MAAS with Docker (Community Image)

For testing, you can run MAAS in Docker using the community image:

```yaml
# docker-compose-maas.yml
version: '3.8'
services:
  maas-region:
    image: maas/region:3.5
    container_name: maas-region
    ports:
      - "5240:5240"
      - "5248:5248"
    environment:
      - MAAS_REGION=yes
      - MAAS_RACK=yes
      - MAAS_DBHOST=maas-db
      - MAAS_DBPASS=maas-password
    volumes:
      - maas-config:/etc/maas
    depends_on:
      - maas-db

  maas-db:
    image: postgres:14
    container_name: maas-db
    environment:
      - POSTGRES_DB=maasdb
      - POSTGRES_USER=maas
      - POSTGRES_PASSWORD=maas-password
    volumes:
      - maas-data:/var/lib/postgresql/data

volumes:
  maas-config:
  maas-data:
```

### Commissioning and Deploying with MAAS

Once MAAS is running, add servers via their BMC/IPMI addresses:

```bash
# Using the MAAS CLI (install with: sudo snap install maas-cli)
maas admin machines create \
  hostname=node-01 \
  architecture=amd64/generic \
  power_type=ipmi \
  power_parameters_power_address=192.168.1.100 \
  power_parameters_power_user=admin \
  power_parameters_power_password=ipmi-password

# Commission the machine
maas admin machines commission <machine-id>

# Deploy Ubuntu 24.04
maas admin machines deploy <machine-id> \
  distro_series=ubuntu/jammy \
  user_data="$(base64 -w0 cloud-init.yaml)"
```

MAAS will PXE boot the server, run hardware discovery, and then install the target OS unattended.

## Cobbler

Cobbler is a versatile Linux deployment server that has been around since 2008. It manages PXE boot environments, kickstart templates, and system profiles across multiple distributions. Cobbler is distribution-agnostic and excels in mixed-Linux environments.

### When to Choose Cobbler

- You manage a mix of RHEL, Fedora, SUSE, and Debian-based systems
- You need a mature, battle-tested tool with a long track record
- You prefer traditional kickstart/preseed workflows over cloud-native approaches
- You want integrated DNS, DHCP, and TFTP management

### Installing Cobbler

Cobbler is available in most Linux distribution repositories:

```bash
# On Ubuntu/Debian
sudo apt update
sudo apt install cobbler cobbler-web dhcp3-server tftpd-hpa debmirror

# On RHEL/Rocky/AlmaLinux
sudo dnf install epel-release
sudo dnf install cobbler cobbler-web dhcp-server tftp-server syslinux

# Enable and start services
sudo systemctl enable --now cobblerd httpd dhcpd tftpd
```

### Cobbler Configuration

The main configuration file is `/etc/cobbler/settings.yaml`. Key settings to adjust:

```yaml
# /etc/cobbler/settings.yaml
server: 192.168.1.10
next_server: 192.168.1.10
manage_dhcp: true
manage_tftpd: true
manage_dns: true
pxe_just_once: true
```

After editing, run `cobbler sync` to push changes to DHCP, DNS, and TFTP configurations.

### Adding Distributions and Profiles

```bash
# Import an OS from an ISO mount point
sudo mount -o loop /path/to/ubuntu-24.04.iso /mnt/iso
sudo cobbler import --name=ubuntu-24.04 --arch=x86_64 --path=/mnt/iso

# Create a kickstart profile
sudo cobbler profile add \
  --name=ubuntu-prod \
  --distro=ubuntu-24.04-x86_64 \
  --kickstart=/var/lib/cobbler/kickstarts/ubuntu-prod.ks

# Define a system with a specific MAC address
sudo cobbler system add \
  --name=web-server-01 \
  --profile=ubuntu-prod \
  --mac=AA:BB:CC:DD:EE:01 \
  --ip-address=192.168.1.101 \
  --hostname=web-01.example.com \
  --gateway=192.168.1.1

# Sync all configurations
sudo cobbler sync
```

### Cobbler Docker Image

For testing Cobbler without a full system install, use the official Docker compose setup:

```bash
# Clone the repo
git clone https://github.com/cobbler/cobbler.git
cd cobbler

# The project provides build-focused compose files.
# For production deployment, install via package manager as shown above.
# Community Docker images are available at:
# docker pull cobbler/cobbler:latest
```

## Tinkerbell

Tinkerbell is the CNCF bare metal provisioning project originally built by Equinix Metal (formerly Packet). Unlike MAAS and Cobbler, Tinkerbell uses a workflow-based approach: you define a sequence of actions (download OS, partition disk, write image, reboot) and execute them on target machines via gRPC.

### When to Choose Tinkerbell

- You want cloud-native, declarative bare metal workflows
- You operate in a Kubernetes-native environment and want bare metal to behave like pods
- You need fine-grained control over the provisioning pipeline
- You manage hardware across multiple data centers or edge locations

### Installing Tinkerbell via Tink CLI

Tinkerbell's core component is `tink`, the workflow engine. The project provides a sandbox for getting started:

```bash
# Install Tink CLI (Go-based, install from GitHub releases)
curl -LO https://github.com/tinkerbell/tink/releases/download/v0.10.0/tink-linux-amd64
chmod +x tink-linux-amd64
sudo mv tink-linux-amd64 /usr/local/bin/tink

# Clone the sandbox for a quick start
git clone https://github.com/tinkerbell/sandbox.git
cd sandbox

# The sandbox uses docker compose to spin up the full stack:
# tink-server, tink-controller, tink-worker, Hegel (metadata service),
# and Hook (the in-memory OS for bootstrapping)
```

### Tinkerbell Workflow Definition

Tinkerbell workflows are defined as YAML templates that specify ordered actions:

```yaml
# workflow-template.yaml
name: "ubuntu-install"
version: "0.1"
tasks:
  - name: "os-installation"
    worker: "{{.device_1}}"
    volumes:
      - /dev:/dev
      - /dev/console:/dev/console
      - /lib/firmware:/lib/firmware:ro
    actions:
      - name: "stream-ubuntu"
        image: ubuntu-bionic-action:${TAG}
        timeout: 600
        environment:
          - DEST_DISK=/dev/sda
          - IMG_URL="http://192.168.1.10/ubuntu-24.04.raw.tar.gz"
          - COMPRESSED=true
      - name: "kexec-reboot"
        image: kexec-action:${TAG}
        timeout: 90
        environment:
          - FS_TYPE=ext4
          - DEST_DISK=/dev/sda1
```

Create and execute the workflow:

```bash
# Create a template
tink template create --name ubuntu-install workflow-template.yaml

# Create a hardware definition (target machine)
cat > hardware.json << 'HWEOF'
{
  "id": "device-01",
  "metadata": {
    "facility": {
      "facility_code": "homelab"
    },
    "instance": {
      "id": "ubuntu-install",
      "storage": {
        "disks": [{ "device": "/dev/sda" }]
      }
    }
  },
  "network": {
    "interfaces": [{
      "dhcp": {
        "mac": "AA:BB:CC:DD:EE:01",
        "ip": { "address": "192.168.1.101" },
        "name_servers": ["1.1.1.1"],
        "time_servers": ["pool.ntp.org"]
      }
    }]
  }
}
HWEOF

tink hardware push --file hardware.json

# Create and run the workflow
TEMPLATE_ID=$(tink template list | grep ubuntu-install | awk '{print $1}')
tink workflow create --template $TEMPLATE_ID --hardware device-01
```

## Comparison: Architecture and Workflow

| Aspect | MAAS | Cobbler | Tinkerbell |
|---|---|---|---|
| **Architecture** | Monolithic (region + rack controllers) | Single-server daemon | Microservices (server, controller, worker) |
| **Scaling** | Add rack controllers for sites | Single-server, scale with sync | Kubernetes-native, scales horizontally |
| **Boot Protocol** | iPXE with dynamic config | PXELINUX/syslinux with templates | iPXE fetching from Hook |
| **Configuration** | Web UI + CLI + REST API | CLI + Web UI + config files | CLI + YAML workflow definitions |
| **Hardware Inventory** | Automatic discovery | Manual system definitions | Hardware JSON definitions |
| **Image Management** | Built-in image store | Import from ISO/mirror | External image URLs |
| **Cloud Integration** | Native OpenStack/K8s | None | CNCF, Equinix Metal |

## Choosing the Right Tool

| Your Situation | Recommended Tool |
|---|---|
| Ubuntu data center with OpenStack/K8s plans | **MAAS** |
| Mixed Linux environment (RHEL, SUSE, Debian) | **Cobbler** |
| Cloud-native stack with Kubernetes everywhere | **Tinkerbell** |
| Quick homelab setup, minimal configuration | **MAAS** (snap install is fastest) |
| Need fine-grained provisioning pipelines | **Tinkerbell** (workflow templates) |
| Long-term stability, minimal change | **Cobbler** (mature since 2008) |
| Integrated power management (IPMI/Redfish) | **MAAS** (built-in support) |

## FAQ

### What is bare metal provisioning?

Bare metal provisioning is the automated process of installing an operating system onto physical (non-virtualized) servers over a network. Instead of booting from USB or DVD, the server performs a PXE network boot, downloads a boot image, and completes an unattended installation configured by the provisioning tool.

### Can MAAS provision non-Ubuntu operating systems?

Yes. While MAAS is optimized for Ubuntu, it supports deploying CentOS, RHEL, Windows Server, and VMware ESXi through custom preseed and cloud-init configurations. However, Ubuntu remains the best-supported OS.

### Does Cobbler support Windows deployment?

Cobbler can deploy Windows via WIM (Windows Imaging Format) images integrated with its PXE boot environment. This requires configuring a Windows answer file (unattend.xml) and setting up the appropriate boot entries in Cobbler's PXE configuration.

### How does Tinkerbell differ from PXE-based tools?

Tinkerbell still uses PXE/iPXE for the initial boot, but instead of traditional kickstart/preseed files, it loads an in-memory OS called Hook and then executes workflow actions defined as YAML. This allows for more complex, multi-stage provisioning pipelines with conditional logic and custom actions.

### Do I need a dedicated server for the provisioning tool?

All three tools can run on a modest server or VM. MAAS requires a dedicated machine for the region controller in production. Cobbler and Tinkerbell can share hardware with other services. For a homelab, any machine with 4GB RAM and two network interfaces works.

### Can these tools manage server power (turn on/off/reboot)?

MAAS has built-in support for IPMI, Redfish, and vendor-specific BMC APIs. Cobbler supports IPMI through its koan client. Tinkerbell delegates power management to the infrastructure layer and does not include native BMC control.

## Related Reading

For post-provisioning automation, check our [Ansible vs SaltStack vs Puppet configuration management guide](../ansible-vs-saltstack-vs-puppet-configuration-management-2026/). If you are deploying Kubernetes on freshly provisioned hardware, the [Rancher vs Kubespray vs Kind management guide](../rancher-vs-kubespray-vs-kind-self-hosted-kubernetes-management-guide-2026/) covers the next step in the pipeline.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "MAAS vs Cobbler vs Tinkerbell: Bare Metal Provisioning Guide 2026",
  "description": "Compare MAAS, Cobbler, and Tinkerbell for self-hosted bare metal server provisioning. Complete guide with deployment configs, PXE setup, and workflow automation.",
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
