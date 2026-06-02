---
title: "Self-Hosted SMTP SASL Authentication: Cyrus SASL vs Dovecot SASL vs GNU libgsasl Guide"
date: "2026-06-02"
tags: ["email", "smtp", "authentication", "security", "self-hosted", "postfix", "dovecot"]
draft: false
---

## Introduction

SMTP authentication is the gatekeeper of every self-hosted email server. Without proper SASL (Simple Authentication and Security Layer) configuration, your mail server is either an open relay — a spammer's dream — or unusable by legitimate users who need to send email from remote locations. The SASL framework provides a pluggable authentication layer between your MTA (Mail Transfer Agent) and your credential store, supporting mechanisms from simple password checks to modern SCRAM-SHA-256 challenge-response authentication.

Three major SASL implementations dominate the self-hosted email landscape: **Cyrus SASL** (the traditional workhorse shipped with Postfix), **Dovecot SASL** (tightly integrated with the Dovecot IMAP/POP3 server), and **GNU libgsasl** (a lightweight, modern alternative with GSSAPI and SCRAM support). This guide compares their architecture, configuration patterns, and best use cases for self-hosted deployments.

## Comparison Table

| Feature | Cyrus SASL | Dovecot SASL | GNU libgsasl |
|---------|-----------|--------------|--------------|
| **Primary Role** | General-purpose SASL library | IMAP/POP3 server with SASL | Lightweight SASL library |
| **Author** | Carnegie Mellon University | Dovecot OSS Team | Simon Josefsson (GNU) |
| **Language** | C | C | C |
| **GitHub Stars** | Part of cyrus-sasl | Part of Dovecot (~2,500) | ~85 (gsasl standalone) |
| **MTA Integration** | Postfix, Sendmail, Exim | Postfix (via socket), Exim | Postfix, Exim, msmtp |
| **Auth Backends** | sasldb, PAM, LDAP, SQL, SASLdb | Dovecot's passdb (SQL, LDAP, PAM, passwd-file) | PAM, GSSAPI, plain-text |
| **Mechanisms Supported** | PLAIN, LOGIN, CRAM-MD5, DIGEST-MD5, SCRAM-SHA-*, GSSAPI, NTLM, OTP | PLAIN, LOGIN, CRAM-MD5 (via compat) | PLAIN, LOGIN, CRAM-MD5, SCRAM-SHA-*, GSSAPI, GS2-KRB5, SAML20, OPENID20 |
| **SCRAM Support** | Yes (2.1.28+) | No (Dovecot removed SCRAM for SASL) | Yes (native, well-tested) |
| **TLS Integration** | External (requires STARTTLS) | Built-in (Dovecot TLS) | External (channel binding) |
| **Configuration File** | `/etc/sasl2/smtpd.conf` | `/etc/dovecot/conf.d/10-auth.conf` | `/etc/gsasl.conf` or app-specific |
| **Active Maintenance** | Moderate (legacy) | Active (Dovecot core) | Active (GNU project) |
| **Docker Image** | Available via distro packages | Official `dovecot/dovecot` | Available via distro packages |
| **Best For** | Legacy Postfix setups, LDAP backends | Postfix + Dovecot stacks, virtual users | Modern SCRAM deployments, GSSAPI |

## Cyrus SASL: The Battle-Tested Workhorse

Cyrus SASL is the original SASL implementation from Carnegie Mellon University's Project Cyrus. It has been the default SASL provider for Postfix for over two decades and supports virtually every authentication mechanism and backend ever created.

### Installation

```bash
# Debian/Ubuntu (with all plugins)
sudo apt install sasl2-bin libsasl2-modules libsasl2-modules-db     libsasl2-modules-sql libsasl2-modules-ldap libsasl2-modules-gssapi-mit

# RHEL/Fedora
sudo dnf install cyrus-sasl cyrus-sasl-plain cyrus-sasl-md5     cyrus-sasl-scram cyrus-sasl-gssapi cyrus-sasl-sql cyrus-sasl-ldap
```

### Postfix Integration

Cyrus SASL communicates with Postfix via the `smtpd` service. Configure `/etc/sasl2/smtpd.conf`:

```ini
# SASL backend: use sasldb2 for local users
pwcheck_method: auxprop
auxprop_plugin: sasldb
mech_list: PLAIN LOGIN CRAM-MD5 DIGEST-MD5 SCRAM-SHA-256

# Or use PAM for system users
# pwcheck_method: saslauthd
# mech_list: PLAIN LOGIN
```

