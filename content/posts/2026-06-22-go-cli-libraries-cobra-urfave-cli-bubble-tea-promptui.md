---
title: "Self-Hosted Go CLI Libraries: Cobra vs urfave/cli vs Bubble Tea vs Promptui"
date: "2026-06-22"
tags: ["go", "cli", "developer-tools", "command-line", "golang", "tui", "terminal"]
draft: false
---

Go has become the de facto language for building command-line tools, and its ecosystem offers a rich set of libraries for everything from simple flag parsing to full-featured terminal user interfaces. Choosing the right CLI library can dramatically affect your development velocity, the quality of your tool's user experience, and long-term maintainability. This guide compares four leading Go CLI libraries — **Cobra**, **urfave/cli**, **Bubble Tea**, and **Promptui** — across architecture, features, learning curve, and ecosystem support.

## Comparison: Cobra vs urfave/cli vs Bubble Tea vs Promptui

Each of these libraries serves a different niche within the Go CLI ecosystem. Cobra and urfave/cli are general-purpose CLI frameworks for building subcommand-based tools. Bubble Tea is a TUI (Terminal User Interface) framework built on the Elm Architecture. Promptui specializes in interactive prompts and input collection.

| Feature | Cobra | urfave/cli | Bubble Tea | Promptui |
|---------|-------|------------|------------|----------|
| **Stars** | 44,149 | 24,132 | 43,300 | 6,396 |
| **Paradigm** | Subcommand-based | Declarative flags | Elm Architecture (TUI) | Interactive prompts |
| **TUI Support** | No | No | Full TUI | Prompt dialogs only |
| **Subcommands** | Excellent | Excellent | Manual | N/A |
| **Flag Types** | pflag (POSIX/GNU) | Flag package | Bubble Tea helpers | N/A |
| **Completions** | Built-in shell completions | Fish/Zsh via library | Manual | N/A |
| **Learning Curve** | Moderate | Low | Moderate-High | Low |
| **Documentation** | Extensive | Good | Good + Examples | Basic |
| **Last Updated** | 2025-2026 | June 2026 | June 2026 | August 2024 |
| **Best For** | Complex multi-command CLI apps | Simple-to-medium CLI tools | Full interactive TUIs | Input prompts & forms |

## Cobra: The Commander Pattern

Cobra is the most widely adopted Go CLI framework, powering tools like Kubernetes (`kubectl`), Hugo, GitHub CLI, and Helm. It follows the Commander pattern where you define a root command and attach subcommands as children. Cobra integrates seamlessly with Viper for configuration management.

**Installation:**

```bash
go get -u github.com/spf13/cobra@latest
```

**Basic CLI with Commands:**

```go
package main

import (
    "fmt"
    "os"
    "github.com/spf13/cobra"
)

func main() {
    var name string

    rootCmd := &cobra.Command{
        Use:   "greeter",
        Short: "A friendly CLI tool",
        Long:  "Greeter says hello with configurable options.",
        Run: func(cmd *cobra.Command, args []string) {
            fmt.Printf("Hello, %s!\n", name)
        },
    }

    rootCmd.Flags().StringVarP(&name, "name", "n", "World", "Name to greet")
    
    // Subcommand: greet in different languages
    esCmd := &cobra.Command{
        Use:   "es",
        Short: "Greet in Spanish",
        Run: func(cmd *cobra.Command, args []string) {
            fmt.Printf("¡Hola, %s!\n", name)
        },
    }
    rootCmd.AddCommand(esCmd)

    if err := rootCmd.Execute(); err != nil {
        fmt.Fprintln(os.Stderr, err)
        os.Exit(1)
    }
}
```

Cobra automatically generates help text, supports persistent flags (flags inherited by all subcommands), and integrates with `cobra-cli` for scaffolding new commands. Its ecosystem includes libraries for shell completion (`bash`, `zsh`, `fish`, `powershell`), man page generation, and documentation generation.

**Strengths:** Battle-tested at massive scale, extensive plugin ecosystem, works with Viper for 12-factor config management.

**Weaknesses:** Overkill for simple single-command tools, steeper learning curve, heavier boilerplate compared to urfave/cli.

## urfave/cli: Declarative Simplicity

