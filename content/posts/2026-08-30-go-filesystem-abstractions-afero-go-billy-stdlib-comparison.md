---
title: "Go Filesystem Abstractions in 2026: afero vs go-billy vs the Standard Library"
date: "2026-08-30"
tags: ["go", "filesystem", "afero", "go-billy", "testing", "golang"]
draft: false
cover: "/img/screenshots/afero-cover.jpg"
---

Every Go project that touches disk eventually hits the same testing wall: your `os.ReadFile` calls are great in production and impossible to test without touching the real filesystem. You either refactor every function to accept an interface, or you live with tests that create temp directories, pollute CI runners, and occasionally break because a file actually exists when it shouldn't. In 2026 the Go ecosystem has two mature filesystem abstraction libraries — spf13/afero and go-git/go-billy — plus the standard library's own `io/fs` interfaces that quietly got better than most developers realize. This guide compares all three with real code and current GitHub data.

## TL;DR / Quick Verdict

**If you want the simplest possible path to testable code, start with the standard library's `io/fs` + `fs.FS` interfaces** — zero dependencies, and since Go 1.16 every function you write against them is testable with `fstest.MapFS`. **If you need multiple storage backends (memory, OS, ZIP, SFTP, S3) behind one API, use afero** — it is the most complete abstraction in the ecosystem. **If you are building git-like tools or need an interface that mirrors `os` exactly, use go-billy** — it was born inside go-git for exactly that purpose. Afero wins on backend breadth, go-billy wins on interface fidelity, stdlib wins on zero-dependency discipline.

## Quick Comparison Table (August 2026, live GitHub data)

| Dimension | afero (spf13/afero) | go-billy (go-git/go-billy) | stdlib io/fs + os |
|---|---|---|---|
| GitHub stars | 6,694★ | 424★ | — (Go project) |
| Last commit | 2026-08-14 | 2026-08-28 | Go release cadence |
| License | Apache-2.0 | Apache-2.0 | BSD-3 |
| Core idea | Multi-backend `Fs` interface | `os`-mirroring interface for git tooling | Read-only `fs.FS` for portability |
| Backends | OS, memory, ZIP, TAR, SFTP, GCS, S3 (3rd party) | OS, memory, plus chroot/union layers | `os.DirFS`, `fstest.MapFS`, `embed.FS` |
| Write support | Full | Full | `fs.FS` is read-only; `os` for writes |
| `os` compatibility | Mirrors `os` package | Mirrors `os` package (closest) | Native |
| In-memory testing | `MemMapFs` (concurrent-safe) | `memory.New()` | `fstest.MapFS` (read-only) |
| Chroot/jail | `BasePathFs` | `chroot.New()` | Manual |
| Composition layers | CopyOnWrite, CacheOnRead, ReadOnly, Regexp | Union, chroot | Manual |
| Best for | Multi-backend apps, plugins | Git-like tools, embedded FS | Minimal-dependency code |

## Scenario Decision Matrix

| Use Case | Recommended Tool | Why |
|---|---|---|
| Unit-test code that reads files | stdlib `fs.FS` + `fstest.MapFS` | Zero deps; MapFS is read-only and perfect for fixtures |
| App that must switch between disk and memory | afero | `MemMapFs` is a drop-in swap at the call site |
| Tools that walk git repos | go-billy | Born inside go-git; matches its FS semantics |
| Sandbox a plugin to a subdirectory | afero `BasePathFs` | One line: `afero.NewBasePathFs(base, "/sandbox")` |
| Read-only embedded assets | stdlib `embed.FS` | Compile-time embedding, no abstraction needed |
| Cache over slow storage | afero `CacheOnReadFs` | Built-in layered caching |

## The Standard Library — io/fs and fstest

Since Go 1.16, the standard library ships `io/fs`, and it quietly solved half the problem afero and go-billy solve. The `fs.FS` interface (read-only) plus `os.DirFS`, `embed.FS`, and `fstest.MapFS` give you an abstraction layer with **zero dependencies** — and the Go team's blessing, since `http.FileServer`, `template`, and `archive/zip` all accept `fs.FS` today.

```go
import (
    "io/fs"
    "testing/fstest"
)

func LoadConfig(fsys fs.FS, path string) (string, error) {
    data, err := fs.ReadFile(fsys, path)
    if err != nil {
        return "", err
    }
    return string(data), nil
}

// Test with a virtual filesystem — no disk touched
func TestLoadConfig(t *testing.T) {
    fsys := fstest.MapFS{
        "config/app.json": &fstest.MapFile{Data: []byte(`{"port": 8080}`)},
    }
    cfg, err := LoadConfig(fsys, "config/app.json")
    if err != nil {
        t.Fatal(err)
    }
    // assert on cfg...
}
```