Then configure Postfix in `/etc/postfix/main.cf`:

```ini
# Enable SASL authentication
smtpd_sasl_auth_enable = yes
smtpd_sasl_security_options = noanonymous
smtpd_sasl_local_domain = $myhostname
broken_sasl_auth_clients = yes

# Restrict relaying to authenticated users
smtpd_relay_restrictions = permit_mynetworks, permit_sasl_authenticated, reject_unauth_destination

# Cyrus SASL configuration path
smtpd_sasl_path = smtpd
```

### User Management with sasldb2

```bash
# Add a user to the SASL password database
sudo saslpasswd2 -c -u example.com username

# List all users
sudo sasldblistusers2

# Delete a user
sudo saslpasswd2 -d username
```

### SASL + LDAP Backend

For larger deployments, Cyrus SASL can authenticate against LDAP:

```ini
# /etc/sasl2/smtpd.conf
pwcheck_method: saslauthd
mech_list: PLAIN LOGIN
```

Then configure `saslauthd` for LDAP in `/etc/saslauthd.conf`:

```ini
ldap_servers: ldap://ldap.example.com
ldap_search_base: ou=users,dc=example,dc=com
ldap_filter: (&(uid=%U)(objectClass=posixAccount))
ldap_bind_dn: cn=admin,dc=example,dc=com
ldap_bind_pw: secret
```

### Docker Compose Example

Here is a minimal Postfix + Cyrus SASL setup:

```yaml
version: "3.8"
services:
  postfix:
    image: boky/postfix:latest
    container_name: postfix
    hostname: mail.example.com
    environment:
      ALLOWED_SENDER_DOMAINS: example.com
      POSTFIX_myhostname: mail.example.com
      POSTFIX_mydomain: example.com
    volumes:
      - ./postfix/main.cf:/etc/postfix/main.cf:ro
      - ./sasl/smtpd.conf:/etc/sasl2/smtpd.conf:ro
      - ./sasl/sasldb2:/etc/sasldb2:ro
    ports:
      - "25:25"
      - "587:587"
    restart: unless-stopped
```

## Dovecot SASL: Integrated Authentication

Dovecot SASL is the modern preferred approach for Postfix deployments that already use Dovecot as the IMAP/POP3 server. Instead of maintaining a separate SASL database, Dovecot reuses its existing user database (passdb) for SMTP authentication — eliminating duplicate credential management.

### Why Dovecot SASL?

- **Single credential store**: Users authenticate with the same password for IMAP and SMTP
- **No saslauthd overhead**: Postfix communicates with Dovecot directly via a Unix socket
- **Rich backend support**: Dovecot's passdb supports SQL, LDAP, PAM, passwd-file, static, and more
- **Active development**: Dovecot is actively maintained with security updates

### Dovecot Configuration

Enable SASL in `/etc/dovecot/conf.d/10-master.conf`:

```ini
service auth {
  # Postfix SASL socket
  unix_listener /var/spool/postfix/private/auth {
    mode = 0660
    user = postfix
    group = postfix
  }

  # Dovecot internal auth
  unix_listener auth-userdb {
    mode = 0600
    user = vmail
    group = vmail
  }
}
```

Configure authentication mechanisms in `/etc/dovecot/conf.d/10-auth.conf`:

```ini
auth_mechanisms = plain login

# Use SQL backend for virtual users
passdb {
  driver = sql
  args = /etc/dovecot/dovecot-sql.conf.ext
}

userdb {
  driver = static
  args = uid=vmail gid=vmail home=/var/mail/vhosts/%d/%n
}
```

### Postfix Side Configuration

In `/etc/postfix/main.cf`:

```ini
# Dovecot SASL via Unix socket
smtpd_sasl_type = dovecot
smtpd_sasl_path = private/auth
smtpd_sasl_auth_enable = yes
smtpd_sasl_security_options = noanonymous
smtpd_sasl_tls_security_options = noanonymous
smtpd_tls_auth_only = yes
smtpd_relay_restrictions = permit_mynetworks, permit_sasl_authenticated, reject_unauth_destination
```

### Docker Compose Example

