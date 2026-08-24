---
title: "JavaScript Gesture Libraries in 2026: hammer.js vs @use-gesture vs interact.js"
date: "2026-08-24"
tags: ["javascript", "react", "frontend", "touch"]
draft: false
cover: "/img/screenshots/hammer-cover.png"
---

Mobile traffic is no longer the future of the web — it is the majority, and gesture support is the difference between an app that feels native and one that feels like a website. But "gestures" is a trap of a category: swipe-to-delete on a task list, drag-to-reorder in a kanban board, pinch-to-zoom on an image, and resize-handle interactions on a canvas are all gestures, and they are all different problems. The three libraries that own this space — **hammer.js**, **@use-gesture**, and **interact.js** — are so often compared as if they were interchangeable that teams routinely pick the wrong one and rebuild it from scratch two sprints later.

The reality is that they are not competitors in the way most library trios are. hammer.js is a gesture *recognizer* (tap, swipe, pinch). @use-gesture is a hooks layer that turns mouse and touch input into animated state for React (and vanilla JS). interact.js is an interaction *engine* for drag, drop, and resize with inertia and snapping. Understanding which job each tool actually does is the entire decision — and this guide gives you the role-first breakdown plus the honest maintenance picture as of August 2026, because two of the three have gone quiet.

## TL;DR: Which JavaScript Gesture Library Should You Use?

If you need **simple recognition — tap, double-tap, swipe, press — on any element**, use **hammer.js** (24,344 stars): it is the classic, stable, dependency-free recognizer that still ships in countless production apps. If you are **building animated React interactions** (draggable cards, pinch-zoom, pull-to-refresh) and want declarative hooks, use **@use-gesture** — but know it has not been updated since July 2024, so evaluate it as stable-maintenance, not actively-developed. If you need **full interaction machinery — drag, drop, resize, multi-touch with inertia, snapping, and SVG support**, use **interact.js** (12,925 stars, actively pushed in August 2026). And if you only need one drag-and-drop interaction, skip all three and check our dedicated [drag-and-drop library guide](../2026-08-14-react-drag-and-drop-libraries-dnd-kit-react-dnd-sortablejs-guide/) first.

## Feature Comparison Table

Data fetched from GitHub on 2026-08-24. All three are MIT-licensed.

| Feature | hammer.js | @use-gesture | interact.js |
|---|---|---|---|
| GitHub stars | 24,344 | 9,622 | 12,925 |
| Last push | 2026-01 | 2024-07 | 2026-08 |
| License | MIT | MIT | MIT |
| Core job | Gesture recognition | Hooks + gesture state | Drag/drop/resize engine |
| Tap / double-tap / press | ✅ Built-in | ⚠️ Partial (via drag/click) | ✅ |
| Swipe detection | ✅ | ❌ (no swipe recognizer) | ✅ |
| Drag with animation | ❌ | ✅ (pairs with react-spring) | ✅ |
| Resize handles | ❌ | ❌ | ✅ |
| Inertia / momentum | ❌ | ✅ (via spring) | ✅ Built-in |
| Snapping / modifiers | ❌ | ❌ | ✅ Grid + custom targets |
| Pinch / multi-touch | ✅ Recognize | ✅ `usePinch` | ✅ |
| React hooks | ❌ | ✅ `useDrag`/`usePinch`/`useWheel`/`useMove` | ❌ (imperative API) |
| Vanilla JS | ✅ | ✅ `@use-gesture/vanilla` | ✅ |
| SVG interaction | ⚠️ | ⚠️ | ✅ Explicit support |
| TypeScript types | ⚠️ Community | ✅ | ✅ Built-in |
| Custom recognizers | ✅ `Hammer.Manager` | ⚠️ Limited | ✅ Actions/modifiers |
| Bundle (gzipped) | ~7 KB | ~9 KB (React) | ~25 KB |

## Use-Case Decision Matrix

