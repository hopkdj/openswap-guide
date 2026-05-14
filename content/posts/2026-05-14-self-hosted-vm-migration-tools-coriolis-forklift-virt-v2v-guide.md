---
title: "Self-Hosted VM Migration Tools: Coriolis vs Forklift vs Virt-v2v"
date: "2026-05-14"
tags: ["virtualization", "migration", "kvm", "vmware", "self-hosted"]
draft: false
---

Migrating virtual machines between hypervisors is one of the most challenging infrastructure operations. Whether you are moving away from VMware due to licensing changes, consolidating multiple hypervisor platforms, or building a disaster recovery pipeline, you need tools that can convert VM disk formats, adapt hardware configurations, and preserve operating system bootability — all without data loss.

This guide compares three open-source VM migration tools that support self-hosted, on-premises deployments: **Coriolis**, **Forklift**, and **Virt-v2v** — each with a different approach to the migration challenge.

## Why Self-Hosted VM Migration Tools Matter

Cloud provider migration services (like AWS MGN, Azure Migrate, or VMware HCX) are powerful but come with significant drawbacks for self-hosted environments:

- **Vendor lock-in** — cloud migration tools are designed to move workloads to that specific cloud, not between on-premises hypervisors
- **Data transfer costs** — uploading VM images to the cloud for conversion incurs egress and storage fees
- **Compliance requirements** — many organizations cannot move VM disk images outside their data center
- **Network bandwidth** — large VM images (hundreds of gigabytes) are impractical to transfer over WAN links

Self-hosted migration tools operate entirely within your infrastructure, keeping data local, avoiding vendor lock-in, and giving you full control over the migration timeline and process.

## Coriolis: Cross-Platform Migration as a Service

Coriolis, developed by Cloudbase Solutions, is the most comprehensive open-source VM migration platform available. It supports migration from VMware, Hyper-V, OpenStack, AWS, and Azure to KVM-based destinations, with a full REST API and web interface for orchestration.

### Architecture

Coriolis uses a worker-based architecture where dedicated worker nodes perform the actual disk conversion and data transfer. The central API server manages migration plans, schedules, and orchestration. This distributed design allows parallel migrations across multiple source and destination environments.

Key capabilities:
- **Multi-platform source support** — VMware vSphere, Hyper-V, OpenStack, AWS EC2, Azure VMs
- **Multiple destination targets** — OpenStack Nova, KVM/libvirt, AWS EC2, Azure VMs
- **Live migration** — minimize downtime with incremental disk synchronization
- **REST API** — full automation and integration with CI/CD pipelines
- **Web dashboard** — monitor migration progress, view logs, and manage endpoints
- **Pre/post migration scripts** — run custom commands before and after migration (driver installation, network configuration, licensing)

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  coriolis-api:
    image: cloudbase/coriolis-api:latest
    container_name: coriolis-api
    ports:
      - "7666:7666"
    environment:
      - CORIOLIS_DB_URI=postgresql://coriolis:coriolis-pass@postgres/coriolis
      - CORIOLIS_RABBITMQ_URI=amqp://coriolis:coriolis-pass@rabbitmq
    volumes:
      - ./coriolis-api.conf:/etc/coriolis/coriolis.conf:ro
    depends_on:
      - postgres
      - rabbitmq

  coriolis-worker:
    image: cloudbase/coriolis-worker:latest
    container_name: coriolis-worker
    environment:
      - CORIOLIS_RABBITMQ_URI=amqp://coriolis:coriolis-pass@rabbitmq
      - CORIOLIS_MIGRATION_SSH_USER=migrator
    volumes:
      - ./migration-data:/var/lib/coriolis
    depends_on:
      - rabbitmq

  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: coriolis
      POSTGRES_PASSWORD: coriolis-pass
      POSTGRES_DB: coriolis
    volumes:
      - pg-data:/var/lib/postgresql/data

  rabbitmq:
    image: rabbitmq:3-management
    environment:
      RABBITMQ_DEFAULT_USER: coriolis
      RABBITMQ_DEFAULT_PASS: coriolis-pass

volumes:
  pg-data:
  migration-data:
```

### Migration via Coriolis CLI

```bash
# Install Coriolis CLI
pip install coriolis-cli

# Register source endpoint (VMware vCenter)
coriolis-cli endpoint create vmware-source     --type vmware     --name "vcenter-production"     --connection-info '{
        "host": "vcenter.example.com",
        "port": 443,
        "username": "administrator@vsphere.local",
        "password": "vcenter-pass",
        "allow_untrusted": false
    }'

