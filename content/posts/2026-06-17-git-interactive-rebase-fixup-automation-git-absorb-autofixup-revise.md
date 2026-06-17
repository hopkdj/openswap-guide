---
title: "Self-Hosted Git Interactive Rebase & Fixup Automation: git-absorb vs git-autofixup vs git-revise"
date: "2026-06-17"
tags: ["git", "developer-tools", "version-control", "automation", "code-review", "git-workflow"]
draft: false
---

## Introduction

Git's interactive rebase is one of the most powerful tools for crafting a clean commit history. However, manually squashing, reordering, and fixing up commits can be tedious and error-prone — especially on large feature branches with dozens of commits. Enter automated fixup and rebase tools: they analyze your working tree changes, match them to existing commits that introduced those lines, and automatically generate fixup commits or rewrite history. This article compares three leading open-source tools for Git rebase automation: **git-absorb**, **git-autofixup**, and **git-revise**.

| Feature | git-absorb | git-autofixup | git-revise |
|---------|-----------|---------------|------------|
| **Language** | Rust | Python | Python |
| **Stars** | ~6,500 | ~1,200 | ~500 |
| **Installation** | `cargo install git-absorb` | `pip install git-autofixup` | `pip install git-revise` |
| **Approach** | Automatic commit absorption | Auto-generates fixup commits | Interactive history editing |
| **Git Integration** | Standalone binary | Git alias wrapper | Git subcommand |
| **Merge Conflict Handling** | Aborts and reports | Relies on rebase | Built-in conflict resolution |
| **Customizability** | Low (opinionated) | Medium (configurable) | High (interactive) |
| **Learning Curve** | Minimal (one command) | Low | Moderate (TUI) |

## How Git Fixup Automation Works

Before diving into each tool, let's understand the workflow they automate. In a typical feature branch with 10-15 commits, you might need to:

1. Fix a bug introduced in commit #3 (buried 5 commits deep)
2. Update a variable name that changed across 4 different commits
3. Remove debug logging scattered across 3 early commits

Without automation, you'd manually run `git rebase -i HEAD~10`, mark commits for editing, make changes, amend, and continue. This is slow and error-prone.

Fixup automation tools work by:
- Taking your current working tree changes (`git diff` against HEAD)
- Analyzing which existing commit(s) introduced each changed line (using `git blame`)
- Automatically creating fixup commits targeting those specific commits
- Running `git rebase --autosquash` to fold them in

## git-absorb: Facebook's Automatic Commit Fixer

