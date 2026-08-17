---
title: "marked vs markdown-it vs remark in 2026: Which JavaScript Markdown Parser Should You Use?"
date: "2026-08-18"
tags: ["markdown", "javascript", "nodejs", "parser", "developer-tools", "static-site", "web-development"]
draft: false
cover: "/img/screenshots/marked-cover.jpg"
---

Every blog, documentation site, chat app, and notes tool in existence now renders Markdown in the browser, and the parser you choose silently decides how fast that render is, whether your users get XSS'd, and whether your docs can be linted, transformed, and exported to a dozen formats. Most teams pick one at 2 a.m. during scaffolding and never revisit the decision. That is a mistake — the three dominant JavaScript options, marked, markdown-it, and remark, have diverged so much that they are barely the same category of software anymore.

Here is the short version: **marked is a speed-obsessed compiler (37,059 stars), markdown-it is a spec-compliant parser with a rich plugin ecosystem (21,824 stars), and remark is an entire pluggable processing pipeline built around a syntax tree (8,977 stars).** They differ in what they output, how safe they are by default, and what they let you do between input and output. Choose based on your pipeline, not on name recognition.

## TL;DR: Quick Verdict

- **Use marked** when you render Markdown in the browser or a CLI and care most about speed and simplicity — but always pair it with a sanitizer like DOMPurify, because marked does **not** sanitize output.
- **Use markdown-it** for server-side rendering, static site generators, and projects that need strict CommonMark/GFM compliance plus mature plugins (footnotes, task lists, math).
- **Use remark** when you need to *process* Markdown — lint it, transform it, convert it to HTML, PDF, or other formats — through a plugin pipeline. It is a toolkit, not a one-liner.
- If you just need `markdown -> HTML` with zero dependencies and maximum speed, marked wins. If you need an ecosystem, markdown-it. If you need a pipeline, remark.

## Feature Comparison: marked vs markdown-it vs remark (2026)

| Feature | marked | markdown-it | remark |
|---|---|---|---|
| GitHub stars (2026-08-18) | **37,059** | 21,824 | 8,977 |
| Last commit | 2026-08-17 | 2026-08-13 | 2026-07-01 |
| License | MIT | MIT | MIT |
| Output | HTML string (sync/async) | HTML string | AST (mdast) → anything via plugins |
| CommonMark compliance | High, custom extensions | **Full + GFM presets** | Full via remark-parse |
| Plugin ecosystem | Minimal (custom extensions) | Large (markdown-it plugins) | **Massive (unified ecosystem)** |
| Sanitization built in | **No (README warns)** | No (escapeHTML option) | No (rehype-sanitize plugin) |
| Browser usage | Yes (UMD + ESM) | Yes | Yes (bundled) |
| CLI included | Yes (`marked` command) | No (separate tools) | Yes (remark-cli) |
| Typed (TypeScript) | Full types | Community types | **First-class types** |
| Learning curve | Trivial | Low | Steep (unified concepts) |
| Best for | Browser rendering, speed-critical paths | Static sites, server rendering, plugins | Docs pipelines, linting, custom formats |

## Use-Case Decision Matrix

| Use Case | Recommendation | Why |
|---|---|---|
| Chat/editor live preview in browser | **marked** | Smallest bundle, fastest parse, renders inline instantly; sanitize with DOMPurify |
| Static site generator rendering | **markdown-it** | GFM, footnotes, task lists, and the plugin set that SSGs (Eleventy, VitePress ecosystem) rely on |
| Docs pipeline: lint + check links + build | **remark** | `remark-lint`, `remark-validate-links`, and transform plugins run on the AST before HTML is ever generated |
| Converting Markdown to PDF/HTML/LaTeX | **remark** | unified ecosystem has output plugins for rehype (HTML), and bridges to other formats |
| Server-side rendering with security review | **markdown-it** | `html: false` by default — raw HTML is escaped unless you opt in |
| Microservice or edge function with tight size budget | **marked** | The entire parser is a few KB gzipped; ideal for Cloudflare Workers or Lambda |

## marked — Built for Speed

marked positions itself explicitly as a compiler rather than a renderer: it is a low-level, dependency-free parser that converts Markdown to HTML with no caching and no long-running state. At **37,059 stars**, it is the most-starred Markdown parser in the JavaScript ecosystem, and its README leads with three words: *built for speed*.

The API could not be simpler. Node.js:

```js
import { marked } from 'marked';
const html = marked.parse('# Marked in Node.js');
console.log(html);
```

Browser, via UMD build:

```html
<div id="content"></div>
<script src="https://cdn.jsdelivr.net/npm/marked/lib/marked.umd.js"></script>
<script>
  document.getElementById('content').innerHTML =
    marked.parse('# Marked in the browser\n\nRendered by **marked**.');
</script>
```

