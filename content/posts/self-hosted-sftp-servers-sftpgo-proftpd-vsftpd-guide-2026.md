---
title: "Best Self-Hosted SFTP Servers: SFTPGo vs ProFTPD vs vsftpd (2026)"
date: 2026-04-16
tags: ["comparison", "guide", "self-hosted", "privacy"]
draft: false
description: "Complete comparison and setup guide for self-hosted SFTP and FTP servers in 2026. Compare SFTPGo, ProFTPD, and vsftpd with Docker deployment instructions and security hardening tips."
---

File transfer is one of the oldest and most essential services in any infrastructure. Whether you are sharing backups between servers, distributing software packages to clients, or giving team members secure access to shared directories, a reliable self-hosted file transfer server is the backbone of operations.

While managed services like Dropbox, AWS Transfer Family, and Azure Blob Storage dominate the enterprise space, they come with recurring costs, vendor lock-in, and the fundamental problem of trusting a third party with your data. Self-hosting an SFTP or FTP server gives you complete control over access policies, storage limits, encryption standards, and audit trails — without per-user pricing surprises.

This guide compares three of the best open source self-hosted SFTP/FTP servers available in 2026: **SFTPGo**, **ProFTPD**, and **vsftpd**. We cover features, performance, security, deployment options, and provide copy-paste Docker configurations to get each one running in minutes.

## Why Self-Host Your File Transfer Server

Running your own SFTP server solves several problems that cloud file transfer services simply cannot address:

**Data sovereignty.** Files never leave your infrastructure. For organizations handling sensitive customer data, financial records, or health information, keeping file transfers in-house is often a regulatory requirement rather than an option.

**Zero per-user costs.** Cloud SFTP providers typically charge per user or per gigabyte transferred. With a self-hosted server, the only costs are your hardware and bandwidth. Whether you serve 10 users or 10,000, the price remains the same.

**Custom integrations.** Self-hosted servers can connect directly to your internal authentication systems (LDAP, Active Directory, OAuth), storage backends (S3-compatible object storage, Ceph, local filesystems), and monitoring stacks (Prometheus, Grafana) without workarounds.

**Full auditability.** Every login attempt, file upload, download, and deletion can be logged locally. You control retention policies, log formats, and can pipe audit data directly into your SIEM or log aggregation pipeline.

**Offline resilience.** Cloud file transfer services are useless when your internet connection drops. A self-hosted server on your LAN works regardless of upstream connectivity, making it ideal for edge locations, manufacturing floors, and remote sites.

## Comparison at a Glance

| Feature | SFTPGo | ProFTPD | vsftpd |
|---|---|---|---|
| **Protocol Support** | SFTP, SCP, FTP/S, WebDAV, HTTP | FTP, FTP/S, SFTP (via mod_sftp) | FTP, FTP/S, SFTP (limited) |
| **Authentication** | Internal DB, LDAP, AD, OAuth2, OIDC, MySQL, PostgreSQL | PAM, LDAP, SQL, RADIUS, system users | PAM, virtual users, system users |
| **Storage Backends** | Local, S3, Google Cloud, Azure Blob, encrypted local | Local, NFS-mounted | Local, NFS-mounted |
| **Web Admin UI** | Yes (built-in, full-featured) | No (config files only) | No (config files only) |
| **REST API** | Yes (comprehensive) | No | No |
| **Web Client** | Yes (browser-based file manager) | No | No |
| **Data Providers** | SQLite, PostgreSQL, MySQL, BoltDB | System files, SQL modules | System files |
| **Event Webhooks** | Yes | No | No |
| **Bandwidth Throttling** | Yes (per-user, per-IP) | Yes (via mod_ban) | Limited |
| **Two-Factor Auth** | Yes (TOTP, email) | Via external PAM modules | Via external PAM modules |
| **Active Users** | 10k+ GitHub stars | Mature, stable project | Mature, stable project |
| **Language** | Go | C | C |
| **Docker Image** | Official, multi-arch | Community-maintained | Community-maintained |
| **Best For** | Modern teams needing UI + API | Traditional FTP setups with SFTP add-on | Minimal, fast FTP-only servers |

