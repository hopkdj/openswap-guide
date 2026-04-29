---
title: "Atuin vs McFly vs Bash History: Best Self-Hosted Terminal History Tools 2026"
date: 2026-04-29
tags: ["comparison", "guide", "self-hosted", "developer-tools", "terminal"]
draft: false
description: "Compare Atuin, McFly, and enhanced bash history for self-hosted terminal shell history management. Learn how to sync, search, and manage shell history across multiple machines in 2026."
---

If you spend hours in the terminal every day, your shell history is one of your most valuable productivity assets. The default `~/.bash_history` or `~/.zsh_history` file stores commands in plain text — no search, no sync across machines, and no intelligence. In 2026, self-hosted terminal history tools solve all three problems.

This guide compares **Atuin**, **McFly**, and enhanced **Bash History** setups to help you pick the right tool for your workflow. We cover self-hosting the sync server, Docker deployment, and configuration for each option.

## Why Self-Host Your Terminal History

Your shell history contains sensitive information — API keys, server addresses, database queries, and deployment commands. Using a cloud-hosted history sync service means trusting a third party with all of that data. Self-hosting gives you:

- **Full data ownership** — your command history stays on your infrastructure
- **Cross-machine sync** — access your history from any workstation or server
- **Advanced search** — fuzzy search, filtering, and context-aware results
- **Privacy** — no telemetry, no tracking, no corporate data collection
- **Customization** — configure retention, filtering, and access controls

For developers managing multiple servers, self-hosted history sync is a practical productivity upgrade — especially when paired with tools like a [terminal multiplexer](../self-hosted-terminal-multiplexer-tmux-screen-abduco-remote-dev-guide-2026/) for managing complex workflows.

## Atuin: Magical Shell History with Self-Hosted Sync

**Atuin** (29,500+ GitHub stars) replaces your shell history with a SQLite database, offering encrypted sync across machines via a self-hosted server. Written in Rust, it works with bash, zsh, and fish.

Key features:
- End-to-end encrypted sync between machines
- Full-text fuzzy search with filtering by directory, exit code, and time
- Automatic recording of exit codes, execution time, and working directory
- Self-hosted sync server via Docker
- Statistical insights into your most-used commands

### Atuin Self-Hosted Sync Server — Docker Compose

```yaml
version: "3.8"

services:
  atuin:
    image: ghcr.io/atuinsh/atuin:latest
    container_name: atuin-server
    restart: unless-stopped
    ports:
      - "8888:8888"
    environment:
      ATUIN_HOST: "0.0.0.0"
      ATUIN_PORT: 8888
      ATUIN_OPEN_REGISTRATION: "true"
      ATUIN_DB_URI: "sqlite:///data/atuin.db"
      ATUIN_TLS_ENABLE: "false"
    volumes:
      - atuin-data:/data

volumes:
  atuin-data:
    driver: local
```

### Atuin Client Setup

Install Atuin on each machine that needs history sync:

```bash
# Install via cargo (Rust package manager)
cargo install atuin

# Or install via shell script
curl --proto '=https' --tlsv1.2 -LsSf https://setup.atuin.sh | sh

# Initialize for your shell
atuin init bash >> ~/.bashrc   # for bash
atuin init zsh >> ~/.zshrc     # for zsh
atuin init fish >> ~/.config/fish/config.fish  # for fish

# Login to your self-hosted server
atuin register -u <username> -e <email> -p <password> \
  --host http://your-server:8888

# Sync your history
atuin sync
```

### Atuin Configuration

```toml
# ~/.config/atuin/config.toml
sync_address = "http://your-server:8888"
sync_frequency = "5m"
db_path = "~/.local/share/atuin/history.db"
record_format = "auto"
workspaces = false
filter_mode = "global"
filter_mode_shell_up_key_binding = "global"
search_mode = "fuzzy"
style = "compact"
```

## McFly: Context-Aware Shell History with Fuzzy Search

**McFly** (7,700+ GitHub stars) enhances your shell history with a context-aware, fuzzy-searching replacement for Ctrl+R. Also written in Rust, it ranks commands by recency, frequency, and the current directory context.

Key features:
- Context-aware ranking — prioritizes commands relevant to your current directory
- Fuzzy search with real-time results
- Records exit codes, timestamps, and execution duration
- SQLite-backed local database
- No sync server (local-only by design)
- Lightweight and fast — minimal overhead on every command

### McFly Installation

```bash
# Install via cargo
cargo install mcfly

# Or via Homebrew (macOS)
brew install mcfly

# Or via package manager (Arch Linux)
yay -S mcfly

# Initialize in your shell
echo 'eval "$(mcfly init bash)"' >> ~/.bashrc
echo 'eval "$(mcfly init zsh)"' >> ~/.zshrc

# Reload your shell or source the config
source ~/.bashrc
```

### McFly Configuration