| Use case | Recommendation | Why |
|---|---|---|
| Swipe-to-delete / tap detection on list items | **hammer.js** | Recognition-only; zero integration cost; battle-tested |
| React draggable cards, pinch-zoom gallery | **@use-gesture** + react-spring | Declarative hooks, gesture state directly into animation |
| Drag between zones with drop targets | **interact.js** (or dnd-kit) | Drop zones + snapping built in; dnd-kit if React-only |
| Canvas/whiteboard drag, resize, rotate | **interact.js** | Resize handles and multi-action support |
| Legacy app, IE9-era browser support | **interact.js** | Documents IE9+ support; hammer.js works but is older |
| Animation-heavy gesture UI (viewpager, action sheet) | **@use-gesture** | The demos in its README are exactly these patterns |
| Long-term project, needs active maintenance | **interact.js** | Only one of the three with 2026 commit activity |
| A11y-critical public app | **None of these alone** | Every gesture needs keyboard/mouse fallback (see pitfalls) |

## hammer.js: The Classic Gesture Recognizer

hammer.js (hammerjs/hammer.js, **24,344 stars**, MIT, last push January 2026) is the oldest and most widely deployed of the three — it has been the default answer to "detect touch gestures" since 2014. Its scope is deliberately narrow: it *recognizes* gestures and tells you when they happen; it does not animate, snap, or manage drop targets. If your need is "swipe left deletes this row", that narrowness is a feature.

```bash
npm install --save hammerjs
```

```js
// Quick-start: gestures hammer already recognizes
var square = document.querySelector('.square');
var hammer = new Hammer(square);

hammer.on('press', function(e) {
  e.target.classList.toggle('expand');
  console.log("You're pressing me!", e);
});
```

Custom gestures are supported through the recognizer manager — a three-tap recognizer, for example:

```js
var manager = new Hammer.Manager(square);

var TripleTap = new Hammer.Tap({ event: 'tripletap', taps: 3 });
manager.add(TripleTap);

manager.on('tripletap', function(e) {
  e.target.classList.toggle('expand');
});
```