## SFTPGo: The Modern All-in-One Solution

**SFTPGo** is the newest entrant of the three, written in Go, and has quickly become the most feature-rich self-hosted file transfer server. Its standout feature is treating SFTP, FTP/S, WebDAV, and HTTP file sharing as a single unified platform with a built-in web administration panel and REST API.

### Key Advantages

- **Unified protocol support:** Run SFTP, FTP with TLS, WebDAV, and an HTTP file browser from a single process. Clients can connect via their preferred protocol while sharing the same user database and storage backend.
- **Pluggable storage:** Store files on the local filesystem, Amazon S3, Google Cloud Storage, or Azure Blob Storage — all transparently through the same user-facing interface. Users never need to know where their files actually live.
- **Built-in web admin UI:** Manage users, groups, quotas, connections, and view real-time activity from a polished web interface. No more editing configuration files and restarting daemons.
- **REST API:** Automate user provisioning, retrieve usage statistics, configure folders, and manage connections programmatically. Integrates cleanly with Terraform, Ansible, and custom orchestration scripts.
- **Event-driven hooks:** Trigger external scripts or HTTP callbacks on events like user login, file upload, file download, and SSH command execution. Pipe these events into monitoring systems or trigger downstream workflows.
- **Multi-factor authentication:** Native support for TOTP (Google Authenticator, Authy), with optional email-based second factors. No external PAM configuration needed.

### Docker Deployment

The following Docker Compose configuration deploys SFTPGo with a PostgreSQL backend for user data and persistent local storage for files:

```yaml
# docker-compose.yml
version: "3.9"

services:
  sftpgo:
    image: drakkan/sftpgo:latest
    container_name: sftpgo
    restart: unless-stopped
    ports:
      - "2022:2022"   # SFTP
      - "8080:8080"   # Web UI & REST API
      - "2121:2121"   # FTP (optional)
      - "10080:10080" # WebDAV (optional)
    environment:
      - SFTPGO_DATA_PROVIDER__DRIVER=postgres
      - SFTPGO_DATA_PROVIDER__NAME=sftpgo_db
      - SFTPGO_DATA_PROVIDER__HOST=postgres
      - SFTPGO_DATA_PROVIDER__PORT=5432
      - SFTPGO_DATA_PROVIDER__USERNAME=sftpgo
      - SFTPGO_DATA_PROVIDER__PASSWORD=sftpgo_secret_password
      - SFTPGO_DATA_PROVIDER__SSL_MODE=disable
      - SFTPGO_HTTPD__BINDINGS__0__PORT=8080
      - SFTPGO_SFTPD__BINDINGS__0__PORT=2022
      - SFTPGO_FTPD__BINDINGS__0__PORT=2121
      - SFTPGO_FTPD__BINDINGS__0__TLS_MODE=1
      - SFTPGO_WEBDAVD__BINDINGS__0__PORT=10080
      - SFTPGO_WEBDAVD__BINDINGS__0__TLS_MODE=1
    volumes:
      - sftpgo_data:/srv/sftpgo/data
      - sftpgo_backups:/var/lib/sftpgo/backups
    depends_on:
      - postgres
    networks:
      - sftpgo_net

  postgres:
    image: postgres:16-alpine
    container_name: sftpgo_postgres
    restart: unless-stopped
    environment:
      - POSTGRES_DB=sftpgo_db
      - POSTGRES_USER=sftpgo
      - POSTGRES_PASSWORD=sftpgo_secret_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - sftpgo_net

volumes:
  sftpgo_data:
  sftpgo_backups:
  postgres_data:

networks:
  sftpgo_net:
    driver: bridge
```

After starting with `docker compose up -d`, access the admin panel at `http://your-server:8080`. The default admin credentials are `admin` / `admin` — change them immediately on first login.

