---
title: "Self-Hosted Remote Shell: Mosh vs Eternal Terminal vs OpenSSH with tmux"
date: "2026-06-16"
tags: ["remote-shell", "ssh", "terminal", "developer-tools", "networking"]
draft: false
---

Remote server access is the daily bread of system administrators, DevOps engineers, and backend developers. While OpenSSH has been the gold standard for secure remote access since 1999, its design assumes reliable, low-latency connections — an assumption that breaks down over WiFi, mobile networks, and intercontinental links. Two open-source tools have emerged to solve this problem: Mosh (Mobile Shell) and Eternal Terminal (ET). This article compares them against the classic OpenSSH + tmux combination to help you choose the right remote access strategy.

## The Problem with Plain SSH

OpenSSH operates over TCP, which means every keystroke is a round trip. On a high-latency connection (200ms+), typing `ls -la` can feel like wading through molasses — you press 'l', wait, press 's', wait, see the wrong character because the echo is delayed, backspace, wait...

The deeper issue is that TCP connections break when your IP address changes. Switch from WiFi to mobile data, or walk between access points, and your SSH session dies. For developers who keep long-running tmux sessions with carefully arranged panes, this is a daily frustration.

Modern remote shell tools solve both problems: they use UDP for responsive typing even on bad connections, and they survive network changes transparently.

## Tool Comparison Table

| Feature | Mosh | Eternal Terminal | OpenSSH + tmux |
|---------|------|-----------------|----------------|
| **GitHub Stars** | 14,049 | 3,726 | OpenSSH (built into OS) |
| **Protocol** | SSP over UDP | TCP with session recovery | SSH over TCP |
| **IP Roaming** | Yes (automatic) | Yes (automatic) | No (session dies) |
| **Local Echo** | Yes (instant typing) | Yes (instant typing) | No (waits for server) |
| **High-Latency** | Excellent | Excellent | Poor (keystroke lag) |
| **Port Forwarding** | No | Via SSH tunnel | Yes (native) |
| **File Transfer** | No | Via scp tunnel | Yes (scp/sftp) |
| **Scrollback** | Limited (in-session) | Via tmux integration | Via tmux |
| **Encryption** | AES-128-OCB | AES-256-GCM + SSH | SSH ciphers |
| **Written In** | C++ | C++ | C |
| **License** | GPL-3.0 | Apache 2.0 | BSD |
| **Auto-Reconnect** | Yes (instant) | Yes (with daemon) | No (manual) |
| **Writes to Disk** | No (in-memory only) | Yes (journal file) | Via tmux socket |
| **Multi-Window** | No (single window) | Via tmux | Via tmux |
| **Latest Update** | March 2026 | June 2026 | Ongoing |

## Mosh: UDP-Powered Mobile Shell

Mosh (Mobile Shell) was developed at MIT to solve the specific problem of using SSH over unreliable connections. It works by running a small server process alongside SSH that communicates over UDP using the State Synchronization Protocol (SSP). Your keystrokes are echoed locally before being sent to the server, so typing feels instant even on 500ms satellite links.

### Installation

```bash
# Both client and server need mosh installed

# Debian/Ubuntu
sudo apt install mosh

# macOS
brew install mosh

# Fedora
sudo dnf install mosh

# Arch
sudo pacman -S mosh
```

### Usage

```bash
# Connect to server (uses SSH for auth, then switches to UDP)
mosh user@server.example.com

# Specify UDP port range (for firewall rules)
mosh -p 60000:61000 user@server.example.com

# Run a specific command
mosh user@server.example.com -- tmux attach

# Server daemon (auto-started by SSH, but can run standalone)
mosh-server new -s -l LANG=en_US.UTF-8
```

### Docker Compose for Mosh Server

```yaml
version: "3.8"
services:
  mosh-server:
    image: ubuntu:22.04
    ports:
      - "22:22"           # SSH for auth
      - "60000-61000:60000-61000/udp"  # Mosh UDP range
    volumes:
      - ./sshd:/etc/ssh
      - mosh-data:/home/mosh-user
    environment:
      - LANG=en_US.UTF-8
    command:
      - /bin/bash
      - -c
      - |
        apt update && apt install -y mosh openssh-server
        useradd -m mosh-user && echo "mosh-user:changeme" | chpasswd
        service ssh start
        tail -f /dev/null
volumes:
  mosh-data:
```

### Firewall Configuration

```bash
# UFW rules for Mosh
sudo ufw allow 22/tcp
sudo ufw allow 60000:61000/udp

# iptables rules
sudo iptables -A INPUT -p udp --dport 60000:61000 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT
```

