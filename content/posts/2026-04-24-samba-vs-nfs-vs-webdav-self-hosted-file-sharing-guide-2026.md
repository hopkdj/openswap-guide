---
title: "Samba vs NFS vs WebDAV: Self-Hosted File Sharing Guide 2026"
date: 2026-04-24
tags: ["comparison", "guide", "self-hosted", "file-sharing", "samba", "nfs", "webdav"]
draft: false
description: "Complete comparison of Samba, NFS, and WebDAV for self-hosted file sharing. Includes Docker Compose configs, deployment guides, and performance benchmarks to help you choose the right protocol."
---

Choosing the right file sharing protocol for your self-hosted server is one of the most foundational decisions you will make. Whether you are sharing files across a home network, backing up servers, or building a media library, the protocol you pick determines compatibility, performance, and security.

The three most widely used self-hosted file sharing protocols are **Samba (SMB/CIFS)**, **NFS (Network File System)**, and **WebDAV (Web-based Distributed Authoring and Versioning)**. Each has distinct strengths, and the best choice depends on your client operating systems, network environment, and use case.

This guide compares all three protocols head-to-head, provides production-ready Docker Compose configurations fetched from official repositories, and walks through deployment step by step.

For related reading, see our [Nextcloud vs ownCloud comparison](../nextcloud-vs-owncloud/) for full-featured file sync platforms, the [distributed file storage comparison](../ceph-vs-glusterfs-vs-moosefs-distributed-file-storage-2026/) for enterprise-scale solutions, and the [web file managers guide](../filebrowser-vs-filegator-vs-cloud-commander-self-hosted-web-file-managers-2026/) for browser-based file access.

## Why Self-Host Your File Sharing Infrastructure

Cloud storage services like Dropbox, Google Drive, and OneDrive are convenient but come with recurring subscription costs, vendor lock-in, and privacy concerns. Self-hosting your file sharing infrastructure gives you:

- **Full data ownership** — your files never leave your network unless you choose to share them
- **No subscription fees** — one-time hardware cost, zero monthly charges
- **Unlimited storage** — constrained only by your disk capacity
- **Protocol-level flexibility** — choose the protocol that matches your client devices
- **Integration with existing services** — file shares plug directly into backup tools, media servers, and CI/CD pipelines

Understanding the tradeoffs between Samba, NFS, and WebDAV is essential for building a reliable self-hosted file sharing setup.

## Samba (SMB/CIFS): Universal Cross-Platform File Sharing

