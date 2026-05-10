---
title: "Self-Hosted WebDAV Servers: Radicale vs WebDAV-Go vs Nextcloud WebDAV Comparison"
date: "2026-05-10"
tags: ["webdav", "file-sharing", "radicale", "nextcloud", "calendaring"]
draft: false
---

WebDAV (Web Distributed Authoring and Versioning) extends HTTP to allow collaborative file management on remote servers. It enables users to create, edit, move, and delete files on a server as if they were local — the foundation for calendar sync (CalDAV), contact sync (CardDAV), and collaborative document editing.

Three popular open-source WebDAV implementations serve different use cases: **Radicale** (lightweight CalDAV/CardDAV), **WebDAV-Go** (minimal standalone server), and **Nextcloud's WebDAV** (full-featured collaboration platform).

## Comparison Table

| Feature | Radicale | WebDAV-Go | Nextcloud WebDAV |
|---------|----------|-----------|------------------|
| GitHub Stars | 4,637+ | 5,501+ | 34,853+ |
| Language | Python | Go | PHP |
| WebDAV | ✅ Yes | ✅ Yes | ✅ Yes |
| CalDAV | ✅ Yes | ❌ No | ✅ Yes |
| CardDAV | ✅ Yes | ❌ No | ✅ Yes |
| Authentication | htpasswd, PAM, LDAP | htpasswd, PAM | Built-in user management |
| Encryption | Via reverse proxy | Via reverse proxy | Built-in TLS support |
| Storage | Filesystem (custom) | Filesystem | Database + filesystem |
| Plugins | ✅ Custom backends | ❌ No | ✅ Extensive app ecosystem |
| Multi-user | ✅ Yes | ✅ Yes | ✅ Yes |
| Docker Support | ✅ Community images | ✅ Official image | ✅ Official image |
| Resource Usage | ~50MB RAM | ~5MB RAM | ~500MB+ RAM |
| Scalability | Single server | Single server | Horizontal scaling possible |

## How WebDAV Works

WebDAV extends HTTP/1.1 with new methods:
- **PROPFIND** — retrieve properties (metadata) of resources
- **PROPPATCH** — set or modify properties
- **MKCOL** — create collections (directories)
- **COPY/MOVE** — copy or move resources
- **LOCK/UNLOCK** — lock resources for editing

CalDAV and CardDAV build on WebDAV by defining specific collection types (calendars, address books) and data formats (iCalendar, vCard).

## Radicale

Radicale is a lightweight CalDAV and CardDAV server written in Python. It provides WebDAV access to calendar and contact collections with minimal resource usage.

### Key Features
- **Simple setup** — single binary, minimal configuration
- **CalDAV + CardDAV** — full support for both protocols
- **Multiple auth backends** — htpasswd, PAM, LDAP, IMAP
- **Custom storage backends** — filesystem, Git-based, or custom

### Docker Compose

```yaml
version: '3.8'
services:
  radicale:
    image: tomsquest/docker-radicale:latest
    container_name: radicale
    ports:
      - "5232:5232"
    volumes:
      - ./config:/etc/radicale
      - ./data:/var/lib/radicale/collections
    restart: unless-stopped
```

Radicale's configuration file (`/etc/radicale/config`) controls authentication, storage, and access rights:

```ini
[server]
hosts = 0.0.0.0:5232

[auth]
type = htpasswd
htpasswd_filename = /etc/radicale/users
htpasswd_encryption = bcrypt

[storage]
type = multifilesystem
filesystem_folder = /var/lib/radicale/collections
```

Connect any CalDAV/CardDAV client (Thunderbird, Evolution, DAVx5 on Android) to `http://your-server:5232/username/` to access calendars and contacts.

## WebDAV-Go

WebDAV-Go (hacdias/webdav) is a minimal, standalone WebDAV server written in Go. It focuses solely on file serving via WebDAV without calendar or contact support.

### Key Features
- **Extremely lightweight** — single Go binary, ~5MB RAM usage
- **Fast** — concurrent file serving with Go's goroutines
- **Simple configuration** — YAML-based config file
- **Cross-platform** — runs on Linux, macOS, Windows, ARM

### Docker Compose

```yaml
version: '3.8'
services:
  webdav:
    image: hacdias/webdav:latest
    container_name: webdav
    ports:
      - "8080:80"
    volumes:
      - ./data:/data
      - ./config.yaml:/etc/webdav.yaml
    environment:
      - TZ=UTC
    restart: unless-stopped
```

Configuration file (`config.yaml`):

```yaml
address: 0.0.0.0
port: 80
prefix: /
auth: true
users:
  - username: admin
    password: $2y$10$...  # bcrypt hash
permissions:
  - path: /data
    user: admin
    modify: true
```

WebDAV-Go is ideal when you need a simple, low-resource file sharing server that speaks standard WebDAV — perfect for mounting as a network drive on Linux, macOS, or Windows.

## Nextcloud WebDAV

Nextcloud includes a full-featured WebDAV server as part of its collaboration platform. Every file stored in Nextcloud is accessible via WebDAV at `/remote.php/dav/files/username/`.

### Key Features
- **Full collaboration suite** — files, calendar, contacts, mail, talk
- **Rich WebDAV endpoint** — supports extended WebDAV properties
- **App ecosystem** — hundreds of plugins and integrations
- **Mobile apps** — iOS and Android clients

### Docker Compose

