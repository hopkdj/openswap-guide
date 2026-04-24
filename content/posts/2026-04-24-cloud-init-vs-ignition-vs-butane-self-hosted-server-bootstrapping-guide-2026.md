---
title: "Cloud-Init vs Ignition vs Butane: Self-Hosted Server Bootstrapping Guide 2026"
date: 2026-04-24
tags: ["comparison", "guide", "self-hosted", "infrastructure", "cloud-init", "ignition"]
draft: false
description: "Compare cloud-init, Ignition, and Butane for self-hosted server bootstrapping and first-boot configuration. Complete guide with cloud-config examples, Ignition specs, and deployment automation."
---

When you spin up a new virtual machine or bare metal server, the first boot is the most critical moment in its lifecycle. The operating system needs users, SSH keys, network configuration, storage mounts, and service definitions before it can do anything useful. Doing all of this manually does not scale past a handful of machines. **Server bootstrapping tools** solve this problem by automating the entire first-boot configuration process.

In this guide, we compare the three most widely used server initialization systems — **cloud-init**, **Ignition**, and **Butane** — and walk through configuring each one for self-hosted infrastructure.

| Feature | cloud-init | Ignition | Butane |
|---|---|---|---|
| **Developer** | Canonical | Red Hat / CoreOS | Red Hat / CoreOS |
| **Language** | Python | Go | Go |
| **GitHub Stars** | 3,663 | 949 | 317 |
| **Last Updated** | Apr 2026 | Apr 2026 | Apr 2026 |
| **License** | GPL-3.0 / Apache-2.0 | Apache-2.0 | Apache-2.0 |
| **Config Format** | YAML (cloud-config), JSON, scripts | JSON (Ignition spec) | YAML (Butane config) |
| **Config Delivery** | Metadata service, config drive, NoCloud | HTTP URL, embedded in ISO | Compiled to Ignition JSON |
| **Execution Timing** | Every boot (configurable stages) | First boot only | N/A (compiles to Ignition) |
| **Disk Partitioning** | Limited (cc-growpart) | Full (ignition-dracut) | Via Ignition output |
| **Filesystem Creation** | mount + fs_setup modules | storage.filesystem | Via Ignition output |
| **Systemd Unit Management** | Yes (write_files + runcmd) | Yes (systemd units) | Via Ignition output |
| **Best For** | Multi-cloud, Ubuntu/Debian | Fedora CoreOS, Flatcar, RHCOS | Human-friendly Ignition configs |

## Why Self-Hosted Server Bootstrapping Matters

Whether you manage a homelab, a private cloud, or a colocation rack, provisioning new servers by hand introduces several problems:

- **Inconsistency** — manual setup leads to configuration drift between machines
- **Time waste** — installing packages, creating users, and configuring services takes 30+ minutes per server
- **Error-prone** — typos in config files, missed steps, forgotten security hardening
- **No audit trail** — no record of what changed on each machine

Server bootstrapping tools address these issues by treating first-boot configuration as code. You define the desired state in a config file, the tool runs at boot time, and every machine comes up identically. This is the foundation of **immutable infrastructure** — servers are never patched in place, they are replaced with freshly bootstrapped instances.

For related reading on server provisioning, see our [MAAS vs Cobbler vs Tinkerbell bare metal provisioning guide](../maas-vs-cobbler-vs-tinkerbell-bare-metal-provisioning-guide-2026/) for the physical layer, and the [Ansible vs SaltStack vs Puppet configuration management comparison](../ansible-vs-saltstack-vs-puppet-configuration-management-2026/) for ongoing post-bootstrap configuration.

## Cloud-Init: The Industry Standard

Cloud-init is the most widely adopted server initialization tool, pre-installed in virtually every major cloud image (Ubuntu, Debian, CentOS, Fedora, Arch Linux, and more). It was originally developed by Canonical for Ubuntu cloud images and has since become the de facto standard across cloud providers.

### How Cloud-Init Works

Cloud-init runs in stages during the boot process:

1. **Local stage** — detects the data source (metadata service, config drive, or NoCloud)
2. **Network stage** — fetches metadata and user data from the data source
3. **Config stage** — applies the configuration (users, packages, write_files)
4. **Final stage** — runs user scripts and cloud-final services

The most common configuration format is **cloud-config**, a YAML-based syntax processed by the `cloud-config` module.

### Cloud-Config Example

