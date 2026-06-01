---
title: "Self-Hosted PAM Authentication Modules: Google Authenticator vs pam_u2f vs pam_oath vs pam_duo"
date: "2026-06-01"
tags: ["authentication", "security", "linux", "2fa", "pam", "server-hardening", "mfa", "identity"]
draft: false
---

## Introduction

Pluggable Authentication Modules (PAM) form the backbone of Linux authentication. Every SSH login, `sudo` invocation, and system service authentication flows through PAM's modular stack. While the default `pam_unix` module handles basic password authentication, modern security requirements demand multi-factor authentication (MFA), hardware token support, and push-based verification.

This guide compares four major PAM modules for adding second-factor authentication to your Linux servers: **Google Authenticator PAM** (TOTP-based), **pam_u2f** (FIDO2/U2F hardware keys), **pam_oath** (OATH HOTP/TOTP from the PAM ecosystem), and **pam_duo** (Duo Security push-based 2FA).

## Why Self-Host Your Authentication Stack?

Self-hosting your PAM authentication layer means you control the entire authentication pipeline — no third-party service sees your login attempts, user credentials never leave your infrastructure, and you're not vendor-locked into a proprietary MFA solution that could change pricing or shut down.

For organizations running on-premises or colocated infrastructure, local PAM modules integrate directly with existing directory services like OpenLDAP, FreeIPA, or Samba AD. You can enforce MFA policies uniformly across SSH, console, and `sudo` without deploying a separate authentication proxy.

Beyond security, self-hosting eliminates per-user SaaS licensing costs for MFA. A Google Authenticator PAM deployment costs nothing beyond the server it runs on, while pam_u2f works with any FIDO2-compatible hardware key — no recurring fees. For teams already managing their own Linux infrastructure, adding PAM-based MFA is a natural extension of existing operations.

Beyond the security benefits, PAM-based MFA is transparent to applications. Unlike application-layer MFA that requires modifying every web app with OAuth/OIDC callbacks, PAM sits below the application — any service that authenticates via PAM (SSH, sudo, login, su, cron, atd) automatically inherits your MFA policy. This means your database login, your monitoring agent, and your deployment scripts all get the same MFA protection without per-application configuration. For teams managing dozens of services across hundreds of servers, this uniformity is invaluable.

PAM modules also integrate with existing monitoring and alerting stacks. Failed authentication attempts flow through syslog, which you can ship to your SIEM or log aggregator. Combined with fail2ban or crowdsec, you can automatically block IPs that trigger repeated MFA failures — creating a defense-in-depth authentication perimeter that spans your entire server fleet.


If you're also hardening SSH access, see our [SSH security auditing guide](../2026-06-01-self-hosted-ssh-security-auditing-ssh-audit-sshscan-lynis-guide/). For hardware-based authentication at the application layer, check our [passkey authentication comparison](../self-hosted-passkey-webauthn-authentication-solutions-2026/). For broader security awareness, our [phishing simulation guide](../self-hosted-phishing-simulation-security-awareness-training-gophish-2026/) complements MFA deployment.

## Comparison Table

| Feature | pam_google_authenticator | pam_u2f | pam_oath | pam_duo |
|---------|--------------------------|---------|----------|---------|
| **Auth Method** | TOTP (time-based) | FIDO2/U2F hardware | HOTP/TOTP (OATH) | Push notification |
| **Hardware Required** | Phone/app (any TOTP) | YubiKey/security key | Hardware token or app | Phone with Duo app |
| **Offline Capable** | Yes (fully offline) | Yes (fully offline) | Yes (fully offline) | No (requires Duo cloud) |
| **Dependency** | libpam-google-authenticator | libpam-u2f | liboath (oath-toolkit) | duo_unix + Internet |
| **Setup Complexity** | Low | Low | Medium | Medium |
| **RHEL/CentOS Package** | google-authenticator | pam_u2f | pam_oath | duo_unix |
| **Debian/Ubuntu Package** | libpam-google-authenticator | libpam-u2f | libpam-oath | duo-unix |
| **GitHub Stars** | 1,986 ★ | 642 ★ | Part of oath-toolkit | 360 ★ |
| **Last Updated** | Feb 2026 | Mar 2025 | Active (system project) | May 2026 |

