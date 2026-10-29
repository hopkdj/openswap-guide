---
title: "Erlang/OTP Concurrency in 2026: gen_server vs gen_statem vs poolboy vs gproc"
date: "2026-10-29"
tags: ["erlang", "beam", "concurrency", "developer-tools"]
draft: false
cover: "/img/screenshots/erlang-logo.jpg"
description: "gen_server, gen_statem, poolboy and gproc compared with live GitHub data, real OTP code, and the mailbox, pooling and registry pitfalls that take down BEAM services in production."
---

Your Erlang service has been up for eleven days, memory is climbing, and `erlang:process_info(Pid, message_queue_len)` returns 1.8 million. One `gen_server` is doing database work inline, every caller is queued behind it, and the node is one OOM killer away from a restart. Nothing in the language stopped you — the BEAM happily lets you build a single-process bottleneck and call it architecture.

That failure is not a `gen_server` problem. It is a *choosing-the-right-OTP-tool* problem. Erlang gives you four building blocks that people routinely confuse: the plain `gen_server` behaviour, the state-machine behaviour `gen_statem`, the worker-pool library `poolboy`, and the process registry `gproc`. They overlap just enough to be misapplied, and the differences decide whether your node survives Black Friday.

This guide compares all four with live repository data, real code from each project's own documentation, and the specific failure modes each one introduces.

## TL;DR: The Quick Verdict

**Use `gen_server` for anything that owns state and answers requests** — a connection, a cache, a rate limiter. It is in OTP, it is stable, and 90% of "we need a custom behaviour" instincts are wrong.

**Use `gen_statem` the moment your process has modes.** Retry/backoff loops, protocol handshakes, session lifecycles and anything where a message means different things depending on where you are. `gen_statem` also replaced the ancient `gen_fsm`, which you should not start new code with in 2026.

**Use `poolboy` when you must cap concurrency over a finite, expensive resource** — database connections, external API sessions, hardware. It is small, ISC-licensed, and has not needed a commit since April 2023 because there is nothing left to fix.

**Use `gproc` when you need to find processes by property rather than by name**, or when you need the same process registered under many keys, cluster-wide. It is a registry, not a scheduler — it will not solve throughput problems.

**And never put a blocking call inside a `gen_server` that other processes call synchronously.** That single rule prevents more outages than library choice ever will.

## Side-by-Side Comparison (live data, October 2026)

| Dimension | gen_server | gen_statem | poolboy | gproc |
|---|---|---|---|---|
| Where it lives | OTP `stdlib` | OTP `stdlib` | `devinus/poolboy` | `uwiger/gproc` |
| Stars | **12,357** (`erlang/otp`) | same repo | **1,597** | **1,101** |
| Last push | **2026-10-29** | **2026-10-29** | 2023-04-18 | 2026-08-09 |
| License | Apache-2.0 | Apache-2.0 | ISC | Apache-2.0 |
| Core abstraction | process + callback module | finite state machine | checked-out worker | key → pid index |
| Handles state | Yes | Yes, per state | No (delegates to worker) | No (metadata only) |
| Concurrency limit | 1 process = 1 mailbox | 1 process = 1 mailbox | **explicit pool size** | n/a |
| Cluster-aware | Manual | Manual | No | **Yes (`g` scope)** |
| Failure isolation | per process | per process | per worker + supervisor | per registered process |
| Typical misuse | doing slow I/O inline | using it as a plain server | pooling cheap ephemeral work | using it as a queue |

## Decision Matrix: Match the Tool to the Failure You Are Preventing

| Symptom you have today | Tool | Why it fixes the symptom |
|---|---|---|
| One process is a throughput bottleneck | **poolboy** | Fan work across N workers instead of one mailbox |
| "It works until the peer sends messages out of order" | **gen_statem** | Illegal transitions become explicit, testable states |
| `whereis/1` cannot express "all workers for tenant 42" | **gproc** | Arbitrary term keys, multiple aliases, `select/2` queries |
| Callers time out under load | **poolboy** + async casts | Bound concurrency, return `noreply` early |
| Code is a 900-line `case` on an atom called `State` | **gen_statem** | One function per state, compiler-checked events |
| You need a global singleton across nodes | **gproc** (`g` scope) | Cluster-wide registry with `{global, Key}` |
| You need to store and mutate data per entity | **gen_server** | It is literally what it is for |

## gen_server: Still the Default, Still the Trap

`gen_server` is a process with a mailbox, a state term and eight optional callbacks. The skeleton has not changed in a decade, which is exactly why it is trustworthy:

```erlang
%% file: src/rate_limiter.erl
-module(rate_limiter).
-behaviour(gen_server).

-export([start_link/1, allow/1]).
-export([init/1, handle_call/3, handle_cast/2, handle_info/2, terminate/2]).

-record(state, {limit :: pos_integer(), window_ms :: pos_integer(), hits = [] :: [integer()]}).

start_link(Limit) ->
    gen_server:start_link({local, ?MODULE}, ?MODULE, Limit, []).

allow(Key) ->
    gen_server:call(?MODULE, {allow, Key}, 1000).

init(Limit) ->
    {ok, #state{limit = Limit, window_ms = 60_000}}.

handle_call({allow, _Key}, _From, #state{limit = L, window_ms = W, hits = H} = S) ->
    Now = erlang:monotonic_time(millisecond),
    Recent = [T || T <- H, Now - T < W],
    case length(Recent) >= L of
        true  -> {reply, {error, limited}, S#state{hits = Recent}};
        false -> {reply, ok, S#state{hits = [Now | Recent]}}
    end;
handle_call(_Req, _From, S) ->
    {reply, {error, unknown_call}, S}.

handle_cast(_Msg, S) -> {noreply, S}.
handle_info(_Info, S) -> {noreply, S}.
terminate(_Reason, _S) -> ok.
```

Two production rules for this behaviour:

1. **Never do blocking I/O in `handle_call/3`.** Every caller waits behind it. If you need a database round trip, either make the call asynchronous (`gen_server:cast/2` plus a reply later via `gen_server:reply/2`) or move the I/O into a dedicated process that the server only supervises.
2. **Always pass an explicit timeout** to `gen_server:call/3`. The default is 5000 ms, and a caller that blocks forever turns one slow server into a cascading outage across your supervision tree.

When the mailbox grows anyway, `sys:get_state/1`, `erlang:process_info(Pid, [message_queue_len, memory])` and `recon` are the tools that tell you whether you have a slow handler or a message flood.

![Official Erlang/OTP heap garbage collection diagram](/img/screenshots/erlang-heap-gc.jpg "Heap scanning phases in the Erlang runtime, from the official ERTS internal documentation")

## gen_statem: When Your Process Has Modes

If you have ever written `handle_call({connect, Host}, ...)` guarded by `case State#state.status of disconnected -> ...; connecting -> ... end`, you have hand-rolled a state machine. `gen_statem` makes it explicit, and — critically — makes illegal transitions a compile-time or test-time discovery rather than a 3 a.m. incident.

```erlang
%% file: src/session.erl
-module(session).
-behaviour(gen_statem).

-export([start_link/1, login/2]).
-export([init/1, callback_mode/0, disconnected/3, connecting/3, connected/3, terminate/3]).

start_link(Opts) ->
    gen_statem:start_link(?MODULE, Opts, []).

login(Pid, User) ->
    gen_statem:call(Pid, {login, User}).

init([Host]) ->
    {ok, disconnected, #{host => Host, attempts => 0}}.

callback_mode() -> state_functions.

disconnected({call, From}, {login, User}, Data) ->
    {next_state, connecting, Data#{user => User, from => From}, [{state_timeout, 3000, connect}]};
disconnected(_EventType, _Event, _Data) ->
    {keep_state_and_data, [postpone]}.

connecting(state_timeout, connect, #{host := Host, attempts := A} = Data) ->
    case gen_tcp:connect(Host, 443, [binary, {active, false}], 2000) of
        {ok, Sock} ->
            {next_state, connected, Data#{socket => Sock, attempts => 0}};
        {error, _Reason} when A < 5 ->
            {keep_state, Data#{attempts => A + 1},
             [{state_timeout, backoff(A), connect}]};
        {error, Reason} ->
            {stop, {connect_failed, Reason}, Data}
    end.

connected({call, From}, logout, #{socket := Sock} = Data) ->
    gen_tcp:close(Sock),
    {next_state, disconnected, maps:remove(socket, Data), [{reply, From, ok}]};
connected(_EventType, _Event, _Data) ->
    {keep_state_and_data, [postpone]}.

backoff(A) -> min(30_000, 250 bsl A).

terminate(_Reason, _State, _Data) -> ok.
```

Three things this buys you that a `gen_server` with a status atom does not: the `postpone` flag (messages received in the wrong state are queued and replayed later, instead of being dropped or crashing), `state_timeout` (a timer that is automatically cancelled when the state changes), and a code layout where each state's legal events are visible in one function clause group.

Note the API detail that trips people up: `gen_statem` uses `{call, From}` and `{cast, ...}` tuples rather than separate callback functions, and `callback_mode/0` must return either `state_functions` or `handle_event_function` (or those plus `state_enter`). Get `callback_mode` wrong and you get a `function_clause` at the first event, not at compile time.

## poolboy: Bounding Expensive Concurrency