### Creating Users via REST API

Once the admin password is changed, you can create users programmatically:

```bash
# Get an admin token
TOKEN=$(curl -s -X POST http://localhost:8080/api/v2/token \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your_new_password"}' \
  | jq -r '.access_token')

# Create a new user with 10GB quota
curl -s -X POST http://localhost:8080/api/v2/users \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "developer-01",
    "status": 1,
    "home_dir": "/srv/sftpgo/data/developer-01",
    "uid": 1000,
    "gid": 1000,
    "permissions": {
      "/": ["*"]
    },
    "quota_size": 10737418240
  }'
```

### SFTP Storage Backend Configuration

SFTPGo can mount S3-compatible storage as a user's home directory. Configure it in the admin UI or via API:

```bash
# Configure a user with S3 backend storage
curl -s -X POST http://localhost:8080/api/v2/users \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "archive-user",
    "status": 1,
    "home_dir": "/bucket-name/prefix",
    "uid": 1000,
    "gid": 1000,
    "permissions": { "/": ["*"] },
    "filesystems": [{
      "base_dir": "/bucket-name/prefix",
      "config": {
        "provider": "s3",
        "bucket": "sftpgo-archives",
        "region": "us-east-1",
        "access_key": "${AWS_ACCESS_KEY}",
        "access_secret": "${AWS_SECRET_KEY}",
        "endpoint": "https://s3.us-east-1.amazonaws.com",
        "auto_create_bucket": false,
        "encryption": "AES256"
      }
    }]
  }'
```

### Security Hardening for SFTPGo

- **Enable TLS for all protocols:** Configure certificates for SFTPGo's FTP/S and WebDAV endpoints. SFTP is encrypted by default.
- **Restrict admin panel:** Place the admin UI behind a reverse proxy with IP allowlisting. Never expose port 8080 directly to the internet.
- **Set file permissions:** Ensure the Docker volume directories have appropriate ownership. SFTPGo runs as user `sftpgo` (UID 1000) by default.
- **Enable two-factor authentication:** Require TOTP for admin and privileged user accounts through the web UI.
- **Configure connection limits:** Set `max_connections` per user and per IP to prevent abuse.

## ProFTPD: The Battle-Tested Traditional Choice

**ProFTPD** has been around since 1997 and remains one of the most configurable FTP servers available. While it started as an FTP-only server, the `mod_sftp` module adds full SFTP support, and `mod_tls` provides FTP over TLS (FTPS).

### Key Advantages

- **Extremely modular architecture:** Over 50 official modules covering authentication, logging, quotas, quotas, bandwidth limiting, SQL backends, LDAP integration, RADIUS, and more. Add or remove functionality by editing a single configuration file.
- **VFS (Virtual File System):** Mount disparate storage locations under a unified directory tree visible to FTP clients. Combine local directories, SQL-backed virtual paths, and NFS mounts into one coherent namespace.
- **PAM integration:** Authenticate against any PAM-configured backend — system accounts, LDAP, Kerberos, RADIUS, or two-factor authentication systems.
- **Apache-style configuration:** Uses familiar `<Directory>`, `<IfModule>`, `<VirtualHost>`, and `<Anonymous>` blocks. Administrators with Apache experience find ProFTPD configuration intuitive.
- **Chroot isolation:** Each user can be jailed to their home directory with fine-grained controls over what they can see and access.
- **Proven stability:** Running in production at thousands of organizations for over 25 years. Few security surprises.

### Docker Deployment

```yaml
# docker-compose.yml
version: "3.9"

services:
  proftpd:
    image: stilliard/proftpd:latest
    container_name: proftpd
    restart: unless-stopped
    ports:
      - "21:21"       # FTP control
      - "21000-21010:21000-21010"  # Passive mode ports
      - "2222:2222"   # SFTP (via mod_sftp)
    volumes:
      - ./proftpd.conf:/etc/proftpd/proftpd.conf:ro
      - ftp_data:/home/ftp
      - ./tls:/etc/proftpd/tls:ro
    environment:
      - FTP_USER=ftpuser
      - FTP_PASS=s3cur3_p4ssw0rd
      - FTP_HOME=/home/ftp
    networks:
      - proftpd_net

volumes:
  ftp_data:

networks:
  proftpd_net:
    driver: bridge
```