```bash
# ~/.bashrc or ~/.zshrc
export MCFLY_HISTORY=20000        # Max history entries
export MCFLY_RESULTS=10           # Default number of search results
export MCFLY_RESULTS_SORT=RANK    # Sort by rank (or TIME)
export MCFLY_LIGHT=true           # Use light color scheme
export MCFLY_DISABLE_MENU=true    # Disable fuzzy finder menu mode
```

McFly does not include a built-in sync server. If you need cross-machine sync, you'd need to pair it with a file synchronization tool like [rsync or syncthing](../self-hosted-file-sync-sharing-nextcloud-seafile-syncthing-guide-2026/) to replicate the SQLite database — though this approach is less seamless than Atuin's native sync.

## Enhanced Bash History: The Traditional Approach

Before dedicated history tools, power users enhanced their default bash history with clever configuration. This approach requires no additional software, just shell configuration.

### Advanced Bash History Setup

```bash
# ~/.bashrc — Enhanced bash history configuration

# Increase history size and file size
export HISTSIZE=100000
export HISTFILESIZE=200000

# Append to history file instead of overwriting
shopt -s histappend

# Write history after every command (not just on exit)
PROMPT_COMMAND="history -a; history -c; history -r; ${PROMPT_COMMAND:-}"

# Ignore duplicate commands and commands starting with space
export HISTCONTROL=ignoreboth:erasedups

# Ignore common useless commands
export HISTIGNORE="ls:cd:pwd:exit:history:clear:bg:fg:jobs"

# Include timestamp in history
export HISTTIMEFORMAT="%F %T "

# Multi-line commands are saved as single entry
shopt -s cmdhist lithist

# Case-insensitive history search
bind 'set completion-ignore-case on'
bind '"\e[A": history-search-backward'
bind '"\e[B": history-search-forward'
```

### Zsh History Enhancement

```zsh
# ~/.zshrc — Enhanced zsh history

setopt APPEND_HISTORY          # Append to history file
setopt INC_APPEND_HISTORY      # Write immediately
setopt HIST_FIND_NO_DUPS       # No duplicate results in search
setopt HIST_IGNORE_ALL_DUPS    # Delete old duplicate
setopt HIST_REDUCE_BLANKS      # Remove superfluous blanks
setopt HIST_SAVE_NO_DUPS       # Don't write duplicates
setopt SHARE_HISTORY           # Share history between sessions

HISTFILE=~/.zsh_history
HISTSIZE=100000
SAVEHIST=100000
```

While enhanced bash/zsh history is free and requires no dependencies, it lacks fuzzy search, cross-machine sync, command metadata (exit codes, timing), and the statistical insights that Atuin and McFly provide.

## Feature Comparison Table

| Feature | Atuin | McFly | Enhanced Bash |
|---------|-------|-------|---------------|
| **Language** | Rust | Rust | Shell built-in |
| **GitHub Stars** | 29,500+ | 7,700+ | N/A |
| **Fuzzy Search** | ✅ Full-text | ✅ Context-aware | ❌ Prefix only |
| **Cross-Machine Sync** | ✅ Encrypted sync server | ❌ Local only | ❌ Manual rsync |
| **Self-Hosted Server** | ✅ Docker image available | ❌ N/A | ❌ N/A |
| **Exit Code Tracking** | ✅ | ✅ | ❌ |
| **Execution Time** | ✅ | ✅ | ❌ |
| **Directory Context** | ✅ Filter by dir | ✅ Ranks by dir | ❌ |
| **End-to-End Encryption** | ✅ | ❌ N/A | ❌ |
| **Shell Support** | bash, zsh, fish | bash, zsh | bash, zsh |
| **Database** | SQLite | SQLite | Plain text file |
| **Resource Usage** | Low | Low | Minimal |
| **Setup Complexity** | Medium (server + client) | Low (client only) | Low (config only) |

## When to Choose Each Tool

### Choose Atuin if:
- You work across multiple machines and need history sync
- You want end-to-end encrypted history backup
- You need rich search with filtering by directory, exit code, and time
- You want statistical insights into your terminal usage patterns
- You're comfortable running a small sync server (SQLite-backed, minimal resource usage)

### Choose McFly if:
- You work primarily on a single machine
- You want context-aware ranking without the complexity of a sync server
- You prefer a lightweight, zero-maintenance setup
- You want fuzzy search that adapts to your current working directory

### Choose Enhanced Bash if:
- You want zero dependencies and no additional software
- You're on a restricted system where you can't install packages
- You only need basic history improvements (larger size, dedup, timestamps)
- You prefer the simplicity of plain-text history files

## Installation and Deployment Comparison

| Aspect | Atuin | McFly | Enhanced Bash |
|--------|-------|-------|---------------|
| **Install Method** | `cargo install` or shell script | `cargo install` or `brew` | Shell config only |
| **Server Required** | Yes (sync server) | No | No |
| **Docker Support** | ✅ Official GHCR image | ❌ | ❌ |
| **Disk Usage** | ~50 MB (SQLite + binary) | ~30 MB (SQLite + binary) | ~0 MB |
| **Network Required** | Yes (sync) | No | No |
| **Backup Strategy** | Sync server database | SQLite file backup | Text file backup |

