---
title: "Self-Hosted Dotfile Management: chezmoi vs yadm vs homeshick Compared (2026)"
date: "2026-06-16"
tags: ["dotfiles", "configuration-management", "dev-tools", "git", "automation", "cli"]
draft: false
---

## Why Manage Dotfiles?

Every serious developer quickly accumulates a sprawling collection of configuration files across multiple machines — shell aliases, editor settings, git configs, tmux layouts, and dozens of environment-specific tweaks that define their workflow. When you work across multiple machines (work laptop, home desktop, remote servers, CI environments), keeping these files synchronized becomes a maintenance headache. Copying files manually with `scp` or USB drives is error-prone, and forgetting to sync a critical alias or keybinding disrupts your workflow.

Dotfile managers solve this by treating your configuration files as version-controlled code. They track changes, handle machine-specific variations, and make it trivial to bootstrap a new machine with your entire development environment in minutes. Rather than spending hours configuring a new server from scratch, a single command restores your complete toolkit.

For broader configuration management across servers, see our [guide on self-hosted configuration management tools](../apollo-vs-nacos-vs-consul-kv-self-hosted-configuration-management-guide-2026/). If you're looking to automate Git workflows, our [Git hooks management comparison](../2026-04-26-pre-commit-vs-lefthook-vs-husky-git-hooks-management-guide-2026/) covers pre-commit, lefthook, and husky.

## Comparison Table

| Feature | chezmoi | yadm | homeshick |
|---------|---------|------|-----------|
| **Language** | Go | Bash (POSIX) | Bash |
| **Stars** | 20,210+ | 6,329+ | 2,191+ |
| **Template Engine** | Go templates | Built-in (Jinja-like) | None (symlinks) |
| **Encrypted Secrets** | age, GPG, Vault | GPG, OpenSSL | Manual (git-crypt) |
| **Machine-Specific Configs** | Yes (templates + data) | Yes (alternate files) | Limited (manual branching) |
| **Dry-Run / Diff** | Yes (built-in) | Yes (`yadm diff`) | Limited |
| **Script Execution** | Yes (run_ scripts) | Yes (bootstrap) | No |
| **Password Manager Integration** | Yes (1Password, Bitwarden, etc.) | No | No |
| **Windows Support** | Yes | Limited (Git Bash) | Limited |
| **Initial Setup Complexity** | Medium | Low | Low |
| **Active Development** | Very active (weekly releases) | Active | Slow (maintenance) |

## chezmoi: The Enterprise-Grade Dotfile Manager

