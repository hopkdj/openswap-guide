---
title: "Icon Libraries in 2026: Lucide vs react-icons vs Heroicons — Which One Should You Actually Use?"
date: "2026-08-22"
tags: ["icons", "javascript", "react", "frontend", "lucide", "heroicons", "react-icons"]
draft: false
cover: "/img/screenshots/lucide-icons-cover.jpg"
---

Your app's icons are a 100-KB decision hiding in a 10-second decision. Import the wrong icon library and you either ship 30,000 unused SVGs in your bundle (yes, that happens), or you hand-copy SVG paths into your components and pray the design system survives a rebrand. The three libraries that dominate 2026 — **Lucide** (24,080 stars), **react-icons** (12,620 stars), and **Heroicons** (23,753 stars) — answer the same question differently: Lucide gives you one consistent hand-drawn set, react-icons gives you *every* set behind one API, and Heroicons gives you Tailwind-native pairs designed for product UI.

## TL;DR — Quick Verdict

Want a **single, consistent, actively-maintained icon set** with first-class React/Vue/Svelte/Solid packages → **Lucide**. Need to pull icons from **many different brands and sets** (Font Awesome, Material, Bootstrap, and fifty more) without juggling packages → **react-icons** — but verify your bundler tree-shakes, or you pay for all of them. Building a **Tailwind CSS app** and want icons that look designed-for-your-stack → **Heroicons**, with the caveat that its release cadence has slowed (last push May 2026). For most product teams in 2026, the default answer is **Lucide + a brand-pack fallback via react-icons when you need a logo**.

## Feature Comparison: Lucide vs react-icons vs Heroicons (2026)

| Criterion | Lucide | react-icons | Heroicons |
|---|---|---|---|
| GitHub stars | 24,080 | 12,620 | 23,753 |
| Last push | 2026-08-20 | 2026-08-12 | 2026-05-12 |
| License | ISC | MIT | MIT |
| Icon sets included | 1 (own set, ~1,500 icons) | 20+ sets (~30,000 icons) | 2 (solid + outline) |
| Icon style | Consistent stroke-based, 24px grid | Mixed — whatever each source set ships | Dual solid/outline, 24px grid |
| React package | `lucide-react` | `react-icons` (all sets) | `@heroicons/react` |
| Other framework bindings | React, Vue, Svelte, Solid, Angular, Preact, vanilla | React only (web) | React, Vue |
| Tree-shaking | ✅ ESM, per-icon exports | ✅ Per-icon subpaths, but bundler-sensitive | ✅ Per-icon imports |
| Brand logos (GitHub, Slack, X) | ❌ Deliberately excluded | ✅ Included in Font Awesome / Simple Icons packs | ❌ Excluded |
| Release cadence | Weekly (very active) | Active (monthly) | Slowed (quarterly-ish) |

## Use-Case Decision Matrix

| Use Case | Recommended Library | Why |
|---|---|---|
| SaaS product UI with a cohesive design system | **Lucide** | One hand-drawn set, consistent stroke width, no mixing styles |
| Need GitHub/Slack/Stripe brand logos in docs or marketing | **react-icons** | The `si` (Simple Icons) and `fa` packs include brand marks |
| Tailwind CSS project (shadcn/ui, headless stacks) | **Heroicons** | Designed for the Tailwind aesthetic; `shadcn/ui` ships them by default |
| Design-system component library (multi-package monorepo) | **Lucide** | Per-icon imports + framework bindings for React/Vue/Svelte/Solid |
| Legacy app migrating from Font Awesome | **react-icons** | `react-icons/fa` mirrors the Font Awesome icon names you already use |
| Ultra-strict bundle budget (< 3 KB of icons) | **Heroicons or Lucide** | Import one icon = one icon; no aggregator overhead |

## Lucide — The Consistent, Community-Driven Set