```yaml
#cloud-config
hostname: web-server-01
manage_etc_hosts: true

users:
  - name: admin
    ssh_authorized_keys:
      - ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA... admin@infra
    sudo: ALL=(ALL) NOPASSWD:ALL
    shell: /bin/bash

package_update: true
package_upgrade: true
packages:
  - nginx
  - fail2ban
  - ufw

write_files:
  - path: /etc/nginx/sites-available/default
    content: |
      server {
          listen 80;
          server_name _;
          location / {
              proxy_pass http://127.0.0.1:8080;
          }
      }
    owner: root:root
    permissions: '0644'

runcmd:
  - systemctl enable nginx
  - systemctl start nginx
  - ufw allow 22/tcp
  - ufw allow 80/tcp
  - ufw --force enable

power_state:
  mode: reboot
  condition: true
```

### NoCloud Data Source for Self-Hosted Use

For self-hosted environments without a cloud provider's metadata service, the **NoCloud** data source is the simplest option. It reads configuration from a local `seed.iso` image or a mounted `/dev/sr0` device:

```bash
# Create a seed directory with meta-data and user-data
mkdir -p seed/
cat > seed/meta-data << 'METAEOF'
instance-id: web-server-01
local-hostname: web-server-01
METAEOF

cp my-cloud-config.yaml seed/user-data

# Generate the seed ISO
genisoimage -output seed.iso -volid cidata -joliet -rock seed/

# Attach seed.iso to your VM (qemu/kvm example)
qemu-system-x86_64 \
  -drive file=ubuntu-cloud.img,format=qcow2 \
  -cdrom seed.iso \
  -m 2048 -nographic
```

### Cloud-Init with LXD/Proxmox

Both LXD and Proxmox support cloud-init natively:

```bash
# LXD: pass cloud-config via profile
lxc launch ubuntu:22.04 web01 --config user.user-data="$(cat cloud-config.yaml)"

# Proxmox: use the cloud-init drive
qm create 100 --name web01 --memory 2048 \
  --ide2 local:cloudinit,format=qcow2 \
  --ciuser admin --cipassword "$(openssl passwd -6 mypassword)" \
  --ipconfig0 gw=192.168.1.1,ip=192.168.1.10/24
```

## Ignition: Immutable Infrastructure Specialist

Ignition is the first-boot configuration system developed by the CoreOS team (now part of Red Hat). It is the standard initialization tool for **Fedora CoreOS**, **Flatcar Linux**, and **Red Hat CoreOS** (the base of OpenShift). Unlike cloud-init, Ignition runs only once — on the very first boot — and its design philosophy is tightly coupled with **immutable, container-focused** operating systems.

### How Ignition Works

Ignition reads a JSON configuration file (following the **Ignition specification v3.x**) from a URL, disk partition, or embedded data. It then:

1. **Partitions disks** — creates GUID partition tables, RAID arrays, and LVM volumes
2. **Creates filesystems** — formats ext4, xfs, btrfs, or swap partitions
3. **Writes files** — creates configuration files with specific owners and permissions
4. **Creates systemd units** — enables and starts services
5. **Configures users** — adds SSH keys, passwords, and groups

Because Ignition runs in the initramfs stage (via dracut), it can modify the filesystem before the root filesystem is even mounted. This makes it far more powerful than cloud-init for disk-level operations.

### Ignition Configuration Example

```json
{
  "ignition": {
    "version": "3.4.0"
  },
  "passwd": {
    "users": [
      {
        "name": "admin",
        "sshAuthorizedKeys": [
          "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA... admin@infra"
        ],
        "groups": ["sudo", "docker"]
      }
    ]
  },
  "storage": {
    "files": [
      {
        "path": "/etc/nginx/nginx.conf",
        "mode": 420,
        "user": { "name": "root" },
        "group": { "name": "root" },
        "contents": {
          "source": "data:text/plain;charset=utf-8;base64,..."
        }
      }
    ],
    "filesystems": [
      {
        "path": "/var/data",
        "device": "/dev/disk/by-label/DATA",
        "format": "ext4",
        "wipeFilesystem": true
      }
    ]
  },
  "systemd": {
    "units": [
      {
        "name": "nginx.service",
        "enabled": true,
        "contents": "[Unit]\nDescription=NGINX Web Server\n\n[Service]\nExecStart=/usr/sbin/nginx -g 'daemon off;'\n\n[Install]\nWantedBy=multi-user.target"
      }
    ]
  }
}
```

### Running Ignition on Non-CoreOS Distributions

Ignition can run on any Linux distribution that uses dracut. To enable it on a Debian or Ubuntu-based system:

```bash
# Install ignition-dracut from source
git clone https://github.com/coreos/ignition-dracut.git
cd ignition-dracut
make install

# Add ignition to the initramfs
echo 'add_dracutmodules+=" ignition "' >> /etc/dracut.conf.d/ignition.conf
dracut --force

# Reboot with the ignition.config.url kernel parameter
# Add to GRUB_CMDLINE_LINUX in /etc/default/grub:
# ignition.config.url=http://192.168.1.10/configs/web01.json
update-grub
reboot
```

