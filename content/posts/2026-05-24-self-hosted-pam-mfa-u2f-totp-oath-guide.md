---
title: "Self-Hosted PAM Multi-Factor Authentication: pam-u2f vs Google Authenticator PAM vs libpam-oath"
date: "2026-05-21"
tags: ["authentication", "pam", "mfa", "totp", "u2f", "fido2", "security", "ssh"]
draft: false
---

Multi-factor authentication (MFA) is essential for securing self-hosted servers, but most organizations rely on cloud-based MFA services like Duo, Okta, or Azure MFA. For fully self-hosted infrastructure, PAM (Pluggable Authentication Module) provides MFA capabilities without external dependencies. In this guide, we compare three open-source PAM MFA modules: **pam-u2f** (FIDO2/U2F hardware keys), **Google Authenticator PAM** (TOTP time-based codes), and **libpam-oath** (OATH HOTP/TOTP protocols) — evaluating their security models, deployment complexity, and user experience.

## PAM MFA Architecture on Linux

Linux authentication flows through the PAM stack, defined in `/etc/pam.d/` configuration files. Each service (SSH, login, sudo) has its own PAM configuration that chains authentication modules. Adding an MFA module inserts an additional required step before granting access:

```
# /etc/pam.d/sshd (excerpt)
auth    required    pam_unix.so
auth    required    pam_u2f.so          # Hardware key verification
# or:
auth    required    pam_google_authenticator.so  # TOTP code verification
# or:
auth    required    pam_oath.so         # OATH HOTP/TOTP verification
```

The `required` control flag means the MFA check must pass in addition to the standard password authentication. Using `sufficient` would allow MFA alone to grant access (passwordless login with a hardware key).

## pam-u2f: FIDO2/U2F Hardware Key Authentication

pam-u2f, maintained by Yubico, enables FIDO2 and U2F hardware security key authentication for any PAM-enabled service. Users authenticate by inserting a USB security key (YubiKey, SoloKey, Nitrokey) and touching it — no code entry required.

### Installation and Configuration

```bash
# Install pam-u2f (Debian/Ubuntu)
apt install libpam-u2f

# Install pam-u2f (RHEL/CentOS/Fedora)
dnf install pam-u2f
```

Registering a user's hardware key:

```bash
# Create the .config/Yubico directory
mkdir -p ~/.config/Yubico

# Register the key (user inserts and touches the key when prompted)
pamu2fcfg > ~/.config/Yubico/u2f_keys

# For a backup key (recommended):
pamu2fcfg -n >> ~/.config/Yubico/u2f_keys
```

PAM configuration for SSH:

```
# /etc/pam.d/sshd
auth    required    pam_u2f.so cue nouserok
```

The `cue` flag displays a visual prompt ("Please touch the device"), and `nouserok` allows login without MFA for users who haven't registered a key (useful during migration).

### Docker Deployment for Testing

While PAM modules run on the host system, you can test pam-u2f in a Docker container with USB passthrough:

```yaml
version: "3.8"
services:
  pam-test:
    image: ubuntu:24.04
    container_name: pam-u2f-test
    privileged: true
    devices:
      - /dev/hidraw0:/dev/hidraw0
    volumes:
      - ./pam-configs:/etc/pam.d
    command: >
      bash -c "
        apt update && apt install -y libpam-u2f openssh-server &&
        /usr/sbin/sshd -D
      "
    restart: unless-stopped
```

### pam-u2f Strengths

| Feature | Details |
|---------|---------|
| Security | Phishing-resistant (FIDO2), hardware-bound credential |
| User Experience | Touch-to-authenticate — no code entry |
| Protocol | FIDO2 CTAP2 / U2F CTAP1 |
| Key Compatibility | YubiKey, SoloKey, Nitrokey, Feitian, any FIDO2 device |
| Offline Operation | Fully offline — no network dependency |
| Cost | Hardware key required ($25-75 per user) |
| GitHub Stars | 638 |

## Google Authenticator PAM: TOTP Time-Based Codes

Google Authenticator's PAM module generates and verifies TOTP (Time-Based One-Time Password) codes compatible with any TOTP app (Google Authenticator, FreeOTP, Authy, 1Password). Users scan a QR code during setup, then enter a 6-digit code that changes every 30 seconds.

### Installation and Configuration

```bash
# Install (Debian/Ubuntu)
apt install libpam-google-authenticator

# Install (RHEL/CentOS/Fedora)
dnf install google-authenticator
```

Per-user setup — each user runs this to generate their TOTP secret:

```bash
google-authenticator -t -d -f -r 3 -R 30 -w 3

# Flags explained:
# -t: Time-based (TOTP)
# -d: Disallow reuse of tokens
# -f: Force write to ~/.google_authenticator
# -r 3 -R 30: Rate limit (3 attempts per 30 seconds)
# -w 3: Window size (accepts codes within ±3 time steps)
```

This outputs a QR code (for scanning) and scratch codes (for emergency access):

```
Your new secret key is: ABCDEFGHIJKLMNOP
Your verification code is 123456
Your emergency scratch codes are:
  11111111
  22222222
  33333333
  44444444
  55555555
```

