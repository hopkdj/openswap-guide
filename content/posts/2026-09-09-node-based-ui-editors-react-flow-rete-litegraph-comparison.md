---
title: "Node-Based UI Editors in 2026: React Flow vs Rete.js vs LiteGraph.js"
date: "2026-09-09"
tags: ["javascript", "react", "node-editor", "visual-programming", "frontend"]
draft: false
cover: "/img/screenshots/react-flow-node-editor-cover.jpg"
---

Every second product team now ships some kind of node graph: workflow builders, data transformation editors, diagramming surfaces, pipeline designers. The hard part is never the idea — it is picking the editor library underneath it. Choose wrong and you rebuild the whole interaction model eighteen months in, when your custom nodes and serialization format are already baked into every user workflow.

The three serious contenders are **React Flow (xyflow, 38,305 stars)**, **Rete.js (12,239 stars)** and **LiteGraph.js (8,130 stars)**. They look similar in screenshots and behave very differently in production. This guide compares them on rendering architecture, framework coupling, plugin ecosystems and maintenance reality, with real code from the official repositories.

## TL;DR: Quick Verdict

**If you build with React and want a polished, ready-out-of-the-box canvas** — minimap, controls, zoom, custom node components — **pick React Flow**. **If you are building a visual programming language** where the graph *is* the product (typed sockets, node palettes, dataflow execution) and you need it framework-agnostic or in Vue/Angular, **pick Rete.js**. **If you need a dependency-free canvas engine** that runs on plain HTML or inside a game/simulation loop and you are comfortable owning maintenance, **LiteGraph.js still works — but treat it as unmaintained since August 2024 and pin your version**.

## Why This Decision Costs Teams So Much

Node-based editors are not a list component. They are a **state model** (nodes, edges, positions), a **rendering strategy** (DOM vs canvas), an **interaction layer** (drag, connect, select, pan, zoom) and a **serialization format** you will store in your database. When you swap libraries, all four layers change at once. That is why the choice deserves a full comparison rather than a "just use the popular one" default.

There is also a licensing and longevity angle that most tutorials skip: two of these projects are MIT and actively maintained, and one has effectively entered maintenance mode. Your editor library becomes part of your product's foundation — its bus factor is your bus factor.

## Feature Comparison at a Glance

| | **React Flow (xyflow)** | **Rete.js** | **LiteGraph.js** |
|---|---|---|---|
| GitHub stars | 38,305 | 12,239 | 8,130 |
| Last push | 2026-09-08 | 2026-07-24 | 2024-08-01 |
| License | MIT | MIT | MIT |
| Rendering | DOM (HTML nodes) | DOM via render plugins | HTML5 Canvas 2D |
| Framework | React (+ Svelte Flow for Svelte) | Core is framework-agnostic; React/Vue/Angular plugins | None (vanilla JS) |
| Built-in minimap/controls | Yes (MiniMap, Controls, Background) | Via plugins (minimap-plugin, context-menu-plugin) | Graph canvas with node list; minimal UI chrome |
| Typed sockets / dataflow | Manual (via custom nodes) | First-class (ClassicPreset Input/Output/Socket) | First-class (typed inputs/outputs, data propagation) |
| Custom nodes | React components, full styling freedom | Render-plugin components | JS prototype classes registered by name |
| Node execution engine | Not included (UI only) | Plugins (code-plugin, task-plugin, engine) | Built-in graph execution (`graph.start()`) |
| Serialization | `toObject()` / `fromObject()` | Editor data + plugins | `graph.serialize()` / `deserialize()` |
| Learning curve | Low (React-friendly) | Medium (plugin wiring) | Low to start, steep to master |

## Use Case → Decision Matrix

| Use Case | Recommendation | Why |
|---|---|---|
| React app, workflow/diagram UI, want results this week | **React Flow** | Components, minimap and state hooks out of the box; largest community and most examples |
| Product *is* a visual programming environment (typed node logic) | **Rete.js** | Sockets, presets and engine plugins are designed for dataflow semantics, not just boxes and arrows |
| Vue or Angular team | **Rete.js** (official render plugins) or **React Flow's sibling Svelte Flow** for Svelte | Rete has first-party Vue and Angular plugin packages; React Flow is React-only |
| No framework at all, embedded canvas, game/sim tooling | **LiteGraph.js** | Zero dependencies, runs anywhere, includes a graph execution engine |
| Anything where you cannot afford upstream abandonment | **React Flow or Rete.js** | Both pushed commits within the last two months; LiteGraph has been quiet since 2024 |

## React Flow: The React Standard

React Flow — the library behind the `@xyflow/react` package — is the default answer for React-based node UIs, and for good reason. It is a **DOM-based** editor: every node is a real React component, so styling is just CSS and complex nodes (forms, previews, nested widgets) are trivial to build. The package ships with `MiniMap`, `Controls`, `Background`, custom edge types, sub-flows and a hooks-based state API (`useNodesState`, `useEdgesState`) that keeps your graph data in plain React state.