Or as a CLI:

```bash
$ marked -o hello.html
hello world
^D
$ cat hello.html
<p>hello world</p>
```

One sentence from the README matters more than any benchmark: **"Marked does not sanitize the output HTML. Please use a sanitize library, like DOMPurify, on the output HTML!"** Marked is a compiler, not a security boundary. If your input comes from users — comments, chat messages, note content — you must run the output through DOMPurify, sanitize-html, or equivalent. This is not a bug; it is the price of being a fast, unopinionated compiler.

marked is also highly configurable through extensions: you can override renderers (custom heading renderer, custom link renderer) and add custom block-level and inline-level tokenizers. That extension mechanism is powerful but smaller and less mature than markdown-it's plugin ecosystem. If you need GFM tables and strikethrough out of the box, you configure marked's `gfm: true` option — but for advanced plugin coverage you will often end up adding `marked-gfm-heading-id`-style helper packages.

## markdown-it — The Spec-First, Plugin-Rich Choice

markdown-it's tagline is *"Markdown parser, done right. 100% CommonMark support, extensions, syntax plugins & high speed."* It is the workhorse behind countless static site generators and documentation platforms, and its **21,824 stars** reflect a reputation for correctness: it follows the CommonMark spec religiously and ships presets for GitHub-flavored Markdown and the legacy "zero" mode that approximates old-school Markdown.pl behavior.

The core API is one constructor and one render call:

```js
import MarkdownIt from 'markdown-it'
const md = new MarkdownIt()
const result = md.render('# markdown-it rulezz!')
```

The crucial design decision is the default `html: false` mode: raw HTML in your Markdown is **escaped** rather than passed through. Where marked requires you to add sanitization, markdown-it defaults to the safe behavior and lets you opt in with `new MarkdownIt({ html: true })` when you control the content. That single default flips the security calculus for server-side rendering — if you render untrusted user content, markdown-it is safe out of the box and marked is not.

The plugin ecosystem is the other big draw. The official documentation lists plugins for footnotes, task lists, abbreviations, definition lists, subscript/superscript, and container blocks, and community plugins add syntax highlighting hooks, math (KaTeX/TeX), and custom block types. Configuring a rich document setup looks like this:

```js
const md = new MarkdownIt({
  html: false,
  linkify: true,
  typographer: true
}).use(require('markdown-it-footnote'))
  .use(require('markdown-it-task-lists'))
  .use(require('markdown-it-katex'));
```

For an SSG like Eleventy or a docs platform, markdown-it is usually the right default: correct, safe by default, plugin-rich, and fast enough that parsing is never your bottleneck. If you are building a static documentation site, our [self-hosted flat-file Markdown notes comparison](../2026-05-23-self-hosted-flat-file-markdown-notes-flatnotes-dendron-hedgedoc/) covers the storage layer that typically sits behind such a parser.

## remark — The Unified Processing Pipeline

remark is not a single parser; it is an ecosystem. `remark-parse` turns Markdown into an **mdast syntax tree** (a JSON-like structure where every heading, paragraph, link, and text node is a typed object), plugins transform that tree, and other unified packages serialize it. You can lint Markdown without rendering it, rewrite links in bulk, convert to HTML via rehype, or emit entirely custom formats.

The canonical pipeline from the README converts Markdown to sanitized HTML by combining the remark and rehype ecosystems:

```js
import rehypeSanitize from 'rehype-sanitize'
import rehypeStringify from 'rehype-stringify'
import remarkParse from 'remark-parse'
import remarkRehype from 'remark-rehype'
import {unified} from 'unified'

const file = await unified()
  .use(remarkParse)
  .use(remarkRehype)
  .use(rehypeSanitize)
  .use(rehypeStringify)
  .process('# Hello, *Mercury*!')
```

Every `.use()` call is a plugin. The same AST pipeline powers `remark-lint` (linting rules for Markdown style and structure), `remark-validate-links` (checking internal and external links in a docs repo), `remark-frontmatter`, and dozens of transforms. This is why remark is the backbone of modern documentation toolchains: **you can check, transform, and render the same content through one pipeline, and the tree structure means nothing is lost in an intermediate HTML string.**

The cost is complexity. The unified model — syntax trees, plugins, transformers, bridges between ecosystems — has a real learning curve, and the TypeScript-first design means the types are excellent but the concepts are many. For a one-off "convert this string" job, remark is overkill. For a docs repo with hundreds of files that need linting, link validation, and consistent output, it is the only option that scales.

**When remark shines:** monorepo documentation, knowledge bases, and any pipeline where Markdown is an *input format* rather than a display format. It also pairs with tools in the broader ecosystem; our [Markdown presentation tools comparison](../2026-04-20-slidev-vs-revealjs-vs-marp-markdown-presentation-tools-2026/) shows the same unified philosophy applied to slides.