**Why this is often enough:** the `fs.FS` interface is deliberately small — `Open(name) (fs.File, error)` plus the optional `ReadDirFS` and `StatFS` refinements. Any function written against it is immediately testable with `fstest.MapFS` and usable with `embed.FS` for production assets. The trade-off: `fs.FS` is **read-only**. Writes, removal, and renaming still require `os` directly, which is exactly why the abstractions below exist.

## afero — The Multi-Backend Filesystem

Afero, at **6,694★ with its last commit on 2026-08-14** in `spf13/afero`, is the most widely adopted filesystem abstraction in Go. Its pitch: write your code against the `afero.Fs` interface once, then choose the backend at runtime — OS disk, in-memory, ZIP/TAR archives, SFTP, GCS, or a third-party S3 backend. The `Fs` interface is deliberately shaped like the `os` package so refactoring existing code is mostly mechanical.

```go
import "github.com/spf13/afero"

func ProcessConfiguration(fs afero.Fs, path string) error {
    data, err := afero.ReadFile(fs, path)
    if err != nil {
        return err
    }
    // ... process data ...
    return nil
}

// Production: real disk
AppFs := afero.NewOsFs()
ProcessConfiguration(AppFs, "/etc/myapp.conf")

// Tests: pure memory, no cleanup needed
MemFs := afero.NewMemMapFs()
afero.WriteFile(MemFs, "/etc/myapp.conf", []byte(`{"feature": true}`), 0644)
ProcessConfiguration(MemFs, "/etc/myapp.conf")
```

The features that make afero sticky:

- **Backend breadth.** `NewOsFs`, `NewMemMapFs`, `NewBasePathFs` (chroot/jail), `NewCopyOnWriteFs` (read-only base + writable overlay), `NewCacheOnReadFs` (layer a fast cache over slow storage), `NewReadOnlyFs`, `NewRegexpFs`, `NewHttpFs`, plus `zipfs` and `tarfs` archive views.
- **`os` package compatibility.** Function names and signatures mirror `os`, so `afero.ReadFile(fs, path)` reads like the stdlib call you already know.
- **`io/fs` compatibility.** Afero implements `io/fs` interfaces, so you can hand an afero filesystem to `http.FileServer`.
- **Concurrent-safe memory FS.** `MemMapFs` is atomic and concurrent-safe, which makes parallel tests deterministic.

**Where it hurts:** the interface is broader than `os` (it adds `Chmod`-style extras you may never use), the S3/GCS/SFTP backends are marked experimental, and the project's activity is steady but not frenetic. For simple read-only needs, afero is heavier than stdlib — but for multi-backend apps it is the most complete answer.

## go-billy — The os-Mirroring Interface from go-git

go-billy, at **424★ with its last commit on 2026-08-28** in `go-git/go-billy`, is the filesystem abstraction born inside the go-git project. Its defining trait: the `billy.Filesystem` interface mirrors the `os` package's surface **exactly** — `Open`, `Create`, `OpenFile`, `Stat`, `Rename`, `Remove`, `MkdirAll`, `TempFile`, `ReadDir`, `Chroot` — so code written against it behaves identically to code written against `os`, including write operations.

```go
import (
    "github.com/go-git/go-billy/v6"
    "github.com/go-git/go-billy/v6/memfs"
)

// LoadToMemory copies every readable file from any billy FS into memory
func LoadToMemory(origin billy.Filesystem, path string) (*memfs.Memory, error) {
    memory := memfs.New()
    files, err := origin.ReadDir(path)
    if err != nil {
        return nil, err
    }
    for _, file := range files {
        if file.IsDir() {
            continue
        }
        src, err := origin.Open(origin.Join(path, file.Name()))
        if err != nil {
            return nil, err
        }
        dst, err := memory.Create(memory.Join(path, file.Name()))
        if err != nil {
            return nil, err
        }
        if _, err = io.Copy(dst, src); err != nil {
            return nil, err
        }
        src.Close()
        dst.Close()
    }
    return memory, nil
}
```

Where go-billy shines:

- **Faithful `os` mirror.** Unlike `fs.FS`, billy supports the full write surface — `Create`, `Remove`, `Rename`, `MkdirAll` — with the same signatures as `os`.
- **Chroot built in.** `chroot.New(base, path)` returns a filesystem jailed to a subdirectory — the security primitive afero exposes as `BasePathFs`.
- **Proven in production.** go-git, one of the most widely embedded Go libraries, uses billy for all its working-tree and storage operations.
- **Versioned imports.** `go-git/go-billy/v6` uses clean module versions, so upgrades are explicit.

**Where it hurts:** the ecosystem is tiny (424★), the API is lower-level than afero's (no copy-on-write or caching layers), and unless you are building git-like tooling or embedding an FS in a library, billy's exact-`os` fidelity buys you little over stdlib for read-only cases.

## Migration and Adoption Pitfalls

