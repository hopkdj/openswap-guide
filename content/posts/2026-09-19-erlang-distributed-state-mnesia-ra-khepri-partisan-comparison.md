---
title: "Erlang Distributed State in 2026: Mnesia vs Ra vs Khepri vs Partisan"
date: "2026-09-19"
tags: ["erlang", "distributed-systems", "database", "beam"]
draft: false
cover: "/img/screenshots/erlang-khepri-logo.jpg"
description: "Mnesia, Ra, Khepri and Partisan compared for replicated state and cluster membership on the BEAM, with real code from official repos and a decision matrix."
---

You need state that survives a node dying. On the BEAM you have four credible answers, and picking wrong means discovering the limits of your choice at 3am — usually as a split-brain incident or a table that silently stopped replicating.

Mnesia is the built-in answer everyone reaches for first. Ra began as RabbitMQ's Raft implementation and is now used by more than one production message broker. Khepri is RabbitMQ's successor to Mnesia, rebuilt on top of Ra with tree semantics. Partisan solves a different problem entirely — making a cluster that actually scales past the point where full-mesh distribution falls over. This guide compares all four with live repository data and code taken from each project's own documentation.

## TL;DR — Quick Verdict

**Use Mnesia for small clusters and configuration-like data** — it is built into OTP, it is transactional, and for three to five nodes with `disc_copies` it is entirely adequate. **Use Ra when you need real consensus** — it is a multi-Raft implementation with a clear leader, and it is the foundation other production systems build on. **Use Khepri when you want replicated state with tree-structured namespacing** and you would otherwise be fighting Mnesia's table model. **Use Partisan when your problem is cluster size, not consensus** — it replaces OTP's full-mesh distribution with scalable membership for clusters in the hundreds.

One sentence: *Mnesia for simple, Ra for consensus, Khepri for structured replicated state, Partisan for cluster scale.*

## The Contenders at a Glance

Live GitHub figures pulled at publication time:

