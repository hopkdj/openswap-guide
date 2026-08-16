---
title: "Node.js Template Engines in 2026: EJS vs Pug vs Nunjucks — Which One for Server-Side Rendering?"
date: "2026-08-17"
tags: ["javascript", "nodejs", "templating", "frontend"]
draft: false
cover: "/img/screenshots/ejs-cover.jpg"
---

Your Express server needs to render HTML. You can concatenate strings — for about a week, until you need layouts, includes, conditionals, and HTML escaping that actually works. That is what template engines are for, and Node.js has three serious candidates: **EJS (8,117 stars), Pug (21,853 stars), and Nunjucks (8,984 stars)**. They look interchangeable at a glance — they all take data and produce HTML — but they differ so much in syntax, safety defaults, and ecosystem fit that picking the wrong one will cost you either a debugging week or a security review.

## TL;DR / Quick Verdict

Choose **EJS** if you want plain JavaScript inside your templates and a one-line Express integration (`app.set('view engine', 'ejs')`) — it is the least magical option and the safest for teams that hate learning new syntax. Choose **Pug** if you care about terse, indentation-based markup and are building design-heavy, template-maintained sites — its syntax is beautiful and its star count reflects that love, but the whitespace rules have a learning curve. Choose **Nunjucks** if you need jinja2-style inheritance, filters, and macros with **autoescaping on by default**, or if your templates must run in the browser. If you are handling untrusted user input as template source, all three are unsafe — that is the one rule that overrides every other consideration.

## Feature Comparison (live GitHub data, August 2026)

| Feature | EJS | Pug | Nunjucks |
|---|---|---|---|
| GitHub stars | 8,117 | 21,853 | 8,984 |
| Last push | 2026-08-10 | 2026-03-13 | 2026-02-07 |
| License | Apache-2.0 | MIT | BSD-2-Clause |
| Syntax style | HTML + `<% %>` tags | Indentation-based (Haml heritage) | jinja2-style `{{ }}` / `{% %}` |
| Autoescaping by default | No (use `<%= %>` explicitly) | Yes (escapes by default) | Yes (configured on) |
| Template inheritance | Via includes/partials | Yes (extends/block) | Yes (extends/block) |
| Filters / macros | No (plain JS functions) | Mixins | Yes (filters, macros) |
| Async template rendering | Limited | Limited | Yes (async control) |
| Browser support | Yes (client-side) | Yes (compile to JS) | Yes (slim build, ~8 kB) |
| Express view engine | Native (`res.render`) | Native | Via adapter |
| File watching | N/A (dev reload via tools) | N/A | Built-in (needs chokidar) |
| Runtime safety for user templates | **Not sandboxed** | Not sandboxed | **Not sandboxed** |

## Use-Case Decision Matrix

| Use Case | Recommendation | Why |
|---|---|---|
| Express app, fastest possible start | **EJS** | `view engine` works out of the box; templates are HTML with JS tags — zero new syntax |
| Marketing site with heavy custom design | **Pug** | Terse syntax keeps large template files readable; mixins reuse UI blocks |
| Complex page composition (inheritance, filters) | **Nunjucks** | jinja2-style inheritance + macros handle nested layouts better than includes |
| Templates must run in the browser too | **Nunjucks** | Officially supported browser builds, including a slim precompiled-only variant |
| Email templates rendered server-side | **EJS** | Renders to plain HTML strings easily; pair with MJML workflows |
| Team already knows jinja2 (Python) | **Nunjucks** | Nearly identical mental model — see our [jinja2 vs handlebars vs mustache comparison](../2026-06-21-template-engine-libraries-jinja2-handlebars-mustache-tera/) |

## EJS — JavaScript, But Inside Your HTML

EJS ("Embedded JavaScript Templates") is the closest thing to "no framework at all": your template file is HTML, with `<% %>` tags where logic goes. The README's canonical example is exactly two lines of control flow:

```ejs
<% if (user) { %>
  <h2><%= user.name %></h2>
<% } %>
```