### ProFTPD Configuration

Here is a production-ready configuration with SFTP, TLS, and user isolation:

```apache
# proftpd.conf

ServerName "My SFTP Server"
ServerType standalone
DefaultServer on
Port 21
User ftp
Group nogroup

# Limit passive port range for firewall configuration
PassivePorts 21000 21010

# Log files
TransferLog /var/log/proftpd/xferlog
SystemLog /var/log/proftpd/proftpd.log

# TLS configuration for FTPS
<IfModule mod_tls.c>
  TLSEngine on
  TLSRequired on
  TLSRSACertificateFile /etc/proftpd/tls/server.crt
  TLSRSACertificateKeyFile /etc/proftpd/tls/server.key
  TLSCipherSuite HIGH:!aNULL:!MD5
  TLSProtocol TLSv1.2 TLSv1.3
  TLSLog /var/log/proftpd/tls.log
</IfModule>

# SFTP configuration via mod_sftp
<IfModule mod_sftp.c>
  <VirtualHost 0.0.0.0>
    SFTPEngine on
    Port 2222
    SFTPHostKey /etc/ssh/ssh_host_rsa_key
    SFTPHostKey /etc/ssh/ssh_host_ecdsa_key
    SFTPDHParamFile /etc/proftpd/dhparams.pem
    SFTPLog /var/log/proftpd/sftp.log

    SFTPAuthMethods password publickey
    SFTPAuthorizedUserKeys file:/etc/proftpd/authorized_keys/%u
  </VirtualHost>
</IfModule>

# User isolation with chroot
DefaultRoot ~

# Disable anonymous access
<Anonymous ~ftp>
  User ftp
  Group nogroup
  UserAlias anonymous ftp
  RequireValidShell off
  MaxClients 10
  <Limit LOGIN>
    DenyAll
  </Limit>
</Anonymous>

# SQL backend for virtual users (optional)
<IfModule mod_sql.c>
  SQLEngine on
  SQLBackend postgres
  SQLConnectInfo sftpgo_db@postgres:5432 sftpgo sftpgo_secret_password
  SQLAuthTypes Crypt
  SQLUserInfo users username password uid gid home_dir shell
  SQLGroupInfo groups groupname gid members
</IfModule>
```

### Generating TLS Certificates

```bash
# Create a self-signed certificate (replace with Let's Encrypt in production)
mkdir -p ./tls
openssl req -x509 -nodes -days 365 \
  -newkey rsa:2048 \
  -keyout ./tls/server.key \
  -out ./tls/server.crt \
  -subj "/CN=your-server-hostname"

# Generate DH parameters for stronger key exchange
openssl dhparam -out ./dhparams.pem 2048
```

### Security Hardening for ProFTPD

- **Always require TLS:** Set `TLSRequired on` to reject any unencrypted FTP connection. Plain FTP sends passwords in cleartext.
- **Limit passive ports:** Define a narrow `PassivePorts` range and open only those ports in your firewall.
- **Disable root login:** Never allow the root user to authenticate via FTP or SFTP.
- **Use Fail2Ban:** ProFTPD logs are compatible with Fail2Ban out of the box. Configure it to block IPs after repeated failed login attempts.
- **Restrict shell access:** Set user shells to `/bin/false` or `/sbin/nologin` to prevent SSH login while still allowing SFTP access.

## vsftpd: The Minimalist Speed Demon

**vsftpd** (Very Secure FTP Daemon) powers some of the largest FTP installations in the world, including ftp.debian.org and ftp.gnu.org. Its design philosophy is minimalism and security over feature richness.

