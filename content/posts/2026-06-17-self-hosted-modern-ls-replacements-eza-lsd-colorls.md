---
title: "Self-Hosted Modern ls Replacements: eza vs lsd vs colorls"
date: "2026-06-17"
tags: ["shell", "terminal", "developer-tools", "cli-tools", "productivity", "rust", "file-management"]
draft: false
---

## Why Replace the Standard ls Command?

The standard `ls` command has served us well since the early days of Unix, but it shows its age. No syntax highlighting, no Git integration, no icons, and limited sorting options. Modern alternatives to `ls` bring color-coded file types, Git-aware status indicators, tree views, and human-readable file sizes — turning the humble directory listing into a rich information display.

For a broader look at terminal productivity tools, see our [shell customization frameworks guide](../2026-06-17-self-hosted-shell-customization-frameworks-ohmyzsh-starship-bashit/). If you want to supercharge your entire terminal workflow, check out our [fuzzy finder comparison](../2026-06-16-self-hosted-cli-fuzzy-finders-fzf-skim-peco/) and [terminal dashboard guide](../self-hosted-terminal-dashboard-btop-glances-bottom-system-monitoring-guide-2026/).

## Comparison: eza vs lsd vs colorls

| Feature | eza | lsd | colorls |
|---------|-----|-----|---------|
| **GitHub Stars** | 22,200+ | 16,000+ | 5,100+ |
| **Language** | Rust | Rust | Ruby |
| **Speed** | Extremely fast | Very fast | Fast (Ruby overhead) |
| **Colors** | 24-bit true color | 24-bit true color | 256-color with Font Awesome icons |
| **Icons** | Nerd Font icons | Nerd Font icons | File-specific icons via Font Awesome |
| **Git Integration** | Full (staged, unstaged, ignored, conflicted) | Basic (--git flag) | None |
| **Tree View** | Built-in (--tree) | Built-in (--tree) | Via tree mode |
| **Hyperlink Support** | Yes (terminal hyperlinks) | Yes | No |
| **Mount Point Detection** | Yes | Yes | No |
| **Extended Attributes** | Yes | Yes | No |
| **SELinux Context** | Yes | No | No |
| **Install Method** | cargo, brew, apt, pacman, nix | cargo, brew, apt, pacman, snap | gem install |
| **Active Development** | Very active (community fork of exa) | Active | Moderate |
| **Memory Usage** | Minimal (~5 MB) | Minimal (~5 MB) | Higher (~30 MB Ruby runtime) |

### eza

eza is the community-maintained successor to exa, the original modern ls replacement written in Rust. With over 22,000 GitHub stars, it is the most popular choice. It is a drop-in replacement — `alias ls=eza` and you are done.

```bash
# Install eza
cargo install eza

# Or via package manager
sudo apt install eza          # Debian/Ubuntu
brew install eza              # macOS
sudo pacman -S eza            # Arch Linux

# Basic usage with recommended flags
alias ls='eza --icons --group-directories-first'
alias ll='eza -la --icons --group-directories-first'
alias lt='eza --tree --level=2 --icons'
```

eza's standout feature is its deep Git integration. When you run `eza --git`, you see exactly which files are tracked, modified, staged, or untracked:

```bash
# Full Git-aware listing
eza -la --git --icons --group-directories-first

# Tree view with Git status
eza --tree --level=3 --git --icons

# Show only files modified in the last 24 hours
eza -la --changed --icons --sort=modified
```

eza supports extended file attributes on Linux, SELinux contexts, and even generates clickable hyperlinks for supported terminals. The `--no-user` and `--no-permissions` flags are useful for scripting when you do not need owner/permission columns.

### lsd

lsd (LSDeluxe) is another Rust-based ls replacement with 16,000+ stars. It takes a slightly different design philosophy — it emphasizes visual clarity with Nerd Font icons by default and a clean, modern output format.

```bash
# Install lsd
cargo install lsd

# Or via package manager
brew install lsd
sudo apt install lsd
sudo snap install lsd

# Basic usage
alias ls='lsd'
alias ll='lsd -la'
alias lt='lsd --tree --depth=2'
```

lsd's configuration file gives you fine-grained control:

```yaml
# ~/.config/lsd/config.yaml
classic: false
blocks:
  - permission
  - user
  - group
  - size
  - date
  - name
color:
  when: auto
date: date
size: default
sorting:
  column: name
  reverse: false
total-size: false
```

lsd excels at making directory listings visually scannable. Files and directories are clearly differentiated with distinct icons and colors. The `--total-size` flag shows the cumulative size of directories (unlike standard `ls` which just shows the directory entry size). Tree view with `--tree` and grid layout make it easy to visualize directory structure at a glance.

### colorls

colorls is the Ruby-based alternative with 5,100+ stars. It takes a different approach — instead of being a binary, it is a Ruby gem that beautifies `ls` output with colorful icons from Font Awesome and detailed file type indicators.

```bash
# Install colorls
gem install colorls

# Basic usage
alias ls='colorls'
alias ll='colorls -lA'
alias lt='colorls --tree'
```

