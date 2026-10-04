---
title: "Pygments vs highlight.js vs Chroma vs Shiki in 2026: The Syntax Highlighting Library Showdown"
date: "2026-10-05"
tags: ["developer-tools", "syntax-highlighting", "documentation", "python", "javascript", "golang"]
draft: false
cover: "/img/screenshots/shiki-logo.jpg"
---

# Pygments vs highlight.js vs Chroma vs Shiki in 2026

Every documentation site, blog, developer portal, and code review tool has the same ugly little dependency: the thing that turns a fenced code block into colored tokens. Get it wrong and you ship either a half-megabyte JavaScript bundle to render three lines of YAML, or a build pipeline that takes four minutes because it re-tokenizes the same file on every deploy.

Four libraries have effectively split this market in 2026 — **Pygments** (Python), **highlight.js** (JavaScript), **Chroma** (Go), and **Shiki** (TypeScript). They solve the same problem from very different angles: grammar source, where highlighting runs (build time vs browser), and how much of the output the caller has to manage. This guide compares them on live 2026 data, shows the CLI and API for each, and ends the "which one?" debate with a decision matrix.

## TL;DR: The 30-second verdict

- **Static sites and docs that want editor-accurate colors with zero runtime cost?** Use **Shiki** at build time.
- **Client-side highlighting with the smallest possible setup and no dependencies?** Use **highlight.js**.
- **Go applications, Hugo pipelines, or terminal output?** Use **Chroma**.
- **CI checks, slides, terminals, LaTeX/RTF output, or "highlight literally everything"?** Use **Pygments**.

The practical rule: **highlight at build time whenever you can.** Every library here except Pygments is happy to run in the browser, but shipping tokens instead of a tokenizer keeps your runtime bundle small and your page fast.

## Library health and feature comparison

All star counts and commit dates below were verified live on GitHub in October 2026.

| Library | Language | GitHub stars | License | Last commit | Grammar source | Distribution |
|---|---|---|---|---|---|---|
| **highlight.js** | JavaScript | 25,004 | BSD-3-Clause | 2026-09-06 | Custom regex grammars | npm, CDN, zero dependencies |
| **Shiki** | TypeScript | 13,842 | MIT | 2026-10-01 | TextMate grammars | npm (ESM), Node and browser |
| **Chroma** | Go | 5,047 | MIT | 2026-10-03 | Lexers ported from Pygments | Go module plus a CLI |
| **Pygments** | Python | 2,214 | BSD-2-Clause | 2026-09-27 | The original Python lexers | pip package plus `pygmentize` CLI |
| *(syntect)* | Rust | 2,437 | MIT | 2026-04-28 | Sublime Text syntax definitions | Rust crate |

Notice which project has the most stars and which has the most languages: highlight.js leads on adoption, but **Pygments and Chroma support far more languages**, and Shiki wins on output fidelity because it reuses the exact grammars your editor already uses.

![Shiki renders code with TextMate grammars for editor-accurate highlighting](/img/screenshots/shiki-logo.jpg "Shiki syntax highlighter, the TextMate-based highlighter")

## Which highlighter for which job?

| Use case | Recommendation | Why |
|---|---|---|
| Hugo or any Go static site generator | **Chroma** | Hugo embeds Chroma natively; no extra JS shipped |
| Next.js, Astro, or Vitepress docs | **Shiki** | Build-time tokens, TextMate fidelity, fine-grained bundles |
| Plain HTML page needing a quick win | **highlight.js** | Drop in a CDN script and one CSS theme, done |
| CI linting, terminal coloring, slides | **Pygments** | Huge language coverage and CLI-first workflow |
| Email HTML with inline styles | **Pygments** | Inline style output survives email clients |
| Rust application embedding a highlighter | **syntect** | Native crate using Sublime syntax definitions |

## Shiki: editor-accurate colors at build time

**13,842 stars · MIT · last commit October 1, 2026**

Shiki's central idea is simple and, in retrospect, obviously correct: instead of maintaining its own grammars, it loads **TextMate grammars** — the same files Visual Studio Code and Sublime Text use. The result is highlighting that matches your editor exactly, including your chosen theme, because Shiki ships real VS Code themes.