Mosh is ideal when you need **reliable shell access from anywhere**: trains, coffee shops, airports, or any scenario where your network connection might change mid-session. Its local echo makes typing feel native regardless of latency, and its UDP-based protocol means a brief network dropout (up to several minutes) won't kill your session.

The main limitation of Mosh is that it doesn't support port forwarding or file transfers natively. You'll still use SSH for `scp`, `rsync`, or tunneling, and Mosh for interactive shell work. It's also single-window, so if you need split panes or multiple windows, you'll run tmux inside Mosh.

## Eternal Terminal: Session Persistence with Journaling

Eternal Terminal (ET) takes a different approach from Mosh. Instead of switching to UDP, it keeps using TCP but adds an intelligent session daemon (`etserver`) that journals all terminal output. When your connection drops, ET's client (`et`) reconnects and replays the journal to restore your exact terminal state — scrollback, output, and all.

### Installation

```bash
# Debian/Ubuntu (from releases)
wget https://github.com/MisterTea/EternalTerminal/releases/latest/download/et_7.0.0_amd64.deb
sudo dpkg -i et_*.deb

# macOS
brew install eternal-terminal

# From source
git clone --recurse-submodules https://github.com/MisterTea/EternalTerminal
cd EternalTerminal && mkdir build && cd build
cmake .. && make -j$(nproc) && sudo make install
```

### Server Setup

```bash
# Start the ET server daemon
sudo systemctl enable etserver --now

# Or manually
etserver --daemon --port=2022

# Firewall (single port!)
sudo ufw allow 2022/tcp
```

### Client Usage

```bash
# Basic connection
et user@server.example.com

# With specific port
et user@server.example.com:2022

# With jump host
et user@target-host:2022 --jump user@jumphost

# Using tmux inside ET
et user@server.example.com -c "tmux attach || tmux new"
```

### Docker Compose for ET Server

```yaml
version: "3.8"
services:
  et-server:
    image: ubuntu:22.04
    ports:
      - "2022:2022"
    volumes:
      - et-data:/root/.et
    environment:
      - TERM=xterm-256color
    command:
      - /bin/bash
      - -c
      - |
        apt update && apt install -y wget tmux
        wget https://github.com/MisterTea/EternalTerminal/releases/latest/download/et_7.0.0_amd64.deb
        dpkg -i et_*.deb || apt-get install -f -y
        useradd -m et-user && echo "et-user:changeme" | chpasswd
        etserver --daemon --port=2022
        tail -f /dev/null
volumes:
  et-data:
```

Eternal Terminal shines when you need **session persistence with full scrollback history**. Unlike Mosh, which discards output when you disconnect, ET journals everything to disk. This means you can run a long build, disconnect your laptop, go home, reconnect, and see the complete build output — including everything that scrolled by while you were offline.

The trade-off is that ET still uses TCP, so it's slightly less responsive than Mosh on very high-latency connections. But for most real-world scenarios (WiFi dropping, ISP hiccups, laptop sleep/wake cycles), ET's automatic reconnection with full session replay is transformative.

## OpenSSH + tmux: The Classic Combo

The traditional solution to SSH disconnection is combining OpenSSH with tmux (or GNU screen). tmux runs as a server process that survives SSH disconnections, and you reattach to it after reconnecting. While this works, it requires manual intervention and doesn't solve the latency problem.

### Configuration

```bash
# Server-side: tmux configuration (~/.tmux.conf)
cat > ~/.tmux.conf << 'EOF'
# Enable mouse support
set -g mouse on

# Increase scrollback buffer
set -g history-limit 50000

# Faster key repeat
set -sg escape-time 0

# Auto-rename windows
set -g automatic-rename on
set -g renumber-windows on

# Better split keybindings
bind | split-window -h
bind - split-window -v
EOF

# Client-side: SSH config (~/.ssh/config)
cat >> ~/.ssh/config << 'EOF'
Host myserver
    HostName server.example.com
    User myuser
    ServerAliveInterval 60
    ServerAliveCountMax 3
    TCPKeepAlive yes
    Compression yes
EOF
```

### Auto-Reconnect Script

```bash
#!/bin/bash
# ~/bin/autossh-tmux.sh — auto-reconnect wrapper

while true; do
    ssh -t myserver "tmux attach -d || tmux new -s main"
    echo "Disconnected. Reconnecting in 3s..."
    sleep 3
done
```

### Ansible Playbook for Deployment

