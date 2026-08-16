---
title: "TipTap vs Slate vs ProseMirror in 2026: Which Rich Text Editor Framework Should You Use?"
date: "2026-08-16"
tags: ["javascript", "react", "rich-text-editor", "tiptap", "slate", "prosemirror", "frontend"]
draft: false
cover: "/img/screenshots/tiptap-cover.jpg"
---

Every product team eventually hits the same wall: the spec says "add rich text editing," and suddenly you're debugging contenteditable quirks, fighting caret placement, and rebuilding Medium. Rich text editing is one of the hardest UI problems on the web — the DOM wasn't designed for it. TipTap, Slate, and ProseMirror are the three frameworks that dominate the space in 2026, and they represent three completely different philosophies: a batteries-included wrapper, a React-native toolkit, and a modular core library. Picking wrong means rewriting your editor (and your document format) a year from now. Here's the data-backed comparison with real GitHub numbers, honest trade-offs, and the migration traps that nobody puts in the README. It sits naturally next to our [React component libraries comparison](../2026-08-16-shadcn-ui-vs-mantine-vs-chakra-react-component-libraries-comparison/) — the UI kit you pair with your editor matters just as much — and our [drag-and-drop libraries guide](../2026-08-14-react-drag-and-drop-libraries-dnd-kit-react-dnd-sortablejs-guide/) covers the interaction layer you'll likely bolt onto an editor for block-based layouts.

## TL;DR — Quick Verdict

**Choose TipTap if you want an editor working this week** — it wraps ProseMirror with a clean extension API, ships 100+ extensions (mentions, tables, images, code blocks), and integrates with React/Vue/plain JS in minutes. **Choose Slate if you're all-in on React and need a fully custom editing experience** — it gives you complete control but expects you to build features yourself. **Choose ProseMirror directly only if you need a headless, schema-first core** (think Notion-class document models or heavy programmatic document manipulation) and you're willing to write the wiring. For 80% of teams, TipTap is the answer; the other two are power tools for specific jobs.

## Quick Comparison: The 2026 Landscape

| Dimension | TipTap | Slate | ProseMirror |
|---|---|---|---|
| **Philosophy** | Headless, framework-agnostic, extension-based | Pluggable `contenteditable` framework built on React | Modular, schema-first editor core |
| **GitHub stars** | **38,032** | 31,737 | 8,702 |
| **Last push** | 2026-08-15 (very active) | 2026-08-08 (active) | 2026-04-01 (stable, spec repo) |
| **Underlying engine** | Wraps ProseMirror | Own React renderer | Own core + separate view module |
| **Frameworks** | React, Vue, Svelte, plain JS | React only | Framework-agnostic (any view) |
| **Out-of-the-box features** | 100+ official extensions, StarterKit | Core primitives only — you build | Core primitives only — you build |
| **Collaborative editing** | Hocuspocus backend (open source, Yjs-based) | DIY (no official collab layer) | Native collab support in core |
| **Document model** | ProseMirror schema (via PM) | Custom Slate JSON tree | Custom schema with strict validation |
| **Learning curve** | Low | Medium-high | High |
| **License** | MIT (Pro Extensions paid) | MIT | MIT |
| **Backing** | ueberdosis + Linux Foundation health score | Community/contributor-driven | Marijn Haverbeke (independent) |

## Use-Case Decision Matrix

| Use Case | Recommended Tool | Why |
|---|---|---|
| "We need a full editor in a sprint" | TipTap | StarterKit gives you bold/italic/lists/links/headings out of the box; toolbar and UX are yours to style |
| "We're building a docs/wiki/Notion-style app" | TipTap + Hocuspocus | Extension ecosystem + open-source collaboration backend that Just Works |
| "React team, fully custom UX, no time to learn PM internals" | Slate | Everything is React components and plugins; no schema DSL to learn |
| "We manipulate documents programmatically (import/export, transforms)" | ProseMirror | Its transaction/step model is unmatched for programmatic document changes |
| "We need a custom document schema with strict validation" | ProseMirror (or TipTap on top) | Schema is a first-class concept; invalid content can't enter the doc |
| "Plain JS or Vue app, not React" | TipTap | Framework-agnostic by design; Slate is React-only |
| "Long-term, heavily customized editor (like Medium/Dropbox Paper)" | Slate (React) or TipTap (any) | Both are built for this; expect months of feature work either way |

## TipTap — The Batteries-Included Wrapper Everyone Should Start With

TipTap (ueberdosis/tiptap, 38,032 stars, last push 2026-08-15) is a headless, framework-agnostic rich text editor built directly on top of ProseMirror. "Headless" means it ships no UI — you bring your own toolbar, styling, and components, which is exactly why it integrates cleanly with React, Vue, Svelte, or plain JavaScript without fighting a vendor's look-and-feel.