The official minimal example from the repository README shows how little boilerplate a working editor needs:

```jsx
import { useCallback } from 'react';
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
} from '@xyflow/react';

import '@xyflow/react/dist/style.css';

const initialNodes = [
  { id: '1', position: { x: 0, y: 0 }, data: { label: '1' } },
  { id: '2', position: { x: 0, y: 100 }, data: { label: '2' } },
];

const initialEdges = [{ id: 'e1-2', source: '1', target: '2' }];

function Flow() {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  const onConnect = useCallback((params) => setEdges((eds) => addEdge(params, eds)), [setEdges]);

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      onConnect={onConnect}
    >
      <MiniMap />
      <Controls />
      <Background />
    </ReactFlow>
  );
}

export default Flow;
```

Because the graph data is ordinary React state, you can persist it to your backend, load it into a different view, and render read-only variants without a second library. React Flow's model is deliberately **UI-first**: it does not execute your graph or understand typed sockets. If your nodes are just visual steps in a human-driven flow (approvals, checklists, deployment steps), that is exactly right — execution belongs in your own engine anyway.

The same team publishes **Svelte Flow** with a matching API, and the xyflow monorepo (MIT, last push September 2026) is one of the most active in the frontend space.

## Rete.js: The Visual Programming Framework

Rete.js (v2, rewritten from scratch in TypeScript) is not a diagram library with a graph theme — it is a **visual programming framework**. The core package (`rete`) holds the editor and the `ClassicPreset` with typed sockets, and everything visual is opt-in through plugins: `@retejs/area-plugin` (pan/zoom/drag, selectable, snap, restrictor extensions), `@retejs/connection-plugin`, `@retejs/react-plugin` or `@retejs/vue-plugin` for rendering, plus minimap, context-menu, history, auto-arrange, linter and code plugins in the same org.

The core model — verified directly from the repository's own test suite — is built around typed inputs and outputs from the start:

```ts
import { NodeEditor, ClassicPreset } from 'rete';

const editor = new NodeEditor();

// Classic preset nodes carry typed sockets
const a = new ClassicPreset.Node('A');
const input = new ClassicPreset.Input(new ClassicPreset.Socket('number'));
const output = new ClassicPreset.Output(new ClassicPreset.Socket('number'));

a.addInput('in', input);
a.addOutput('out', output);

editor.addNode(a);

// Connections are first-class and type-checked by socket
const connection = new ClassicPreset.Connection(a, 'out', a, 'in');
editor.addConnection(connection);
```

The official scaffolding tool (`npx rete-kit app`, from the project README) generates a working editor with the area, connection and a render plugin wired together, so you do not hand-roll the bootstrap. Rete also ships **task-plugin** and **code-plugin** for graph execution and code generation, which is what makes it the usual choice when the node canvas is a real programming surface — think blueprint-style logic editors rather than process diagrams.

The trade-off: the plugin architecture gives you flexibility but costs setup. A minimal Rete editor needs the area plugin plus a render plugin plus connection handling before the first node appears, whereas React Flow renders in one component. Teams that only need "boxes and arrows" frequently find Rete's socket model overkill.

## LiteGraph.js: The Zero-Dependency Canvas Engine

LiteGraph.js is the outlier: a **Canvas 2D** graph engine with its own built-in editor UI, no framework, no npm dependency tree — one script tag and you have a working node canvas that can even execute the graph. It was designed for things "similar to PD or UDK Blueprints" (per the project description): creative tools, simulation editors, and embedded node systems where you cannot afford a React runtime.

The README's own example is a complete, runnable page:

```html
<script>
var graph = new LGraph();

var canvas = new LGraphCanvas("#mycanvas", graph);

var node_const = LiteGraph.createNode("basic/const");
node_const.pos = [200, 200];
graph.add(node_const);
node_const.setValue(4.5);

var node_watch = LiteGraph.createNode("basic/watch");
node_watch.pos = [700, 200];
graph.add(node_watch);

node_const.connect(0, node_watch, 0);

graph.start();
</script>
```

Custom nodes are plain JavaScript prototype classes registered by name — no JSX, no component tree:

```javascript
function MyAddNode() {
  this.addInput("A", "number");
  this.addInput("B", "number");
  this.addOutput("A+B", "number");
  this.properties = { precision: 1 };
}

MyAddNode.title = "Sum";

MyAddNode.prototype.onExecute = function () {
  var A = this.getInputData(0);
  if (A === undefined) A = 0;
  var B = this.getInputData(1);
  if (B === undefined) B = 0;
  this.setOutputData(0, A + B);
};

LiteGraph.registerNodeType("basic/sum", MyAddNode);
```