```yaml
- name: Deploy tmux + autossh setup
  hosts: all
  tasks:
    - name: Install tmux
      apt:
        name: tmux
        state: present
      become: yes

    - name: Copy tmux config
      copy:
        src: files/tmux.conf
        dest: /home/{{ ansible_user }}/.tmux.conf

    - name: Enable SSH keepalive
      lineinfile:
        path: /etc/ssh/sshd_config
        regexp: '^ClientAliveInterval'
        line: 'ClientAliveInterval 60'
      become: yes
      notify: restart sshd

  handlers:
    - name: restart sshd
      service:
        name: sshd
        state: restarted
      become: yes
```

OpenSSH + tmux is the **zero-dependency solution** that works everywhere SSH works. You don't need to install additional server software, open extra firewall ports, or change your workflow. The downside is that on bad connections, you'll feel the latency in every keystroke, and reconnection is a manual process.

## Choosing the Right Remote Access Strategy

For **mobile-first developers** who frequently work from different locations with varying network quality, Mosh provides the best typing experience. The instant local echo and automatic IP roaming make it feel like a local terminal regardless of your connection quality.

For **long-running operations** where you need complete session history (builds, database migrations, log tailing), Eternal Terminal's journaling system is a game-changer. You can start a process, close your laptop, and come back hours later with the full output intact. Pair it with tmux for multi-window sessions.

For **traditional server administration** where you control the network quality and need port forwarding or file transfers, OpenSSH + tmux remains the most flexible option. It requires zero additional setup and integrates seamlessly with the entire SSH ecosystem (scp, rsync, SSH tunnels, ProxyJump).

## Why Self-Host Your Remote Access Tooling?

Standardizing remote access tools across your infrastructure provides measurable benefits:

**Reduced context-switching cost** is the biggest win. When every server in your fleet supports the same remote access protocol, you don't need to remember which host uses which tool. Automated deployment via Ansible or Docker ensures consistency. For more on infrastructure automation patterns, see our [Git branch management guide](../2026-06-16-self-hosted-git-branch-management-git-town-git-branchless-sapling/) for workflow standardization parallels.

**Security through standardization** means you can audit and harden a single access path rather than juggling multiple protocols. Mosh and ET both use SSH for initial authentication, so you retain the full security benefits of SSH keys, certificate-based auth, and hardware tokens. For deeper security tooling, check our [code signing guide](../2026-05-12-self-hosted-git-commit-signing-gpg-ssh-sigstore-cosign-guide/).

**Observability and logging** improve when you know exactly which protocol is being used for remote access. ET's journal files provide an audit trail of all terminal output, and Mosh's UDP traffic can be monitored separately from SSH traffic for anomaly detection.

## FAQ

**Q: Does Mosh support IPv6?**
A: Yes, Mosh fully supports IPv6. If your DNS resolves to an IPv6 address, Mosh will use it automatically. You can also specify `mosh --family=inet6 user@server` to force IPv6.

**Q: Can I use Mosh or ET through a corporate firewall?**
A: Mosh requires a range of UDP ports (usually 60000-61000). If your firewall blocks UDP, Mosh won't work. ET uses a single TCP port (default 2022), which is easier to allow through firewalls. OpenSSH uses port 22 by default and is the most firewall-friendly option.

**Q: How secure is Mosh's encryption compared to SSH?**
A: Mosh uses AES-128-OCB for the data channel after SSH handles authentication. The encryption is modern and considered secure, but Mosh doesn't support key rotation or cipher negotiation the way SSH does. For compliance-sensitive environments, ET or plain SSH may be preferable because they use standard SSH encryption end-to-end.

**Q: Can I use these tools with jump hosts / bastion servers?**
A: Yes, all three support jump hosts. Mosh can tunnel through SSH ProxyJump (`mosh --ssh="ssh -J jump.example.com" target`). ET has a native `--jump` flag. OpenSSH supports `ProxyJump` natively in its config file.

**Q: What happens if the server reboots while I'm connected?**
A: Mosh sessions survive server reboots transparently — you reconnect and everything works. ET sessions also survive reboots because the journal is on disk. With OpenSSH + tmux, you'll need to reconnect and reattach to tmux after the server comes back up. For maximum resilience, consider running tmux as a systemd user service that auto-starts on boot.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Remote Shell: Mosh vs Eternal Terminal vs OpenSSH with tmux",
  "description": "Compare Mosh (UDP, instant local echo), Eternal Terminal (TCP with journaling/session replay), and OpenSSH + tmux for remote server access. Docker Compose setups, firewall configs, Ansible playbooks, and latency benchmarks for unreliable connections.",
  "datePublished": "2026-06-16",
  "dateModified": "2026-06-16",
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