# Register destination endpoint (KVM/libvirt)
coriolis-cli endpoint create kvm-dest     --type libvirt     --name "kvm-cluster"     --connection-info '{
        "connection": "qemu+ssh://migrator@kvm-host/system",
        "target_storage": "default"
    }'

# List VMs on the source
coriolis-cli endpoint list-instances vcenter-production

# Create and execute migration
coriolis-cli migration create vcenter-production kvm-dest     --instances "vm-uuid-1234"     --name "production-webserver-migration"     --shutdown-instances

# Monitor progress
coriolis-cli migration show production-webserver-migration
```

## Forklift: Kubernetes-Native VM Migration

Forklift, developed by the KubeVirt community, is purpose-built for migrating virtual machines from VMware vSphere and oVirt into Kubernetes clusters running KubeVirt. It provides a web console integrated with the OpenShift Virtualization experience and supports both warm (live) and cold migrations.

### Architecture

Forklift operates as a set of Kubernetes operators that extend the KubeVirt control plane. It discovers VMs from VMware or oVirt, maps them to Kubernetes resources (VirtualMachine objects), and handles the disk import process using Containerized Data Importer (CDI).

Key capabilities:
- **VMware and oVirt sources** — direct integration with vCenter and oVirt APIs
- **KubeVirt destination** — creates native Kubernetes VirtualMachine resources
- **Warm migration** — uses VMware Changed Block Tracking (CBT) for incremental syncs
- **Network and storage mapping** — maps VMware port groups and datastores to Kubernetes NetworkAttachmentDefinitions and StorageClasses
- **Web console** — integrated with OpenShift console for visual migration management
- **Provider inventory** — discovers and catalogs source VMs, networks, and storage

### Deployment (Operator-based)

```bash
# Install Forklift operator
kubectl apply -f https://github.com/kubev2v/forklift/releases/latest/download/operator.yaml

# Create Forklift namespace
kubectl create namespace forklift

# Deploy Forklift controller
kubectl apply -f - <<EOF
apiVersion: forklift.konveyor.io/v1beta1
kind: ForkliftController
metadata:
  name: forklift-controller
  namespace: forklift
spec:
  feature_vmware: true
  feature_ovirt: true
  feature_openstack: false
  feature_container: true
  feature_migration_ui: true
EOF

# Verify deployment
kubectl get pods -n forklift
```

### Provider Configuration

```yaml
# Register VMware vCenter as a source provider
apiVersion: forklift.konveyor.io/v1beta1
kind: Provider
metadata:
  name: vcenter-source
  namespace: forklift
spec:
  type: vmware
  url: https://vcenter.example.com
  secret:
    name: vcenter-credentials
    namespace: forklift
---
apiVersion: v1
kind: Secret
metadata:
  name: vcenter-credentials
  namespace: forklift
type: Opaque
stringData:
  user: administrator@vsphere.local
  password: vcenter-pass
  insecure: "false"
```

### Migration Plan

```yaml
apiVersion: forklift.konveyor.io/v1beta1
kind: Plan
metadata:
  name: vmware-to-kubevirt
  namespace: forklift
spec:
  provider:
    source:
      name: vcenter-source
    destination:
      name: host
  map:
    network:
      name: network-map
    storage:
      name: storage-map
  vms:
    - name: web-server-01
      namespace: vmware
    - name: db-server-01
      namespace: vmware
  targetNamespace: production
```

## Virt-v2v: The Command-Line Conversion Workhorse

Virt-v2v, part of the libguestfs project, is the foundational tool underlying both Coriolis and Forklift. It converts virtual machines from VMware, Xen, KVM, VirtualBox, and OVA/OVF formats to run on KVM. It is a single-purpose command-line tool that focuses on one thing: converting a VM image so it boots on KVM.

### Architecture

Virt-v2v operates on VM disk images (VMDK, VDI, QCOW2, raw). It mounts the guest filesystem using libguestfs, installs appropriate drivers, updates boot configurations, and outputs a KVM-compatible disk image. It does not handle orchestration, scheduling, or network mapping — it is purely a conversion tool.

Key capabilities:
- **Multi-format input** — VMware VMDK (vSphere and Workstation), Xen, VirtualBox VDI, Hyper-V VHDX, OVA/OVF
- **Driver injection** — automatically installs VirtIO drivers for Windows and Linux guests
- **Boot configuration** — updates GRUB, BCD, and fstab for the new hardware environment
- **First-boot scripts** — supports custom scripts that run on the migrated VM's first boot
- **Libguestfs integration** — uses libguestfs for safe, read-only disk inspection and modification
- **Batch conversion** — can process multiple VMs in sequence via shell scripting

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  virt-v2v:
    image: libguestfs/virt-v2v:latest
    container_name: virt-v2v
    privileged: true
    volumes:
      - ./input-vms:/input:ro
      - ./output-vms:/output
      - ./scripts:/scripts:ro
    command: ["--help"]  # Override with actual conversion commands
```