```yaml
version: '3.8'
services:
  nextcloud:
    image: nextcloud:apache
    container_name: nextcloud
    ports:
      - "8080:80"
    volumes:
      - ./nextcloud:/var/www/html
    environment:
      - MYSQL_HOST=db
      - MYSQL_PASSWORD=secret
      - MYSQL_DATABASE=nextcloud
      - MYSQL_USER=nextcloud
    restart: unless-stopped
  db:
    image: mariadb:10
    volumes:
      - ./db:/var/lib/mysql
    environment:
      - MYSQL_ROOT_PASSWORD=rootpass
      - MYSQL_DATABASE=nextcloud
      - MYSQL_USER=nextcloud
      - MYSQL_PASSWORD=secret
    restart: unless-stopped
```

Access Nextcloud's WebDAV endpoint at `https://your-server/remote.php/dav/files/username/`. Mount it as a network drive on any OS using the built-in WebDAV client.

## Choosing the Right WebDAV Server

- **Choose Radicale** if you need a lightweight CalDAV/CardDAV server for calendar and contact synchronization with minimal resource usage.
- **Choose WebDAV-Go** if you need a minimal, standalone WebDAV file server with low memory footprint — ideal for simple file sharing without the overhead of a full platform.
- **Choose Nextcloud WebDAV** if you want a complete collaboration platform with WebDAV access to files, plus calendar, contacts, talk, and hundreds of apps.

## Why Self-Host a WebDAV Server?

Running your own WebDAV server gives you complete control over file access, synchronization, and sharing. Unlike cloud storage providers, a self-hosted WebDAV server doesn't scan your files, impose storage limits, or require internet connectivity for local access.

WebDAV is particularly valuable for organizations that need to integrate with existing workflows. Microsoft Office, LibreOffice, and many other applications can open and save files directly from WebDAV URLs, making it a drop-in replacement for network file shares without the complexity of SMB or NFS configuration.

For calendar and contact synchronization, self-hosted CalDAV/CardDAV via WebDAV means your personal data never leaves your server. Unlike iCloud or Google Calendar, a self-hosted Radicale server stores calendar data in plain iCalendar format on your filesystem, making backups trivial and data portability guaranteed.

For related file sharing, see our [Samba vs NFS vs WebDAV comparison](../2026-04-24-samba-vs-nfs-vs-webdav-self-hosted-file-sharing-guide/) and [Gokapi vs Lufi secure file sharing](../2026-05-05-gokapi-vs-lufi-vs-fileshelter-secure-self-hosted-file-sharing/). For calendar-specific setup, our [Baikal vs SabreDAV CardDAV guide](../2026-05-01-baikal-vs-sabredav-vs-nextcloud-contacts-self-hosted-carddav-guide/) covers contact synchronization options.


## WebDAV Security Hardening

Securing your WebDAV deployment requires attention to several attack vectors. First, always deploy behind HTTPS — WebDAV transmits credentials via HTTP Basic or Digest authentication, which are vulnerable to interception on unencrypted connections. Use Let's Encrypt or your preferred CA to obtain valid TLS certificates.

Second, restrict WebDAV methods at the reverse proxy level if you don't need the full protocol. For read-only file sharing, allow only `GET`, `HEAD`, and `PROPFIND`. Block `PUT`, `DELETE`, `MKCOL`, and `MOVE` to prevent unauthorized modifications. For Radicale, additionally restrict CalDAV/CardDAV access to authenticated users only by enabling its access control module.

Third, implement brute-force protection. WebDAV authentication failures should trigger rate limiting or account lockout after repeated failures. Use fail2ban with the WebDAV access log pattern to automatically block suspicious IPs. Both WebDAV-Go and Radicale support configurable rate limiting natively.

## FAQ

### What is WebDAV and why use it?
WebDAV (Web Distributed Authoring and Versioning) extends HTTP to allow collaborative file management on remote web servers. It enables you to create, edit, move, copy, and delete files on a server using standard HTTP methods. Use WebDAV when you need a simple, firewall-friendly file sharing protocol that works across all operating systems.

### What is the difference between WebDAV, CalDAV, and CardDAV?
WebDAV is the base protocol for file management over HTTP. CalDAV (Calendar DAV) extends WebDAV for calendar data using the iCalendar format. CardDAV (Contact DAV) extends WebDAV for contact/address book data using the vCard format. CalDAV and CardDAV are specialized subtypes of WebDAV.

### Can I mount a WebDAV server as a local drive?
Yes. On Linux, use `davfs2` or `rclone mount`. On macOS, use Finder's "Connect to Server" (Cmd+K) with the WebDAV URL. On Windows, use "Map Network Drive" with the WebDAV URL or use tools like RaiDrive or Cyberduck.

### Does WebDAV support encryption?
WebDAV itself does not include encryption, but it runs over HTTPS just like any other web service. Deploy WebDAV behind a reverse proxy (Nginx, Caddy, or Traefik) with TLS termination for encrypted connections. Nextcloud includes built-in HTTPS support.

### How does Radicale compare to Baikal for CalDAV?
Both Radicale and Baikal provide CalDAV and CardDAV servers. Radicale is more minimal with a simpler configuration, while Baikal offers a web admin interface. Radicale uses less memory (~50MB vs ~100MB) and has more active development (4,600+ stars). See our [Baikal vs SabreDAV guide](../2026-05-01-baikal-vs-sabredav-vs-nextcloud-contacts-self-hosted-carddav-guide/) for more details.

### Is WebDAV-Go suitable for production file sharing?
WebDAV-Go is a production-ready standalone WebDAV server with authentication, permissions, and TLS support. However, it lacks advanced features like file versioning, sharing links, and collaborative editing. For simple file sharing needs, it's excellent. For collaboration features, consider Nextcloud.


<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted WebDAV Servers: Radicale vs WebDAV-Go vs Nextcloud WebDAV Comparison",
  "description": "Compare Radicale, WebDAV-Go, and Nextcloud WebDAV for self-hosted file and calendar synchronization. Learn which WebDAV server fits your needs for CalDAV, CardDAV, and file sharing.",
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