What sets colorls apart is its file-type-specific coloring and its `--report` flag that generates summary statistics:

```bash
# Show file type breakdown
colorls --report

# Dark mode
colorls --dark

# Sort by file size
colorls -l --sort=size
```

colorls requires a Ruby runtime (which adds overhead), and its development pace has slowed compared to eza and lsd. However, for users already in the Ruby ecosystem, it integrates naturally.

## Installation and Configuration Summary

To get started quickly with eza (recommended for most users):

```bash
# Install (choose one method)
cargo install eza
# OR: brew install eza
# OR: sudo apt install eza

# Add to ~/.bashrc or ~/.zshrc
alias ls='eza --icons --group-directories-first --color=auto'
alias ll='eza -la --icons --group-directories-first --git --color=auto'
alias la='eza -a --icons --group-directories-first'
alias lt='eza --tree --level=2 --icons'
alias lr='eza -la --icons --sort=modified --reverse'
```

For lsd with its config file approach:

```bash
# Install
cargo install lsd

# Alias
alias ls='lsd'
alias ll='lsd -la'
alias lt='lsd --tree'
```

## Performance and Resource Usage

All three tools are significantly faster at coloring output than the traditional `ls --color=auto` approach:

| Tool | Cold Start | 10,000 Files Dir | Memory |
|------|-----------|-----------------|--------|
| eza | <10ms | ~150ms | ~5 MB |
| lsd | <10ms | ~140ms | ~5 MB |
| colorls | ~200ms | ~2s | ~30 MB |
| GNU ls | <5ms | ~100ms | ~2 MB |

Both eza and lsd are nearly as fast as GNU ls thanks to Rust implementations, while colorls pays the Ruby startup cost on every invocation.


## Advanced Usage and Customization Tips

### Color Schemes and Theming

eza supports the `LS_COLORS` environment variable (the same one used by GNU ls), which means it works with popular color schemes like `vivid` and `dircolors`. You can generate a custom color scheme and export it:

```bash
# Generate a vivid theme
vivid generate snazzy > ~/.config/lscolors.sh
source ~/.config/lscolors.sh
export LS_COLORS=$(vivid generate snazzy)
```

lsd reads its color configuration from `~/.config/lsd/colors.yaml`, allowing per-file-type color customization. colorls uses YAML-based color mapping in `~/.config/colorls/dark_colors.yaml`.

### Integrating With Git Workflows

For developers who spend most of their time in Git repositories, combining eza with Git-aware flags creates a powerful workflow:

```bash
# Show only files that changed since last commit
alias gchanged='eza -la --git --changed --icons'

# Recursive listing of tracked files only
alias gtracked='eza --tree --git --git-ignore --icons'

# Show ignored files for debugging .gitignore
alias gignored='eza -la --git-ignore --icons'
```

### Adding to Docker Development Environments

For consistent tooling across team members, add these tools to your development Docker images:

```dockerfile
FROM ubuntu:jammy
RUN apt-get update && apt-get install -y eza lsd bat fzf
RUN echo "alias ls='eza --icons --group-directories-first'" >> /etc/bash.bashrc
RUN echo "alias ll='eza -la --icons --git'" >> /etc/bash.bashrc
```

This ensures every developer on the team has the same modern tooling, regardless of their local machine setup. Combined with dev containers or GitHub Codespaces, your entire team gets a consistent, productive terminal environment.


## FAQ

### Can I use these as a complete ls replacement?

Yes. All three tools support standard ls flags (`-l`, `-a`, `-h`, `-t`, `-r`, `-R`). Create an alias in your shell config file. For scripts, use `/bin/ls` explicitly to avoid alias dependencies.

### Do I need a special font for the icons?

eza and lsd use Nerd Font icons, which require a patched font like "FiraCode Nerd Font" or "JetBrains Mono Nerd Font" to display correctly. Without a Nerd Font, you will see placeholder characters. colorls uses Font Awesome characters that work with standard Unicode fonts.

### Which one handles large directories best?

eza and lsd are both built in Rust and handle directories with hundreds of thousands of files smoothly. colorls is Ruby-based and may become slow with very large directories due to Ruby startup time and garbage collection overhead.

### Can I combine these with fuzzy finders like fzf?

Absolutely. All three tools work well in pipelines. A common pattern is to pipe eza or lsd output into fzf for interactive file selection:

```bash
# Interactive file selection with preview
eza -la --icons | fzf --preview 'bat --color=always {}'
```

### How do I keep these tools updated?

eza and lsd can be updated via cargo (`cargo install eza --force`), your system package manager, or Homebrew. colorls updates via RubyGems (`gem update colorls`). Set up a cron job or use unattended-upgrades for automatic updates.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Modern ls Replacements: eza vs lsd vs colorls",
  "description": "Compare eza, lsd, and colorls — modern alternatives to the standard ls command with Git integration, icons, tree views, and syntax highlighting for your terminal.",
  "datePublished": "2026-06-17",
  "dateModified": "2026-06-17",
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