## Security and Privacy Considerations

When self-hosting your terminal history, consider these security practices:

1. **Filter sensitive commands** — Configure history ignore patterns to exclude commands containing passwords, tokens, or keys:
```bash
# Atuin: filter commands containing secrets
export ATUIN_FILTER="*password* *secret* *token* *key*"
```

2. **Enable TLS on the sync server** — If your Atuin server is accessible over the internet, configure TLS:
```yaml
# Docker Compose with TLS (using reverse proxy)
services:
  atuin:
    image: ghcr.io/atuinsh/atuin:latest
    environment:
      ATUIN_TLS_ENABLE: "true"
      ATUIN_TLS_CERT_PATH: "/certs/cert.pem"
      ATUIN_TLS_KEY_PATH: "/certs/key.pem"
    volumes:
      - ./certs:/certs:ro
```

3. **Restrict server access** — Use a firewall or reverse proxy to limit who can register and sync:
```bash
# Disable open registration after creating your account
ATUIN_OPEN_REGISTRATION: "false"
```

4. **Regular backups** — Back up the Atuin SQLite database and McFly SQLite files:
```bash
# Backup Atuin database
docker exec atuin-server cp /data/atuin.db /data/atuin.db.backup
cp ~/.local/share/mcfly/history.db ~/backups/mcfly-history-$(date +%F).db
```

For developers who also manage [web SSH access](../2026-04-29-shellhub-vs-sshwifty-vs-wetty-self-hosted-web-ssh-access-guide-2026/) to their servers, combining terminal history sync with secure remote access creates a comprehensive self-hosted development environment.

## FAQ

### Is Atuin safe to self-host? Does it store my commands in plain text?

Atuin stores commands in a SQLite database on your sync server. By default, the data is **not encrypted at rest** on the server — only the network transmission can be encrypted via TLS. However, Atuin supports end-to-end encryption for sync, meaning commands are encrypted on your client before being sent to the server. Enable this in your Atuin config to ensure even the server admin cannot read your history.

### Can I use McFly with multiple machines?

McFly is designed as a local-only tool — it does not have a built-in sync server. However, you can sync McFly's SQLite database across machines using tools like Syncthing, rsync, or a shared network filesystem. Keep in mind that concurrent writes from multiple machines could cause database conflicts. Atuin's native sync handles this scenario much more gracefully.

### Does Atuin work with fish shell?

Yes. Atuin supports bash, zsh, and fish shells. After installing Atuin, run `atuin init fish` and add the output to your Fish configuration file (`~/.config/fish/config.fish`). The fuzzy search UI and sync functionality work identically across all three shells.

### How much disk space does Atuin's sync server use?

For a single developer typing ~500 commands per day, the SQLite database grows to approximately 50-100 MB per year. The server binary (Docker image) is about 30 MB. For a team of 10 developers, expect 500 MB to 1 GB of database storage annually. SQLite is efficient — even with millions of records, query performance remains fast.

### Can I migrate my existing bash/zsh history to Atuin?

Yes. Atuin automatically imports your existing shell history during the first setup. Run `atuin import auto` to import from your current shell's history file. You can also import from specific files: `atuin import zsh` or `atuin import bash`. McFly similarly imports existing history on first launch.

### What happens if my Atuin sync server goes down?

Atuin stores a local copy of your history on each machine. If the sync server becomes unavailable, your local history continues to work normally — search, recording, and filtering all function offline. Once the server is back online, run `atuin sync` to synchronize any commands recorded during the outage.

### Is there a mobile client for Atuin?

Atuin is currently a CLI-only tool for desktop/server environments (bash, zsh, fish). There is no official mobile client. If you need to search your history from a phone, you could access the sync server's SQLite database directly via SSH or a web admin interface (third-party community tools exist).

## Summary

| Tool | Best For | Setup Effort | Sync |
|------|----------|-------------|------|
| **Atuin** | Multi-machine developers who need encrypted sync | Medium | ✅ Native |
| **McFly** | Single-machine developers who want smart search | Low | ❌ Local only |
| **Enhanced Bash** | Minimalists who want zero dependencies | Low | ❌ Manual |

For most developers working across multiple machines, **Atuin** is the clear winner — its self-hosted sync server, encrypted data transfer, and rich search capabilities make it the most complete terminal history solution in 2026. If you only work on one machine and want a lightweight upgrade, **McFly** provides excellent context-aware search with minimal setup.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Atuin vs McFly vs Bash History: Best Self-Hosted Terminal History Tools 2026",
  "description": "Compare Atuin, McFly, and enhanced bash history for self-hosted terminal shell history management. Learn how to sync, search, and manage shell history across multiple machines in 2026.",
  "datePublished": "2026-04-29",
  "dateModified": "2026-04-29",
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
