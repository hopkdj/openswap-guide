---
title: "OpenSSH vs Dropbear vs TinySSH in 2026: Which SSH Server Should You Actually Run?"
date: "2026-10-04"
tags: ["comparison", "guide", "self-hosted", "ssh", "security", "networking"]
draft: false
---

Your server's SSH daemon is the single most attacked process on the box. Every botnet on the internet scans port 22 continuously, and a single unpatched daemon is a full root compromise waiting to happen. Yet most people run whatever `apt install` gave them without ever asking whether the 2.5-million-line OpenSSH codebase is the right fit for a Raspberry Pi in a shed, an embedded router, or a hardened jump host.

Here is the uncomfortable truth: **OpenSSH is not the small, auditable program it was in 2001.** It is a sprawling, feature-rich daemon that ships with an SFTP server, agent forwarding, X11 forwarding, certificate infrastructure, and — as of the 2026 release cycle — post-quantum host keys. That is exactly the right tool for a general-purpose server. It is the wrong tool for a 32 MB device that only ever lets one key in.

This guide compares the three SSH servers that actually matter in 2026 — **OpenSSH, Dropbear, and TinySSH** — plus wolfSSH as a fourth option, using live GitHub data pulled on 2026-10-04.

## The 60-Second Verdict (TL;DR)

- **Run OpenSSH** on any normal Linux server. It is the reference implementation, it is the most audited, and everything (Ansible, rsync, git, Proxmox, Kubernetes tooling) assumes it. 4,033 stars, last commit 2026-10-03.
- **Run Dropbear** when the device is small: routers, embedded Linux, initramfs, IoT gateways, or where you need an SSH daemon under a few hundred kilobytes. 2,419 stars, last commit 2026-08-31.
- **Run TinySSH** when your threat model is "minimize the number of lines I have to trust". It deliberately implements *only* Ed25519 keys and a modern cipher suite. 1,534 stars, last commit 2026-10-01.
- **Run wolfSSH** if you need a small SSH stack with a commercial support path and FIPS-oriented builds. 499 stars, last commit 2026-10-02.

If you only read one line: **OpenSSH for servers, Dropbear for devices, TinySSH for paranoia.**

## Feature and Footprint Comparison

All star counts and last-push dates below were fetched live from GitHub on 2026-10-04.

| Feature | OpenSSH | Dropbear | TinySSH | wolfSSH |
|---|---|---|---|---|
| GitHub repo | `openssh/openssh-portable` | `mkj/dropbear` | `janmojzis/tinyssh` | `wolfSSL/wolfssh` |
| Stars | **4,033** | 2,419 | 1,534 | 499 |
| Last commit | 2026-10-03 | 2026-08-31 | 2026-10-01 | 2026-10-02 |
| Language | C | C | C | C |
| SFTP server | ✅ built in | ✅ (`dropbear-sftp`) | ❌ (use `scp`) | ✅ |
| Port forwarding | ✅ full | ✅ limited | ❌ | ✅ |
| Agent forwarding | ✅ | ✅ | ❌ | ✅ |
| Password auth | ✅ (optional) | ✅ | ❌ keys only | ✅ |
| Key types | RSA, ECDSA, Ed25519, **post-quantum** | RSA, ECDSA, Ed25519 | **Ed25519 only** | RSA, ECDSA, Ed25519 |
| X11 forwarding | ✅ | ❌ | ❌ | ❌ |
| SSH certificates | ✅ | ❌ | ❌ | ❌ |
| Typical binary size | ~1.2 MB | ~150 KB | **~80 KB** | ~200 KB |
| Config file | `sshd_config` | CLI flags / `-c` | CLI flags only | `wolfssh.conf` |
| Best for | Linux servers | embedded / routers | minimal attack surface | commercial embedded |

The pattern is obvious: **every feature you remove shrinks the daemon and the attack surface.** TinySSH gives up SFTP, forwarding, and every non-Ed25519 key type — and in exchange ships a daemon roughly 15x smaller than OpenSSH's.

## Which SSH Server for Which Situation?

| Your situation | Pick | Why |
|---|---|---|
| Standard VPS / bare-metal server | OpenSSH | Certificates, SFTP, forwarding, and tooling compatibility |
| Ansible / CI runners / git over SSH | OpenSSH | Only implementation with full agent + cert support |
| OpenWrt / router firmware | Dropbear | Already the OpenWrt default; tiny footprint |
| initramfs / rescue shell | Dropbear | Static-linked, no libc gymnastics |
| Bastion host facing the public internet | OpenSSH + hardening | Needs certs, MFA hooks, `Match` blocks |
| Appliance where you only need a shell | TinySSH | Smallest verifiable code base, Ed25519 only |
| FIPS-validated product | wolfSSH | FIPS-ready crypto module from wolfSSL |

## OpenSSH: The Default for a Reason

OpenSSH is the reference implementation. The 2026 `sshd_config` shipped in `openssh/openssh-portable` is a good snapshot of where the project stands — including this line, which tells you everything about the last three years of work:

