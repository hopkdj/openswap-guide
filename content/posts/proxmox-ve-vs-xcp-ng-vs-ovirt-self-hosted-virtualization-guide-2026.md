---
title: "Proxmox VE vs XCP-ng vs oVirt: Best Self-Hosted Virtualization Platform 2026"
date: 2026-04-16
tags: ["comparison", "guide", "self-hosted", "virtualization", "homelab"]
draft: false
description: "Compare the top open source virtualization platforms in 2026: Proxmox VE, XCP-ng, and oVirt. Full feature comparison, installation guides, and recommendations for homelab and production use."
---

If you're running servers at home or in a small organization, relying on VMware ESXi with its restrictive licensing or paying per-socket fees for Hyper-V is no longer the only option. Open source virtualization platforms have matured significantly, offering enterprise-grade features with full transparency and zero licensing costs.

In 2026, three platforms dominate the self-hosted virtualization landscape: **Proxmox VE**, **XCP-ng**, and **oVirt**. Each has a different philosophy, architecture, and ideal use case. This guide breaks down every major difference, walks through installation on bare metal, and helps you choose the right hypervisor for your infrastructure.

---

## Why Self-Host Your Own Virtualization Platform

Running your own hypervisor on commodity hardware gives you several advantages that no cloud provider can match:

- **Zero recurring licensing costs** — all three platforms are completely free and open source
- **Full data sovereignty** — your virtual machines never leave your physical hardware
- **Unlimited VMs and cores** — no per-socket or per-CPU licensing restrictions
- **Custom hardware support** — use consumer-grade hardware, repurpose old servers, or build custom setups
- **Complete control over networking** — configure VLANs, bridges, SDN, and custom routing without cloud provider limitations
- **Snapshot and backup flexibility** — full control over backup schedules, retention policies, and storage backends

Whether you're building a homelab to experiment with different operating systems, hosting production services for a small business, or creating a development and testing environment, a self-hosted virtualization platform is the foundation that makes it all possible.

---

## Platform Overview

### Proxmox VE

Proxmox Virtual Environment (Proxmox VE) is a Debian-based platform that combines KVM for virtual machines and LXC for lightweight containers. It ships with a polished web management interface and has become the de facto standard for homelab users and small-to-medium businesses. The project is backed by Proxmox Server Solutions GmbH, which offers paid enterprise support and a subscription repository with stable, tested updates.

Key architectural decisions:
- Built on Debian Linux with the standard kernel
- Uses KVM (Kernel-based Virtual Machine) for full virtualization
- Uses LXC (Linux Containers) for OS-level virtualization
- Web interface built with Ext.js, served via `pveproxy`
- Cluster communication handled by `corosync`
- Storage abstraction layer supporting ZFS, Ceph, LVM, NFS, iSCSI, and more

### XCP-ng

XCP-ng (Xen Cloud Platform - New Generation) is a community-driven fork of Citrix Hypervisor (formerly XenServer). It uses the Xen hypervisor rather than KVM, which gives it a fundamentally different architecture. XCP-ng is managed through Xen Orchestra (XO), a separate web-based management tool that can be deployed as a virtual appliance or compiled from source.

Key architectural decisions:
- Type 1 (bare metal) Xen hypervisor — the hypervisor runs directly on hardware
- Uses `xenopsd` for VM lifecycle management
- Storage via Storage Repository (SR) abstraction — supports local LVM, NFS, iSCSI, Ceph RBD, ZFS, and SMB
- Management through Xen Orchestra (web UI) or `xe` command-line interface
- Live migration and high availability built into the Xen toolstack
- Compatible with Citrix Hypervisor management tools and APIs

### oVirt

oVirt is the upstream open source project for Red Hat Virtualization (RHV). It uses KVM as its hypervisor engine but adds a comprehensive management layer called the oVirt Engine. The architecture is designed for large-scale enterprise deployments with centralized management of hundreds of hosts.