PAM configuration for SSH:

```
# /etc/pam.d/sshd
auth    required    pam_google_authenticator.so nullok
```

The `nullok` flag allows users without a `.google_authenticator` file to log in without the TOTP code — useful during the migration period.

### Google Authenticator PAM Strengths

| Feature | Details |
|---------|---------|
| Security | Time-based codes resistant to replay attacks |
| User Experience | Requires manual code entry every login |
| Protocol | RFC 6238 TOTP (30-second intervals) |
| App Compatibility | Works with any TOTP app |
| Offline Operation | Server-side verification is offline; app generates codes offline |
| Cost | Free — no hardware required |
| GitHub Stars | 1,984 |

## libpam-oath: OATH HOTP and TOTP

libpam-oath, maintained by the OATH Initiative, provides both HOTP (HMAC-Based One-Time Password, counter-based) and TOTP (Time-Based One-Time Password, time-based) authentication through PAM. Unlike Google Authenticator which only supports TOTP, libpam-oath supports both standards, plus a file-based user database that can be centrally managed.

### Installation and Configuration

```bash
# Install (Debian/Ubuntu)
apt install libpam-oath oathtool

# Install (RHEL/CentOS/Fedora)
dnf install pam_oath oath-toolkit
```

Setting up the users file:

```bash
# /etc/users.oath
# Format: HOTP/T30/6 - username - hex_secret
HOTP/T30/6  admin     -  a1b2c3d4e5f6a7b8c9d0e1f2
TOTP/T30/6  deploy    -  1234567890abcdef12345678
HOTP/T30/6  webmaster -  fedcba0987654321fedcba09

# Generate a random secret:
head -20 /dev/urandom | sha256sum | cut -c1-30
```

Generate a QR code for the user:

```bash
oathtool --totp --verbose a1b2c3d4e5f6a7b8c9d0e1f2
# Shows the current TOTP value for testing
```

PAM configuration:

```
# /etc/pam.d/sshd
auth    required    pam_oath.so usersfile=/etc/users.oath window=20 digits=6
```

### libpam-oath Strengths

| Feature | Details |
|---------|---------|
| Security | Supports both HOTP (counter) and TOTP (time) |
| Protocol | RFC 4226 HOTP + RFC 6238 TOTP |
| Central Management | Single `/etc/users.oath` file for all users |
| Window Size | Configurable token window for clock skew tolerance |
| User Experience | Manual code entry (same as Google Authenticator) |
| Cost | Free — no hardware required |
| GitHub Stars | Part of OATH Toolkit (community-maintained) |

## Comparison: pam-u2f vs Google Authenticator PAM vs libpam-oath

| Criteria | pam-u2f (FIDO2) | Google Authenticator (TOTP) | libpam-oath (HOTP/TOTP) |
|----------|----------------|----------------------------|------------------------|
| Factor Type | Possession (hardware key) | Possession (smartphone app) | Possession (smartphone/app) |
| Phishing Resistance | Yes (cryptographic challenge-response) | No (codes can be phished) | No (codes can be phished) |
| Setup per User | Register hardware key | Scan QR code | Generate secret + QR |
| Login Experience | Insert + touch key | Enter 6-digit code | Enter 6-digit code |
| Offline Capability | Fully offline | Fully offline | Fully offline |
| Central Management | Per-user key files | Per-user config files | Single users.oath file |
| Backup/Recovery | Backup key or scratch codes | Emergency scratch codes | Counter resync (HOTP) |
| Cost | $25-75 per hardware key | Free | Free |
| Best For | High-security environments | General-purpose MFA | Legacy HOTP requirements |

## Security Considerations

**Phishing resistance** is the primary differentiator between hardware-key and code-based MFA. pam-u2f uses a cryptographic challenge-response protocol where the server sends a challenge that the hardware key signs. An attacker cannot replay or forward this challenge because the signature is bound to the server's origin domain. In contrast, TOTP codes (Google Authenticator and libpam-oath) are simple numeric values that can be intercepted via phishing pages and immediately reused by the attacker within the 30-second validity window.

For high-value accounts (root SSH access, database servers, CI/CD deployment keys), pam-u2f provides measurably stronger security. For general user accounts on less critical systems, TOTP-based MFA still provides substantial protection against credential stuffing and password brute-force attacks.

**Rate limiting** is essential for all three modules. Both Google Authenticator PAM and libpam-oath include built-in rate limiting (`-r 3 -R 30` for Google Authenticator, `window=20` for libpam-oath). pam-u2f is inherently rate-limited by the physical requirement of touching a hardware key.

**Emergency access** must be planned for all MFA methods. pam-u2f users should register a backup key. TOTP users should store emergency scratch codes in a secure location (password manager, printed and stored in a safe). libpam-oath HOTP users should note their current counter value for resynchronization if the server and client counters drift out of sync.

## Why Self-Host Your MFA Infrastructure?

Running your own PAM-based MFA on self-hosted servers eliminates dependency on cloud authentication services. When you use Duo, Okta, or Azure MFA, every login attempt traverses external infrastructure. The authentication provider sees when your users log in, from which IP addresses, and how frequently. This metadata is valuable intelligence that you surrender to a third party simply by outsourcing MFA.