```
#HostKey /etc/ssh/ssh_host_rsa_key
#HostKey /etc/ssh/ssh_host_ecdsa_key
#HostKey /etc/ssh/ssh_host_ed25519_key
#HostKey /etc/ssh/ssh_host_mldsa44_ed25519_key
```

That fourth host key type — **ML-DSA-44 hybridized with Ed25519** — is post-quantum. OpenSSH has been rolling out hybrid key exchange for several cycles now, and the host key side has caught up. Dropbear and TinySSH have nothing equivalent.

A sane hardened `sshd_config` for a public VPS, using the real directive defaults as the starting point:

```conf
# /etc/ssh/sshd_config
Port 22
AddressFamily inet

# Host keys: keep the modern ones
HostKey /etc/ssh/ssh_host_ed25519_key
HostKey /etc/ssh/ssh_host_ecdsa_key

# Authentication
PermitRootLogin no
PubkeyAuthentication yes
PasswordAuthentication no
KbdInteractiveAuthentication no
AuthorizedKeysFile .ssh/authorized_keys
MaxAuthTries 3
LoginGraceTime 30

# Only let the people who need in, in
AllowUsers deploy ops
AllowGroups ssh-users

# Kill idle sessions
ClientAliveInterval 300
ClientAliveCountMax 2

# Logging
SyslogFacility AUTH
LogLevel VERBOSE
```

Verify what the daemon *actually* believes rather than what you think the file says — this works on every OpenSSH 7.x+ build and is the single most useful command in this article:

```bash
# Dump the effective configuration (requires root)
sudo sshd -T | grep -Ei 'permitrootlogin|passwordauth|maxauthtries|allowusers'
```

For containerized labs, the LinuxServer.io image (`linuxserver/docker-openssh-server`, 614 stars, last push 2026-09-20) is the fastest way to stand up a disposable SSH target. This Compose file uses the environment variables documented by that image, including `PUBLIC_KEY` for key injection and `SUDO_ACCESS`:

```yaml
services:
  sshd:
    image: lscr.io/linuxserver/openssh-server:latest
    container_name: sshd
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=UTC
      - PUBLIC_KEY=ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI...you@host
      - SUDO_ACCESS=false
      - USER_NAME=labuser
      - PASSWORD_ACCESS=false
      - PORT=2222
    volumes:
      - ./config:/config
    ports:
      - "2222:2222"
    restart: unless-stopped
```

**Practical caveat:** if you are already running certificate-based access, our [SSH certificate management guide comparing step-ca, Teleport, and Vault](../2026-04-25-step-ca-vs-teleport-vs-vault-self-hosted-ssh-certificate-management-guide-2026/) is the natural next step — only OpenSSH speaks that protocol.

## Dropbear: The Embedded Router Workhorse

Dropbear exists because OpenSSH does not fit on a router. It is the OpenWrt default, it compiles statically against a stripped libc, and it will happily run from `inetd` or as a systemd socket unit. Its client (`dbclient`) and key generator (`dropbearkey`) come in the same tiny package.

Installing and running it on a Debian-based device:

```bash
sudo apt-get install dropbear

# Generate an Ed25519 host key the Dropbear way
sudo dropbearkey -t ed25519 -f /etc/dropbear/dropbear_ed25519_host_key

# Run on port 2222, no password auth, no root login
sudo dropbear -p 2222 -s -w -E \
  -r /etc/dropbear/dropbear_ed25519_host_key
```

Flag meanings worth memorizing: `-s` disables password logins, `-w` disallows root login, `-E` logs to stderr (essential when running under systemd or `docker logs`), and `-p` sets the listen port.

Where Dropbear bites you:

- **No X11 forwarding, no SSH certificates.** If your automation expects `ssh -o CertificateFile=`, it will fail.
- **Limited forwarding semantics.** Local and remote port forwards work, but the behaviour under path MTU weirdness is not OpenSSH-grade.
- **SFTP needs a separate binary.** The `dropbear-sftp` component must be installed and referenced by path.
- **Config is flags, not a file.** There is no `dropbear_config`; you express policy on the command line or in your init script. That is great for appliances and painful for humans.

## TinySSH: Attack Surface Minimalism

TinySSH's pitch is in its own repository description: *"small server (less than 100000 words of code)"*. It implements a deliberately narrow slice of the SSH protocol — Ed25519 host and user keys only, Curve25519 key exchange, and a modern AEAD cipher suite. There is no SFTP subsystem, no port forwarding, no agent forwarding, no password authentication, and no configuration file. You either fit its model or you use something else.

The official install path, taken verbatim from the project's installation page:

```bash
# Debian / Ubuntu
sudo apt-get install tinysshd

# Or build from a signed release tarball
wget https://github.com/janmojzis/tinyssh/archive/20240101.tar.gz
gunzip < 20240101.tar.gz | tar -xf -
cd tinyssh-20240101
make
sudo make install

# Create the key directory
sudo tinysshd-makekey /etc/tinyssh/sshkeydir
```

