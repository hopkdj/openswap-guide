---
title: "HTML and Template Linting in 2026: HTMLHint vs html-validate vs djLint"
date: "2026-11-12"
tags: ["html", "linting", "developer-tools", "ci-cd", "templating"]
draft: false
cover: "/img/screenshots/djlint-template-lint.jpg"
---

Ship a broken `<div>` nesting to production and browsers will silently repair it — differently, in every engine. Ship an unclosed `<button>` inside a Django template and your form stops submitting for exactly the users who matter. Neither failure shows up in a screenshot test, and neither shows up in your JavaScript test suite.

HTML is the one language in your stack that nobody validates. That is why three very different tools dominate this space: **HTMLHint**, **html-validate**, and **djLint**. They look interchangeable on a feature matrix, but they fail in completely different ways on template syntax — and one of them will waste your afternoon if you point it at the wrong files.

## TL;DR: Quick Verdict

- **Server-rendered templates (Django, Jinja, Twig, Nunjucks, Handlebars, Go templates, Liquid): use `djLint`.** It is the only one of the three that parses template syntax as syntax instead of treating `{% if %}` as malformed markup.
- **Static HTML, component fragments, or a strict HTML5 conformance check: use `html-validate`.** Its parser is deliberately unforgiving, it validates fragments from Vue/Angular-style components, and its element metadata catches real accessibility and semantics bugs rather than style nits.
- **Use `HTMLHint` when you want the cheapest possible gate**: one npm dependency, zero configuration, readable output, and a rule set that flags the boring-but-real mistakes (duplicate IDs, missing `alt`, unpaired tags). It is a smoke detector, not a building inspector.

If you write templates and pick `html-validate`, expect a pile of parse errors that are not errors at all. If you write plain HTML and pick `djLint`, you get formatting opinions you did not ask for. Tool choice here is a function of file type, not preference.

## Side-by-Side Comparison

| Dimension | HTMLHint | html-validate | djLint |
|---|---|---|---|
| Stars | **3,320** | GitLab-primary (GitHub mirror: 19) | **958** |
| Latest release | v1.9.2 | 11.21.0 | v1.50.0 |
| Last push | 2026-11-10 | 2026-11-11 | 2026-11-11 |
| Language | JavaScript | TypeScript | Python |
| License | MIT | MIT | GPL-3.0 |
| Template awareness | None | Fragments only | **Native** (12+ template dialects) |
| Formatter included | No | No | **Yes** (`--reformat`) |
| Offline | Yes | Yes (documented) | Yes |
| Config file | `.htmlhintrc` | `.htmlvalidate.json` | CLI flags / pre-commit |
| Best at | Fast rule checks | Strict structural validation | Template lint + format |

One number needs context: **html-validate's GitHub repository is a mirror.** Primary development happens on GitLab, so the 19 stars on the GitHub copy understate real adoption. Judge it by release cadence (11.21.0, pushed the same week this article was published) rather than by mirror popularity.

## Decision Matrix: Pick in Ten Seconds

| Your file types | Use this | Reason |
|---|---|---|
| `.html` static pages, email templates, landing pages | **HTMLHint** | Zero-config, instant, no false positives on plain markup |
| Vue/Angular/Svelte component fragments | **html-validate** | Explicitly designed to validate incomplete documents |
| Django / Jinja / Twig / Nunjucks / Liquid templates | **djLint** | Only tool that understands the template syntax |
| Go `html/template` or Handlebars partials | **djLint** | Has a dedicated profile per dialect |
| You also want consistent indentation and attribute wrapping | **djLint** | It is a formatter first, linter second |
| You need spec-level conformance for a public site | **html-validate** | Strict, non-forgiving HTML5 parsing |
| You have 5 minutes and a legacy codebase | **HTMLHint** | Add one CI step and start with `tag-pair` only |

## HTMLHint: The Five-Minute Gate

HTMLHint's pitch is that you can adopt it without a design meeting. Install it as a dev dependency and point it at your HTML:

```bash
npm install htmlhint --save-dev
npx htmlhint "src/**/*.html"
```

Configuration lives in `.htmlhintrc`, which the CLI searches for in the current directory and every parent directory. That makes monorepos behave sanely: a root config applies everywhere unless a package overrides it.

```json
{
  "tagname-lowercase": true,
  "attr-lowercase": true,
  "attr-value-double-quotes": true,
  "doctype-first": true,
  "tag-pair": true,
  "id-unique": true,
  "src-not-empty": true,
  "alt-require": true
}
```