Self-hosted PAM MFA keeps all authentication data — login timestamps, source IPs, success/failure rates — within your infrastructure. For organizations in regulated industries, this data sovereignty requirement is often non-negotiable. Healthcare organizations subject to HIPAA, financial institutions under SOX, and government contractors with CMMC requirements all benefit from keeping authentication telemetry on-premises.

Resilience is another critical advantage. If your cloud MFA provider experiences an outage (as Duo did in 2023, locking out millions of users for hours), self-hosted PAM MFA continues working without interruption. Your SSH access, sudo elevation, and service authentication remain operational because the verification logic runs locally on each server.

Cost is a consideration for large deployments. Duo charges per-user pricing that scales linearly with team size. Self-hosted PAM MFA modules are free and open-source — the only marginal cost is hardware security keys for pam-u2f deployments ($25-75 per user, one-time purchase). For a 100-person team, this represents a savings of thousands of dollars annually compared to cloud MFA subscriptions.

Integration flexibility matters too. PAM modules work with any PAM-aware service — SSH, login, sudo, su, cron, and custom applications. Cloud MFA providers typically require specific integrations (SAML, RADIUS, or proprietary APIs) that may not cover all your services. With PAM MFA, you add multi-factor protection to any service that uses PAM with a single configuration line.

For those already running self-hosted identity infrastructure, see our [MFA/OTP server comparison](../2026-05-07-privacyidea-vs-linotp-vs-2fauth-self-hosted-mfa-otp-servers-guide/) for centralized MFA platforms, our [PAM management guide](../2026-05-11-self-hosted-pam-management-sssd-pwquality-pam-auth-update-guide/) for system-level authentication configuration, and our [SSO solutions comparison](../2026-04-21-casdoor-vs-zitadel-vs-authentik-lightweight-sso-guide/) for single sign-on alternatives.

## FAQ

### Can I use multiple MFA methods simultaneously on the same server?

Yes. Linux PAM supports stacking multiple authentication modules. You can configure SSH to require BOTH a TOTP code AND a hardware key touch by adding both modules to `/etc/pam.d/sshd`:

```
auth    required    pam_google_authenticator.so
auth    required    pam_u2f.so
```

This provides defense-in-depth — an attacker would need both the user's phone and their hardware key. Be aware that this increases login friction and may frustrate users.

### What happens if a user loses their hardware key or TOTP device?

For pam-u2f: Users should register a backup key during initial setup (the `-n` flag in `pamu2fcfg`). Without a backup key, an administrator must delete the user's `u2f_keys` file and re-register a new key.

For TOTP (Google Authenticator/libpam-oath): Emergency scratch codes are generated during initial setup and should be stored securely. If scratch codes are exhausted, an administrator must generate a new TOTP secret for the user and have them re-scan the QR code.

### Does pam-u2f work over SSH without USB passthrough?

pam-u2f requires the hardware key to be physically connected to the server running the PAM module. For SSH login, the user's key must be plugged into the server itself — not the client machine. This makes pam-u2f ideal for physical console access but less practical for remote SSH sessions. For remote SSH with hardware key authentication, consider using FIDO2 SSH keys (native OpenSSH 8.2+) instead of PAM-based hardware key verification.

### Can I enforce MFA for specific users but not others?

Yes, using PAM's `pam_succeed_if.so` module to conditionally apply MFA:

```
auth    [success=1 default=ignore]  pam_succeed_if.so user notingroup mfa-required
auth    required    pam_google_authenticator.so
auth    required    pam_unix.so
```

This configuration requires MFA only for users in the `mfa-required` group. Users not in this group skip the MFA module entirely. This is useful during MFA migration — add users to the group incrementally as they register their MFA devices.

### How does HOTP (counter-based) differ from TOTP (time-based) in libpam-oath?

HOTP generates codes based on a counter that increments each time a code is generated. The client and server must maintain synchronized counters. If the user generates codes without using them (e.g., accidentally pressing the key fob button multiple times), the counters drift and authentication fails until resynchronized. TOTP uses the current Unix timestamp (divided by 30 seconds) instead of a counter, eliminating drift issues as long as the server clock is accurate. TOTP is recommended for most deployments; HOTP is useful for environments where time synchronization is unreliable.

### Is libpam-oath compatible with Google Authenticator app?

Yes. libpam-oath with TOTP mode (`TOTP/T30/6`) uses the same RFC 6238 standard as Google Authenticator. Users can scan a QR code generated from the libpam-oath secret using the Google Authenticator app, FreeOTP, or any other TOTP-compatible application. The QR code URI format is: `otpauth://totp/user@hostname?secret=BASE32SECRET&issuer=hostname`.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted PAM Multi-Factor Authentication: pam-u2f vs Google Authenticator PAM vs libpam-oath",
  "description": "Compare self-hosted PAM MFA modules: pam-u2f (FIDO2), Google Authenticator (TOTP), and libpam-oath (HOTP/TOTP). Includes installation guides, Docker configs, and security analysis.",
  "datePublished": "2026-05-21",
  "dateModified": "2026-05-21",
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