The three tag types are the whole syntax model: `<% %>` executes code (control flow), `<%= %>` outputs *escaped* HTML, and `<%- %>` outputs raw HTML. The README also documents the full API surface:

```javascript
const template = ejs.compile(str, options);
template(data);
// => Rendered HTML string

ejs.render(str, data, options);
// => Rendered HTML string

ejs.renderFile(filename, data, options, function(err, str){
    // str => Rendered HTML string
});
```

EJS v6.0 (current) imports cleanly under Rollup, esbuild, Webpack, Vite, Browserify, Bun, and Deno, and supports both CommonJS and ES Modules — a genuine improvement after years of dual-package pain. It is also the only one of the three that is a first-class Express view engine with zero configuration. Features from the README: custom delimiters (e.g. `[? ?]` instead of `<% %>`), includes, newline-slurping `-%>` tags, whitespace-trimming `<%_ _%>`, client-side support, and static template caching.

**The trade-off:** because templates are plain JavaScript, there is no escaping default — you must remember `<%= %>` for anything user-controlled, and any logic you can write, you can also write badly. And EJS is *effectively a JavaScript runtime*: the README's security section is blunt — never give end-users unfettered access to the render method, or you are responsible for the consequences (remote code execution, data exposure).

## Pug — Terse Markup With a Cult Following

Pug (formerly Jade — renamed when "Jade" turned out to be a registered trademark) is a high-performance engine heavily influenced by Haml. Instead of tags, you write indentation, and the README's syntax example shows the whole philosophy in a dozen lines:

```pug
doctype html
html(lang="en")
  head
    title= pageTitle
    script(type='text/javascript').
      if (foo) bar(1 + 5);
  body
    h1 Pug - node template engine
    #container.col
      if youAreUsingPug
        p You are amazing
      else
        p Get on it!
      p.
        Pug is a terse and simple templating language with a
        strong focus on performance and powerful features.
```

No closing tags, no angle brackets — `#container.col` means `<div id="container" class="col">`, `title= pageTitle` means `<title>` with the variable interpolated. Pug compiles to highly optimized JavaScript and escapes output by default, and its mixins let you define reusable UI blocks. It also has a real CLI (`pug --help` after `npm install pug-cli -g`) for one-off rendering and file watching, plus professional support through Tidelift.

**The trade-off:** the syntax is the whole product, and it is unforgiving — an extra space or a wrong indentation level is a parse error, and debugging generated HTML that came from a template you can't "see" in the output is a real skill. Pug's last push was March 2026, and its package is split across many sub-packages (lexer, parser, linker, code-gen), which is great for maintenance but confusing when you start reading its source. If your team includes designers who edit templates directly, be sure they buy into indentation-based markup.

## Nunjucks — jinja2's JavaScript Cousin, by Mozilla

Nunjucks is Mozilla's full-featured engine, heavily inspired by jinja2 (Python). If you know `{{ variable }}` and `{% for %}` you already know 80% of it. The official getting-started shows the two-level API — configure once, then render:

```js
nunjucks.configure({ autoescape: true });
nunjucks.renderString('Hello {{ username }}', { username: 'James' });

// usually you'll render files from a views directory instead:
nunjucks.configure('views', { autoescape: true });
nunjucks.render('index.html', { foo: 'bar' });
```

The docs are explicit that you should prefer `render` over `renderString` so you get template inheritance and includes. Nunjucks's differentiators: **autoescaping is on by default**, filters and macros (jinja2-style), async control flow for loading data during render, and first-class browser support — there is a full build (~20 kB min/gzipped) and a slim build (~8 kB) that only works with precompiled templates, plus grunt/gulp tasks for production precompilation. The built-in file watcher (which requires installing chokidar separately) is a nice development convenience.

**The trade-off:** Nunjucks is the heaviest of the three to integrate with Express (it needs an adapter rather than being a native view engine), and its docs carry the same sandbox warning as EJS — *"nunjucks does not sandbox execution so it is not safe to run user-defined templates"* — with remote code execution and cross-site scripting listed as the consequences. Treat it as a trusted-template engine, not a user-input template engine.