Its superpower is the **extension system**. Instead of learning ProseMirror's node/mark/plugin APIs, you compose an editor from declarative extensions:

```jsx
import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Image from '@tiptap/extension-image'
import Table from '@tiptap/extension-table'

const Editor = () => {
  const editor = useEditor({
    extensions: [
      StarterKit,
      Image.configure({ inline: true }),
      Table.configure({ resizable: true }),
    ],
    content: '<p>Start writing…</p>',
  })

  return <EditorContent editor={editor} />
}
```

Install is two packages — the React bindings and the ProseMirror engine it wraps:

```bash
npm install @tiptap/react @tiptap/pm @tiptap/starter-kit
```

With over 100 official and community extensions — mentions, tables, images, code blocks, placeholders, character count, and more — most teams never write a custom node. When you do need one, the extension API is the same shape as the built-ins, so your custom feature fits right in.

The pragmatic catch: TipTap's advanced features split into open source and paid. The base editor, Hocuspocus collaboration, and core extensions are MIT. "Pro" extensions (advanced collaboration features, commenting, versioning, document conversion) require a subscription. Teams should plan for the open-source path first — it covers the vast majority of use cases.

## Slate — React-Native, Fully Custom, and Honestly Still Hard

Slate (ianstormtaylor/slate, 31,737 stars, last push 2026-08-08) takes the opposite approach: instead of wrapping an existing engine, it's a pluggable implementation of `contenteditable` built directly on React, inspired by Draft.js, ProseMirror, and Quill. Every part of the editing logic is a plugin, so nothing is "in core" and nothing is off-limits.

The model is a plain JSON tree, and the API is deliberately React-shaped:

```jsx
import { createEditor } from 'slate'
import { Slate, Editable, withReact } from 'slate-react'
import { useMemo } from 'react'

const App = () => {
  const editor = useMemo(() => withReact(createEditor()), [])

  return (
    <Slate editor={editor} initialValue={[{ type: 'paragraph', children: [{ text: 'Hello!' }] }]}>
      <Editable />
    </Slate>
  )
}
```

Slate's own README is refreshingly honest: **it is in beta, its APIs are not finalized, and it is contributor-driven** — no company backs it. That's the double-edged sword. On one hand, you get complete control: the document is just data, transforms are plain functions, and everything renders through React. On the other, you are building the editor: mention menus, toolbars, serializers to HTML/Markdown, undo/redo polish — none of it ships. The Slate community has produced solid companion packages (slate-react, slate-history, and serialization helpers), but feature velocity depends on volunteers.

Slate is the right call for React-only teams building a genuinely bespoke editing experience — think collaborative canvases, block-based builders, or editors where the content model is deeply custom. It's the wrong call if you want an editor, not an editor-building project.

## ProseMirror — The Schema-First Core That Powers Everything

ProseMirror (ProseMirror/prosemirror, 8,702 stars, last push 2026-04-01) is the oldest and most academically rigorous of the three — and it's the engine underneath TipTap. Its own description is precise: "a well-behaved rich semantic content editor based on contentEditable, with support for collaborative editing and custom document schemas."

The defining idea is the **schema**. You declare exactly what a document may contain — nodes, marks, attributes, and their nesting rules — and ProseMirror guarantees no invalid content ever enters the document. This is why Notion-class document models and programmatic document manipulation (import/export pipelines, document transforms) belong to ProseMirror: the transaction/step model records every change as a composable, replayable step, which is also what makes collaborative editing a first-class feature rather than an add-on.

A minimal setup wires the core packages together:

```bash
npm install prosemirror-state prosemirror-view prosemirror-model prosemirror-schema-basic
```

```js
import { EditorState } from 'prosemirror-state'
import { EditorView } from 'prosemirror-view'
import { schema } from 'prosemirror-schema-basic'

const state = EditorState.create({ schema })
const view = new EditorView(document.querySelector('#editor'), { state })
```

Note the architecture: ProseMirror is deliberately split into small npm packages (`prosemirror-state`, `prosemirror-view`, `prosemirror-model`, `prosemirror-commands`, `prosemirror-history`, and more), so you import exactly what you need. In 2024 the development repository moved off GitHub to `code.haverbeke.berlin`; the GitHub repo remains the issue tracker, and npm distribution is unchanged.

The cost of all this power is real: the learning curve is the steepest of the three, the docs assume you understand document schemas and transactions, and there's no starter kit — you assemble the pieces. Choose ProseMirror when you need its guarantees; choose TipTap when you'd rather stand on its shoulders.

## Building the Right Editor for Your Team