urfave/cli takes a declarative approach: you define your CLI as data structures (slices of `cli.Flag` and `cli.Command`) rather than building an object tree. This makes it particularly well-suited for tools where you want to see the entire command structure at a glance.

**Installation:**

```bash
go get github.com/urfave/cli/v3
```

**Declarative CLI Structure:**

```go
package main

import (
    "context"
    "fmt"
    "log"
    "os"
    "github.com/urfave/cli/v3"
)

func main() {
    cmd := &cli.Command{
        Name:  "greeter",
        Usage: "A friendly CLI tool",
        Flags: []cli.Flag{
            &cli.StringFlag{
                Name:    "name",
                Aliases: []string{"n"},
                Value:   "World",
                Usage:   "Name to greet",
            },
        },
        Commands: []*cli.Command{
            {
                Name:  "es",
                Usage: "Greet in Spanish",
                Action: func(ctx context.Context, c *cli.Command) error {
                    fmt.Printf("¡Hola, %s!\n", c.String("name"))
                    return nil
                },
            },
        },
        Action: func(ctx context.Context, c *cli.Command) error {
            fmt.Printf("Hello, %s!\n", c.String("name"))
            return nil
        },
    }

    if err := cmd.Run(context.Background(), os.Args); err != nil {
        log.Fatal(err)
    }
}
```

The declarative style shines in medium-sized tools where the CLI structure fits naturally in a single file. urfave/cli v3 introduced context-aware commands, improved error handling, and a cleaner API that eliminates global state.

**Strengths:** Rapid prototyping, clean data-driven design, excellent for tools with 5-15 subcommands, shallow learning curve.

**Weaknesses:** Less extensible for plugin architectures, no built-in TUI support, fewer integrations than Cobra ecosystem.

## Bubble Tea: Full TUI Framework

Bubble Tea, from Charmbracelet, brings the Elm Architecture to the terminal. Instead of building command-line tools with subcommands and flags, you build interactive terminal applications with models, messages, and view rendering. It powers tools like Glow (markdown reader), Soft Serve (git server TUI), and many Charmbracelet applications.

**Installation:**

```bash
go get github.com/charmbracelet/bubbletea
```

**TUI Counter Application:**

```go
package main

import (
    "fmt"
    "os"
    tea "github.com/charmbracelet/bubbletea"
)

type model struct {
    count int
}

func (m model) Init() tea.Cmd {
    return nil
}

func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
    switch msg := msg.(type) {
    case tea.KeyMsg:
        switch msg.String() {
        case "q", "ctrl+c":
            return m, tea.Quit
        case "+", "=":
            m.count++
        case "-":
            m.count--
        }
    }
    return m, nil
}

func (m model) View() string {
    return fmt.Sprintf(
        "\n  Count: %d\n\n  Press +/- to change, q to quit\n",
        m.count,
    )
}

func main() {
    p := tea.NewProgram(model{count: 0})
    if _, err := p.Run(); err != nil {
        fmt.Fprintf(os.Stderr, "Error: %v\n", err)
        os.Exit(1)
    }
}
```

Bubble Tea's ecosystem includes **Bubbles** (reusable components like text inputs, spinners, viewports, tables, and lists), **Lip Gloss** (declarative terminal styling), and **Huh** (interactive forms). Together, they enable building rich TUIs comparable to GUI applications.

**Strengths:** Gorgeous interactive terminals, component library, great documentation, active community.

**Weaknesses:** Overhead for simple CLI tools, different mental model from traditional CLI frameworks, not suitable for non-interactive scripting.

## Promptui: Interactive Input Made Simple

Promptui focuses exclusively on interactive input collection: select lists, confirmation prompts, password inputs, and text prompts with validation. It's the right choice when you need rich prompting but don't want a full TUI framework.

**Installation:**

```bash
go get github.com/manifoldco/promptui
```

**Interactive Selection:**

```go
package main

import (
    "fmt"
    "github.com/manifoldco/promptui"
)

func main() {
    languages := []string{"Go", "Python", "Rust", "TypeScript", "Zig"}
    
    prompt := promptui.Select{
        Label: "Select your favorite language",
        Items: languages,
        Size:  5,
    }

    _, result, err := prompt.Run()
    if err != nil {
        fmt.Printf("Prompt failed: %v\n", err)
        return
    }
    fmt.Printf("You chose: %s\n", result)
}
```