## Pitfalls and Gotchas

1. **XSS is the number one issue, and defaults differ.** marked ships unsanitized; markdown-it escapes raw HTML by default; remark needs rehype-sanitize wired in explicitly (as in the example above). Whatever you pick, decide *who owns the input* first. Untrusted user input → sanitizer mandatory, no exceptions. Trusted docs → you can relax but still prefer escaping.
2. **CommonMark compliance is not binary.** marked implements CommonMark with some deviations, markdown-it is the reference-quality implementation, remark uses its own tokenizer. Edge cases (nested emphasis, link reference definitions, indented code blocks) render differently across all three. If you migrate a corpus between parsers, diff your output before shipping.
3. **GFM is a preset, not a default.** Tables, strikethrough, task lists, and autolinks are GitHub extensions. markdown-it has a `preset: 'default'` with GFM-ish rules and a `commonmark` preset; marked has `gfm: true`; remark needs `remark-gfm`. If your docs rely on tables, test the exact option combination — this is the most common "why is my table broken" report.
4. **Beware the `html: true` seduction.** Enabling raw HTML passthrough for one nice feature (embedded video, custom divs) opens the entire script-tag attack surface. If you need one HTML feature, implement it as a renderer override or a plugin, not a global flag.
5. **Rendering time matters at scale.** marked is fastest for single renders, but if you render thousands of documents at build time, the difference is milliseconds per file and total build time is dominated by I/O. Optimize for maintainability first; micro-benchmarks mislead.
6. **CLI availability differs.** marked ships a `marked` CLI out of the box; remark ships `remark-cli`; markdown-it has no official standalone CLI (tools like mdformat or md2html wrap it). For scripted pipelines, this can decide your pick.
7. **Version churn in the unified ecosystem.** remark's packages evolve quickly and breaking changes land between major versions (`remark-parse` v10 → v11 changed the parser API). Pin versions in CI and use the official presets (`remark-preset-lint-consistent`) rather than hand-rolling lint configs.

## FAQ

**Which JavaScript Markdown parser is fastest?**
marked is consistently the fastest in community benchmarks for single-document parsing, which is why it dominates browser-side live preview. markdown-it is also fast (within ~2-3x of marked in most benchmarks) and its spec adherence makes it the safer pick server-side. remark is slower because it builds a full syntax tree — the AST work is the point, not a side effect.

**Is marked safe for user-generated content?**
Not by itself. The marked README explicitly warns that it does not sanitize output HTML. If you render untrusted content, run the output through DOMPurify or sanitize-html, or choose markdown-it with its default `html: false` mode. Never pass raw marked output for user content into `innerHTML` without sanitization.

**What is the difference between remark and rehype?**
remark processes Markdown (mdast tree); rehype processes HTML (hast tree). They are separate unified ecosystems connected by the `remark-rehype` bridge. You go Markdown → remark-parse → mdast → remark-rehype → hast → rehype plugins → rehype-stringify → HTML. The bridge is why remark pipelines can do things like sanitize HTML *after* converting, or lint the HTML output of a Markdown file.

**Can I use these with React to render Markdown?**
Yes. The common pattern is parsing Markdown to HTML with any of the three, then using `dangerouslySetInnerHTML` (with sanitization) or a React Markdown component that renders the AST to React elements — which is what remark's ecosystem enables via `rehype-react`. For interactive docs, the AST-based approach gives you custom component rendering for headings, code blocks, and links.

**Which parser does GitHub use?**
GitHub's own implementation is cmark-based (the reference C implementation of CommonMark), not any of these JavaScript parsers. markdown-it is the closest JavaScript equivalent in spec fidelity. In the JavaScript world, markdown-it powers or inspired many SSG pipelines, while remark powers documentation toolchains like those used across the unified ecosystem itself.

**Do these parsers support tables and task lists?**
Only with GFM features enabled: marked with `gfm: true`, markdown-it with the `preset: 'default'` (or explicit rules), remark with the `remark-gfm` plugin. Out of the box, pure CommonMark has no tables. For a full comparison of the underlying Markdown parsing landscape across languages, see our [Markdown parser libraries comparison](../2026-06-20-markdown-parser-libraries-pulldown-cmark-goldmark-comrak-commonmarkjs/).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "marked vs markdown-it vs remark in 2026: Which JavaScript Markdown Parser Should You Use?",
  "description": "Compare marked, markdown-it, and remark in 2026 — the three dominant JavaScript Markdown parsers. Speed, security, plugins, GitHub stats, and use-case recommendations.",
  "datePublished": "2026-08-18",
  "dateModified": "2026-08-18",
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