The API surface is tiny (the README is shorter than this article's table) and the library ships no dependencies. It recognizes tap, double-tap, press, pan, swipe, pinch, and rotate out of the box, with per-recognizer thresholds (`taps`, `threshold`, `direction`) you can tune. It also predates the Pointer Events era, which cuts both ways: it normalizes touch events across a huge range of old devices, but you are carrying an abstraction modern browsers barely need anymore.

**Where it hurts:** no React integration (you wire `useEffect` yourself), no animation, no drop-target concept, and a maintenance cadence that is best described as "stable": the January 2026 push was a dependency-and-CI housekeeping release, not a feature roadmap. If you need gesture state feeding an animation loop, hammer.js hands you raw events and walks away.

## @use-gesture: Hooks That Turn Input Into Animation

@use-gesture (pmndrs/use-gesture, **9,622 stars**, MIT, last push July 2024) comes from the pmndrs ecosystem — the same org behind react-spring, zustand, and drei — and its pitch is different from hammer.js: it binds *richer mouse and touch events to any component* and hands you a gesture state object designed to be fed straight into an animation library. It ships both React hooks and a vanilla package, but the React story is where it shines.

```bash
npm install @use-gesture/react
```

```jsx
import { useSpring, animated } from '@react-spring/web'
import { useDrag } from '@use-gesture/react'

function Example() {
  const [{ x, y }, api] = useSpring(() => ({ x: 0, y: 0 }))

  // Set the drag hook and define component movement based on gesture data.
  const bind = useDrag(({ down, movement: [mx, my] }) => {
    api.start({ x: down ? mx : 0, y: down ? my : 0 })
  })

  // Bind it to a component.
  return <animated.div {...bind()} style={{ x, y, touchAction: 'none' }} />
}
```

That is the whole pattern: a hook returns a `bind` function, you spread it on a component, and every frame of the gesture arrives as structured state (`down`, `movement`, `velocity`, `pinch`, `offset`). The available hooks — `useDrag`, `usePinch`, `useWheel`, `useMove`, `useHover`, `useScroll` — map one-to-one to interaction types, and the README's demos (draggable lists, card stacks, action sheets, viewpagers, pinch-zoom cards) are precisely the animated interactions that made this library popular. The vanilla flavor mirrors the hooks API:

```js
const el = document.getElementById('drag')
const gesture = new DragGesture(el, ({ active, movement: [mx, my] }) => {
  anime({
    targets: el,
    translateX: active ? mx : 0,
    translateY: active ? my : 0,
    duration: active ? 0 : 1000
  })
})
```

**Where it hurts — and this is the honest part:** the last commit was July 2024, over two years before this article was written. The library still works and is stable — the ecosystem around it (react-spring, zustand) is thriving, and many production apps run it — but there is no active development, no issue triage momentum, and no roadmap. Treat it as a stable-maintenance dependency: fine for a shipping product, a risk for a greenfield architecture review. Also note it does not recognize "swipe" as a discrete gesture — you derive swipes from drag velocity yourself.

## interact.js: The Drag, Drop, and Resize Engine

interact.js (taye/interact.js, **12,925 stars**, MIT, last push August 2026) is the most full-featured of the three and the only one with active 2026 development. Its README positions it precisely: "JavaScript drag and drop, resizing and multi-touch gestures with inertia and snapping." Where hammer.js recognizes and @use-gesture animates, interact.js *manages interactions* — including the two jobs the others do not touch: drop targets and resize handles.

```bash
npm install interactjs
```

```js
var pixelSize = 16;

interact('.rainbow-pixel-canvas')
  .origin('self')
  .draggable({
    modifiers: [
      interact.modifiers.snap({
        // snap to the corners of a grid
        targets: [
          interact.snappers.grid({ x: pixelSize, y: pixelSize }),
        ],
      })
    ],
    listeners: {
      move: function (event) {
        var context = event.target.getContext('2d');
        // draw a square at the drag position
        context.fillRect(event.pageX - pixelSize / 2, event.pageY - pixelSize / 2,
                         pixelSize, pixelSize);
      }
    }
  })
  .on('doubletap', function (event) {
    var context = event.target.getContext('2d');
    context.clearRect(0, 0, context.canvas.width, context.canvas.height);
  });
```

The chainable API exposes `.draggable()`, `.resizable()`, `.gesturable()`, and `.dropzone()` — the dropzone concept (drag element A onto element B and get a `drop` event) is the piece that makes kanban boards and file-drop UIs work. Inertia is built in (release a drag and it glides with momentum), snapping supports grids and arbitrary target functions, and simultaneous multi-touch interactions are handled natively. It is written in TypeScript with definitions shipped in the package, and it documents SVG element interaction and IE9+ support.

**Where it hurts:** the API is imperative and stringly-ish (selector-based, event-listener callbacks), which feels dated next to @use-gesture's hooks — there is no first-class React binding, so in React you wrap it in `useEffect` and manage cleanup yourself. The bundle is also the heaviest of the three at ~25 KB gzipped. For a simple tap/swipe recognition job, it is far more machinery than you need.

## Pitfalls and Gotchas

**1. You must set `touchAction: 'none'` on draggable elements.** @use-gesture's README says it, and it applies to all three: without it, the browser's native scrolling and pinch-zoom fight your gesture handler and produce glitchy, jumpy drags on touch devices. This is the single most common "my drag is broken on mobile" bug.

**2. Two of the three libraries are effectively in maintenance mode.** hammer.js's 2026 activity is housekeeping, and @use-gesture has had no commits since July 2024. Only interact.js shows real 2026 development. This is not a reason to avoid hammer.js or @use-gesture — stability is a feature — but it *is* a reason to avoid building new architecture on assumptions that a feature will be added.

**3. Gestures are an accessibility hazard.** WCAG 2.5.1 (Pointer Gestures) requires that every single-pointer gesture has an alternative: buttons for swipe actions, visible drag handles, keyboard equivalents. A swipe-to-delete list with no "delete" button is an accessibility failure regardless of which library implements the swipe. Budget for the fallback UI, not just the gesture.

**4. Pointer Events changed the landscape.** Modern browsers have a unified `pointerdown/pointermove/pointerup` model with `touch-action` CSS — many "gesture" needs (a simple drag, a tap with a threshold) are now a dozen lines of native code. hammer.js's touch-event normalization is most valuable on old devices; on a modern mobile-only app, evaluate whether you need the library at all. For the dependency-vs-native trade-off in the wider React ecosystem, our [React hooks comparison](../2026-08-22-react-hooks-libraries-ahooks-usehooks-ts-react-use-comparison/) has the same discussion.

**5. Passive event listener warnings are real.** Chrome logs "Unable to preventDefault inside passive event listener" when touch handlers block scrolling. All three libraries handle this internally, but the moment you add your own `touchmove` listener to the same element, you will hit it — attach listeners with `{ passive: false }` only when you truly need `preventDefault()`.

**6. Don't mix gesture libraries.** If hammer.js recognizes a tap and interact.js also has a gesture recognizer on the same element, both fire, and you get double-handling. Pick one library per element; if you need both recognition and drag/resize on the same surface, interact.js alone covers both, or use hammer.js purely for recognition and keep interactions on a separate layer.

**7. Performance on long lists.** Gesture handlers attached to thousands of rows (or re-created on every render) will jank. For infinite scrolling lists, pair your choice with virtualization — see our [virtual scroll library comparison](../2026-08-17-javascript-virtual-scroll-libraries-tanstack-virtual-react-window-react-virtualized-comparison/) for TanStack Virtual vs react-window patterns.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "JavaScript Gesture Libraries in 2026: hammer.js vs @use-gesture vs interact.js",
  "description": "Role-first comparison of the three dominant JavaScript gesture libraries in 2026: hammer.js (24,344 stars, gesture recognition), @use-gesture (9,622 stars, React hooks for animated interactions), and interact.js (12,925 stars, drag/drop/resize engine with inertia and snapping). Includes feature table, decision matrix, maintenance-status assessment, and accessibility pitfalls.",
  "datePublished": "2026-08-24",
  "dateModified": "2026-08-24",
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

### Which JavaScript gesture library is the most popular?

hammer.js has the most stars (24,344) and the longest production history — it has been the default touch-gesture recognizer since 2014. interact.js follows with 12,925 stars, and @use-gesture has 9,622. By npm downloads, hammer.js also leads among these three.

### Is hammer.js still maintained in 2026?

Hammer.js is stable but slow-moving: the last push was January 2026 and mostly contained dependency and CI housekeeping. It is not archived and still works in production across thousands of apps, but do not expect new features. For long-term active development, interact.js (August 2026 push) is the only one of the three with real momentum.

### Is @use-gesture dead?

Not archived, but effectively in maintenance mode — the last commit was July 2024, over two years ago. The library is stable and widely used with react-spring, and it works fine in production, but it receives no new features or active issue triage. Evaluate it as a frozen dependency.

### What is the difference between gesture recognition and gesture hooks?

Recognition (hammer.js) tells you *when* a gesture happens — tap, swipe, pinch. Hooks (@use-gesture) give you a state stream of the gesture in progress — position, velocity, movement — designed to drive animations. They are different layers: recognition answers "did it happen?", hooks answer "what is it doing right now?".

### Does interact.js support React?

Not natively — it is a framework-agnostic imperative API (selector + chained actions) that you wrap in `useEffect` inside React components, managing cleanup yourself. If you want declarative React gesture hooks, use @use-gesture; if you want React drag-and-drop specifically, see our [dnd-kit vs react-dnd vs SortableJS guide](../2026-08-14-react-drag-and-drop-libraries-dnd-kit-react-dnd-sortablejs-guide/).

### Can I use these libraries for pinch-to-zoom?

Yes. hammer.js recognizes pinch events (`pinch` recognizer), @use-gesture has a dedicated `usePinch` hook (designed for exactly this), and interact.js supports multi-touch gestures via `.gesturable()`. The best choice depends on whether you need recognition only, animated state, or full interaction control.

### Which library supports drag and drop with snapping?

interact.js is the clear answer — inertia and grid/custom-target snapping are built-in features, along with dropzones. hammer.js does not do drop targets, and @use-gesture leaves snapping to your animation logic.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
