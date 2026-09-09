---
title: "Markdown Editor Components in 2026: Milkdown vs Vditor vs ByteMD"
date: "2026-09-10"
tags: ["markdown", "javascript", "frontend", "editor"]
draft: false
cover: "/img/screenshots/vditor-editor.jpg"
---

Every developer-facing product ends up needing Markdown input at some point — and that is exactly when the wheel gets reinvented for the thousandth time. Pasting a `<textarea>` with a "preview" button next to it stops being acceptable the day your users start pasting tables, dragging in images, and complaining that the syntax highlighting is ugly. The three open-source editor components below — **Milkdown (11,900+ stars), Vditor (11,300+ stars), and ByteMD (1,400+ stars, with its v2 successor HashMD at 4,300+)** — are the most battle-tested ways to embed a real Markdown editing experience without building one from scratch. This comparison covers what each one actually feels like to integrate, where their licenses and maintenance situations genuinely differ in 2026, and which one you should ship.

**Quick verdict:** if you want a Typora-style live rendering editor with the biggest feature surface out of the box, pick **Vditor** — it is a single-file drop-in with zero build-step opinion. If you are building a React or Vue application and want an editor that behaves like a framework (plugins, themes, controlled state), pick **Milkdown**, especially via its all-in-one Crepe preset. If your priority is a tiny, secure, SSR-friendly editor that renders on both server and client, **ByteMD** is the lean choice — but budget for its v2 migration to HashMD, since the v1 repository is frozen.

## Markdown Editor Components at a Glance

| Feature | Milkdown | Vditor | ByteMD (v1) |
| --- | --- | --- | --- |
| GitHub stars | 11,903 | 11,310 | 1,366 (v1, frozen) |
| Latest push | 2026-09-09 | 2026-08-30 | 2025-02 (successor: HashMD, 4,348 stars) |
| License | MIT | MIT | MIT |
| Core architecture | Plugin-driven framework on ProseMirror + remark | Standalone editor with bundled Lute parser | Svelte-built, framework-agnostic component |
| Editing modes | WYSIWYG (Typora-like) via Crepe | WYSIWYG, Instant Rendering, Split View | WYSIWYG + preview |
| Framework bindings | Official React/Vue/Svelte/Solid/Nuxt packages | Any framework via vanilla JS API | Official Svelte/React/Vue 2/Vue 3 packages |
| XSS handling | Via ProseMirror schema + plugins | Built-in sanitization | Sanitized by default, no extra DOM purify step |
| SSR compatible | Yes (with care) | Yes (render mode) | Yes, explicitly |
| Bundle personality | Modular — pay for what you use | One UMD/ESM file, CSS included | Tiny core (~30 kB gzipped family) |
| Extras | Slash menu, tooltip, code block components | Mermaid, ECharts, math, mind map, speech, outline | Plugins: GFM, math, mermaid, highlight |
| Active development | Very active (weekly releases) | Active (monthly) | v1 frozen; v2 = HashMD |

## Which Editor Should You Pick? (Decision Matrix)

| Use Case | Recommended Tool | Reason |
| --- | --- | --- |
| Typora-like instant rendering in a plain website or docs page | **Vditor** | Three editing modes behind one `new Vditor()` call, no framework required |
| React/Vue app where the editor must react to app state | **Milkdown** | `@milkdown/react` / `@milkdown/vue` bindings with a real plugin ecosystem |
| Server-side rendered blog or docs site | **ByteMD** | Explicit SSR compatibility and an `Editor` + `Viewer` split |
| Long-term project needing active maintenance | **Milkdown or Vditor** | Both pushed within the last month; ByteMD v1 is archived in all but name |
| Markdown *viewing* (rendering untrusted content) | **ByteMD Viewer** | Sanitized by default — no extra DOMPurify wiring |
| Deep customization: custom blocks, commands, UI | **Milkdown** | The entire editor is composed of plugins you can replace |

## Milkdown — The Plugin-Driven Framework