### Key Advantages

- **Security-first architecture:** vsftpd was designed from the ground up with security as the primary concern. It uses a chroot sandbox, privilege separation, and drops root privileges as early as possible.
- **Extremely lightweight:** The binary is under 150KB, uses minimal memory, and handles thousands of concurrent connections with negligible overhead.
- **Virtual IP support:** Bind different virtual hosts to different IP addresses with independent configurations, user databases, and security policies.
- **Bandwidth throttling:** Built-in rate limiting per user and per IP without requiring external modules.
- **Simple configuration:** A single configuration file with straightforward directives. No complex module system to understand.
- **Battle-tested:** Runs on many of the largest public FTP mirrors. If it can handle Debian's mirror traffic, it can handle yours.

### Limitations

- **FTP-only:** vsftpd does not support SFTP. It handles FTP and FTPS (FTP over TLS) only. If you need SFTP (SSH-based file transfer), you must run OpenSSH's SFTP subsystem separately or choose a different server.
- **No web interface:** All configuration is done through the `vsftpd.conf` file. No API, no web dashboard, no user self-service portal.
- **Basic authentication:** Supports system users and a flat-file virtual user database. No native LDAP, OAuth, or SQL integration without external PAM configuration.

### Docker Deployment

```yaml
# docker-compose.yml
version: "3.9"

services:
  vsftpd:
    image: fauria/vsftpd:latest
    container_name: vsftpd
    restart: unless-stopped
    ports:
      - "21:21"
      - "21100-21110:21100-21110"  # Passive ports
    volumes:
      - ftp_data:/home/vsftpd
      - ./vsftpd.conf:/etc/vsftpd/vsftpd.conf:ro
      - ./log:/var/log/vsftpd
    environment:
      - FTP_USER=ftpuser
      - FTP_PASS=s3cur3_p4ssw0rd
      - PASV_ADDRESS=your-server-ip
      - PASV_MIN_PORT=21100
      - PASV_MAX_PORT=21110
    networks:
      - vsftpd_net

volumes:
  ftp_data:

networks:
  vsftpd_net:
    driver: bridge
```

### vsftpd Configuration

```ini
# vsftpd.conf

# Run standalone
listen=YES
listen_ipv6=NO

# Security
anonymous_enable=NO
local_enable=YES
write_enable=YES
local_umask=022

# Chroot jail - users cannot escape home directory
chroot_local_user=YES
chroot_list_enable=YES
chroot_list_file=/etc/vsftpd/chroot_list
allow_writeable_chroot=YES

# TLS encryption
ssl_enable=YES
allow_anon_ssl=NO
force_local_data_ssl=YES
force_local_logins_ssl=YES
ssl_tlsv1_2=YES
ssl_tlsv1_3=YES
ssl_sslv2=NO
ssl_sslv3=NO
rsa_cert_file=/etc/ssl/certs/vsftpd.pem
rsa_private_key_file=/etc/ssl/private/vsftpd.key

# Passive mode
pasv_enable=YES
pasv_min_port=21100
pasv_max_port=21110
pasv_addr_resolve=NO
pasv_address=your-server-ip

# Connection limits
max_clients=100
max_per_ip=5
local_max_rate=1048576  # 1 MB/s per user

# Logging
xferlog_enable=YES
xferlog_file=/var/log/vsftpd/xferlog
xferlog_std_format=YES
dual_log_enable=YES
vsftpd_log_file=/var/log/vsftpd/vsftpd.log

# Directory listing
dirlist_enable=YES
ls_recurse_enable=NO

# Idle and session timeouts
idle_session_timeout=600
data_connection_timeout=120
connect_timeout=60
accept_timeout=60
```

### Generating Self-Signed Certificate for vsftpd

vsftpd requires a combined PEM file containing both the certificate and key:

```bash
openssl req -x509 -nodes -days 365 \
  -newkey rsa:2048 \
  -keyout /etc/ssl/private/vsftpd.key \
  -out /etc/ssl/certs/vsftpd.pem \
  -subj "/CN=your-server-hostname" \
  -addext "subjectAltName=DNS:your-server-hostname,IP:your-server-ip"

# vsftpd needs the cert and key combined
cat /etc/ssl/certs/vsftpd.pem /etc/ssl/private/vsftpd.key > /etc/ssl/certs/vsftpd-combined.pem
cp /etc/ssl/certs/vsftpd-combined.pem /etc/ssl/certs/vsftpd.pem
```

### Security Hardening for vsftpd

- **Force TLS:** Set `force_local_data_ssl=YES` and `force_local_logins_ssl=YES` to reject all unencrypted connections.
- **Chroot all users:** Enable `chroot_local_user=YES` and maintain a `chroot_list` of any users who need broader access (keep this list empty for maximum security).
- **Rate limit connections:** Set `max_per_ip` to limit concurrent connections from a single IP and `local_max_rate` to cap transfer speeds.
- **Disable directory recursion:** Set `ls_recurse_enable=NO` to prevent users from listing entire directory trees recursively, which can be used for reconnaissance.
- **Run behind a reverse proxy:** Place vsftpd behind an NGINX or HAProxy load balancer for DDoS protection and centralized TLS termination (for the control channel).

## Performance and Resource Usage

| Metric | SFTPGo | ProFTPD | vsftpd |
|---|---|---|---|
| **Memory footprint** | ~50-100 MB (Go runtime) | ~10-20 MB per daemon | ~5-10 MB total |
| **Binary size** | ~45 MB (statically linked Go) | ~1.2 MB | ~150 KB |
| **Max concurrent users** | 10,000+ (tested) | 5,000+ (tested) | 10,000+ (production-proven) |
| **Throughput (1 Gbps)** | ~900 Mbps | ~850 Mbps | ~950 Mbps |
| **Startup time** | < 1 second | < 1 second | < 0.5 seconds |
| **Configuration reload** | Instant (hot reload) | Requires restart | Requires restart |

## Choosing the Right Server

**Choose SFTPGo if:**
- You need a web admin interface and REST API for user management
- You want unified support for SFTP, FTP/S, WebDAV, and HTTP file sharing
- You need cloud storage backends (S3, GCS, Azure Blob)
- You want event-driven hooks and webhooks for automation
- You prefer modern, actively maintained software with frequent releases
- You need built-in two-factor authentication

**Choose ProFTPD if:**
- You need the most flexible and modular FTP server available
- You want Apache-style configuration syntax you already know
- You need VFS to combine multiple storage backends into one namespace
- You rely on PAM for complex authentication chains
- You need granular control over every aspect of FTP behavior
- You run traditional hosting environments with many virtual FTP users

**Choose vsftpd if:**
- You want the simplest, fastest, most resource-efficient FTP server
- You only need FTP/FTPS (no SFTP requirement)
- You run public-facing FTP mirrors with massive traffic volumes
- You prioritize security and simplicity over features
- You have limited hardware resources (edge devices, containers with tight limits)
- You want a battle-tested solution that powers major Linux distribution mirrors

## Final Thoughts

The self-hosted file transfer landscape in 2026 offers excellent options at every level. SFTPGo leads in features and modernity with its API, web UI, and cloud storage support. ProFTPD remains the most configurable option for complex hosting environments. vsftpd delivers unmatched simplicity and performance for FTP-only workloads.

Regardless of which server you choose, the fundamental principles remain the same: enforce encryption for all connections, implement strong authentication with multi-factor where possible, monitor access logs for anomalies, and keep your software updated. Self-hosting gives you control — but it also means security is your responsibility.

The Docker configurations provided above are production-ready starting points. Adapt the user credentials, TLS certificates, storage paths, and network settings to your environment, and you will have a secure, reliable file transfer server running in minutes — with zero monthly fees and zero vendor lock-in.