`poolboy` does exactly one thing: it keeps N workers alive under a supervisor and hands them out. No queueing policy language, no metrics endpoint, no plugin system — which is why the last commit was in 2023 and why it still works.

Wiring it up follows the pattern from the project README: a supervisor builds one child spec per pool.

```erlang
%% file: src/example_sup.erl  (from the poolboy README)
-module(example_sup).
-behaviour(supervisor).

-export([start_link/0, init/1]).

start_link() -> supervisor:start_link({local, ?MODULE}, ?MODULE, []).

init([]) ->
    PoolArgs = [
        {name, {local, pg_pool}},
        {worker_module, pg_worker},
        {size, 10},
        {max_overflow, 20}
    ],
    ChildSpec = poolboy:child_spec(pg_pool, PoolArgs, [{hostname, "127.0.0.1"}]),
    {ok, {{one_for_one, 10, 10}, [ChildSpec]}}.
```

```erlang
%% file: src/pg_worker.erl  (trimmed from the README example)
-module(pg_worker).
-behaviour(gen_server).
-behaviour(poolboy_worker).

-export([start_link/1]).
-export([init/1, handle_call/3, handle_cast/2, terminate/2]).

-record(state, {conn}).

start_link(Args) ->
    gen_server:start_link(?MODULE, Args, []).

init(Args) ->
    process_flag(trap_exit, true),
    Host = proplists:get_value(hostname, Args),
    {ok, Conn} = epgsql:connect(Host, "app", "secret", [{database, "app"}]),
    {ok, #state{conn = Conn}}.

handle_call({squery, Sql}, _From, #state{conn = Conn} = S) ->
    {reply, epgsql:squery(Conn, Sql), S};
handle_call(_Req, _From, S) ->
    {reply, ok, S}.

handle_cast(_Msg, S) -> {noreply, S}.
terminate(_Reason, _S) -> ok.
```

Callers then use `poolboy:transaction/3`, which checks a worker out, runs your fun, and checks it back in — including on exception:

```erlang
squery(Sql) ->
    poolboy:transaction(pg_pool, fun(Worker) ->
        gen_server:call(Worker, {squery, Sql})
    end, 5000).
```

The size parameters matter more than the library: `size` is the number of long-lived workers, `max_overflow` is how many extra workers may be started when the pool is empty, and anything beyond that queues the caller until `poolboy:transaction/3`'s timeout fires. Set `size` against your database's `max_connections`, not against your request rate — the pool is a concurrency *limiter*, and a limiter sized by demand is not a limiter.

One caveat: `poolboy` has no built-in metrics. Wrap `poolboy:status/1` (`{ready, N}`, `{overflow, N}`, `{checked_out, N}`) into your monitoring, or you will discover the pool is exhausted via user complaints rather than alerts.

## gproc: A Registry, Not a Scheduler

`gproc` extends the process dictionary with arbitrary-term keys, multiple aliases per process, cluster-wide registration and QLC-backed queries. If `whereis/1` is a hash map with atom keys, `gproc` is a queryable index.

```erlang
%% Register the current process under a composite key, and await it from elsewhere.
-module(tenant_worker).
-export([start/2, notify/2]).

start(TenantId, ShardId) ->
    Pid = spawn(fun() -> loop(TenantId) end),
    gproc:reg({n, l, {tenant, TenantId, ShardId}}, Pid),
    Pid.

notify(TenantId, ShardId) ->
    case gproc:lookup_pids({n, l, {tenant, TenantId, ShardId}}) of
        [Pid] -> Pid ! refresh, ok;
        []    -> {error, not_running}
    end.

loop(TenantId) ->
    receive
        refresh -> loop(TenantId);
        stop    -> ok
    end.
```

The `{n, l, Key}` triple means "non-unique name, local scope, this key" — non-unique is the useful part, because it lets you register many processes under one property and look them all up. Swap `l` for `g` and the registration becomes cluster-wide, which is how people build distributed singletons and pub/sub fan-out without an external service.

Two hard warnings. First, `g` scope inherits the BEAM's partition behaviour: during a netsplit both sides can believe they own the name. That is fine for "who is the current leader" if your application handles it, and catastrophic for "who owns this unique job". Second, `gproc` is a registry invoked by every registering process; it is not a message queue and not a work distributor. Using it to push jobs to workers turns the registry process into exactly the bottleneck you were trying to avoid.

## Pitfalls That Actually Cause Outages