Milkdown describes itself as "plugin driven WYSIWYG markdown editor," and that is not marketing fluff: it is built on **ProseMirror** for the document model and **remark** for Markdown parsing, which means you get a real schema, transactions, and undo history under the hood instead of a contenteditable hack. The trade-off is that bare Milkdown is a framework — you wire up a theme and presets. The project solved this with **Crepe**, an all-in-one editor preset that gives the Typora-like experience without assembling a dozen plugins yourself. As of September 2026 the repository has 11,903 stars, an MIT license, and commits landing daily; the maintainers also run an active Discord and a public roadmap project.

A minimal Crepe editor, taken from the official `Milkdown/examples` repository, is remarkably small:

```ts
import { Crepe } from '@milkdown/crepe';

import '@milkdown/crepe/theme/common/style.css';
import '@milkdown/crepe/theme/frame.css';

const markdown = `# Hello Milkdown

> This is a demo for using Milkdown Crepe.`;

await new Crepe({
  root: '#app',
  defaultValue: markdown,
}).create();
```

![Milkdown editor social preview](/img/screenshots/milkdown-social.jpg "Milkdown editor project preview")

In a React application you go through `@milkdown/react`, where the editor lifecycle is owned by the `useEditor` hook and rendering happens through a `<Milkdown />` component — this is the pattern from the official `react-crepe` example:

```tsx
import { Crepe } from "@milkdown/crepe";
import { Milkdown, useEditor } from "@milkdown/react";

const Editor: FC = () => {
  useEditor((root) => {
    return new Crepe({ root, defaultValue: markdown });
  }, []);
  return <Milkdown />;
};
```

Milkdown's power is also its cost: the framework is modular, so you pick presets (`commonmark`), themes (`@milkdown/theme-nord`, `theme-frame`), and feature plugins (slash menu, tooltip, code blocks, image blocks). The learning curve is real — the docs assume you understand ProseMirror concepts like schema and node views. Teams that want a component, not a framework, should look at the other two options.

## Vditor — The Three-Mode Workhorse

Vditor comes from the B3log open-source community (the same group behind the SiYuan note-taking app) and answers a different question: "what if one editor handled every Markdown user archetype?" It ships **three editing modes**: WYSIWYG for people who never want to see syntax, **Instant Rendering** (the Typora-style mode where syntax is visible while typing and renders on blur), and classic Split View. It is written in TypeScript, implements CommonMark and GFM through its own Lute parser, and drops into any page with two tags and one constructor call. Its 11,310 stars come with MIT licensing and an active maintenance cadence — the last push was August 30, 2026.

Installation is deliberately old-school, which makes it the fastest option for server-rendered templates:

```html
<!-- pin a version in production, e.g. https://unpkg.com/vditor@3.x/dist/... -->
<link rel="stylesheet" href="https://unpkg.com/vditor/dist/index.css" />
<script src="https://unpkg.com/vditor/dist/index.min.js"></script>
```

The constructor options below are a condensed version of the official `demo/index.js` — note the mode switch, the toolbar as a plain array of string names, the KaTeX math engine, and the outline panel:

```js
const vditor = new Vditor('vditor', {
  toolbar: [
    'emoji', 'headings', 'bold', 'italic', 'strike', 'link', '|',
    'list', 'ordered-list', 'check', 'quote', 'line', 'code', 'inline-code', '|',
    'upload', 'record', 'table', '|', 'undo', 'redo', '|',
    'edit-mode', 'content-theme', 'code-theme', 'export',
    { name: 'more', toolbar: ['fullscreen', 'both', 'preview', 'info', 'help'] },
  ],
  mode: 'wysiwyg',          // or 'ir' (instant rendering) or 'sv' (split view)
  height: 480,
  placeholder: 'Start writing...',
  typewriterMode: true,
  outline: { enable: true, position: 'right' },
  preview: {
    markdown: { toc: true, mark: true, footnotes: true, autoSpace: true },
    math: { engine: 'KaTeX', inlineDigit: true },
  },
  toolbarConfig: { pin: true },
  counter: { enable: true, type: 'text' },
});
```