```bash
npm i shiki
```

```js
import { codeToHtml } from 'shiki'

const html = await codeToHtml('const greeting = "hello"', {
  lang: 'javascript',
  theme: 'vitesse-dark'
})
```

Two operational notes matter in production. First, the primary API is **asynchronous** — `codeToHtml` returns a promise, so your template layer must await it (or you pre-render at build time, which you should). Second, Shiki's default bundle is large because it includes many grammars and themes; use the fine-grained bundle and register only the languages you actually use. Do that and Shiki becomes one of the leanest options, because it emits static HTML with inline styles and ships zero highlighting JavaScript to the visitor.

## highlight.js: the fastest path to colored code

**25,004 stars · BSD-3-Clause · last commit September 6, 2026**

highlight.js is the library most people meet first, and for good reason: it has zero dependencies, works with a single script tag, auto-detects the language, and covers around 190 languages in its full distribution. For a one-off page, nothing is faster to set up.

```bash
npm install highlight.js
```

```js
import hljs from 'highlight.js'
import 'highlight.js/styles/github-dark.css'

const html = hljs.highlight('<h1>Hello World!</h1>', { language: 'xml' }).value

// Or, in the browser, highlight every <pre><code> block:
document.querySelectorAll('pre code').forEach((el) => hljs.highlightElement(el))
```

The trade-offs are real. The full build is heavy, so use the custom build tool to include only your languages. Auto-detection is convenient but occasionally wrong on short snippets — **specify the language explicitly** when you know it. And highlight.js styles come from a separate theme CSS file; if you forget to import it, you get correctly tokenized but completely unstyled code.

## Chroma: the Go workhorse behind Hugo

**5,047 stars · MIT · last commit October 3, 2026**

Chroma is a general-purpose highlighter in pure Go, and it has a strong claim to being the most widely deployed one on the planet — **Hugo embeds Chroma** to highlight every code block in the enormous population of Hugo sites, including the one you are reading. It was ported from Pygments, which means its lexer and style catalogues inherit two decades of Pygments work.

```bash
go get github.com/alecthomas/chroma/v2
chroma -l go -f html -s monokai main.go
```

The CLI makes it easy to wire into shell pipelines:

```bash
cat server.go | chroma -l go -f terminal256 -s dracula
```

Want to try themes and languages without installing anything? The project maintains an official Chroma Playground where you can paste code and flip through formatters and styles. One forward-looking caveat: **Chroma v3 is in alpha** and changes the module path to `github.com/alecthomas/chroma/v3` while replacing its custom iterator type with Go's built-in `iter.Seq[Token]`. Pin v2 for now unless you are deliberately migrating.

## Pygments: the original and still the widest

**2,214 stars · BSD-2-Clause · last commit September 27, 2026**

Pygments is the library the others benchmark against, and it is still the answer to two questions: *"can you highlight this obscure language?"* and *"can you output it as something other than HTML?"* With 500-plus lexers and 15-plus formatters, Pygments speaks to HTML, LaTeX, RTF, SVG, terminal escape codes, and more.

```bash
pip install Pygments

# Render a Python file as standalone HTML with line numbers
pygmentize -l python -f html -O full,linenos=1 -o demo.html demo.py

# Inline styles, ideal for emails
pygmentize -l yaml -f html -O noclasses=True config.yaml
```

You can also use it from Python directly:

```python
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter

lexer = get_lexer_by_name("javascript")
formatter = HtmlFormatter(cssclass="code", style="monokai")
print(highlight("const x = 1", lexer, formatter))
print(HtmlFormatter(style="monokai").get_style_defs(".code"))
```

Pygments is a build-time tool first: it is excellent in CI, Sphinx, and scripted pipelines, and fine in a web request if you cache the result. For a high-traffic dynamic route, do not call it on every request.

## Pitfalls and migration notes