Promptui provides searchable select lists (type to filter), masked password inputs, input validation with custom error messages, and styled output templates. It's commonly used as a complement to Cobra or urfave/cli for commands that need user interaction, like setup wizards, configuration prompts, and confirmation dialogs.

**Strengths:** Dead simple API, searchable selects, good for form-like input collection.

**Weaknesses:** Limited to prompts (not a CLI framework), unmaintained since August 2024, fewer features than Bubble Tea's Huh forms.

## Choosing the Right Go CLI Library

The choice between these libraries depends on your use case. For traditional CLI tools with subcommands and flags, **Cobra** is the industry standard — it powers most major Go CLIs and provides everything you need out of the box. If you prefer a declarative, data-driven style for medium-sized tools, **urfave/cli** offers a cleaner API with less boilerplate.

For interactive terminal applications that need rich UI — tables, spinners, progress bars, text inputs, and real-time updates — **Bubble Tea** is the clear leader. The Charmbracelet ecosystem has matured into a comprehensive toolkit for building dashboards, TUIs, and interactive dev tools. No other Go TUI framework matches its component library and documentation quality.

If all you need is prompting (select lists, confirmations, text input with validation), **Promptui** provides the simplest API — but consider Bubble Tea's Huh component as a maintained alternative for new projects. Promptui's lack of recent updates makes it a risk for long-lived projects.

For a complete development workflow, many teams combine Cobra for CLI structure with Bubble Tea for interactive modes within specific commands. The libraries are complementary rather than mutually exclusive. For related Go ecosystem tooling, see our [Go microservices frameworks guide](../2026-05-03-dapr-vs-go-micro-vs-go-kit-self-hosted-microservices-frameworks-guide/) and [application configuration libraries comparison](../2026-06-21-application-configuration-libraries-viper-koanf-configrs-typesafe/).

## FAQ

### Which Go CLI library does Kubernetes use?

Kubernetes uses **Cobra** for its `kubectl` CLI. Cobra handles command routing, flag parsing (via `pflag`), help text generation, and shell completion across bash, zsh, fish, and PowerShell. Many other CNCF projects — including Helm, containerd, and etcd — also use Cobra for their command-line interfaces.

### Can I combine Bubble Tea with Cobra or urfave/cli?

Yes. A common pattern is using Cobra for top-level command routing and flag parsing, then launching a Bubble Tea TUI within a specific subcommand. For example, `myapp dashboard` might start a Bubble Tea program that provides an interactive terminal dashboard, while `myapp deploy --env prod` remains a traditional CLI subcommand. The libraries don't conflict because Bubble Tea takes over terminal I/O only when explicitly invoked.

### Is Promptui still maintained?

Promptui's last release was in August 2024, and the repository no longer receives regular updates. For new projects requiring interactive prompts, consider Charmbracelet's **Huh** library (`github.com/charmbracelet/huh`), which provides a modern, maintained alternative with similar functionality — select lists, text inputs, confirmations, and multi-step form flows — built on Bubble Tea and Lip Gloss.

### What about Go's standard library `flag` package?

Go's `flag` package is perfectly sufficient for simple single-command utilities with a handful of flags. However, it lacks subcommand support, shell completion, required/optional flag validation, environment variable binding, and help text customization — all of which Cobra and urfave/cli provide. For anything beyond a one-off script with `-name` and `-verbose`, a CLI framework saves significant development time.

### How do I add shell completions to my Go CLI?

Both Cobra and urfave/cli support shell completions. In Cobra, add `rootCmd.CompletionOptions.DisableDefaultCmd = false` or generate custom completions with `ValidArgsFunction`. Cobra's completions work with bash, zsh, fish, and PowerShell. In urfave/cli v3, use the `EnableShellCompletion` field on the `App` struct. For Bubble Tea TUIs, shell completion is typically not applicable since the interaction happens within the TUI itself.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Go CLI Libraries: Cobra vs urfave/cli vs Bubble Tea vs Promptui",
  "description": "Comprehensive comparison of Go command-line libraries — Cobra, urfave/cli, Bubble Tea, and Promptui — covering architecture, features, code examples, and use cases for building production CLI tools.",
  "datePublished": "2026-06-22",
  "dateModified": "2026-06-22",
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

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