- **Read-only vs write abstraction — decide first.** If your code only reads files, `fs.FS` + `fstest.MapFS` is the right call and you need nothing else. The moment you need writes, you need afero or billy — retrofitting `fs.FS` for writes means breaking every call site twice.
- **Afero's `MemMapFs` path semantics.** `MemMapFs` treats paths literally — there is no implicit `/` joining. Use `afero.FilepathHasPrefix` and the helpers (`afero.WriteFile`, `afero.ReadFile`) instead of hand-concatenating strings.
- **`os.Chmod` compatibility traps.** On Windows, chmod semantics differ; afero and billy both pass through the OS behavior, so don't write tests that assert Unix permissions on Windows CI.
- **Don't pass `*os.File` through abstractions.** Interfaces like `afero.File` exist so callers stay backend-agnostic; leaking concrete `*os.File` values reintroduces the coupling you abstracted away.
- **`fs.FS` path rules are strict.** Paths must be slash-separated, relative, and use `.` for the root; `os.DirFS` normalizes for you, but hand-rolled `fs.FS` implementations must follow the `validPath` rules or `fs.ValidPath` will reject them.
- **Embedded assets are read-only by design.** `embed.FS` cannot be written; if you need to write alongside embedded defaults, copy from `embed.FS` into an afero memory or disk FS at startup.
- **Version pinning.** afero is stable (v1.x) but check for the latest tagged release; go-billy majors (v5/v6) change the interface, so upgrading across majors is a real migration, not a drop-in.

## How They Compare in Practice

**Library authors (the biggest decision):** if your library accepts an FS from callers, prefer `fs.FS` for read-only APIs (maximum adoption, stdlib-only) and afero or billy for read-write APIs. Libraries that expose afero's interface force the dependency on every consumer; that is a real adoption tax.

**CLI tools and internal services:** stdlib `os` + `fstest` for tests covers 80% of cases. Add afero when you need memory-mode for demos, archive backends (ZIP/TAR), or sandboxing via `BasePathFs`.

**Git-like tooling:** go-billy is the natural fit — it mirrors go-git's own FS semantics, and the `chroot` primitive is exactly what you want for working-tree isolation.

**Testing discipline payoff:** whichever abstraction you choose, the win is the same: no temp dirs in tests, no cleanup goroutines, no CI flakiness from leftover files. The in-memory backends (`MemMapFs`, `memfs.New`, `fstest.MapFS`) are the whole point.

For more Go ecosystem deep dives, see our [Go CLI library comparison covering Cobra, urfave/cli, and Bubble Tea](../2026-06-22-go-cli-libraries-cobra-urfave-cli-bubble-tea-promptui/), the [Go error handling guide for pkg/errors vs stdlib](../2026-07-24-go-error-handling-pkg-errors-cockroachdb-stdlib-guide/), and our [Go CSV libraries roundup with gocsv, csvutil, and encoding/csv](../2026-08-30-go-csv-libraries-gocsv-csvutil-encoding-csv-comparison/).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Go Filesystem Abstractions in 2026: afero vs go-billy vs the Standard Library",
  "description": "2026 comparison of Go filesystem abstractions: spf13/afero (6,694 stars), go-git/go-billy (424 stars), and the standard library io/fs + fstest.MapFS. Real code, testing patterns, and migration pitfalls.",
  "datePublished": "2026-08-30",
  "dateModified": "2026-08-30",
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

**Is afero still maintained in 2026?** Yes. The `spf13/afero` repo shows its last commit on 2026-08-14, and the project remains the most widely used Go filesystem abstraction, used by Hugo and many other tools.

**Do I need a filesystem abstraction at all?** Only if you write tests that touch disk or need multiple storage backends. For simple apps, stdlib `os` plus `t.TempDir()` for tests is perfectly fine. The abstractions pay off when testability or backend flexibility becomes a real requirement.

**What is the difference between afero and go-billy?** Afero is a multi-backend abstraction (memory, OS, archives, network) with composition layers like copy-on-write and caching. go-billy is a smaller, exact mirror of the `os` interface built for go-git, with chroot support as its standout primitive.

**Can I use fstest.MapFS for write tests?** No. `fstest.MapFS` is read-only by design. For write-path tests, use afero's `MemMapFs` or go-billy's `memfs.New`, which support the full write surface in memory.

**Does afero work with embed.FS?** Not directly, but the pattern is simple: read from `embed.FS` at startup and copy into an afero filesystem (memory or disk) when you need writable assets alongside embedded defaults.

**Which is best for a library I'm publishing?** Prefer `fs.FS` (stdlib) for read-only APIs to avoid forcing dependencies on consumers. For read-write library APIs, afero is the safest default because of its adoption and `io/fs` compatibility.

**Is go-billy worth using outside go-git?** Yes, if you want an `os`-faithful interface with chroot isolation and are comfortable with a small ecosystem. For most other use cases, afero or stdlib covers the need with more community support.

**How do I test code that writes files without touching disk?** Inject afero `MemMapFs` (or billy `memfs.New`) into the same interface your production code uses, and write your tests against it. No temp dirs, no cleanup, no CI flakiness.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