```yaml
version: "3.8"
services:
  postfix:
    image: tvial/docker-mailserver:latest
    container_name: mailserver
    hostname: mail.example.com
    env_file: mailserver.env
    volumes:
      - maildata:/var/mail
      - mailstate:/var/mail-state
      - ./config/:/tmp/docker-mailserver/
      - /etc/letsencrypt:/etc/letsencrypt:ro
    ports:
      - "25:25"
      - "587:587"
      - "993:993"
    cap_add:
      - NET_ADMIN
      - SYS_PTRACE
    restart: always

volumes:
  maildata:
  mailstate:
```

With `docker-mailserver`, Dovecot SASL is preconfigured — users are managed through `setup.sh` commands:

```bash
# Add a user
docker exec -it mailserver setup email add user@example.com password123

# Add an alias
docker exec -it mailserver setup alias add alias@example.com user@example.com
```

## GNU libgsasl: Modern and Lightweight

GNU SASL (libgsasl) is a relatively newer implementation focused on modern authentication mechanisms — particularly SCRAM, GSSAPI (Kerberos), and SAML. It's lighter than Cyrus SASL and avoids much of the legacy baggage while supporting more contemporary standards.

### Installation

```bash
# Debian/Ubuntu
sudo apt install gsasl libgsasl7 libgsasl-dev

# RHEL/Fedora
sudo dnf install gsasl libgsasl

# Build from source
wget https://ftp.gnu.org/gnu/gsasl/gsasl-2.2.1.tar.gz
tar xzf gsasl-2.2.1.tar.gz
cd gsasl-2.2.1
./configure --prefix=/usr/local
make && sudo make install
```

### Command-Line Testing

GNU SASL provides a powerful command-line client for testing SMTP authentication:

```bash
# Test SMTP PLAIN auth against a server
gsasl -m PLAIN --no-starttls --imap mail.example.com     -a user@example.com -p password123

# Test SCRAM-SHA-256 (password from stdin)
echo "password123" | gsasl -m SCRAM-SHA-256 --no-starttls     --smtp mail.example.com -a user@example.com

# GSSAPI (Kerberos) authentication
kinit user@EXAMPLE.COM
gsasl -m GSSAPI --smtp mail.example.com
```

### Postfix Integration

GNU SASL integrates with Postfix via the Cyrus SASL compatibility layer or as a standalone service:

```ini
# /etc/postfix/main.cf
smtpd_sasl_type = cyrus
smtpd_sasl_path = smtpd
```

GNU SASL reads from `/etc/gsasl.conf` (though most Postfix setups use the `--application` flag):

```bash
# Start gsasl as a standalone SASL server
gsasl --server --application smtpd     --authentication-db /etc/gsasl/users.db     --mechanisms PLAIN LOGIN SCRAM-SHA-256
```

### SCRAM-SHA-256 Setup

One of the strongest reasons to choose GNU SASL is first-class SCRAM support — enabling password-based authentication without transmitting the password in plaintext:

```bash
# Register a user with SCRAM credentials
gsasl --mkpasswd --mechanism SCRAM-SHA-256 user@example.com
# Enter password, output is the stored credential

# Verify SCRAM credentials
gsasl -m SCRAM-SHA-256 --smtp localhost:587     -a user@example.com
```

## Choosing the Right SASL Provider

### Use Cyrus SASL When

- You have an existing Postfix deployment without Dovecot (e.g., using Courier or no IMAP server)
- You need LDAP-backed authentication and already have Cyrus SASL LDAP configuration
- You require legacy mechanisms like NTLM or OTP
- Your distribution's packages are well-tested and you prefer stability over features

### Use Dovecot SASL When

- You already run Dovecot as your IMAP/POP3 server (the most common self-hosted setup)
- You want **one** credential database for both IMAP and SMTP
- You need SQL-backed virtual user management
- You prefer the simplicity of Unix socket communication (no TCP overhead)

### Use GNU libgsasl When

- You want modern SCRAM-SHA-256 authentication without plaintext password exposure
- You deploy Kerberos/GSSAPI in your infrastructure
- You need a lightweight SASL implementation without the legacy overhead of Cyrus
- You are building a new deployment and want SAML 2.0 / OpenID Connect integration

## Why Self-Host Your SMTP Authentication?

Controlling your own SMTP authentication infrastructure gives you benefits that commercial email services cannot match:

**Complete credential sovereignty**: When Google or Microsoft handles your SMTP authentication, they hold your users' credentials and can terminate access at will. Self-hosted SASL puts you in control of every authentication attempt, with full audit logging. See our [complete email server guide](../self-hosted-email-server-postfix-dovecot-rspamd-complete-guide-2026/) for end-to-end deployment instructions.