- **Synchronous calls into a server that calls itself.** `gen_server:call` to the same PID deadlocks for the call timeout. It happens constantly in "helper" functions that receive a PID as an argument.
- **Unbounded mailbox on a hot path.** A `gen_server` that handles 50k messages/second and does 1 ms of work per message accumulates 50 messages per second of backlog. Backlog compounds; sampling `message_queue_len` and alerting on growth is mandatory, not optional.
- **`gen_statem` with `handle_event_function` and no state guards.** The compiler still type-checks nothing about transitions. Write property tests over random event sequences — our [Erlang testing comparison](../2026-09-07-erlang-testing-frameworks-eunit-commontest-proper-comparison/) covers the PropEr side of that.
- **Pool sized above the database limit.** `size * nodes > max_connections` produces connection-refused storms that look like application bugs. Compute the budget explicitly and encode it in configuration.
- **`gproc` with `g` scope on a flapping network.** Registration churn during partitions generates a storm of monitor messages. If you only need node-local lookup, use local scope — it is dramatically cheaper.
- **Supervision strategy copied from a blog post.** `one_for_one` on mutually dependent children leaves the tree in a half-broken state after one crash. Draw the dependency graph first, then pick `rest_for_one` where ordering matters.

## Migration and Coexistence

Most real systems end up using all four, and that is fine — they compose.

- **`gen_fsm` → `gen_statem`**: `gen_fsm` is deprecated. Port state callbacks to `state_functions` and move `StateName` out of the state record; the event tuples change from `{StateName, Event}` to `{call, From}`/`{cast, ...}` but the case analysis usually ports clause-for-clause.
- **Ad-hoc `spawn` + `receive` → `gen_server`**: if the process has more than two message types or ever needs to be inspected at runtime, it should be a behaviour. The `sys` module (`sys:get_state/1`, `sys:trace/2`) only works for behaviour-based processes.
- **Hand-rolled semaphore → `poolboy`**: if you are tracking "how many in flight" with an ETS counter and a `receive` loop, you have written a worse pool.
- **`global` module → `gproc`**: `global` works, but its name-conflict resolution is heavier and less queryable. For "find all workers for tenant X", `gproc:select/2` is the right tool.

For the service layer around these processes, the [Erlang HTTP server comparison](../2026-09-04-erlang-http-servers-cowboy-mochiweb-yaws-comparison/) covers which acceptor model to put in front of your pools, and the [release engineering guide](../2026-09-20-erlang-elixir-release-engineering-rebar3-relx-mix-releases/) covers shipping them. If your supervised processes are Elixir rather than Erlang, the [background processing comparison](../2026-09-18-elixir-background-processing-oban-broadway-quantum/) is the equivalent decision for job queues.

## FAQ

**Should I use gen_statem or gen_server in 2026?**
Use `gen_server` unless the process genuinely has distinct modes with different legal messages. `gen_statem` gives you `postpone`, `state_timeout` and per-state function clauses, all of which are real wins for protocol and lifecycle code — but it doubles the boilerplate for a simple key-value holder. A useful test: if your `handle_call` contains `case Status of`, you want `gen_statem`.

**Is poolboy still maintained?**
The last commit to `devinus/poolboy` was **April 2023**, and that is a feature, not a warning sign: the library is a few hundred lines implementing one idea, with 1,597 stars and a stable API. If you need per-pool metrics, dynamic resizing or queue introspection built in, look at `pooler` or write a thin wrapper — but for "cap concurrency over 10 database connections", poolboy still does the job.

**What is the difference between gproc and the global module?**
`global` registers names and resolves conflicts across nodes with a defined protocol; `gproc` builds a general property index with arbitrary term keys, non-unique registrations, counters and QLC queries. `gproc` can do everything `global` does plus pattern matching over registrations, at the cost of an extra application dependency and an extra process on the registration path.

**How do I find out which process is eating the node?**
Start with `erlang:process_info(Pid, [memory, message_queue_len, current_function, reductions])` sorted by memory, then `recon:proc_window/3` for a time-windowed view. A high `message_queue_len` with a low `reductions` count means a stalled consumer; high `reductions` with a growing queue means the producer is simply faster than the handler.

**Can I run poolboy workers under gproc registration?**
Yes, and it is a common combination: `gproc` answers "which worker serves tenant 42", `poolboy` answers "how many may run at once". Register in the worker's `init/1` and rely on `gproc`'s monitor-based cleanup so a crashed worker's key disappears automatically.

**Does gen_statem support state entry callbacks?**
Yes — add `state_enter` to `callback_mode/0` and implement `StateName(enter, OldState, Data)`. That is the correct place to start timers or emit transition telemetry, rather than scattering it across every clause that performs the transition.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Erlang/OTP Concurrency in 2026: gen_server vs gen_statem vs poolboy vs gproc",
  "description": "gen_server, gen_statem, poolboy and gproc compared with live GitHub data, real OTP code and the mailbox, pooling and registry pitfalls that cause BEAM outages.",
  "datePublished": "2026-10-29",
  "dateModified": "2026-10-29",
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