You can also run one-off rule sets without touching config files, which is genuinely useful for triaging a legacy tree:

```bash
htmlhint --rules tag-pair,id-class-value=underline index.html
```

Or scope rules to a single file with an inline comment:

```html
<!--htmlhint tag-pair,id-class-value:underline -->
<html>
  <head>
    <title>Checkout</title>
  </head>
</html>
```

**Where it hurts:** HTMLHint does not understand template syntax. Feed it a Jinja partial and `{% extends "base.html" %}` becomes a parse problem, not a statement. Teams that try to lint templates with HTMLHint end up maintaining an ignore list so long that the gate stops meaning anything.

![HTMLHint logo, the zero-configuration HTML linter](/img/screenshots/htmlhint-lint.jpg "HTMLHint catches duplicate IDs, unpaired tags and missing alt attributes with a single npm dependency")

## html-validate: Strict Conformance and Real Semantics

html-validate is an offline HTML5 validator built around a strict parser. Its documentation is explicit about the design goal: it "will not try to correct any incorrect markup or guess what it should do." That is either exactly what you want before a release or exactly what you do not want on a legacy page, with little middle ground.

```bash
npm install -g html-validate
html-validate "src/**/*.html"
```

Configuration in `.htmlvalidate.json` extends a recommended preset and overrides individual rules:

```json
{
  "extends": ["html-validate:recommended"],

  "rules": {
    "close-order": "error",
    "void": ["warn", { "style": "omit" }]
  }
}
```

The output is where the tool earns its place. Given deliberately sloppy markup, the project's own README shows this result:

```plaintext
  1:1  error  Element <p> is implicitly closed by adjacent <div>  no-implicit-close
  2:2  error  Button is missing type attribute                    button-type
  6:4  error  Unexpected close-tag, expected opening tag          close-order
```

Read those three lines again. `no-implicit-close` and `button-type` are not style opinions — they are the two bugs that most often break forms and layouts in ways that survive code review. A missing `type` on a `<button>` inside a `<form>` defaults to `submit`, which is why "the page reloads when I click cancel" is one of the oldest bugs on the web.

The other differentiator is fragment support. html-validate validates incomplete documents, so a Vue or Angular component template does not need a synthetic `<html>` wrapper to pass. It ships four build flavours (CommonJS and ESM, each with a full and a browser variant), and the browser bundle runs entirely client-side with no upload — relevant if compliance rules forbid sending markup to a third-party validator.

**Where it hurts:** it is not template-aware either. Template directives inside attributes will trip the parser, and the fix is usually disabling rules per file — which quietly erodes the value of the preset you just enabled.

## djLint: Template-Aware Linting and Formatting

djLint does something the other two cannot: it parses the template syntax *and* the markup together. That single design decision is why it is the only credible option for server-rendered HTML.

```bash
pip install djlint

djlint . --lint
djlint . --check --single-attribute-per-line
djlint . --reformat --single-attribute-per-line
```

Profiles tell it which dialect it is reading, which changes both the lint rules and the formatting behaviour:

```bash
djlint . --reformat --single-attribute-per-line --profile=django
```

The README lists profiles for Django, Jinja, Twig, Nunjucks, Handlebars, Liquid, Go templates, Angular, Tera, Askama, and Mako — a coverage list that no generic HTML linter can match. Formatting and linting in one binary matters more than it sounds: with HTMLHint or html-validate you need a separate formatter (Prettier with a template plugin, usually), and the two tools will disagree about attribute wrapping until you give up and disable one.

For the pre-commit crowd, the repository ships two hooks — one reformats, one lints:

```yaml
repos:
  - repo: https://github.com/djlint/djLint
    rev: v1.50.0 # use the latest version instead
    hooks:
      - id: djlint-reformat
      - id: djlint
```

Installation has one trap worth flagging. Besides `pip`, `pipx`, `uv tool install`, and a Homebrew formula, there is an npm package — and the README warns in bold that it is only a wrapper whose install script runs `pip` against whatever `python3` is on your `PATH`, potentially **downgrading** an existing djLint install while npm takes no responsibility for managing or uninstalling it. If your project is not already npm-only, install it with pip.

**Where it hurts:** GPL-3.0 licensing is a genuine consideration for tooling vendored into a commercial distribution, and the opinionated formatting will produce a large first diff on any existing template tree. Commit that reformat as its own isolated change or code review becomes impossible.

## A CI Pipeline That Runs All Three Correctly

The mistake teams make is running one linter over every file type. Route by extension instead — templates to djLint, plain HTML to html-validate, and HTMLHint as a fast pre-commit smoke test:

```yaml
name: markup-lint
on: [pull_request]

jobs:
  templates:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install djlint==1.50.0
      - run: djlint . --check --profile=django --lint

  html:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "22"
      - run: npm ci
      - run: npx html-validate "public/**/*.html"
      - run: npx htmlhint "public/**/*.html"
```

Pinning the exact djLint version is not paranoia. Lint rule sets change between minor releases, and a formatter that reformats differently on a Tuesday will block unrelated pull requests. Pin it, then bump deliberately.

## Pitfalls That Will Bite You

**Never point a generic HTML linter at template files.** This is the number one cause of "we tried linting HTML and gave up." A single Jinja `{% for %}` block can generate a dozen parse errors in html-validate. Route by file type, as in the workflow above.

**Formatting and linting must land in separate commits.** Running `djlint --reformat` across an existing project touches nearly every file. Land the reformat alone, then enable the lint gate in the next pull request — otherwise reviewers cannot see the one semantic change buried in 400 whitespace hunks.

**"Offline" is a compliance feature, not a footnote.** html-validate documents that it uploads nothing; the W3C validator, by contrast, sends your markup to a remote service. If your build runs somewhere without outbound network access — air-gapped CI, a regulated environment — only the offline tools are viable.

**Duplicate IDs are the highest-value rule you are probably not enforcing.** `id-unique` in HTMLHint and the equivalent check in html-validate catch a class of bug that unit tests never see: two components rendering the same ID, breaking every `label for=` and `aria-labelledby` on the page. Enable it first.

**GPL tooling has distribution implications.** djLint is GPL-3.0. Running it in CI is fine; bundling it into a shipped product is a conversation your legal team should have. The MIT-licensed alternatives exist, but neither understands templates.

**Lint output volume is not a quality metric.** A gate that reports 3,000 warnings gets ignored within a week. Start with three or four rules that catch real user-visible bugs, get to zero, then add more.

For the broader lint stack, our [documentation linting guide covering markdownlint, remark-lint and Vale](../2026-11-11-docs-linting-markdownlint-remark-lint-vale/) covers the prose side of the same pipeline. Teams standardizing across many languages should read the [mega-linter vs super-linter vs reviewdog comparison](../2026-04-23-megalinter-vs-super-linter-vs-reviewdog-self-hosted-linting-guide-2026/), and if you are still choosing a template engine, the [JavaScript template engine comparison of EJS, Pug and Nunjucks](../2026-08-17-javascript-template-engines-ejs-pug-nunjucks-comparison/) explains the syntax differences these linters have to understand.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "HTML and Template Linting in 2026: HTMLHint vs html-validate vs djLint",
  "description": "A practical comparison of HTMLHint, html-validate and djLint for linting HTML and server-rendered templates, with real configuration, CI routing by file type and the false-positive traps of generic HTML linters.",
  "datePublished": "2026-11-12",
  "dateModified": "2026-11-12",
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

### Which HTML linter is best for Django or Jinja templates?

djLint. It is the only one of the three that parses template syntax, with a `--profile` per dialect that adjusts both lint rules and formatting. HTMLHint and html-validate will report template tags as malformed markup.

### Is html-validate the same as the W3C validator?

No, but it targets the same goal. html-validate runs entirely offline against its own strict HTML5 parser and element metadata, whereas the W3C validator is hosted and receives your markup over the network. For CI in restricted networks, the offline property is the deciding factor.

### Can I use HTMLHint and html-validate together?

Yes, and many teams do: HTMLHint as a fast pre-commit hook with a handful of rules, html-validate as the stricter pull-request gate. Keep their rule sets aligned on the overlapping checks (tag pairing, unique IDs) so developers do not get contradictory advice.

### Why does my linter report hundreds of errors on a template that renders fine?

Because browsers and template engines are forgiving and linters are not. Template directives break the HTML parse tree for non-template-aware tools, and strict parsers reject markup that engines silently repair. Fix by routing files to the correct tool rather than by blanket-disabling rules.

### Does djLint replace a formatter like Prettier?

For HTML and template files, effectively yes — `djlint --reformat` handles markup and template syntax together, which Prettier cannot do without per-dialect plugins. Most teams still keep Prettier for JavaScript and CSS and let djLint own the templates.

### How do I introduce a lint gate without blocking every pull request?

Start with three rules that catch user-visible bugs (unpaired tags, duplicate IDs, missing button `type`), run in report-only mode for a week, then make it blocking. Add rules incrementally after the existing violations reach zero.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