### Ignition with Fedora CoreOS (Docker Compose Setup)

For self-hosted environments, you can serve Ignition configs from a simple HTTP server. Here is a Docker Compose setup that runs an Nginx-based config server:

```yaml
version: "3.8"
services:
  ignition-config-server:
    image: nginx:alpine
    ports:
      - "8080:80"
    volumes:
      - ./ignition-configs:/usr/share/nginx/html:ro
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
    restart: unless-stopped

  # Optional: config change monitoring
  config-watcher:
    image: alpine:latest
    command: >
      sh -c "while true; do
        inotifywait -r -e modify /configs &&
        echo 'Config updated at $(date)' >> /var/log/changes.log;
        sleep 1;
      done"
    volumes:
      - ./ignition-configs:/configs
    restart: unless-stopped
```

## Butane: Human-Friendly Ignition Configuration

Butane is not a standalone initialization system — it is a **config compiler** that translates human-readable YAML configurations into valid Ignition JSON. It was created because writing Ignition configs by hand is tedious: the JSON format requires base64 encoding for file contents, explicit permission integers, and verbose structure.

### Butane Configuration Example

Here is the same configuration as the Ignition example above, but written in Butane's YAML syntax:

```yaml
variant: fcos
version: 1.5.0

passwd:
  users:
    - name: admin
      ssh_authorized_keys:
        - ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA... admin@infra
      groups:
        - sudo
        - docker

storage:
  files:
    - path: /etc/nginx/nginx.conf
      mode: 0644
      contents:
        inline: |
          worker_processes auto;
          events { worker_connections 1024; }
          http {
              server {
                  listen 80;
                  location / {
                      proxy_pass http://127.0.0.1:8080;
                  }
              }
          }

  filesystems:
    - path: /var/data
      device: /dev/disk/by-label/DATA
      format: ext4
      wipe_filesystem: true

systemd:
  units:
    - name: nginx.service
      enabled: true
      contents: |
        [Unit]
        Description=NGINX Web Server

        [Service]
        ExecStart=/usr/sbin/nginx -g 'daemon off;'

        [Install]
        WantedBy=multi-user.target
```

### Compiling Butane to Ignition

```bash
# Install butane (from Fedora repos or GitHub releases)
# On Fedora: dnf install -y butane
# Or download from GitHub:
curl -LO https://github.com/coreos/butane/releases/download/v0.20.0/butane-x86_64-linux
chmod +x butane-x86_64-linux
sudo mv butane-x86_64-linux /usr/local/bin/butane

# Compile Butane config to Ignition JSON
butane web-server.yaml --output web-server.ign

# Verify the output
cat web-server.ign | python3 -m json.tool | head -20

# Pass the Ignition config to a CoreOS VM
# Via QEMU:
qemu-system-x86_64 \
  -m 2048 \
  -fw_cfg name=opt/com.coreos/config,file=web-server.ign \
  -drive file=fedora-coreos.qcow2,format=qcow2
```

### Butane Configuration Variants

Butane supports different variants for different operating systems:

| Variant | Version | Target OS |
|---|---|---|
| `fcos` | 1.5.0 | Fedora CoreOS |
| `openshift` | 4.17.0 | Red Hat CoreOS (OpenShift) |
| `flatcar` | 1.1.0 | Flatcar Linux |

```yaml
# Flatcar Linux variant example
variant: flatcar
version: 1.1.0

passwd:
  users:
    - name: deploy
      ssh_authorized_keys:
        - ssh-ed25519 AAAA... deploy@infra

storage:
  files:
    - path: /etc/motd
      mode: 0644
      contents:
        inline: "Flatcar Linux - Production Node\n"
```

## Choosing the Right Tool

The decision depends on your operating system and infrastructure model:

| Scenario | Recommended Tool | Reason |
|---|---|---|
| Multi-cloud, Ubuntu/Debian VMs | cloud-init | Universal support, pre-installed everywhere |
| Fedora CoreOS / Flatcar Linux | Ignition + Butane | Native integration, first-boot immutability |
| OpenShift / RHCOS clusters | Ignition + Butane | Required by the platform |
| Homelab with mixed OSes | cloud-init | Works on virtually any Linux distro |
| Self-hosted with config drive | cloud-init (NoCloud) | Simple ISO-based config delivery |
| Need disk partitioning at boot | Ignition | Only tool that runs in initramfs |
| Writing configs by hand | Butane | YAML is much easier than raw JSON |
| CI/CD server provisioning | cloud-init + Terraform | Widely supported by Terraform providers |