[chezmoi](https://github.com/twpayne/chezmoi) (20,210+ stars) is the most feature-rich dotfile manager, written in Go with a focus on security and flexibility. It uses Go's `text/template` engine to handle machine-specific variations — you can conditionally include configuration based on hostname, OS, architecture, or any custom data.

### Installation

```bash
# Linux/macOS (single binary)
sh -c "$(curl -fsLS get.chezmoi.io)"

# Or via package manager
brew install chezmoi              # macOS
sudo snap install chezmoi         # Linux
winget install twpayne.chezmoi    # Windows
```

### Key Commands

```bash
# Initialize chezmoi on a new machine
chezmoi init

# Preview changes without applying them
chezmoi diff

# Apply dotfile changes
chezmoi apply

# Edit a managed file
chezmoi edit ~/.bashrc

# Add an existing file to management
chezmoi add ~/.config/nvim/init.lua

# Manage encrypted secrets
chezmoi age decrypt ~/.ssh/id_rsa.age
```

### Template Example

chezmoi templates use Go syntax to generate machine-specific dotfiles. Here's a `.gitconfig` template:

```
[user]
    name = "{{ .name }}"
    email = "{{ .email }}"
{{- if eq .chezmoi.hostname "work-laptop" }}
    signingkey = "{{ .workGPGKey }}"
{{- else }}
    signingkey = "{{ .personalGPGKey }}"
{{- end }}
```

The data file (`~/.config/chezmoi/chezmoi.yaml`) stores per-machine values:

```yaml
name: "Jane Developer"
email: "jane@example.com"
workGPGKey: "ABC123"
personalGPGKey: "DEF456"
```

## yadm: Git-Powered Simplicity

[yadm](https://github.com/yadm-dev/yadm) (6,329+ stars) takes a different approach — it wraps Git itself. If you understand Git, you understand yadm. It stores your dotfiles in a Git repository at `~/.local/share/yadm/repo.git` and uses a thin CLI layer to provide dotfile-specific features like alternate files, encryption, and bootstrapping.

### Installation

```bash
# macOS
brew install yadm

# Linux (Debian/Ubuntu)
sudo apt install yadm

# Linux (Fedora/RHEL)
sudo dnf install yadm

# From source (any Unix-like system)
git clone https://github.com/yadm-dev/yadm.git ~/.local/share/yadm
```

### Key Commands

```bash
# Initialize a new dotfile repository
yadm init
yadm add ~/.bashrc ~/.vimrc
yadm commit -m "Initial dotfiles"
yadm remote add origin git@github.com:user/dotfiles.git
yadm push -u origin main

# Clone existing dotfiles on a new machine
yadm clone git@github.com:user/dotfiles.git

# Manage alternate files per host/OS
yadm alt  # Creates symlinks for alternate files

# Encrypt sensitive files
yadm encrypt ~/.ssh/id_rsa
yadm decrypt
```

### Alternate Files

yadm's alternate file system lets you maintain OS or host-specific variants:

```bash
# File naming convention examples:
.bashrc##os.Darwin      # macOS-specific
.bashrc##os.Linux        # Linux-specific
.bashrc##hostname.work   # Specific machine
.bashrc##class.Work      # Class-based grouping
```

## homeshick: The Minimalist's Choice

[homeshick](https://github.com/andsens/homeshick) (2,191+ stars) is the simplest of the three — a thin symlink manager written in Bash. It treats each "castle" (dotfile repository) as an independent unit, making it easy to mix and match configuration from different sources.

### Installation

```bash
git clone https://github.com/andsens/homeshick.git ~/.homesick/repos/homeshick
source ~/.homesick/repos/homeshick/homeshick.sh
```

### Key Commands

```bash
# Clone a castle (dotfile repo)
homeshick clone user/dotfiles

# Create your own castle
homeshick generate my-dotfiles

# Symlink all files in a castle
homeshick link my-dotfiles

# Pull latest changes
homeshick pull my-dotfiles

# List all castles
homeshick list

# Check castle status
homeshick status my-dotfiles
```

## Choosing the Right Tool for Your Workflow

Each tool addresses a different level of complexity. chezmoi excels in heterogeneous environments where the same dotfiles must behave differently across Linux servers, macOS laptops, and Windows desktops — its template engine and secret management make it suitable for teams as well as individuals. yadm strikes a sweet spot for Git-native users who want dotfile management that feels familiar and integrates naturally with their existing Git workflow. homeshick is ideal for minimalists who just need symlinks and version tracking without learning new concepts.

For teams sharing development environment configurations, see our [guide on self-hosted development environment managers](../2026-05-03-devbox-vs-nix-vs-dev-containers-self-hosted-dev-environment-managers/). For terminal productivity history tools, check our [terminal history sync comparison](../2026-04-29-atuin-vs-mcfly-vs-bash-history-self-hosted-terminal-history-sync-guide-2026/).


## Migration Strategies: Moving Between Dotfile Managers

Transitioning from one dotfile manager to another requires careful planning to avoid losing configuration history or disrupting your workflow. Here are proven migration paths for common scenarios.

**Migrating from homeshick to yadm:** Since homeshick uses standard Git repositories for each "castle," you can consolidate them into a single yadm repository. First, initialize yadm in your home directory with `yadm init`, then copy the contents of each castle into the yadm working tree using `cp -r ~/.homesick/repos/mycaste/home/* ~/`. Run `yadm add` on the copied files, commit, and push to a new remote. The git history from homeshick can be preserved using `git fetch` and `git merge --allow-unrelated-histories` from the old castle repositories.

**Migrating from yadm to chezmoi:** chezmoi can import an existing yadm repository directly. Run `chezmoi init --apply --source ~/.local/share/yadm/repo.git` to use your yadm repository as chezmoi's source. Then run `chezmoi re-add` to convert yadm-style alternate files to chezmoi templates. Files like `.bashrc##os.Darwin` become `.bashrc` with `{{ if eq .chezmoi.os "darwin" }}` conditionals. Encrypted files managed by yadm's GPG encryption need to be re-encrypted using chezmoi's age integration with `chezmoi age encrypt`.

**Starting fresh with chezmoi:** If you've been managing dotfiles manually or with rsync scripts, chezmoi's `add` command is the easiest entry point. Run `chezmoi init` to create a new source directory, then `chezmoi add ~/.bashrc ~/.gitconfig ~/.config/nvim/init.lua` for each file you want to track. chezmoi will automatically template any file that differs between your machines after you run `chezmoi init` on a second machine and compare with `chezmoi diff`.

## FAQ

### Do I need a dotfile manager if I only use one machine?

Yes, even with a single machine, a dotfile manager provides version control for your configurations. When you accidentally break your `.bashrc` or `.vimrc`, you can roll back to a working version instantly. It also serves as off-machine backup — if your laptop dies, your entire development environment configuration is recoverable from a Git remote.

### Can I use chezmoi and yadm together?

Technically yes, but it's not recommended. Both manage files in your home directory and would conflict. Pick one. If you need chezmoi's template features but prefer yadm's Git-native approach, chezmoi can actually use any Git repository as its source, giving you the best of both worlds.

### How do I handle secrets like API keys and SSH keys?

chezmoi has first-class secret management with support for age encryption, GPG, HashiCorp Vault, and major password managers (1Password, Bitwarden, LastPass). yadm uses GPG or OpenSSL for file encryption. homeshick requires external tools like git-crypt or manual encryption. Never commit plain-text secrets to any dotfile repository.

### Are dotfile managers safe to use on production servers?

chezmoi is particularly well-suited for server environments — it has a `--dry-run` mode, diff previews, and can operate non-interactively. yadm also works on servers but requires Git. For production infrastructure, consider whether full dotfile management is appropriate or if a lightweight configuration management tool like Ansible is more suitable.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Dotfile Management: chezmoi vs yadm vs homeshick Compared (2026)",
  "description": "Comprehensive comparison of three leading open-source dotfile managers: chezmoi, yadm, and homeshick. Includes installation guides, template examples, encryption setup, and migration strategies for developers managing configurations across multiple machines.",
  "datePublished": "2026-06-16",
  "dateModified": "2026-06-16",
  "author": {
    "@type": "Organization",
    "name": "Pi Stack"
  },
  "publisher": {
    "@type": "Organization",
    "name": "Pi Stack",
    "logo": {
      "@type": "ImageObject",
      "url": "https://www.pistack.xyz/logo.png"
    }
  }
}
</script>