The three tools are not mutually exclusive — TipTap literally is ProseMirror with ergonomics. The practical decision tree: if your document model is standard rich text (paragraphs, headings, lists, links, images, tables), TipTap's StarterKit plus a handful of extensions covers you in days, and its Hocuspocus backend adds real-time collaboration with Yjs underneath. If your content model is genuinely novel — structured blocks, custom embeds, domain-specific nodes with validation rules — you'll end up writing custom nodes either way, and ProseMirror's schema-first discipline keeps that from becoming a swamp; you can still start from TipTap and drop to the PM API for the custom parts. If your team is React-only and allergic to learning a document schema, Slate's plain-JSON model and component-based rendering will feel most natural — budget for building your own feature set.

Whichever you choose, isolate it: expose a thin `save()` / `load()` interface to the rest of your app, store documents in a versioned format (JSON or HTML with a schema version field), and treat the editor as a replaceable component. Teams that couple business logic to editor internals are the ones that get stuck — the same lesson that applies to [JavaScript state management libraries](../2026-07-05-javascript-state-management-redux-zustand-jotai-mobx-pinia/), where decoupling the store from the UI is what keeps migrations cheap.

## Common Pitfalls (and How to Avoid Them)

1. **Storing HTML and calling it a day.** Browsers normalize HTML differently; a document that round-trips today may not survive a future editor change. Store a structured format (TipTap/ProseMirror JSON) and serialize to HTML only for rendering.
2. **Ignoring the schema when you pick TipTap.** TipTap's defaults are great until you need a custom node — then you're learning ProseMirror schema concepts anyway. Budget for it instead of hacking around it.
3. **Treating Slate like a finished product.** The README says beta, APIs change, and you build the features. Teams that expect `npm install slate` to deliver Medium get burned; schedule feature-building time explicitly.
4. **Reinventing collaboration.** Real-time editing needs CRDT or OT — don't hand-roll it. Use TipTap + Hocuspocus (Yjs-based, open source) or ProseMirror's native collab; Slate has no official path, so factor that in before choosing it for a multi-user app.
5. **Leaking `contenteditable` into your design system.** Editor-internal styles (focus outlines, selection colors, placeholder) must be scoped, or they'll break the rest of your UI. Headless editors help here — you own the markup.
6. **Copy-pasting editor code into Next.js SSR without care.** Editors touch the DOM at mount; render them client-side or use dynamic imports, or you'll get hydration mismatches.
7. **Forgetting mobile.** Desktop-drag selection, hover menus, and keyboard shortcuts don't exist on touch. TipTap's `StarterKit` behavior differs on mobile; test editing on a phone before launch, not after.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "TipTap vs Slate vs ProseMirror in 2026: Which Rich Text Editor Framework Should You Use?",
  "description": "In-depth 2026 comparison of TipTap, Slate, and ProseMirror: headless vs React-native vs schema-first architectures, real GitHub data, extension ecosystems, collaborative editing options, and migration pitfalls.",
  "datePublished": "2026-08-16",
  "dateModified": "2026-08-16",
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

**Is TipTap really built on ProseMirror?**
Yes. TipTap's core is a thin, ergonomic layer over ProseMirror — you get the schema/transaction engine underneath with a much friendlier extension API on top. That's why TipTap documents can be manipulated with ProseMirror libraries when you need the low-level power.

**Is Slate production-ready in 2026?**
It's widely used in production, but its own README still labels it beta with unfinalized APIs and no 1.0 schedule. Companies like Canner and various SaaS apps use it in production successfully — but you must own the feature-building and expect occasional breaking changes between versions.

**Which editor is best for Next.js / React apps?**
For most React apps, TipTap — its `@tiptap/react` bindings work with React Server Components patterns when the editor is mounted client-side, and the extension ecosystem covers common features immediately. Choose Slate only if you need its fully custom, component-driven model and accept building more yourself.

**Can I migrate from Slate to TipTap (or vice versa)?**
The document formats are incompatible, so migration is a conversion job: write an exporter from your current tool's JSON/HTML into the target's schema, test round-trips on a corpus of real documents, and version your stored format. This is exactly why the advice above — isolate the editor behind a save/load interface — pays off.

**Does TipTap's open-source version support collaborative editing?**
Yes. Hocuspocus, the open-source collaboration backend built around Yjs, works with the free TipTap editor. The paid Pro Extensions add advanced collaboration features like comments, versioning, and refined presence on top — but basic real-time multi-user editing is open source.

**What's the bundle-size difference?**
ProseMirror core is the smallest building block; TipTap adds the extension layer on top; Slate ships React bindings in core. Exact numbers depend on tree-shaking, but plan for roughly 40-80 kB gzipped for a functional editor from any of the three — negligible for most apps, meaningful for landing pages.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