| Project | Repository | Stars | Last commit | Primary role | Consensus |
|---|---|---|---|---|---|
| **Mnesia** | [erlang/otp](https://github.com/erlang/otp) | 12,332 (whole OTP) | 2026-09-19 | Built-in transactional store | None (custom, no Raft) |
| **Ra** | [rabbitmq/ra](https://github.com/rabbitmq/ra) | 965 | 2026-09-19 | Multi-Raft consensus library | Raft |
| **Khepri** | [rabbitmq/khepri](https://github.com/rabbitmq/khepri) | 493 | 2026-09-19 | Tree-structured replicated database | Inherited from Ra |
| **Partisan** | [lasp-lang/partisan](https://github.com/lasp-lang/partisan) | 1,051 | 2026-08-31 | Scalable cluster membership and overlay | Not applicable |

Mnesia has no standalone repository — it ships as part of Erlang/OTP, which is why the star count in the table is OTP's. Treat that as a signal about how you consume it: it is a platform feature, not a dependency you version independently. Everything else in this list is a library you add to `rebar.config` or `mix.exs`.

## Scenario Decision Matrix

| Your situation | Recommendation | Reason |
|---|---|---|
| 3-node cluster, config and session data | **Mnesia** | Zero dependencies, transactional, ships with OTP |
| Need a single leader and replicated log | **Ra** | Purpose-built Raft with a proper `process_command` API |
| State is naturally hierarchical (per-tenant trees) | **Khepri** | Path-based API; no need to model everything as rows |
| Building on top of a replicated design | **Khepri** or **Ra** | Khepri already solved the layered-state-machine problem |
| Cluster must exceed ~100 nodes | **Partisan** | Replaces full-mesh distribution, which stops scaling much earlier |
| Need cross-datacenter replication with defined semantics | **Ra** | Explicit membership and leader queries across nodes |
| Prototyping and want the shortest path to working code | **Mnesia** | Ten lines to a replicated table |

## Mnesia — Built In, Adequate, Often Misjudged

Mnesia is transactional, has `disc_copies` for durability, and requires no dependency at all. For a config store or a session table in a small cluster, the shortest correct implementation looks like this:

```erlang
%% On each node, before first start
mnesia:create_schema([node()]),
mnesia:start(),

%% Define a table replicated to disk on every node
mnesia:create_table(user_settings, [
    {disc_copies, [node() | nodes()]},
    {attributes, [user_id, settings]}
]),

%% Write inside a transaction
mnesia:transaction(fun() ->
    mnesia:write({user_settings, <<"alice">>, #{theme => dark}})
end).
```

Three properties matter here. Transactions are real and can span tables. `disc_copies` gives durability with replication. And write performance is genuinely good for small payloads because Mnesia keeps a copy in RAM.

Where Mnesia earns its reputation is at scale and under partition. It has no Raft-style consensus; its handling of network partitions historically involved choosing availability over consistency, and recovering from a split requires operator intervention. Table count and schema changes are also awkward — adding an attribute across a large replicated table is a maintenance event, not a migration script.

The practical rule: Mnesia is excellent for data you could rebuild from an external source if you had to. It is a poor choice for the single source of truth for financial or inventory state.

## Ra — Multi-Raft With a Real Leader

Ra is a Raft implementation for Erlang and Elixir, built for the multi-Raft pattern where a single BEAM cluster hosts many independent consensus groups. RabbitMQ uses it in production for quorum queues and streams, which is about the strongest endorsement available in this ecosystem.

The README's quick-start is refreshingly concrete. You start the application on every node, build server IDs, define a state machine, and form the cluster:

```erlang
%% These Erlang nodes will host Ra nodes. They are the "seed" and assumed to
%% be running or come online shortly after Ra cluster formation is started.
ErlangNodes = ['ra1@hostname.local', 'ra2@hostname.local', 'ra3@hostname.local'],

%% This will check for Erlang distribution connectivity.
[io:format("Attempting to communicate with node ~s, response: ~s~n", [N, net_adm:ping(N)]) || N <- ErlangNodes],

%% The Ra application has to be started on all nodes before it can be used.
[rpc:call(N, ra, start, []) || N <- ErlangNodes],

ServerIds = [{quick_start, N} || N <- ErlangNodes],
ClusterName = quick_start,
%% State machine that implements the logic and an initial state
Machine = {simple, fun erlang:'+'/2, 0},

{ok, ServersStarted, _ServersNotStarted} = ra:start_cluster(default, ClusterName, Machine, ServerIds),
```

Commanding the cluster returns the leader, and — this is the idiom worth internalising — you pass that leader ID into the next command for efficiency:

```erlang
%% Add a number to the state machine.
{ok, StateMachineResult, LeaderId} = ra:process_command(hd(ServersStarted), 5),

%% Use the leader id from the last command result for the next one
{ok, 12, LeaderId1} = ra:process_command(LeaderId, 7).
```

Reading state is where Ra's design becomes clear. There are two kinds of query, and choosing between them is a consistency-versus-latency decision you make explicitly:

```erlang
%% find current Raft cluster leader
{ok, _Members, LeaderId} = ra:members(quick_start),
%% perform a leader query on the leader node
QueryFun = {ra_lib, id, []},
{ok, {_TermMeta, State}, LeaderId1} = ra:leader_query(LeaderId, QueryFun).
```

```erlang
%% this is the replica hosted on the current Erlang node.
{ok, Members, _LeaderId} = ra:members(quick_start),
LocalReplicaId = lists:keyfind(node(), 2, Members),
%% perform a local query on the local node
QueryFun = fun(StateVal) -> StateVal end,
{ok, {_TermMeta, State}, LeaderId1} = ra:local_query(LocalReplicaId, QueryFun).
```

The documentation states the trade-off plainly: local queries are far more efficient but can return out-of-date state, while leader queries offer the best consistency at the cost of a possible network round trip. Very few libraries make you name that trade-off in the call site. Ra does, and that is a good thing.

The cost of Ra is that you must write and version a state machine. The `Machine = {simple, fun erlang:'+'/2, 0}` form is a convenience for examples; a real system defines a module implementing `ra_machine` with `apply/3`, plus snapshot and recovery behaviour. Budget for that, because getting state machine determinism wrong is how you get replicas that diverge.

This is the architecture diagram published in the Ra repository, showing the layered internals — worth studying before you design a state machine on top of it:

![Ra cluster architecture diagram from the official rabbitmq/ra repository](/img/screenshots/erlang-ra-cluster-architecture.jpg "Ra internal architecture from the official repository")

## Khepri — Tree-Structured Replicated State

Khepri is RabbitMQ's answer to Mnesia's table model, built on Ra. Instead of tables with rows, you get a rooted tree of nodes with data attached, addressed by either a native path or a Unix-like string:

```erlang
%% In rebar.config
{deps, [{khepri, "0.19.0"}]}.
```

Starting a default store is a single call:

```erlang
khepri:start().
```

And then reads and writes are path operations — this is the whole API surface you need to get productive:

```erlang
%% Using a native path:
ok = khepri:put([emails, <<"alice">>], "alice@example.org").

%% Using a Unix-like path string:
ok = khepri:put("/:emails/alice", "alice@example.org").

{ok, "alice@example.org"} = khepri:get("/:emails/alice").

ok = khepri:delete("/:emails/alice").
```

There is a small but important behaviour documented alongside that example: parent nodes are created automatically, and after deleting `alice` the `emails` node stays behind — unless you configure conditions so that a parent is removed as soon as its last child disappears. If you are modelling per-tenant data as trees and expect cleanup to be automatic, that is a configuration decision you have to make deliberately.

The default store uses the default Ra system, and Khepri's own documentation recommends configuring your own Ra system and cluster rather than relying on the default — that is how you choose the data directory and run multiple Khepri instances on one node. In other words, Khepri does not hide Ra from you; it gives you a path-oriented API and hands the consensus layer over for configuration.

Elixir teams get a first-class path too:

```elixir
# In mix.exs
defp deps do
  [
    {:khepri, "0.19.0"}
  ]
end
```

## Partisan — Scaling the Cluster Itself

Partisan is solving a different problem, and conflating it with the other three is a category error. It is a distributed computing library for the BEAM that replaces OTP's built-in distribution layer. OTP's default is a full mesh: every node connects to every other node, which means N×(N−1)/2 connections. At a hundred nodes that is nearly five thousand connections, and at anything larger the maintenance traffic alone becomes the bottleneck.

Partisan provides custom overlay topologies and scalable membership so clusters can grow past that wall. Adding it is deliberately frictionless — the build generates Partisan-flavoured copies of OTP's own modules:

```erlang
%% rebar.config
{deps, [{partisan, "6.2.0"}]}.
```

```elixir
# mix.exs
defp deps, do: [{:partisan, "~> 6.0"}]
```

Then `rebar3 compile` (or `mix deps.get && mix compile`). As the project's documentation describes it, on every compile Partisan automatically generates Partisan-flavoured copies of OTP's `gen_server`, `gen_statem` and `supervisor` into its own `ebin/`, with no extra configuration required on the consumer side. That means switching a process to a Partisan-aware behaviour is a module swap rather than an architecture rewrite — which is the difference between a migration you can schedule and one you cannot.

If your cluster is under roughly fifty nodes and stable, Partisan is unnecessary complexity. If you are building something that must grow, adopting it early is far cheaper than retrofitting distribution semantics later.

## Pitfalls and Migration Notes

**Never treat Mnesia as a consensus system.** It does not implement Raft, and split-brain recovery requires deliberate operator action. If you need a definitive answer to "who is the leader and what is the committed state", you want Ra or Khepri, not Mnesia.

**State machine determinism is the failure mode that bites late.** With Ra, every replica replays the same commands, so any non-determinism in your `apply/3` — reading wall-clock time, generating random values, iterating a map in unstable order — produces divergent replicas that look fine until a failover. Keep the state machine pure and pass timestamps in as command payloads.

**Local queries can serve stale reads.** Ra's `local_query/2` is the fast path and it is explicitly documented as potentially out-of-date. Code that reads a value it just wrote via `local_query` can regress if it lands on a follower that has not applied the entry yet. Use `leader_query` for read-your-writes semantics.

**Mnesia table changes are operations, not migrations.** Adding an attribute to a large `disc_copies` table across a cluster is a planned maintenance activity. If your schema is going to evolve frequently, design for that up front — or use a store that treats schema changes as ordinary writes.

**Partisan's generated modules change your dependency graph.** Because Partisan emits its own copies of `gen_server`, `gen_statem` and `supervisor` at compile time, you must be consistent about which module a process uses. Mixing plain and Partisan behaviours in one supervision tree is a category error that produces confusing message-delivery behaviour.

**Cluster formation order matters.** All of these systems require Erlang distribution to be up and nodes to be reachable before clustering. Ra's own quick-start checks connectivity with `net_adm:ping/1` before attempting to form a cluster, which is a pattern worth copying into your own startup sequence rather than relying on blind retries.

For related reading, see our [Erlang HTTP server comparison](../2026-09-04-erlang-http-servers-cowboy-mochiweb-yaws-comparison/) for how these runtimes look at the request layer, and the [Erlang JSON library comparison](../2026-09-05-erlang-json-libraries-jiffy-jsx-jsone-comparison/) for serialisation choices that matter when state machines persist payloads. If you are designing background processing around replicated queues, our [Elixir background processing guide](../2026-09-18-elixir-background-processing-oban-broadway-quantum/) covers the job-layer side. For the alternative approach to distributed coordination — locks in external systems rather than in-language consensus — see the [self-hosted distributed locking guide](../self-hosted-distributed-locking-etcd-zookeeper-consul-redis-guide-2026/).

## FAQ

**Should I use Mnesia or Ra for replicated state?**

Use Mnesia when the data is small, the cluster is small, and you could rebuild the data from another source if a partition forced you to. Use Ra when you need genuine consensus — a single leader, a replicated log, and a defined answer to what the committed state is. The deciding question is not size but consequence: if losing or diverging state during a network partition is unacceptable, Mnesia is the wrong tool regardless of how well it performs on a healthy cluster.

**What is the difference between Ra and Khepri?**

Ra is the consensus layer — a multi-Raft implementation where you define the state machine. Khepri is a database built on top of Ra that gives you a tree-structured namespace with path-based reads and writes, so you do not have to design a state machine yourself. If you want replicated state with hierarchical organisation, Khepri is the shorter path. If you need a custom state machine or a replicated log for messages, work with Ra directly.

**Does Khepri replace Mnesia in RabbitMQ?**

Khepri was developed by the RabbitMQ team as a successor design to Mnesia for metadata storage, and it is built on Ra. Whether you should migrate depends on your version and your tolerance for migration work — the important takeaway is that the same team that operates Mnesia at scale built Khepri as its replacement, which tells you something about Mnesia's limits for large metadata workloads.

**When do I actually need Partisan?**

When cluster size, not consensus, is your bottleneck. OTP's default full-mesh distribution requires every node to connect to every other node, and the maintenance overhead grows quadratically. If you are planning clusters in the hundreds of nodes, or running on infrastructure where node membership changes constantly, Partisan's custom overlay topologies and scalable membership are the relevant fix. Below roughly fifty stable nodes, you almost certainly do not need it.

**How do I handle network partitions with these libraries?**

For anything where partition behaviour matters, choose Ra or Khepri and design around Raft's majority requirement: a partition that loses quorum stops accepting writes, which is the behaviour you want. Mnesia requires a deliberate decision about which side of a partition wins and typically manual recovery, so document that runbook in advance rather than inventing it during an outage. Partisan addresses membership and message delivery, not consistency of your data model, so it does not substitute for a consensus layer.

**What is a Ra state machine and why must it be deterministic?**

A Ra state machine is a module implementing the `ra_machine` behaviour whose `apply/3` function takes a command and the current state and returns the new state plus effects. It must be deterministic because every replica in the Raft group replays the same commands in the same order and must arrive at the same state. Time, randomness and any dependency on external systems inside `apply/3` will eventually cause replicas to diverge — pass those values in as part of the command instead.

---

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Erlang Distributed State in 2026: Mnesia vs Ra vs Khepri vs Partisan",
  "description": "Mnesia, Ra, Khepri and Partisan compared for replicated state and cluster membership on the BEAM, with real code from official repos and a decision matrix.",
  "datePublished": "2026-09-19",
  "dateModified": "2026-09-19",
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