### Converting a VMware VM

```bash
# Convert from VMware vCenter (direct)
virt-v2v     -ic vpx://vcenter.example.com/Datacenter/Cluster     -ip password.txt     -os /output/vms     -oa sparse     "web-server-01"

# Convert from VMDK file
virt-v2v     -i disk /input/vmware-web-server.vmdk     -o libvirt     -os default     -of qcow2     -oa sparse

# Convert with first-boot script
virt-v2v     -i libvirtxml /input/vm-xml.xml     -o libvirt     -os default     --firstboot /scripts/post-migrate.sh     -of qcow2

# Convert OVA file
virt-v2v     -i ova /input/legacy-app.ova     -o glance     --os-version fedora38     -n provider-network
```

### Post-Migration Script Example

```bash
#!/bin/bash
# post-migrate.sh — runs on first boot of migrated VM
set -e

# Install VirtIO drivers if not present
if [ ! -d /sys/bus/virtio ]; then
    echo "VirtIO not detected, installing drivers..."
    apt-get update && apt-get install -y virtio-drivers 2>/dev/null || true
fi

# Update network configuration for new interface names
if [ -f /etc/netplan/01-netcfg.yaml ]; then
    cat > /etc/netplan/01-netcfg.yaml <<NETPLAN
network:
  version: 2
  ethernets:
    ens3:
      dhcp4: true
      dhcp6: true
NETPLAN
    netplan apply
fi

# Remove VMware tools
apt-get purge -y open-vm-tools 2>/dev/null || true
yum remove -y open-vm-tools 2>/dev/null || true

# Regenerate SSH host keys
rm -f /etc/ssh/ssh_host_*
dpkg-reconfigure openssh-server 2>/dev/null || true
ssh-keygen -A

echo "Post-migration configuration complete"
```

## Comparison Table

| Feature | Coriolis | Forklift | Virt-v2v |
|---------|----------|----------|----------|
| **Developer** | Cloudbase Solutions | KubeVirt community | libguestfs / Red Hat |
| **Stars on GitHub** | 125 | 177 | 192 |
| **Last pushed** | Active (2026) | Active (2026) | Active (2026) |
| **Architecture** | API + workers (distributed) | Kubernetes operators | Single CLI tool |
| **Source platforms** | VMware, Hyper-V, OpenStack, AWS, Azure | VMware, oVirt | VMware, Xen, VirtualBox, Hyper-V, OVA |
| **Destination** | KVM, OpenStack, AWS, Azure | KubeVirt/Kubernetes | KVM, OpenStack Glance, libvirt |
| **Live/warm migration** | Yes (incremental sync) | Yes (CBT-based) | No (cold only) |
| **Web interface** | Yes (dashboard) | Yes (OpenShift console) | No (CLI only) |
| **REST API** | Yes (full CRUD) | Yes (Kubernetes API) | No |
| **Network mapping** | Yes (automatic + manual) | Yes (NetworkAttachmentDefinition) | Manual (post-conversion) |
| **Storage mapping** | Yes (automatic + manual) | Yes (StorageClass mapping) | Manual |
| **Windows support** | Yes (VirtIO injection) | Yes (VirtIO injection) | Yes (VirtIO injection) |
| **Orchestration** | Built-in (plans, schedules) | Built-in (Plan CRD) | External (shell scripts) |
| **Best for** | Cross-platform enterprise migrations | VMware to Kubernetes migrations | Individual VM conversions |

## Choosing the Right Migration Tool

For **enterprise migrations across multiple platforms** (VMware to KVM, Hyper-V to OpenStack, etc.), Coriolis offers the most complete feature set. Its worker-based architecture handles parallel migrations, the REST API enables full automation, and the web dashboard provides visibility into complex migration projects with dozens of VMs.

For **VMware to Kubernetes migrations**, Forklift is the purpose-built choice. Its deep integration with KubeVirt means migrated VMs become native Kubernetes resources with all the benefits of the Kubernetes ecosystem — declarative configuration, GitOps workflows, and seamless integration with service meshes and observability stacks.

For **individual VM conversions** or scripting-based migrations, Virt-v2v is the most straightforward option. It has no infrastructure requirements beyond the tool itself, works on a single disk image at a time, and is the underlying engine that powers both Coriolis and Forklift. When you need maximum control over the conversion process and can handle orchestration externally, Virt-v2v is ideal.

## Migration Best Practices

Before migrating any VM, follow this checklist:

1. **Snapshot the source VM** — always have a rollback point
2. **Document the VM configuration** — CPU, memory, network interfaces, attached disks, and special hardware (GPUs, passthrough devices)
3. **Test the conversion on a non-production VM first** — verify the migrated VM boots correctly and applications function
4. **Plan the network mapping** — ensure the destination network provides the same connectivity (VLAN tags, firewall rules, load balancer configuration)
5. **Prepare storage** — pre-provision destination storage with sufficient capacity and appropriate performance tier
6. **Schedule a maintenance window** — even live migrations require a brief cutover period
7. **Validate post-migration** — test application functionality, check logs, and verify network connectivity before decommissioning the source VM


## Why Self-Host VM Migration Tools?

Virtual machine migration is a critical infrastructure capability. Whether you are escaping VMware licensing changes, consolidating multiple hypervisor platforms, or building a disaster recovery pipeline, the ability to move VMs between hypervisors without data loss is essential. Cloud-based migration services introduce risks — data transfer costs, vendor lock-in, compliance violations — that many organizations cannot accept.

Self-hosted migration tools keep your VM disk images within your data center, give you complete control over the migration timeline, and integrate with your existing monitoring and automation stack. The three tools covered in this guide serve different needs: Coriolis for cross-platform enterprise migrations, Forklift for Kubernetes-native virtual machine imports, and Virt-v2v for individual VM conversions with maximum control.

For Kubernetes-native virtualization, see our [KubeVirt vs Harvester vs OpenNebula comparison](../kubevirt-vs-harvester-vs-opennebula-self-hosted-virtualization-platforms-2026/). For container infrastructure that reduces VM dependency, our [rootless container infrastructure guide](../2026-05-10-rootless-container-infrastructure-rootlesskit-fuse-overlayfs-slirp4netns-guide/) covers running workloads without VM overhead. For additional virtualization options, our [Incus vs LXD vs Podman container virtualization guide](../2026-04-24-incus-vs-lxd-vs-podman-self-hosted-container-virtualization-guide-2026/) explores lightweight alternatives to full VM migration.

## FAQ

### What is the difference between cold migration and warm (live) migration?

**Cold migration** shuts down the source VM, copies the disk image, and starts the destination VM. This requires downtime equal to the copy duration plus boot time. **Warm (live) migration** keeps the source VM running while copying the disk in the background, then performs a brief final sync and cutover (typically 1-5 minutes of downtime). Coriolis and Forklift both support warm migration; Virt-v2v only supports cold migration.

### Can these tools migrate running VMs without any downtime?

No tool provides true zero-downtime VM migration across different hypervisor platforms. Even warm migration tools require a brief cutover period to sync the final disk changes and switch network traffic. The downtime is typically 1-5 minutes for well-configured migrations. For true zero-downtime, you need application-level replication (database replication, load-balanced web servers) combined with VM migration.

### What happens to VMware Tools or Hyper-V Integration Services after migration?

Virt-v2v automatically removes VMware Tools from Linux guests and installs VirtIO drivers. For Windows guests, it installs the VirtIO driver package and removes VMware Tools, but you should manually verify the migration and uninstall remaining VMware components from Add/Remove Programs. Coriolis and Forklift handle this automatically through their driver injection pipelines.

### Can I migrate VMs with encrypted disks?

This depends on the encryption method. VMs encrypted with VMware VM Encryption or BitLocker cannot be directly converted by any of these tools — you must decrypt the disk before migration. For LUKS-encrypted Linux VMs, Virt-v2v can handle the conversion if you provide the decryption passphrase via the `--password-file` option. Coriolis supports encrypted VMware VMs if the worker has access to the vCenter Key Management Server.

### How large a VM can these tools migrate?

All three tools can handle VMs with multi-terabyte disks. The practical limit is determined by available storage during the conversion process. Coriolis uses temporary staging storage on worker nodes, Forklift uses Kubernetes PersistentVolumeClaims, and Virt-v2v requires enough disk space for both the source and destination images simultaneously. Plan for at least 2x the VM disk size in available storage during migration.

### Is it safe to migrate domain controllers or database servers?

Yes, but with additional precautions. For **Active Directory domain controllers**, migrate one at a time, verify replication after each migration, and demote the old DC only after confirming the new one is healthy. For **database servers** (MySQL, PostgreSQL, SQL Server), stop the database service before the final sync to ensure data consistency, then start it on the migrated VM. Always test the migrated VM in an isolated network before switching production traffic.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted VM Migration Tools: Coriolis vs Forklift vs Virt-v2v",
  "description": "Self-hosted guide comparing open-source tools for infrastructure management and deployment.",
  "datePublished": "2026-05-14",
  "dateModified": "2026-05-14",
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