## Common Pitfalls and Migration Gotchas

1. **None of these engines sandbox template execution.** This is the #1 security rule across all three: never render user-supplied template source. EJS and Nunjucks both document remote code execution as the direct consequence; Pug is equally unsafe for untrusted source even though its docs are quieter about it.
2. **Escaping is not free.** EJS defaults to raw HTML (`<%= %>` escapes, but only if you use it); Pug and Nunjucks escape by default. Audit every `render` call site for user-controlled data — a single `res.render('index', req.query)` in EJS (the README literally uses this as the anti-example) is a stored XSS factory.
3. **Pug whitespace errors are cryptic.** `Unexpected token "indent"` usually means a mixed tab/space line or a stray indentation. Configure your editor to show whitespace and standardize on spaces; the parser is deterministic, but your editor should be too.
4. **EJS newline-slurping surprises.** `<% -%>` trims the trailing newline, `<%_ _%>` trims surrounding whitespace. Copy-pasting templates between engines or older tutorials often introduces stray blank lines in rendered output — check the rendered HTML, not just the template.
5. **Nunjucks browser builds need precompilation for production.** The slim build only renders precompiled templates; ship the full build in development, then switch to grunt/gulp-precompiled slim builds for production to keep the payload at ~8 kB.
6. **Migrating between engines means rewriting, not translating.** Pug's mixins and Nunjucks's macros are not compatible; EJS includes are not inheritance. If you move a template suite (e.g. to Nunjucks for inheritance), plan a full layout restructure, not a find-and-replace. For email rendering pipelines, our [MJML and handlebars email template guide](../2026-05-14-self-hosted-email-template-rendering-mjml-server-api-handlebars-guide/) and the [PHP template engines comparison](../2026-08-15-php-template-engines-twig-latte-smarty-blade-comparison/) cover adjacent ecosystems worth comparing before you commit.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Node.js Template Engines in 2026: EJS vs Pug vs Nunjucks — Which One for Server-Side Rendering?",
  "description": "Deep comparison of Node.js template engines: EJS, Pug, and Nunjucks. Live GitHub stats, syntax examples, escaping defaults, security warnings, decision matrix, and migration pitfalls.",
  "datePublished": "2026-08-17",
  "dateModified": "2026-08-17",
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

**What is the easiest Node.js template engine to learn?**
EJS. Templates are regular HTML with `<% %>` JavaScript tags, so there is no new syntax to learn and it works as a native Express view engine with `app.set('view engine', 'ejs')`. Pug requires learning indentation-based markup; Nunjucks requires learning jinja2-style tags.

**Is Pug still maintained in 2026?**
Yes. The last push to the Pug repository was March 2026, and the project has professional support through Tidelift. Its development pace is slower than EJS's, but it is not abandoned.

**Which engine escapes HTML by default?**
Pug and Nunjucks (when `autoescape: true` is configured, which the official docs recommend). EJS does not — you must use the `<%= %>` tag for escaped output and `<%- %>` for raw output.

**Can I use these template engines in the browser?**
EJS supports client-side rendering; Pug compiles templates to JavaScript functions you can ship; Nunjucks has official browser builds including a slim ~8 kB variant for precompiled templates.

**Are any of these engines safe for user-submitted templates?**
No. EJS's README and Nunjucks's docs both explicitly state their engines are not sandboxed and that running user-defined templates can lead to remote code execution or cross-site scripting. Pug is equally unsafe. Always treat template source as trusted code.

**Which engine is best for email templates?**
EJS is a common choice because it renders plain HTML strings with minimal ceremony, and Pug/Nunjucks are also used. For visual, responsive emails you will still want an HTML-inlining pipeline — see our [email template rendering guide](../2026-05-14-self-hosted-email-template-rendering-mjml-server-api-handlebars-guide/) for the MJML-based workflow.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