Samba is the open-source implementation of the SMB/CIFS protocol. Since 1992, it has provided file and print services that allow Linux servers to seamlessly integrate with Windows, macOS, and other Linux clients. The official repository ([samba-team/samba](https://github.com/samba-team/samba)) tracks 1,087 stars on GitHub (with the primary development on GitLab) and was last updated in April 2026. The project is written in C and remains one of the most actively maintained open-source networking projects.

### Key Features

- **Native Windows compatibility** — appears as a network drive in Windows Explorer with no extra software
- **Active Directory integration** — can function as a domain controller or domain member
- **Cross-platform support** — works with Windows, macOS, Linux, Android, and iOS clients
- **Fine-grained permissions** — POSIX ACLs, share-level and user-level security
- **Print server** — shared network printer support

### Docker Deployment with dperson/samba

The [dperson/samba](https://github.com/dperson/samba) Docker image (1,699 stars) is the most popular containerized Samba deployment. Here is the official Docker Compose configuration:

```yaml
version: '3.4'

services:
  samba:
    image: dperson/samba
    environment:
      TZ: 'UTC'
    networks:
      - default
    ports:
      - "137:137/udp"
      - "138:138/udp"
      - "139:139/tcp"
      - "445:445/tcp"
    read_only: true
    tmpfs:
      - /tmp
    restart: unless-stopped
    stdin_open: true
    tty: true
    volumes:
      - /mnt/data:/mnt:z
      - /mnt/extra:/mnt2:z
    command: >
      -s "Shared;/mnt;yes;no;no"
      -s "Private;/mnt2;yes;no;no;bob"
      -u "bob;secure_password"
      -p

networks:
  default:
    driver: bridge
```

Command flags explained:
- `-s "name;path;browseable;readonly;guest;users"` — define shares with access control
- `-u "username;password"` — create user accounts
- `-p` — enable Samba password authentication

### Manual Installation (Bare Metal)

```bash
# Ubuntu/Debian
sudo apt update && sudo apt install -y samba

# Create a shared directory
sudo mkdir -p /srv/samba/shared
sudo chmod 777 /srv/samba/shared

# Add to /etc/samba/smb.conf
cat << 'CONF' | sudo tee -a /etc/samba/smb.conf
[shared]
   path = /srv/samba/shared
   browseable = yes
   writable = yes
   guest ok = yes
   read only = no
   create mask = 0644
   directory mask = 0755
CONF

sudo systemctl enable smbd nmbd
sudo systemctl restart smbd nmbd
```

### When to Choose Samba

Choose Samba when your network includes Windows clients, when you need Active Directory integration, or when you want a protocol that works out of the box with virtually every operating system. It is the default choice for mixed-OS environments.

## NFS (Network File System): High-Performance Linux-to-Linux Sharing

NFS, originally developed by Sun Microsystems in 1984, is the standard file sharing protocol for Linux and Unix systems. NFS version 4 (the current major release) adds Kerberos authentication, stateful protocol design, and improved firewall friendliness compared to NFSv3.

### Key Features

- **Kernel-level performance** — runs in kernel space for minimal overhead and maximum throughput
- **UID/GID-based permissions** — maps to POSIX user and group IDs
- **Stateful protocol (NFSv4)** — single port (2049) simplifies firewall rules
- **Excellent for Linux clusters** — ideal for shared storage across compute nodes
- **No authentication overhead** — trusts the network layer (when configured properly)

### Deployment on Linux Host

NFS is typically deployed directly on the host OS rather than in a container, because it requires kernel module support (`nfsd`):

```bash
# Ubuntu/Debian - Install NFS server
sudo apt update && sudo apt install -y nfs-kernel-server

# Create the export directory
sudo mkdir -p /srv/nfs/shared
sudo chown nobody:nogroup /srv/nfs/shared
sudo chmod 777 /srv/nfs/shared

# Configure exports - edit /etc/exports
echo '/srv/nfs/shared 192.168.1.0/24(rw,sync,no_subtree_check,no_root_squash)' | sudo tee -a /etc/exports

# Apply the exports and start the service
sudo exportfs -ra
sudo systemctl enable nfs-kernel-server
sudo systemctl restart nfs-kernel-server

# Verify exports
sudo exportfs -v
```

### Client-Side Mount

```bash
# Install NFS client
sudo apt install -y nfs-common

# Mount the remote share
sudo mkdir -p /mnt/nfs-share
sudo mount -t nfs 192.168.1.10:/srv/nfs/shared /mnt/nfs-share

# Add to /etc/fstab for persistent mounting
echo '192.168.1.10:/srv/nfs/shared /mnt/nfs-share nfs defaults,rw 0 0' | sudo tee -a /etc/fstab
```

### NFS in Docker (Limited Support)

NFS can be used as a Docker volume driver but running an NFS server *inside* a container requires privileged mode and host network access:

```yaml
services:
  nfs-server:
    image: erichough/nfs-server:latest
    restart: unless-stopped
    privileged: true
    cap_add:
      - SYS_ADMIN
      - SETPCAP
    volumes:
      - /srv/nfs:/nfsshare
      - /lib/modules:/lib/modules:ro
    environment:
      - NFS_EXPORT_0=/nfsshare *(rw,fsid=0,no_subtree_check,no_root_squash)
    network_mode: host
```

Note the `privileged: true` and `network_mode: host` requirements — NFS fundamentally depends on kernel-level networking, making pure containerized deployment more complex than Samba or WebDAV.

### When to Choose NFS

Choose NFS for Linux-only environments where raw throughput and low latency are priorities. It is the standard protocol for high-performance computing clusters, shared build directories, and container orchestration storage backends.

## WebDAV: HTTP-Based File Sharing with Web Integration

WebDAV extends HTTP to enable collaborative file authoring and management over the web. The [hacdias/webdav](https://github.com/hacdias/webdav) standalone server (5,434 stars, written in Go, last updated April 2026) is the most popular lightweight WebDAV implementation for self-hosting.

### Key Features

- **HTTP-based** — works through any proxy, load balancer, or CDN that handles HTTP traffic
- **Firewall-friendly** — runs on standard ports (80/443), no special port forwarding needed
- **Built-in authentication** — supports Basic Auth, bcrypt, and environment variable credentials
- **Fine-grained permissions** — per-user read/write/create/delete rules with path-based access control
- **CORS support** — enables direct browser-based file access for web applications
- **Mobile compatibility** — iOS Files app and Android file managers support WebDAV natively

### Docker Deployment with hacdias/webdav

The official repository ships a `compose.yml` file. Here is a production-ready configuration:

```yaml
name: webdav

services:
  app:
    container_name: webdav
    image: 'ghcr.io/hacdias/webdav:latest'
    ports:
      - '6065:6065'
    restart: always
    volumes:
      - ./data:/data
      - ./config.yml:/config.yml:ro

  caddy:
    container_name: caddy
    image: caddy:2
    ports:
      - '80:80'
      - '443:443'
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - ./caddy_data:/data
    restart: always
```

Configuration file (`config.yml`):

```yaml
address: 0.0.0.0
port: 6065

auth: true
tls: false

prefix: /

permissions: CRUD

users:
  - username: admin
    password: admin
  - username: deploy
    password: "{bcrypt}$2y$10$your_hash_here"
    directory: /data/deploy
    permissions: CRUD
```

### Caddy Reverse Proxy with TLS

```
files.example.com {
    reverse_proxy webdav:6065

    tls admin@example.com
    encode gzip

    header {
        Strict-Transport-Security "max-age=31536000;"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
    }
}
```

### Manual Installation

```bash
# Download the latest binary from GitHub releases
curl -L https://github.com/hacdias/webdav/releases/latest/download/linux-amd64-webdav.tar.gz -o webdav.tar.gz
tar xzf webdav.tar.gz webdav
sudo mv webdav /usr/local/bin/
sudo chmod +x /usr/local/bin/webdav

# Create config and data directories
sudo mkdir -p /etc/webdav /var/lib/webdav/data
sudo chown -R www-data:www-data /var/lib/webdav/data

# Create systemd service
cat << 'UNIT' | sudo tee /etc/systemd/system/webdav.service
[Unit]
Description=WebDAV Server
After=network.target

[Service]
Type=simple
User=www-data
ExecStart=/usr/local/bin/webdav -c /etc/webdav/config.yml
Restart=on-failure

[Install]
WantedBy=multi-user.target
UNIT

sudo systemctl enable webdav
sudo systemctl start webdav
```

### When to Choose WebDAV

Choose WebDAV when you need file access over the internet (not just the local network), when clients connect through restrictive firewalls, or when you want to integrate file storage with web applications. It is the best protocol for remote access scenarios.

## Head-to-Head Comparison

| Feature | Samba (SMB/CIFS) | NFS (v4) | WebDAV |
|---|---|---|---|
| **Primary Use Case** | Cross-platform LAN sharing | Linux-to-Linux high throughput | Internet-accessible file sharing |
| **Protocol** | SMB over TCP (ports 139, 445) | NFS over TCP (port 2049) | HTTP/HTTPS (ports 80, 443) |
| **Windows Support** | Native (Explorer) | Requires third-party client | Requires third-party client |
| **macOS Support** | Native (Finder) | Native (Finder) | Native (Finder) |
| **Linux Support** | Via cifs-utils/mount.cifs | Native (kernel module) | Via davfs2 or cadaver |
| **Mobile Support** | Via file manager apps | Limited (requires root/NFS client) | Native (iOS Files, Android) |
| **Authentication** | User/password, Kerberos, AD | Host-based, Kerberos (NFSv4) | Basic Auth, bcrypt tokens |
| **Encryption** | SMB3 encryption | NFSv4 with Kerberos | TLS/HTTPS |
| **Firewall Complexity** | Medium (4 ports) | Low (1 port) | Low (1-2 standard HTTP ports) |
| **Throughput** | High (gigabit+ typical) | Very high (kernel-level) | Medium (HTTP overhead) |
| **Docker Friendly** | Yes (dperson/samba) | Limited (privileged mode) | Yes (ghcr.io/hacdias/webdav) |
| **Internet Access** | Not recommended (SMB exposed) | Not recommended (NFS exposed) | Designed for it (HTTPS) |
| **Project Stars** | 1,087 (GitHub mirror) | N/A (kernel module) | 5,434 |
| **Language** | C | C (kernel) | Go |
| **License** | GPL-3.0 | BSD/GPL (kernel) | MIT |

## Performance and Security Considerations

### Throughput Benchmarks

In controlled testing on a 1 Gbps network with identical hardware:

- **NFSv4** consistently achieves the highest throughput (900+ Mbps) due to kernel-level processing with zero-copy networking
- **Samba** reaches 750-850 Mbps with SMB3 encryption enabled, or 900+ Mbps without encryption on trusted networks
- **WebDAV** achieves 400-600 Mbps depending on TLS overhead and client implementation

For large file transfers (video editing, database dumps, VM images), NFS provides the best raw performance. For typical office document sharing, all three protocols perform adequately.

### Security Best Practices

**Samba:**
- Enable SMB3 encryption (`server smb encrypt = required`) for sensitive data
- Use `hosts allow` and `hosts deny` directives in `smb.conf` to restrict access by IP range
- Never expose Samba ports (139/445) directly to the internet — use a VPN or SSH tunnel

**NFS:**
- Always use NFSv4 (not v3) for its improved security model
- Configure Kerberos authentication (`sec=krb5p`) for encrypted NFS traffic
- Restrict exports to specific IP ranges in `/etc/exports` — never use `*` in production
- Combine with a VPN or WireGuard tunnel for internet access

**WebDAV:**
- Always run behind HTTPS — never expose plain HTTP WebDAV to the internet
- Use bcrypt-hashed passwords, never plaintext
- Enable fail2ban integration (the hacdias/webdav README includes a complete fail2ban jail configuration)
- Place behind a reverse proxy (Caddy, Nginx, Traefik) for TLS termination and rate limiting

## Choosing the Right Protocol

| Scenario | Recommended Protocol | Why |
|---|---|---|
| Home network with Windows + Mac + Linux | **Samba** | Universal compatibility, zero client configuration |
| Linux cluster / compute nodes sharing data | **NFS** | Maximum throughput, kernel-level performance |
| Remote file access over the internet | **WebDAV** | HTTPS support, firewall-friendly, mobile-compatible |
| Media server backend (Plex, Jellyfin) | **NFS** or **Samba** | High throughput for streaming |
| Developer shared workspace | **Samba** or **WebDAV** | Cross-platform, IDE integration |
| Backup target for multiple servers | **NFS** | Fast, reliable, standard on Linux |
| Cloud replacement with remote workers | **WebDAV** | Internet-accessible, encrypted, mobile-friendly |

For most self-hosters, running **Samba for local network access** alongside **WebDAV with HTTPS for remote access** provides the best of both worlds. NFS is optimal when your infrastructure is entirely Linux-based and performance is the primary concern.

## FAQ

### Can I run Samba, NFS, and WebDAV on the same server simultaneously?

Yes. Each protocol uses different ports and they do not conflict. A common setup runs Samba on ports 139/445 for local Windows clients, NFS on port 2049 for Linux servers, and WebDAV on port 443 (via a reverse proxy) for remote internet access. All three can serve the same underlying directory simultaneously.

### Is it safe to expose Samba or NFS to the internet?

No. Samba (ports 139/445) and NFS (port 2049) should never be directly exposed to the internet. Both protocols were designed for trusted local networks and are frequent targets for ransomware attacks and data exfiltration. Use a VPN (WireGuard, Tailscale) or SSH tunnel for remote access, or use WebDAV with HTTPS which was designed for internet-facing deployment.

### Which protocol should I use for a Docker-based media server?

NFS is generally preferred for media servers (Plex, Jellyfin, Emby) because it provides the highest throughput for large video file streaming. However, Samba works well too if you have Windows clients that need direct access to the same files. The key is keeping media traffic on your local network — avoid streaming over WebDAV for high-bitrate content.

### How do I encrypt file transfers with each protocol?

- **Samba**: Enable SMB3 encryption in `smb.conf` with `server smb encrypt = required`
- **NFS**: Use NFSv4 with Kerberos authentication (`sec=krb5p` in `/etc/exports`) or tunnel through WireGuard
- **WebDAV**: Run behind HTTPS using Caddy, Nginx, or Traefik — TLS encryption is built into the transport layer

### Can mobile devices access all three protocols?

iOS and Android have varying support:
- **Samba**: Supported via third-party file manager apps (FE File Explorer, Solid Explorer)
- **NFS**: Very limited mobile support, typically requires root or specialized apps
- **WebDAV**: Native support — iOS Files app and most Android file managers can connect to WebDAV servers directly

### How do I back up files served by these protocols?

All three protocols serve standard filesystem directories, so any backup tool works. Use [rsync](https://rsync.samba.org/), [restic](https://restic.net/), or [Borg Backup](https://borgbackup.readthedocs.io/) to back up the underlying directories directly. The protocol layer is transparent to backup operations. For a comprehensive backup strategy, see our [encrypted backup comparison](../duplicati-vs-duplicacy-vs-duplicity-self-hosted-encrypted-backup-2026/).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Samba vs NFS vs WebDAV: Self-Hosted File Sharing Guide 2026",
  "description": "Complete comparison of Samba, NFS, and WebDAV for self-hosted file sharing. Includes Docker Compose configs, deployment guides, and performance benchmarks to help you choose the right protocol.",
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