### Combining Cloud-Init and Ansible

For many self-hosted setups, the best approach is a **two-stage bootstrapping** strategy:

1. **Cloud-init** handles first-boot basics: users, SSH keys, network, packages
2. **Ansible** handles ongoing configuration management: service configs, monitoring, security hardening

```yaml
#cloud-config (stage 1: bootstrapping)
package_upgrade: true
packages:
  - python3
  - python3-pip
  - git

runcmd:
  - pip3 install ansible
  - git clone https://git.example.com/infra-config.git /opt/infra
  - cd /opt/infra && ansible-playbook site.yml

# ansible-playbook (stage 2: configuration management)
# - name: Configure Nginx
#   template:
#     src: nginx.conf.j2
#     dest: /etc/nginx/nginx.conf
#   notify: restart nginx
```

For a deeper dive into configuration management tools, check our [Ansible vs SaltStack vs Puppet guide](../ansible-vs-saltstack-vs-puppet-configuration-management-2026/) and the [Terraform PR automation comparison with Atlantis vs Digger vs Terrateam](../atlantis-vs-digger-vs-terrateam-self-hosted-terraform-pr-automation-2026/).

## FAQ

### What is the difference between cloud-init and Ignition?

Cloud-init runs at every boot (configurable) and focuses on user creation, package installation, and script execution. Ignition runs only on the first boot, executes in the initramfs stage before the root filesystem mounts, and can partition disks, create filesystems, and write files at a lower level. Cloud-init uses YAML cloud-config; Ignition uses JSON specification v3.x.

### Can I use cloud-init on Fedora CoreOS?

Fedora CoreOS does not include cloud-init by default — it uses Ignition as its sole initialization system. If you need cloud-init features on CoreOS, the recommended approach is to write a Butane config that achieves the same result, or use Fedora Cloud (not CoreOS) which does include cloud-init.

### What data sources does cloud-init support?

Cloud-init supports many data sources including: AWS EC2 metadata, GCE metadata, Azure IMDS, OpenStack ConfigDrive, LXD, NoCloud (local ISO or FAT filesystem), VMware Guestinfo, DigitalOcean, and VMware. For self-hosted use, **NoCloud** and **ConfigDrive** are the most practical options.

### Is Ignition compatible with Kubernetes?

Ignition is the foundation of Fedora CoreOS and Red Hat CoreOS, which are the recommended operating systems for OpenShift (Red Hat's Kubernetes distribution). Each node in an OpenShift cluster is bootstrapped via Ignition, and the Machine Config Operator manages ongoing node configuration through updated Ignition configs.

### How do I debug cloud-init failures?

Check the following logs on a cloud-init enabled system:
- `/var/log/cloud-init.log` — full debug log
- `/var/log/cloud-init-output.log` — stdout/stderr from user scripts
- `cloud-init status --long` — shows current status and errors
- `journalctl -u cloud-init-local` — systemd journal for local stage
- `journalctl -u cloud-config` — systemd journal for config stage

### Can Butane generate configs for non-CoreOS distributions?

Butane generates standard Ignition v3.x JSON, which can be used on any Linux distribution with `ignition-dracut` installed. However, the `fcos`, `openshift`, and `flatcar` variants are optimized for their respective target OSes. For generic Linux, you may need to use `ignition-dracut` directly and pass a manual Ignition config.

### What happens if Ignition fails during first boot?

Ignition fails fast — if any critical step fails (e.g., a disk partition cannot be created, a file cannot be written), the boot process halts and the system drops to an emergency shell. This is by design: an improperly configured immutable system is worse than a non-booting one. You can inspect the failure in the journal (`journalctl -u ignition`) and fix the config.

### How do I pass cloud-config to a Proxmox VM?

Proxmox has built-in cloud-init support. You can configure it via the GUI (Cloud-Init tab on each VM) or via CLI:
```bash
qm set 100 --ciuser admin --cipassword 'hashedpassword' \
  --ipconfig0 gw=192.168.1.1,ip=192.168.1.10/24 \
  --nameserver 192.168.1.1 --searchdomain example.com \
  --sshkeys "$(cat ~/.ssh/id_ed25519.pub)"
```

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Cloud-Init vs Ignition vs Butane: Self-Hosted Server Bootstrapping Guide 2026",
  "description": "Compare cloud-init, Ignition, and Butane for self-hosted server bootstrapping and first-boot configuration. Complete guide with cloud-config examples, Ignition specs, and deployment automation.",
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