**No per-user fees**: Commercial SMTP relay services charge per mailbox or per thousand emails. With Dovecot SASL backed by an SQL database, you can provision thousands of mailboxes at zero per-user cost — only your server hardware and bandwidth expenses.

**Custom authentication policies**: Want to restrict SMTP authentication to specific IP ranges? Enforce MFA for SMTP? Log every authentication attempt to a SIEM? Self-hosted SASL gives you raw access to implement whatever policy your security requirements demand. Our [email security auditing guide](../2026-05-12-self-hosted-email-security-auditing-mailauth-mailsec-check-checkdmarc-guide/) covers comprehensive email security validation.

**Hybrid architectures**: Run Postfix with Dovecot SASL internally while using GNU SASL's SCRAM support for external-facing submission on port 587. Self-hosted SASL is composable — mix and match backends for different use cases within the same deployment.

**Data residency compliance**: For organizations subject to GDPR, HIPAA, or data sovereignty regulations, self-hosted SASL keeps authentication data within your controlled infrastructure — no third-party processors touching user credentials.

## FAQ

### Can I use multiple SASL providers simultaneously?

Yes. Postfix can be configured with different SASL settings per listener. For example, use Dovecot SASL on port 587 (submission) for authenticated users, and Cyrus SASL on port 25 for inbound SMTP from other mail servers (where SMTP AUTH is not performed). Each `smtpd` listener in `master.cf` can have its own `-o smtpd_sasl_type=...` override.

### Is CRAM-MD5 still secure?

No. CRAM-MD5 has been deprecated since 2014 (RFC 8600, then formally obsoleted). The MD5 hash is cryptographically broken, and the mechanism provides no channel binding — making it vulnerable to MITM attacks even with TLS. Modern deployments should use SCRAM-SHA-256 (preferred) or PLAIN/LOGIN over enforced TLS on port 587 (RFC 8314).

### How do I enforce TLS before SASL authentication?

Add `smtpd_tls_auth_only = yes` to your `main.cf`. This prevents clients from sending AUTH commands over unencrypted connections on port 587. For port 25 (MTA-to-MTA SMTP), you typically want STARTTLS but not mandatory TLS, as many legitimate mail servers still send unencrypted SMTP.

### Does Dovecot SASL support LDAP?

Yes, through Dovecot's passdb system. Configure passdb with driver `ldap` and provide an LDAP configuration file mapping users to their credentials. Dovecot supports both direct LDAP binds (verifying the password against the LDAP server) and pre-hashed password lookups. This works identically for both IMAP and SASL authentication — a single LDAP query serves both protocols.

### How do I debug SASL authentication failures?

Check the mail logs with increasing verbosity:

```bash
# Postfix SASL logging
postconf -e "smtpd_sasl_verbose = yes"
postfix reload

# Dovecot auth debug
doveadm log errors

# Test SASL manually
testsaslauthd -u user@example.com -p password123

# GNU SASL test
gsasl -d -m PLAIN --smtp localhost:587 -a user@example.com
```

The key log file is `/var/log/mail.log` (Debian/Ubuntu) or `/var/log/maillog` (RHEL). Look for lines containing `sasl_method=PLAIN` or `sasl_username=`.

For more email infrastructure topics, see our [SMTP relay pool comparison](../2026-05-17-self-hosted-smtp-relay-pool-postal-haraka-stalwart-guide/) and [mail server health monitoring guide](../2026-05-26-self-hosted-mail-server-health-monitoring-postfix-exporter-swaks-mailu-guide/).

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted SMTP SASL Authentication: Cyrus SASL vs Dovecot SASL vs GNU libgsasl Guide",
  "description": "Comprehensive comparison of Cyrus SASL, Dovecot SASL, and GNU libgsasl for self-hosted SMTP authentication — configuration, Postfix integration, and SCRAM support.",
  "datePublished": "2026-06-02",
  "dateModified": "2026-06-02",
  "author": {
    "@type": "Organization",
    "name": "OpenSwap Guide"
  },
  "publisher": {
    "@type": "Organization",
    "name": "OpenSwap Guide",
    "logo": {
      "@type": "ImageObject",
      "url": "https://pistack.xyz/logo.png"
    }
  }
}
</script>