[git-absorb](https://github.com/tummychow/git-absorb) is Facebook's Rust-based tool that takes "automatic" literally. It requires almost no user interaction — just run `git absorb` and it handles everything.

### How It Works

```bash
# After making changes to fixup into previous commits:
git add -A
git absorb

# The tool automatically:
# 1. Runs git blame on changed lines
# 2. Matches each hunk to its originating commit
# 3. Creates fixup! commits pointing to those commits
# 4. Optionally runs git rebase --autosquash
```

### Key Features

- **Zero-config**: Works out of the box with any Git repository
- **Smart hunk splitting**: Uses `git diff` algorithm to match changes to commits precisely
- **Stack safety**: Won't modify commits that have already been pushed (configurable via `--base`)
- **Safe by default**: Creates fixup commits first; you review before rebase

### Configuration

```toml
# In ~/.gitconfig
[absorb]
    # Stop at the first remote branch
    maxStack = 50
    # Automatically run rebase after absorb
    autoRebase = false
```

### Limitations

- **Only creates fixup commits** — cannot squash, reword, or reorder commits
- **No interactive review** — you trust the blame analysis or don't use it
- **Single-purpose** — only handles the "absorb changes into history" workflow

## git-autofixup: Python-Based Intelligent Fixup Generation

[git-autofixup](https://github.com/torbiak/git-autofixup) takes a more flexible approach. Written in Python, it provides intelligent fixup generation with configurable strategies for matching changes to commits.

### How It Works

```bash
# Create fixup commits for all staged changes:
git autofixup

# Create fixup commits for specific files:
git autofixup -- src/main.py tests/

# Dry-run to preview what would happen:
git autofixup --dry-run
```

### Key Features

- **Multiple matching strategies**: `blame` (default), `log` (commit message), `diff` (content similarity)
- **Interactive mode**: Preview and confirm each fixup before it's created
- **Partial staging support**: Only fixup changes in specific files or hunks
- **Customizable mappings**: Define which files should be matched to which commits

### Configuration

```toml
# In ~/.gitconfig or pyproject.toml
[autofixup]
    strategy = "blame"
    interactive = false
    max-commits = 20

# Custom file-to-commit mapping
[autofixup "src/frontend/*.tsx"]
    commit-pattern = "feat.*frontend"
```

### Real-World Workflow

```bash
# 1. Make changes to fix earlier commits
# 2. Stage the changes you want to fixup
git add src/auth.py tests/test_auth.py

# 3. Generate fixup commits with interactive review
git autofixup --interactive

# 4. Review and confirm each fixup target
# 5. Run the autosquash rebase
git rebase --interactive --autosquash origin/main
```

## git-revise: Interactive History Rewriting

[git-revise](https://github.com/mystor/git-revise) is the most powerful of the three, offering a full interactive TUI for rewriting Git history. It's like `git rebase -i` on steroids.

### How It Works

```bash
# Open interactive editor for the last 5 commits:
git revise -i HEAD~5

# Cut a commit into two separate commits:
git revise --cut <commit-hash>

# Amend a commit 3 levels deep without touching others:
git revise HEAD~3
```

### Key Features

- **Efficient re-computation**: Only rebuilds commits that actually change (unlike rebase which rebuilds everything)
- **Interactive TUI**: Full terminal UI for reordering, squashing, splitting, and editing commits
- **Conflict-aware**: Built-in merge conflict resolution that remembers your choices
- **Split commits**: Break a large commit into smaller logical units
- **Preserve timestamps**: Maintains original author dates when desired

### Advanced Usage

```bash
# Interactive mode with custom editor
GIT_EDITOR=vim git revise -i main..HEAD

# Automatically fixup all fixup! and squash! commits
git revise --autosquash

# Cut a large commit into pieces
git revise --cut HEAD~2

# Reorder the last 4 commits
git revise -i HEAD~4
```

### Comparison with `git rebase -i`

```
git rebase -i (traditional)     git revise (modern)
─────────────────────────────   ────────────────────
Rebuilds ALL commits            Only rebuilds changed commits
Single todo list                Split-view editor
Manual fixup resolution         Automatic autosquash
Time: O(n) for n commits        Time: O(changes) typically
```

## Choosing the Right Tool

Your choice depends on your workflow and how much control you need:

### Use git-absorb if:
- You want a **zero-friction** tool that just works
- Your workflow is primarily "make changes, absorb them back"
- You trust automated blame-based matching
- You want minimal cognitive overhead (one command: `git absorb`)

### Use git-autofixup if:
- You need **fine-grained control** over which changes go where
- You have complex mono-repos where blame isn't always reliable
- You want preview/dry-run capabilities before committing
- You work with partial staging (`git add -p`) frequently

### Use git-revise if:
- You do **heavy history rewriting** (splitting commits, reordering)
- You want git-rebase-i but **faster and smarter**
- You need to surgically edit commits deep in history
- You're tired of git-rebase rebuilding every single commit

## Installation & Setup

### Quick Start for Each Tool

```bash
# git-absorb
cargo install git-absorb
# Or: brew install git-absorb (macOS)

# git-autofixup
pip install git-autofixup
git config --global alias.autofixup '!git-autofixup'

# git-revise
pip install git-revise
```

### Recommended Git Config

```ini
[alias]
    # Quick fixup alias chain
    fixup = "!git add -A && git absorb && git rebase --autosquash"
    # Interactive revise  
    ri = revise -i

[rebase]
    autosquash = true
    autostash = true

[absorb]
    autoRebase = false
    maxStack = 50
```

For related reading, see our guides on [Git hooks management with pre-commit, lefthook, and husky](../2026-04-26-pre-commit-vs-lefthook-vs-husky-git-hooks-management-guide-2026/), [Git branch management with git-town, git-branchless, and Sapling](../2026-06-16-self-hosted-git-branch-management-git-town-git-branchless-sapling/), and [Git history visualization tools](../2026-05-05-self-hosted-git-history-visualization-pomber-gource-gitgraph-guide/).

## FAQ

### Q: Do these tools work with merge commits?

Not directly. All three tools operate on linear history. If you need to work with merge commits, you should use `git rebase --rebase-merges` after generating fixup commits. git-revise handles rebase-merges better than the other two because it only rebuilds commits that actually change.

### Q: Can I use multiple tools together?

Yes. A common workflow is to use git-absorb for quick fixups and git-revise for more complex history editing. For example: `git absorb` to auto-generate fixup commits, then `git revise -i` to fine-tune the result before squashing.

### Q: What happens if git-absorb matches changes to the wrong commit?

git-absorb creates fixup commits rather than directly modifying history, so you can always inspect the result before squashing. If a match is wrong, simply abort (`git rebase --abort`) and use git-autofixup with the `--interactive` flag to manually select target commits.

### Q: How do these compare to just using `git commit --fixup`?

Manual fixups (`git commit --fixup=<hash>`) require you to know exactly which commit to target. These tools automate that decision using blame analysis. For 1-2 fixups, manual is fine. For 5-10 fixups across multiple commits, automation saves significant time and reduces errors.

### Q: Will these tools mess up my pushed commits?

All three tools are designed to be safe by default. git-absorb and git-autofixup stop at the first remote-tracking branch by default, so they won't rewrite commits that have been pushed. git-revise warns you before modifying pushed history. You can always add `--force` flags but the defaults are safe.

### Q: Can I use these in CI/CD pipelines?

git-autofixup has a `--check` mode that verifies fixup commits would be created correctly without actually modifying history — useful for pre-merge validation. git-revise can be used in non-interactive mode for automated history cleanup. git-absorb is primarily designed for interactive use.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Git Interactive Rebase & Fixup Automation: git-absorb vs git-autofixup vs git-revise",
  "description": "Compare git-absorb, git-autofixup, and git-revise for automated Git history cleanup. Learn which fixup automation tool fits your workflow with code examples and configuration guides.",
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