**Missing theme CSS is the number one "bug".** highlight.js, Shiki, Chroma, and Pygments' class-based output all separate tokenization from styling. If your code is colored correctly in the DOM but looks flat on screen, you forgot to load the theme stylesheet.

**Never highlight already-escaped HTML.** Feed the highlighter raw source text. If you pre-escape `&` and `<` yourself, you will get double-escaped output and visible `&amp;lt;` artifacts. Let the library escape.

**Client-side highlighting costs bandwidth twice.** You ship the library and you ship the raw code. Build-time highlighting ships neither. For React and static-site frameworks, prefer a build-time plugin over a runtime effect.

**Grammar mis-selection is silent.** Highlighting YAML as plain text "works" — it produces output, just wrong output. Assert a language per block, and make unknown languages a build warning rather than a silent fallback.

**Bundle discipline matters for JavaScript.** highlight.js and Shiki both default to generous bundles. Use highlight.js' custom build and Shiki's fine-grained bundle; trimming either can cut hundreds of kilobytes.

**Watch the Chroma v3 transition.** The module path and iterator type change, so a naive `go get -u` can break a working pipeline. Pin your major version and read the migration notes.

**Treat highlighters as parsers, not sanitizers.** They tokenize code; they do not make untrusted HTML safe. If you ever pass user-controlled markup through a highlighter and inject the result, sanitize it first — our [HTML-focused tooling comparisons](../2026-06-20-markdown-parser-libraries-pulldown-cmark-goldmark-comrak-commonmarkjs/) cover where that boundary belongs in a content pipeline. If your output target is a terminal rather than a browser, our [terminal rendering library comparison](../2026-06-26-cpp-terminal-ui-libraries-ftxui-replxx-linenoise-tabulate/) picks up where the color output mode ends, and the [text UI toolkit guide](../2026-07-01-python-terminal-ui-libraries-textual-rich-prompt-toolkit-urwid/) shows how Rich reuses Pygments under the hood.

## FAQ

### Which syntax highlighter supports the most languages?

Pygments covers the most, with 500-plus lexers. Chroma is next at roughly 200 lexers (ported from Pygments), and highlight.js ships around 190 languages across its distributions. Shiki's coverage is set by the TextMate grammars you install, which in practice means hundreds of languages with editor-grade accuracy.

### Should I highlight code at build time or in the browser?

Build time, whenever possible. It eliminates the highlighting JavaScript from your visitor's download, removes a runtime dependency, and makes output cacheable. Use browser-side highlighting only for user-authored content that arrives after the page loads, such as a live code playground or an editable preview.

### Why does my highlighted code look unstyled?

You almost certainly have not loaded the theme CSS. highlight.js needs a `styles/*.css` import; Shiki needs a theme passed to its API; Chroma needs the `-s` style flag; Pygments class output needs `HtmlFormatter.get_style_defs()` written into your page. Tokenization without styling produces correct but monochrome markup.

### Which highlighter does Hugo use?

Chroma. Hugo embeds it directly, so every Hugo site gets Chroma-quality highlighting with no extra JavaScript. If you write for a Hugo blog, you can control it from `hugo.toml` with the `chroma` style setting rather than adding another library.

### Can I highlight Markdown code fences inside a content pipeline?

Yes, and all four libraries expose per-block APIs rather than whole-document ones. The usual pattern is to parse Markdown first, then hand each fenced block plus its language tag to the highlighter, and replace the fence with the returned HTML. Choosing the parser is a separate decision from choosing the highlighter.

### Are these libraries free for commercial use?

Yes. highlight.js is BSD-3-Clause, Pygments is BSD-2-Clause, and Shiki and Chroma are MIT — all permissive licenses that let you embed them in closed-source and commercial products, provided you keep the license notice. syntect is MIT as well.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Pygments vs highlight.js vs Chroma vs Shiki in 2026: The Syntax Highlighting Library Showdown",
  "description": "A 2026 comparison of syntax highlighting libraries Pygments, highlight.js, Chroma, and Shiki with live GitHub data, CLI and API examples, a decision matrix, and production pitfalls.",
  "datePublished": "2026-10-05",
  "dateModified": "2026-10-05",
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