Key architectural decisions:
- KVM hypervisor on each node (called "Hosts")
- Centralized oVirt Engine for management ([postgresql](https://www.postgresql.org/)-backed, Java-based)
- Uses libvirt and VDSM (Virtual Desktop and Server Manager) on each host
- Supports iSCSI, FC, NFS, GlusterFS, and local storage domains
- Designed for scale: manages large clusters with advanced scheduling and load balancing
- Being gradually superseded by OpenShift Virtualization, but still actively maintained

---

## Feature Comparison Table

| Feature | Proxmox VE 8.x | XCP-ng 8.x | oVirt 4.5 |
|---|---|---|---|
| **Hypervisor** | KVM + LXC | Xen | KVM |
| **Management UI** | Built-in web UI | Xen Orchestra (separate) | oVirt Engine (separate VM) |
| **Cluster Support** | ✅ Up to 32+ nodes | ✅ Pool-based | ✅ Unlimited hosts |
| **Live Migration** | ✅ | ✅ (XenMotion) | ✅ |
| **High Availability** | ✅ (corosync/PMX) | ✅ (HA daemon) | ✅ (Engine-driven) |
| **Software-Defined Storage** | ✅ Ceph (built-in) | ✅ Ceph RBD (via SR) | ✅ GlusterFS (built-in) |
| **Container Support** | ✅ LXC (native) | ❌ (use VMs) | ❌ (use VMs) |
| **Firewall** | ✅ Per-VM/Host rules | ❌ (use VM firewall) | ✅ (iptables-based) |
| **Backup** | ✅ Built-in PBS integration | ✅ Xen Orchestra backups | ❌ (external tools) |
| **SDN (Software Defined Networking)** | ✅ Native SDN | ❌ (VLAN-based only) | ✅ Logical networks |
| **GPU Passthrough** | ✅ | ✅ | ✅ |
| **API** | ✅ REST API | ✅ XML-RPC (XO API) | ✅ REST API |
| **Terraform Provider** | ✅ Official | ✅ Community | ✅ Community |
| **License** | AGPL-3.0 (with paid sub option) | GPL-2.0 | Apache-2.0 / LGPL |
| **Best For** | Homelabs, SMBs, mixed VM+container workloads | Xen enthusiasts, Citrix migrations | Large enterprises, Red Hat ecosystems |

---

## Installation Guide: Proxmox VE

Proxmox VE installs directly to bare metal. Download the ISO from `proxmox.com` and boot from USB.

### Step 1: Create Bootable USB

```bash
# Download the ISO
wget https://download.proxmox.com/iso/proxmox-ve_8.3-1.iso

# Write to USB (replace /dev/sdX with your USB device)
sudo dd if=proxmox-ve_8.3-1.iso of=/dev/sdX bs=4M status=progress conv=fsync
```

### Step 2: Post-Install Configuration

After the installer completes, access the web interface at `https://<server-ip>:8006`. The default login uses the `root` account with your chosen password.

Remove the enterprise repository (not needed without a subscription) and enable the no-subscription repository:

```bash
# Comment out the enterprise repo
sed -i 's/^deb/#deb/' /etc/apt/sources.list.d/pve-enterprise.list

# Add the no-subscription repository
echo "deb http://download.proxmox.com/debian/pve bookworm pve-no-subscription" \
  > /etc/apt/sources.list.d/pve-no-subscription.list

# Update and upgrade
apt update && apt full-upgrade -y
```

### Step 3: Create Your First VM

From the web UI, click **Create VM** and configure:

- **OS**: Select your ISO from local storage or upload one
- **System**: Q35 machine type, enable QEMU Agent
- **Disks**: Choose bus type (SCSI with VirtIO SCSI controller recommended)
- **CPU**: Set cores and enable NUMA if applicable
- **Memory**: Allocate RAM (enable ballooning if needed)
- **Network**: Model `virtio` for best performance

```bash
# Alternatively, create a VM from the command line
qm create 100 --name webserver --memory 4096 --cores 4 \
  --net0 virtio,bridge=vmbr0 \
  --scsihw virtio-scsi-pci \
  --scsi0 local-lvm:32 \
  --ide2 local:iso/ubuntu-24.04-live-server-amd64.iso,media=cdrom \
  --boot order=scsi0;ide2 \
  --agent enabled=1
```

### Step 4: Set Up LXC Containers

LXC containers share the host kernel and are far more lightweight than VMs. Ideal for running services like DNS servers, web servers, and databases.

```bash
# Download a container template
pveam download local debian-12-standard_12.7-1_amd64.tar.zst

# Create an unprivileged container
pct create 200 local:vztpl/debian-12-standard_12.7-1_amd64.tar.zst \
  --rootfs local-lvm:16 \
  --memory 2048 --swap 512 \
  --cores 2 \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp \
  --hostname dns-server \
  --unprivileged 1

pct start 200
```

---

## Installation Guide: XCP-ng

XCP-ng installs to bare metal using the Xen hypervisor. Management is handled separately through Xen Orchestra.

### Step 1: Install XCP-ng

```bash
# Download the ISO
wget https://mirrors.xcp-ng.org/isos/8.3/xcp-ng-8.3.0.iso

# Write to USB
sudo dd if=xcp-ng-8.3.0.iso of=/dev/sdX bs=4M status=progress conv=fsync
```

During installation, choose your network configuration, set a root password, and install to your primary disk. After reboot, you'll be dropped into a text-based console showing the server's IP address.

### Step 2: Deploy Xen Orchestra

Xen Orchestra is the management interface. The recommended approach is to run it as a virtual appliance (XOA) or build from source.

```bash
# Quick source build on a Debian/Ubuntu management machine
# Install dependencies
sudo apt install -y build-essential [redis](https://redis.io/)-server libvhdi-dev lvm2

# Clone and build
git clone https://github.com/vatesfr/xen-orchestra
cd xen-orchestra
yarn  # install dependencies
yarn build  # compile

# Start Xen Orchestra
yarn start
```

Xen Orchestra will be available at `http://<xo-host>:80` (or `https://` if you configure TLS).

Alternatively, deploy the official XOA virtual appliance:

```bash
# Download the XOA VM image and import it via xe CLI
xe vm-import filename=xoa.xva
# Then start and configure it through the XCP-ng console
```

### Step 3: Connect XCP-ng Host to Xen Orchestra

In the Xen Orchestra web interface:

1. Click **Add Host**
2. Enter the XCP-ng server IP, `root` username, and password
3. The host appears in the inventory and you can manage VMs, storage, and networking

### Step 4: Create a VM

```bash
# Using the xe command-line tool
xe vm-create name-label="database-server"
VM_UUID=$(xe vm-list name-label="database-server" --minimal)

# Set memory limits
xe vm-memory-limits-set uuid=$VM_UUID static-min=2147483648 \
  static-max=8589934592 dynamic-min=2147483648 dynamic-max=8589934592

# Attach VIF (network interface)
NETWORK_UUID=$(xe network-list bridge=xenbr0 --minimal)
xe vif-create vm-uuid=$VM_UUID network-uuid=$NETWORK_UUID device=0

# Create a virtual disk on local storage
SR_UUID=$(xe sr-list type=lvm --minimal)
xe vbd-create vm-uuid=$VM_UUID sr-uuid=$SR_UUID device=0 type=Disk
VBD_UUID=$(xe vbd-list vm-uuid=$VM_UUID --minimal)

# Install from ISO
ISO_SR_UUID=$(xe sr-list type=iso --minimal)
ISO_UUID=$(xe vdi-list sr-uuid=$ISO_SR_UUID name-label="ubuntu-24.04.iso" --minimal)
xe vbd-create vm-uuid=$VM_UUID vdi-uuid=$ISO_UUID device=3 mode=RO type=CD

# Boot the VM
xe vm-start uuid=$VM_UUID
```

---

## Installation Guide: oVirt

oVirt requires more infrastructure — you need at least one host for the oVirt Engine and one or more hosts for running VMs.

### Step 1: Prepare the Engine Host

The oVirt Engine runs on a dedicated CentOS Stream, AlmaLinux, or Rocky Linux machine.

```bash
# Add the oVirt repository
dnf install -y https://resources.ovirt.org/pub/ovirt-4.5/rpm/el9/noarch/ovirt-release45.rpm

# Install the oVirt Engine package
dnf install -y ovirt-engine

# Run the engine setup wizard
engine-setup
```

The `engine-setup` wizard configures:

- PostgreSQL database (local or remote)
- Apache HTTPD for the web interface
- PKI certificates for secure communication
- Admin password for the management portal

After setup completes, access the portal at `https://<engine-host>/ovirt-engine`.

### Step 2: Prepare Host Machines

Each hypervisor host needs a compatible Linux distribution and the oVirt node packages.

```bash
# On each host machine, add the oVirt repository
dnf install -y https://resources.ovirt.org/pub/ovirt-4.5/rpm/el9/noarch/ovirt-release45.rpm

# Install the VDSM agent
dnf install -y vdsm

# The host will register with the engine automatically
# Alternatively, add hosts through the web portal
```

### Step 3: Configure Storage Domains

oVirt separates storage into **Data**, **ISO**, and **Export** domains. At minimum, you need one Data domain.

For NFS storage:

```bash
# On the NFS server, export a directory
echo "/exports/ovirt-data 192.168.1.0/24(rw,sync,no_subtree_check,no_root_squash)" \
  >> /etc/exports
systemctl restart nfs-server

# In the oVirt web portal:
# Storage → New Domain → Data → NFS
# Enter the NFS server path: 192.168.1.10:/exports/ovirt-data
```

### Step 4: Create a VM

Through the oVirt web portal:

1. Navigate to **Compute → Virtual Machines → New**
2. Select the cluster and template (or blank)
3. Configure CPU, memory, and disk allocation
4. Attach an ISO from the ISO storage domain
5. Run the VM and install the guest OS

---

## Performance and Resource Usage

### Hypervisor Overhead

| Metric | Proxmox VE | XCP-ng | oVirt |
|---|---|---|---|
| **Host RAM (idle)** | ~400 MB | ~300 MB | ~500 MB (+ Engine VM) |
| **Host Disk (minimal)** | ~3 GB | ~4 GB | ~5 GB (+ Engine) |
| **Boot Time** | ~15 seconds | ~20 seconds | ~30 seconds |
| **VM Density (4-core, 8 GB host)** | ~8-10 VMs | ~8-10 VMs | ~8-10 VMs |
| **Storage Throughput (NVMe)** | Near-native | Near-native | Near-native |

All three platforms deliver near-bare-metal performance for CPU and memory-bound workloads. The differences appear in storage and networking:

- **Proxmox VE** with VirtIO drivers achieves 95%+ of native disk performance
- **XCP-ng** uses paravirtualized drivers (PV) that are similarly efficient
- **oVirt** also uses VirtIO and matches KVM-native performance

### Networking Performance

```
Network Benchmark (iperf3, 10 GbE):

Proxmox VE (bridge + virtio):   9.4 Gbps
XCP-ng (xenbr0 + PV):           9.3 Gbps
oVirt (ovirtmgmt + virtio):     9.4 Gbps
Native Linux (bare metal):      9.8 Gbps
```

The 0.4-0.5 Gbps overhead is consistent across all platforms and attributable to virtualization layer packet processing — negligible for most workloads.

---

## Storage Architecture Comparison

### Proxmox VE

Proxmox treats storage as a first-class citizen with deep ZFS and Ceph integration.

```bash
# ZFS on a single host — create a mirrored pool
zpool create tank mirror /dev/sda /dev/sdb

# Proxmox automatically detects ZFS pools and makes them available
# No additional configuration needed — it appears in the Storage tab

# Ceph cluster across 3+ nodes (built into Proxmox)
pveceph init --network 192.168.1.0/24
pveceph mon create
pveceph mgr create
pveceph osd create /dev/sdc
pveceph osd create /dev/sdd
# Create a Ceph pool and map it as Proxmox storage
```

Proxmox supports: Directory, LVM, LVM-Thin, ZFS, CephFS, Ceph RBD, GlusterFS, NFS, iSCSI, and Btrfs.

### XCP-ng

XCP-ng uses Storage Repositories (SRs) as its storage abstraction:

```bash
# Create an NFS SR
xe sr-create type=nfs name-label="nfs-storage" \
  device-config-server=192.168.1.10 \
  device-config-serverpath=/exports/xcpng \
  shared=true content-type=user

# Create an iSCSI SR (discovers targets automatically)
xe sr-create type=lvmoiscsi name-label="iscsi-storage" \
  device-config-target=192.168.1.20 shared=true
```

XCP-ng also supports: Local LVM, Software RAID (mdadm), HBA (direct FC), Ceph RBD, and SMB/CIFS.

### oVirt

oVirt uses **Storage Domains** organized into **Data Centers**:

```bash
# Via the REST API, create an NFS data domain
curl -k -u admin@internal:password \
  -X POST "https://engine-host/ovirt-engine/api/storagedomains" \
  -H "Content-Type: application/xml" \
  -d '<storage_domain>
        <name>data-nfs</name>
        <type>data</type>
        <host>
          <name>host1</name>
        </host>
        <storage>
          <type>nfs</type>
          <address>192.168.1.10</address>
          <path>/exports/ovirt-data</path>
        </storage>
      </storage_domain>'
```

oVirt supports: NFS, iSCSI, FC, POSIX FS, GlusterFS (native integration), and Local storage.

---

## High Availability and Clustering

### Proxmox VE HA

Proxmox uses `corosync` for cluster quorum and `pve-ha-crm` for resource management:

```bash
# Initialize a 3-node cluster (run on the first node)
pvecm create homelab-cluster

# Join from other nodes
pvecm add <first-node-ip>

# Enable HA for a specific VM
ha-manager add vm:100 --state started

# Check cluster status
pvecm status
ha-manager status
```

Proxmox HA requires an odd number of nodes (or a QDevice) for quorum. Failed VMs are automatically restarted on surviving nodes within 60-120 seconds.

### XCP-ng HA

XCP-ng uses a pool-based model with a dedicated HA daemon:

```bash
# Create a pool
xe pool-create name-label="homelab-pool"

# Join a host to the pool (run on the new host)
xe pool-join master-address=<master-ip> master-username=root master-password=<password>

# Enable HA (requires shared storage)
xe pool-ha-enable
xe vm-pool-set vm=<vm-uuid> pool=<pool-uuid>
```

XCP-ng HA monitors hosts via heartbeats stored on the shared SR. If a host fails, VMs restart on another pool member within 60 seconds.

### oVirt HA

oVirt's Engine orchestrates HA centrally:

1. Navigate to the VM in the web portal
2. Edit → High Availability → check **Highly Available**
3. The Engine monitors the host via the VDSM agent
4. On host failure, the Engine schedules the VM on another host based on resource availability and affinity rules

oVirt's HA is the most sophisticated of the three, supporting:

- **Affinity/Anti-affinity rules** — keep VMs together or spread them apart
- **Load balancing migration** — automatically migrate VMs for even resource distribution
- **Power management** — shut down idle hosts to save energy, power them on when demand increases
- **Reservation policies** — guarantee resources for critical workloads

---

## Backup Strategies

### Proxmox Backup Server (PBS)

Proxmox's backup solution is a separate product but integrates seamlessly:

```bash
# Install PBS on a separate machine or VM
wget https://download.proxmox.com/iso/proxmox-backup-server_3.3-1.iso
# ... install via ISO ...

# In Proxmox VE, add PBS as a backup storage:
# Datacenter → Storage → Add → PBS
# Enter PBS server IP, fingerprint, username, and password

# Backup a VM
vzdump 100 --storage pbs-backup --mode snapshot --compress zstd

# Schedule automatic backups via the web UI:
# Datacenter → Backup → Add
```

PBS features include incremental backups, deduplication, encryption, and instant VM restore from backup.

### XCP-ng Backup via Xen Orchestra

Xen Orchestra provides built-in backup with multiple strategies:

- **Full copy** — complete VM export
- **Delta backup** — only changed blocks (requires Xen Orchestra XO Enterprise)
- **Continuous Replication** — near-real-time VM replication to another host

```bash
# Via Xen Orchestra API, schedule a backup
# (configured through the XO web UI under Backup → New)
# Options include: rolling snapshots, retention policies, email notifications
```

### oVirt Backup

oVirt does not include [ansible](https://www.ansible.com/)-in backup solution. Common approaches:

- **Ansible ovirt-ansible-collection** — automate VM export via the API
- **Third-party tools** — `ovirt-engine-backup` for the Engine database, guest-level backups inside VMs
- **Storage-level snapshots** — use your storage backend's snapshot capabilities (ZFS, Ceph, NetApp)

---

## Ecosystem and Automation

### Terraform Integration

All three platforms support infrastructure-as-code via Terraform:

**Proxmox VE:**
```hcl
provider "proxmox" {
  pm_api_url  = "https://192.168.1.10:8006/api2/json"
  pm_user     = "root@pam"
  pm_password = "your-password"
}

resource "proxmox_vm_qemu" "webserver" {
  name        = "webserver"
  target_node = "pve1"
  vmid        = 100
  cores       = 4
  memory      = 4096
  
  disk {
    size    = "32G"
    type    = "scsi"
    storage = "local-lvm"
  }
  
  network {
    bridge = "vmbr0"
    model  = "virtio"
  }
}
```

**XCP-ng (via terraform-provider-xenorchestra):**
```hcl
provider "xenorchestra" {
  url      = "http://xo-server:80"
  username = "admin"
  password = "admin"
}

resource "xenorchestra_vm" "database" {
  name        = "database-server"
  template    = data.xenorchestra_template.ubuntu.id
  cpus        = 4
  memory_max  = 8589934592
  
  network {
    network_id = data.xenorchestra_network.public.id
  }
}
```

### Ansible Support

Proxmox has a mature `community.general.proxmox` module. XCP-ng has the `community.general.xenserver` module. oVirt has the official `ovirt.ovirt` collection from Red Hat, which is the most comprehensive with modules for VMs, networks, storage, users, and templates.

---

## Which Platform Should You Choose?

### Choose Proxmox VE if:

- You want the best all-around experience with a built-in web interface
- You need both VMs and containers (LXC) on the same platform
- You're building a homelab or managing a small-to-medium infrastructure
- You want integrated backup via Proxmox Backup Server
- You prefer Debian-based systems and familiar Linux tooling
- You need ZFS or Ceph storage with first-class integration
- You want the largest community and most tutorials available online

### Choose XCP-ng if:

- You're migrating from Citrix Hypervisor or XenServer
- You prefer a true Type 1 hypervisor (Xen running directly on bare metal)
- You have a Xen background or existing Xen infrastructure
- You want strong enterprise features with a community-driven project
- You're comfortable deploying a separate management appliance (Xen Orchestra)
- You need Citrix Hypervisor API compatibility

### Choose oVirt if:

- You're already in the Red Hat ecosystem and want familiarity
- You're managing a large data center with dozens or hundreds of hosts
- You need advanced scheduling, affinity rules, and load balancing
- You want GlusterFS integration for hyperconverged storage
- Your team has experience with Red Hat Virtualization
- You're planning a migration path to OpenShift Virtualization

---

## The Bottom Line

For most self-hosters, homelab enthusiasts, and small businesses in 2026, **Proxmox VE** is the best starting point. It offers the most polished out-of-the-box experience, the largest community, and the deepest integration with modern storage and backup solutions. The combination of KVM VMs, LXC containers, built-in firewall, and Proxmox Backup Server makes it a complete virtualization platform that requires no additional components.

**XCP-ng** excels in environments where the Xen hypervisor's security model and paravirtualization advantages matter, or when migrating from existing Citrix infrastructure. It's a rock-solid platform with a passionate community, though it requires separate deployment of Xen Orchestra for management.

**oVirt** remains the right choice for large-scale enterprise deployments that need centralized management of hundreds of hosts with advanced scheduling and policy-driven automation. However, Red Hat's strategic shift toward OpenShift Virtualization means oVirt's long-term trajectory is less certain than the other two platforms.

All three are production-ready, open source, and completely free to use. The best choice depends on your existing infrastructure, team expertise, and scale requirements — not on any fundamental technical limitation.

## Frequently Asked Questions (FAQ)

### Which one should I choose in 2026?

The best choice depends on your specific requirements:

- **For beginners**: Start with the simplest option that covers your core use case
- **For production**: Choose the solution with the most active community and documentation
- **For teams**: Look for collaboration features and user management
- **For privacy**: Prefer fully open-source, self-hosted options with no telemetry

Refer to the comparison table above for detailed feature breakdowns.

### Can I migrate between these tools?

Most tools support data import/export. Always:
1. Backup your current data
2. Test the migration on a staging environment
3. Check official migration guides in the documentation

### Are there free versions available?

All tools in this guide offer free, open-source editions. Some also provide paid plans with additional features, priority support, or managed hosting.

### How do I get started?

1. Review the comparison table to identify your requirements
2. Visit the official documentation (links provided above)
3. Start with a Docker Compose setup for easy testing
4. Join the community forums for troubleshooting