That power comes with a serious caveat: **the repository has had no commits since August 2024**. The engine still works — it is stable, dependency-free code — but there is no upstream addressing issues, and the node ecosystem around it is frozen. If you adopt LiteGraph in 2026, pin the version, budget for a fork, and treat the built-in editor as a starting point rather than a supported product.

## Pitfalls and Migration Gotchas

1. **Maintenance status is a feature decision.** React Flow and Rete.js both had commits in the last eight weeks; LiteGraph.js has been dormant for over two years. For a product you will ship for five years, that difference outweighs most API considerations.
2. **React Flow's version jumps break APIs.** The xyflow team ships major versions regularly (v11 → v12 changed node sizing and edge behavior). Read the migration guide before upgrading, and pin major versions in CI.
3. **"It's just JSON" is a trap.** All three serialize graphs, but your *custom node payloads* become the real contract. Version your node type schemas from day one — renaming a socket in Rete or a node type in LiteGraph silently orphans saved graphs.
4. **Performance cliffs are different per architecture.** DOM-rendered editors (React Flow) degrade when you push past thousands of visible nodes without virtualization strategies; canvas editors (LiteGraph) handle more nodes but redraw the world every frame and make rich per-node UI painful.
5. **React Flow is UI-only.** If you assume edges imply execution, you will build the engine twice. Decide explicitly whether the graph is documentation (flow) or program (dataflow) — that single decision points you to React Flow vs Rete.
6. **SSR and bundlers.** React Flow and Rete render plugins touch `window` — disable server-side rendering for editor routes or you will hit hydration crashes (the same class of issue we cover in our [rich text editor comparison](../2026-08-16-rich-text-editors-tiptap-slate-prosemirror-comparison/), where ProseMirror has identical SSR constraints).

## Integration With Self-Hosted and Full-Stack Apps

Node editors shine when they sit on top of your own backend, and all three serialize cleanly to a REST or database layer. A typical self-hosted stack pairs a React Flow or Rete canvas with your API for persistence and a worker for execution — the editor stays a pure frontend concern. If you are already building drag-and-drop surfaces, our [React drag-and-drop comparison](../2026-08-14-react-drag-and-drop-libraries-dnd-kit-react-dnd-sortablejs-guide/) covers the interaction layer these editors build on, and teams replacing spreadsheet-style UIs often evaluate node canvases next to [web spreadsheet libraries](../2026-08-14-web-spreadsheet-libraries-univer-handsontable-luckysheet-guide/) for the same "power user" audience.

## FAQ

### Is React Flow free for commercial use?

Yes. React Flow and Svelte Flow are MIT licensed, including commercial products. The team behind xyflow sells support and hosted services, but the library itself carries no license fee or attribution requirement.

### What is the difference between React Flow and Rete.js?

React Flow is a React-specific UI library for node graphs: it renders nodes and edges beautifully but does not define typed sockets or execution semantics. Rete.js is a visual programming framework: its core model includes typed inputs/outputs and sockets, with rendering added via plugins for React, Vue or Angular. Choose React Flow for diagram-like UIs and Rete.js when the graph is actual program logic.

### Is LiteGraph.js still maintained?

The repository has received no commits since August 2024. The code remains usable and dependency-free, and it still powers several established open-source creative tools, but there is effectively no upstream maintenance. Pin the version you adopt and plan to own any future fixes yourself.

### Can I use these editors with Vue or Angular?

Rete.js has first-party render plugins for React, Vue and Angular, making it the most framework-flexible option. React Flow is React-only, though the same organization publishes Svelte Flow for Svelte projects. LiteGraph.js is framework-agnostic by virtue of being dependency-free.

### Do any of these libraries execute the node graph?

LiteGraph.js includes a built-in execution engine (`graph.start()` and node `onExecute` handlers). Rete.js offers task and code plugins for execution and code generation. React Flow is strictly a UI library — execution is left to your own engine, which is usually the correct separation for workflow products.

### Which editor scales best to hundreds or thousands of nodes?

Canvas rendering (LiteGraph) handles the largest raw node counts but sacrifices rich per-node UI. DOM-rendered editors (React Flow, Rete with React) stay responsive into the thousands with careful memoization, custom node design and, for React Flow, the built-in viewport culling; beyond that, you need paging or sub-flows regardless of library.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Node-Based UI Editors in 2026: React Flow vs Rete.js vs LiteGraph.js",
  "description": "Compare React Flow, Rete.js and LiteGraph.js for building node-based editors: rendering architecture, framework coupling, typed sockets, maintenance status, real code samples and a use-case decision matrix.",
  "datePublished": "2026-09-09",
  "dateModified": "2026-09-09",
  "author": {
    "@type": "Organization",
    "name": "OpenSwap Guide"
  },
  "publisher": {
    "@type": "Organization",
    "name": "OpenSwap Guide",
    "logo": {
      "@type": "ImageObject",
      "url": "https://www.pistack.xyz/logo.png"
    }
  }
}
</script>

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