Vditor's feature list is almost absurd: Mermaid and Graphviz diagrams, ECharts, WaveDrom, abc.js sheet music, mind maps, speech input, clipboard image upload with progress, "copy to WeChat public account" formatting, and multi-theme support. The Chinese-ecosystem heritage means the default documentation is largely in Chinese, though an English README exists and the API itself is well named. For teams shipping a docs site, a CMS editor, or a forum composer with minimal integration effort, Vditor remains the fastest path to a professional result.

## ByteMD — The Lightweight Succession Story

ByteMD, created by ByteDance, took the opposite design bet: build the editor in **Svelte**, compile to framework-agnostic DOM manipulation, and keep the core tiny. It is built around an `Editor`/`Viewer` split and a small plugin system (GFM, math, Mermaid, syntax highlight). Its four headline properties are lightweight, extensible, **secure by default** (XSS handling is built in — no separate sanitization step), and **SSR compatible**. The React usage from the official README is short enough to quote in full:

```jsx
import gfm from '@bytemd/plugin-gfm';
import { Editor, Viewer } from '@bytemd/react';

const plugins = [gfm()];

const App = () => {
  const [value, setValue] = useState('');
  return (
    <Editor
      value={value}
      plugins={plugins}
      onChange={(v) => { setValue(v); }}
    />
  );
};
```

The honest caveat for 2026: **ByteMD v1 is frozen.** The repository's own README states that v2 is under active development as **HashMD** (`pd4d10/hashmd`, 4,348 stars), and the last v1 push was February 2025. ByteMD also dropped the legacy ES5 bundle after version 1.11.0, so IE-era support now means pinning an old release or compiling the ESNext entry yourself. If you adopt ByteMD today, plan the v1 → HashMD migration path from day one. Its security posture (sanitized by default) and SSR story still make it an excellent *Viewer* for rendering untrusted Markdown on the server — that component is worth adopting even while the editor itself transitions.

## Migration Traps and Integration Pitfalls

These three editors look interchangeable from a screenshot and are absolutely not interchangeable in a codebase. The traps we see teams hit most often:

1. **Controlled-value mismatches.** Milkdown and ByteMD are happy as controlled components (value in, change events out); Vditor is imperative — you call `vditor.setValue()` and read `vditor.getValue()`, and it manages its own undo history. Mixing an imperative editor with a reactive state store requires discipline, or you get cursor jumps and lost undo stacks.
2. **The `new Vditor()` timing trap.** Vditor must be constructed after the target `div` exists in the DOM. In single-page apps that means calling it in `onMounted`/`useEffect`, not during render — and destroying it (`vditor.destroy()`) on unmount or you leak timers and the cached content backup.
3. **Sanitization is not optional.** All three handle common XSS vectors, but if you render user-submitted Markdown anywhere (comments, shared notes), prefer the Viewer/render paths and keep your own output encoding for raw HTML. ByteMD's default sanitization is the most explicit; Milkdown relies on its schema and plugins — do not strip the schema plugins "to save bytes."
4. **Math and diagram engines pull in real weight.** Vditor's KaTeX/Mermaid/ECharts support and Milkdown's math plugins add hundreds of kilobytes. Lazy-load them only where the editor actually mounts; otherwise your marketing page pays the editor's tax.
5. **Bundle budget discipline.** ByteMD's Svelte core is the lightest of the three; Milkdown + ProseMirror + Crepe is the heaviest but buys the plugin architecture; Vditor sits in between with a single-file build that is trivial to cache.
6. **Chinese-ecosystem integrations.** Vditor's paste-from-WeChat and its default CDN references assume access to Chinese infrastructure; self-host the dist files if your audience is outside that region.