Lucide began as a fork of Feather Icons and grew into the most actively maintained icon set in the ecosystem: a **single, stroke-based family on a 24px grid** with a uniform 2px stroke width, so every icon looks like it belongs to the same designer. It ships first-party bindings for React, Vue, Svelte, Solid, Angular, and Preact, and its weekly release cadence means new icons land fast — it passed 1,500 icons years ago and keeps growing.

```jsx
import { Camera } from 'lucide-react';

export function PhotoButton() {
  return <button aria-label="Take a photo"><Camera /></button>;
}
```

Because every icon is a separate ESM export, bundlers tree-shake aggressively — `Camera` costs you exactly one icon, no matter how many of the 1,500+ you *could* import. The trade-off: Lucide is a single stylistic point of view. **It deliberately excludes brand logos** (GitHub, Slack, X, brand marks) to keep the set consistent, so your logo needs come from elsewhere.

![Lucide icon showcase](/img/screenshots/lucide-showcase.jpg "Lucide icon set showcase with the interactive style customizer")

**Watch out for:** if your product mixes icon *styles* (solid app icons next to Lucide's strokes), the inconsistency reads immediately. Lucide also releases so often that you should pin minor versions in lockfiles — icon path changes between weekly releases have broken visual snapshots more than once.

## react-icons — Every Icon Set, One Import

react-icons is not an icon set; it is an **aggregator** — one package that re-exports icons from Font Awesome, Material Design, Bootstrap, Tabler, Simple Icons (brand logos), and roughly fifteen other sets, all under a single naming convention. The canonical example from its README:

```jsx
import { FaBeer } from "react-icons/fa";
// or Material Design icons
import { ICON_NAME } from 'react-icons/md';
```

Each set lives in its own subpath — `react-icons/fa`, `react-icons/md`, `react-icons/si` (Simple Icons, the brand-logos pack) — and each icon is exported as an individual React component, so tree-shaking *can* keep your bundle lean. The strength is breadth: you can grab a Font Awesome icon for one screen and a Material icon for another without adding a second dependency.

**Watch out for:** tree-shaking here is bundler-configuration-sensitive. If your toolchain resolves the barrel `react-icons` index instead of the subpath, you can end up with tens of thousands of icons in the dependency graph — the classic "my bundle grew 800 KB overnight" bug. Also, mixing sets means mixing visual languages: a Font Awesome solid icon next to a Material rounded icon next to a Simple Icons logo is a design smell. For brand marks, the Simple Icons pack is superb; for a cohesive UI, react-icons is a toolbox, not a design system.

## Heroicons — Tailwind's Native Icons

Heroicons is the icon set from the **Tailwind Labs** team, hand-crafted on the same 24px grid philosophy as Tailwind itself. Its defining feature is the **solid/outline pairing**: every icon ships in both styles (`@heroicons/react/24/solid` and `@heroicons/react/24/outline`), and because they're designed by the Tailwind team, they sit perfectly inside Tailwind's default color/size utilities. This is why shadcn/ui and most headless-component templates default to Heroicons.

```jsx
import { BeakerIcon } from '@heroicons/react/24/solid';

export function LabBadge() {
  return <BeakerIcon className="h-6 w-6 text-gray-500" />;
}
```

The raw SVG is equally clean for non-React use — Heroicons publishes standalone SVGs you can drop into any stack, with `stroke="currentColor"` so CSS `color` controls the tint.

**Watch out for:** Heroicons is **not** an actively churning set. The last push was May 2026, and new-icon requests move slowly by design — the set is curated, not crowdsourced. If you need a very specific icon (a niche data format, an obscure device), Lucide is likelier to already have it or add it fast. Also remember Heroicons excludes brand logos, like Lucide.

## Pitfalls and Migration Gotchas

- **The 30,000-icon bundle bug.** With react-icons, an un-treeshaken barrel import pulls *every* set into the graph. Audit with a bundle analyzer after wiring it up; if you see hundreds of KB of icon paths, switch to deep imports (`react-icons/fa` subpaths) or migrate to Lucide's per-icon packages.
- **Dynamic icon components kill tree-shaking.** `<Icon name={dynamicName} />` lookups defeat static analysis in every library. If you need runtime icon names, build an explicit lookup map (`{ 'camera': Camera }`) — the bundler keeps only what you reference.
- **Mixing styles across sets is a design regression.** Decide one visual language (stroke vs solid vs filled) before you start, and enforce it in review. The moment two sets appear in one screen, your UI looks unowned.
- **SVG vs icon fonts.** All three libraries are SVG-based — keep it that way. Font-based icons (Font Awesome's font mode, iconify fonts) suffer FOUC, blurry rendering on non-integer scales, and inaccessible pseudo-element content. If you're migrating *from* a font, switch to SVG and delete the font file — it's the single biggest a11y win in icon work.
- **Accessibility defaults.** Most icon components render `<svg aria-hidden="true">` by default. For *decorative* icons that's correct; for *meaningful* icons (a cart button with no visible label) you must add `aria-label` or a visually-hidden text label, as in the Lucide example above. Screen readers announcing "svg" instead of "shopping cart" is a common audit finding.
- **Stroke width consistency.** Lucide's uniform 2px stroke looks wrong next to a 1.5px custom icon. If you extend any set with custom SVGs, match the source grid (24×24) and stroke, or the difference is visible at 16px.
- **Version pinning.** Active sets (Lucide) ship weekly. Pin exact versions in lockfiles and review icon *changes* in release notes before upgrading — icons sometimes get redrawn, and redraws change pixel geometry in your snapshots.

For related ecosystem guides, see our [font icon libraries comparison](../2026-06-08-self-hosted-font-icon-libraries-fontsource-iconify-material-design/), the [headless component libraries showdown](../2026-08-21-radix-primitives-vs-headlessui-vs-ark-ui-headless-component-comparison/), and our [CSS-in-JS library deep dive](../2026-08-15-css-in-js-styled-components-emotion-linaria-comparison/).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Icon Libraries in 2026: Lucide vs react-icons vs Heroicons",
  "description": "Compare Lucide, react-icons, and Heroicons for React and frontend apps in 2026 — tree-shaking, bundle size, icon sets, brand logos, Tailwind integration, and migration pitfalls.",
  "datePublished": "2026-08-22",
  "dateModified": "2026-08-22",
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

### What is the difference between Lucide, react-icons, and Heroicons?

Lucide is a single consistent stroke-based icon set with official bindings for React, Vue, Svelte, Solid, and more. react-icons is an aggregator package that re-exports icons from 20+ sets (Font Awesome, Material, Simple Icons, and others) behind one API. Heroicons is Tailwind Labs' dual solid/outline set designed for Tailwind CSS apps.

### Can I use brand logos like GitHub or Slack with these libraries?

Lucide and Heroicons deliberately exclude brand logos. react-icons includes them via the Simple Icons pack (`react-icons/si`) and Font Awesome pack (`react-icons/fa`). If your docs or marketing pages need official brand marks, react-icons is the practical choice.

### Does react-icons bloat my bundle?

Only if tree-shaking fails. Importing from the deep subpaths (`import { FaBeer } from 'react-icons/fa'`) lets bundlers drop unused icons. Importing from the package root or resolving the barrel index can pull in thousands of icons — always verify with a bundle analyzer after setup.

### Which icon library does shadcn/ui use?

shadcn/ui ships with Heroicons by default, since both come from the Tailwind ecosystem and share the same visual language. Many shadcn projects switch to Lucide for a lighter stroke style or a larger icon catalog.

### Are these libraries free for commercial use?

Yes. Lucide is ISC-licensed, react-icons is MIT, and Heroicons is MIT — all permissive licenses that allow commercial use, modification, and redistribution with attribution. None require payment or a license key.

### Can I use Lucide with Vue or Svelte?

Yes. Lucide maintains first-party packages for React (`lucide-react`), Vue (`lucide-vue-next`), Svelte (`lucide-svelte`), Solid (`lucide-solid`), Angular, and Preact. Heroicons also has Vue bindings. react-icons is React-only.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