Because there is no config file, you run it from a socket manager. Under `tcpserver` (from `ucspi-tcp`):

```bash
# Listen on :22, hand every connection to tinysshd
tcpserver -HRDl0 0.0.0.0 22 /usr/sbin/tinysshd -v /etc/tinyssh/sshkeydir
```

Or under `inetd`:

```
ssh stream tcp nowait root /usr/sbin/tinysshd tinysshd -l -v /etc/tinyssh/sshkeydir
```

The prerequisite is the whole story: **your client key must be Ed25519** (`ssh-keygen -t ed25519`), and it must already be in `~/.ssh/authorized_keys`. There is no fallback path. If you need `rsync`, `git push` over SSH, or Ansible, TinySSH is the wrong answer — but for a machine that should only ever accept a shell from one key, it is the smallest thing you can reasonably trust.

## wolfSSH: The Fourth Option

wolfSSH rounds out the field. It is a compact SSH implementation from wolfSSL with SSH-2 support, SCP and SFTP, and — uniquely in this group — a commercial support channel and FIPS-oriented builds. At 499 stars it is the least-used of the four, and that is its main downside: fewer eyes, smaller community, and less battle-testing than OpenSSH. Choose it when you are shipping a commercial embedded product and need a vendor to call, not when you want the safest default.

## Hardening Checklist That Applies to All Four

1. **Disable password authentication everywhere.** Every brute-force bot on earth is guessing passwords. Key auth removes the entire class of attack. OpenSSH: `PasswordAuthentication no`. Dropbear: `-s`. TinySSH: not supported at all.
2. **Never allow direct root login.** OpenSSH: `PermitRootLogin no`. Dropbear: `-w`.
3. **Rate-limit and ban.** Any of these daemons benefits from an intrusion-prevention layer — see our [fail2ban vs sshguard vs CrowdSec comparison](../2026-04-24-fail2ban-vs-sshguard-vs-crowdsec-self-hosted-intrusion-prevention-2026/).
4. **Move the port — but do not pretend it is security.** It only removes log noise. Port 22 scans are ambient noise, not targeted attacks.
5. **Add a tunnel layer for admin access.** If your daemon must never be exposed, wrap it: our [SSH tunnel management guide covering sshuttle, autossh, and ssh_tunnel](../2026-05-08-self-hosted-ssh-tunnel-management-sshuttle-autossh-sshtunnel-guide/) shows the patterns.
6. **Rotate host keys when you rebuild.** Cloned VM images with duplicated host keys are how you get MITM warnings that everyone learns to ignore.
7. **Watch the daemon, not the firewall.** `sshd -T` on OpenSSH, `dropbear -h` on Dropbear. Effective config beats assumed config every time.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "OpenSSH vs Dropbear vs TinySSH in 2026: Which SSH Server Should You Actually Run?",
  "description": "A 2026 comparison of OpenSSH, Dropbear, TinySSH, and wolfSSH for self-hosted servers: code size, features, hardening, real configs, and live GitHub data.",
  "datePublished": "2026-10-04",
  "dateModified": "2026-10-04",
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

## FAQ

### Is Dropbear as secure as OpenSSH?

For the features it implements, generally yes — Dropbear is written carefully and has had far fewer CVEs than OpenSSH, largely because it does far less. The real risk is the opposite direction: Dropbear lacks SSH certificates, X11 forwarding, and OpenSSH's configuration granularity, so teams end up bolting on workarounds that are less safe than the OpenSSH feature they avoided. If you need certificates or `Match` blocks, use OpenSSH.

### Does TinySSH support SFTP or port forwarding?

No. TinySSH deliberately omits the SFTP subsystem, agent forwarding, X11 forwarding, and TCP port forwarding. It supports Ed25519 keys with a modern cipher suite and gives you a shell. Use `scp` for file transfer, and if you need tunnels, put something else in front of it. Its value proposition is a code base small enough to read.

### Can I run two SSH daemons on the same machine?

Yes, and it is a common hardening pattern. Bind OpenSSH to a non-standard port for your normal workflow and Dropbear or TinySSH to a second port reachable only over a private network (WireGuard, Tailscale) as a break-glass path. Just make sure the two daemons do not fight over the same host key files or port, and keep both patched.

### Which SSH server should I use for Docker containers?

OpenSSH via the LinuxServer.io image is the practical answer for anything you need to interact with normally, because it supports key injection through `PUBLIC_KEY` and optional sudo through `SUDO_ACCESS`. For throwaway labs where you want the smallest possible fingerprint, a statically built Dropbear in a scratch image is the leanest option.

### Are SSH certificates worth the complexity?

If you have more than a handful of hosts or any short-lived infrastructure, yes. Certificates replace long-lived `authorized_keys` sprawl with a short-lived signed credential, which is what makes key rotation and offboarding tractable. OpenSSH is the only server in this comparison that supports them natively — which is itself a reason most infrastructure standardizes on OpenSSH.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