For teams weighing an editor component against a full rich-text engine, note the architectural difference: engines like TipTap or Slate give you block-level control at the cost of building Markdown semantics yourself, while these three components treat Markdown as the source of truth — see our [rich-text editor engines comparison](../2026-08-16-rich-text-editors-tiptap-slate-prosemirror-comparison/) for when to go that route instead. If your real problem is parsing or transforming Markdown rather than editing it, we have covered that ground too in the [parser library comparison](../2026-06-20-markdown-parser-libraries-pulldown-cmark-goldmark-comrak-commonmarkjs/) and the [marked vs markdown-it vs remark deep dive](../2026-08-18-marked-vs-markdown-it-vs-remark-markdown-parser-comparison/).

## Framework Bindings and Ecosystem Depth

Integration quality is where these projects diverge most in practice. **Milkdown** ships first-class packages for React, Vue, Svelte, Solid, and even Nuxt, plus a VSCode extension — it treats "works inside your framework" as a core feature. **Vditor** is framework-agnostic by construction: the official demos show CommonJS and plain HTML usage, and the community maintains Vue/Svelte wrappers, but there is no canonical React component — you write a thin wrapper around the constructor yourself. **ByteMD** ships `@bytemd/react`, `@bytemd/vue` (Vue 2), `@bytemd/vue-next` (Vue 3), and the Svelte core, which covers the mainstream; its plugin API is the simplest of the three, which is a feature when you only need GFM plus highlighting.

A practical evaluation sequence for your own project: prototype the exact feature set you need (tables, math, image upload, custom toolbar button) in all three in a single afternoon; measure the bundle with the editor lazy-loaded; then grep the issue trackers for your framework version before committing. Maintenance velocity is the least visible and most decisive differentiator — in 2026 that favors Milkdown and Vditor, with ByteMD's future living in HashMD.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Markdown Editor Components in 2026: Milkdown vs Vditor vs ByteMD",
  "description": "Deep comparison of the three leading open-source Markdown editor components in 2026: Milkdown, Vditor and ByteMD. Real code samples, integration pitfalls, decision matrix and FAQ.",
  "datePublished": "2026-09-10",
  "dateModified": "2026-09-10",
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

**Is Milkdown free for commercial use?**
Yes — Milkdown is MIT licensed, including the Crepe preset and all official packages. There is no paid tier or revenue threshold, unlike some commercial editor vendors. The project is funded through GitHub sponsors and JetBrains/Vercel open-source support programs.

**Can Vditor be used in React or Vue applications?**
Yes, because it is framework-agnostic. You create the editor imperatively inside a component lifecycle hook (for example `onMounted` in Vue or `useEffect` in React) targeting a container element, and destroy it on unmount. Community wrappers exist for Vue and Svelte, though none are officially maintained by the Vditor team.

**What is the difference between ByteMD and HashMD?**
ByteMD v1 (the `bytedance/bytemd` repository) is frozen; its successor HashMD is the actively developed v2, MIT-licensed and currently at over 4,300 stars. If you are starting a new project in 2026, evaluate HashMD directly rather than building on the v1 codebase, and check the migration notes for plugin compatibility if you are upgrading.

**Which editor is best for a server-side rendered blog platform?**
ByteMD is the most explicit about SSR support, and its `Viewer` component is ideal for rendering stored Markdown safely on the server. Vditor also offers a render mode that works without a browser editing context. Milkdown's ProseMirror core is document-model driven, which is more natural for interactive clients than for pure server rendering.

**Do these editors support math formulas and diagrams?**
All three support math (KaTeX/MathJax) and Mermaid diagrams through plugins or built-ins, but the depth differs: Vditor bundles the widest range natively (Mermaid, Graphviz, ECharts, WaveDrom, even abc.js sheet music), while Milkdown and ByteMD add them via optional plugins to keep the core small.

**How much do these editors weigh in the browser?**
ByteMD is the lightest of the three thanks to its Svelte core. Vditor ships as a single CSS + JS pair that is easy to cache. Milkdown plus ProseMirror plus Crepe is the heaviest starting point, though its modularity means you can omit unused plugins and presets.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