## PAM Stack Configuration

PAM configuration files live in `/etc/pam.d/`. Each service (sshd, sudo, login) has its own file that defines the authentication modules and their control flags. Here's the standard structure:

```
# /etc/pam.d/sshd
auth       required     pam_env.so
auth       required     pam_unix.so
auth       optional     pam_google_authenticator.so
account    required     pam_unix.so
session    required     pam_unix.so
```

The control flags determine behavior: `required` (must pass, but continues to next module), `requisite` (must pass, stops on failure), `sufficient` (if passes, skip remaining), and `optional` (pass or fail doesn't matter).

### Installing pam_google_authenticator

```bash
# Debian/Ubuntu
sudo apt install libpam-google-authenticator

# RHEL/CentOS/Fedora
sudo dnf install google-authenticator

# Generate a TOTP secret for the current user
google-authenticator -t -d -f -r 3 -R 30 -w 3
```

Then configure PAM to require it. For SSH, add to `/etc/pam.d/sshd`:

```
auth required pam_google_authenticator.so nullok
```

The `nullok` option allows users without a configured secret to still log in. Remove it once all users have set up their tokens.

**Important SSH configuration**: In `/etc/ssh/sshd_config`, ensure:
```
ChallengeResponseAuthentication yes
AuthenticationMethods publickey,keyboard-interactive
```

This requires both SSH key AND TOTP code for login — true two-factor authentication.

### Installing pam_u2f

```bash
# Debian/Ubuntu
sudo apt install libpam-u2f

# RHEL/CentOS
sudo dnf install pam_u2f

# Register a U2F key for the current user
pamu2fcfg -u$(whoami) > ~/.config/Yubico/u2f_keys

# For multiple keys, append with -n flag
pamu2fcfg -n >> ~/.config/Yubico/u2f_keys
```

PAM configuration in `/etc/pam.d/sshd`:
```
auth required pam_u2f.so authfile=/etc/u2f_mappings cue
```

The `authfile` can be a central mapping file or user-specific `~/.config/Yubico/u2f_keys`. The `cue` option prompts users to touch their security key.

**User mapping file format** (`/etc/u2f_mappings`):
```
username:KeyHandle1,PublicKey1:KeyHandle2,PublicKey2
```

### Installing pam_oath

```bash
# Debian/Ubuntu
sudo apt install libpam-oath oathtool

# RHEL/CentOS
sudo dnf install pam_oath oathtool

# Generate a HOTP/TOTP secret
oathtool -v --totp --base32 $(head -c 20 /dev/urandom | base32)
```

PAM uses a central users file at `/etc/users.oath`:
```
# Format: HOTP/TOTP  username  -  secret_key
HOTP/T30  alice  -  00aabbccddeeff00112233445566778899
HOTP/T30  bob    -  ffee99887766554433221100aabbccdd
```

PAM configuration:
```
auth required pam_oath.so usersfile=/etc/users.oath window=20 digits=6
```

### Installing pam_duo

```bash
# Download from Duo's official repo
wget https://dl.duosecurity.com/duo_unix-latest.tar.gz
tar xzf duo_unix-latest.tar.gz
cd duo_unix-*
./configure --with-pam --prefix=/usr && make && sudo make install
```

Configure `/etc/duo/pam_duo.conf`:
```
[duo]
host = api-XXXXXXXX.duosecurity.com
ikey = YOUR_INTEGRATION_KEY
skey = YOUR_SECRET_KEY
failmode = safe
pushinfo = yes
autopush = yes
prompts = 3
```

PAM configuration:
```
auth required pam_duo.so
```

## PAM Configuration Patterns

### Pattern 1: SSH Key + TOTP (Most Common)

This gives you public-key first factor plus time-based code second factor:

```
# /etc/pam.d/sshd
auth [success=1 default=ignore] pam_unix.so
auth required pam_google_authenticator.so
```

### Pattern 2: Password OR Hardware Key

Allows login with EITHER password or U2F key (convenient migration pattern):

```
auth sufficient pam_u2f.so
auth required pam_unix.so
```

### Pattern 3: Required Hardware Key + Optional TOTP

Both factors required for high-security environments:

```
auth required pam_u2f.so
auth required pam_google_authenticator.so
auth required pam_unix.so
```

### Pattern 4: Fail-Open with Duo Push

```
auth sufficient pam_unix.so
auth required pam_duo.so
```

## Testing PAM Configuration

PAM configurations are notoriously unforgiving — one mistake can lock you out. Always test in a separate terminal session:

```bash
# Test PAM for a specific service without actually authenticating
sudo pamtester sshd alice authenticate

# Check PAM configuration syntax
pam-auth-update --check

# View PAM debug output (add 'debug' to module options)
sudo tail -f /var/log/auth.log
```

**Critical safety tip**: Keep a root shell open in a separate tmux/screen session when modifying PAM. If you lock yourself out of SSH, you can recover through the console.

## Security Best Practices

1. **Use `required` not `requisite` for MFA modules** — `requisite` stops processing immediately on failure, which means error messages don't reach the remaining modules. `required` continues to the end of the stack, giving complete audit logging.

2. **Centralize user secret storage** — For pam_oath and pam_u2f with `authfile`, store mappings in a central, root-readable-only file (`/etc/u2f_mappings`, `/etc/users.oath`). Never rely on user-writable home directories for security-critical data.

3. **Rate-limit authentication attempts** — Combine with `pam_faillock.so` to lock accounts after repeated failures:
```
auth required pam_faillock.so preauth silent deny=5 unlock_time=900
auth required pam_faillock.so authfail deny=5 unlock_time=900
```

4. **Avoid `nullok` in production** — The `nullok` option for pam_google_authenticator allows users without configured tokens to bypass MFA. Remove it once all users are enrolled.

5. **Use `failmode=secure` for pam_duo** — In production, change from `failmode=safe` (allows access when Duo is unreachable) to `failmode=secure` (denies access). `safe` mode is appropriate during initial rollout.

## FAQ

### Can I use multiple PAM MFA modules simultaneously?

Yes — PAM's stacking design allows chaining. A common enterprise pattern is `pam_unix.so` (password) + `pam_google_authenticator.so` (TOTP) + `pam_u2f.so` (hardware key). However, each additional module adds authentication latency and complexity. Most deployments stop at two factors.

### What happens if I lose my TOTP device or hardware key?

With pam_google_authenticator, each user's `~/.google_authenticator` file contains emergency scratch codes. Print these and store them securely. For pam_u2f, register at least two U2F keys per user — keep one as a backup in a safe location. For pam_oath, administrators can generate new secrets and update `/etc/users.oath`.

### Does Duo's cloud dependency create a single point of failure?

Yes. If Duo's service is unreachable and you've configured `failmode=safe`, authentication falls through to the next PAM module (typically pam_unix password). With `failmode=secure`, all authentications fail. For mission-critical servers, prefer offline-capable modules like pam_google_authenticator or pam_u2f.

### Which module has the lowest operational overhead?

pam_google_authenticator wins on simplicity — a single package install, user-side `google-authenticator` setup, and one PAM line. No hardware to distribute, no external service dependency, and TOTP apps are free on all platforms. The tradeoff is slightly weaker security compared to hardware-backed U2F.

### Can PAM modules integrate with centralized directory services?

Yes. The PAM stack natively supports LDAP via `pam_ldap.so` and Kerberos via `pam_krb5.so`. You can layer MFA on top: LDAP for user identification, TOTP for second factor. FreeIPA bundles this integration out of the box with its own OTP module.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到科技监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测科技相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted PAM Authentication Modules: Google Authenticator vs pam_u2f vs pam_oath vs pam_duo",
  "description": "Comprehensive comparison of Linux PAM authentication modules for multi-factor authentication. Covers Google Authenticator PAM (TOTP), pam_u2f (FIDO2/U2F hardware keys), pam_oath (OATH HOTP/TOTP), and pam_duo (push-based 2FA) with full configuration examples and PAM stack patterns.",
  "datePublished": "2026-06-01",
  "dateModified": "2026-06-01",
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
