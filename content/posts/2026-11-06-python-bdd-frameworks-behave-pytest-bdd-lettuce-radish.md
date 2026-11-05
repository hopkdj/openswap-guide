---
title: "behave vs pytest-bdd vs lettuce in 2026: 200 Scenarios, Real Timings, One Dead Framework"
date: "2026-11-06"
tags: ["python", "testing", "developer-tools", "bdd", "comparison"]
draft: false
cover: "/img/screenshots/behave-banner.jpg"
---

Python BDD has a quiet problem: the frameworks that defined the style are mostly abandoned, and the one that is actively maintained is the one that looks least like Cucumber. `lettuce` — the library that introduced "feature files in Python" to a generation of teams — has not had a commit since **December 2020**. Its last PyPI release, 0.2.23, predates Python 3.10. Yet it still has 1,275 GitHub stars and still appears in tutorials that rank on the first page for "python bdd".

That gap between popularity and maintenance is exactly where engineering time gets wasted. So I built one feature file with 200 scenarios, implemented the same steps twice — once for `behave`, once for `pytest-bdd` — and measured both on the same machine. Then I read the maintenance and Python-support metadata for all four candidates.

## TL;DR: The Verdict in 40 Seconds

**Use `pytest-bdd` if your team already runs pytest** — which is almost every Python team in 2026. You get the entire pytest plugin ecosystem for free: `pytest-xdist` for parallelism, `pytest-cov` for coverage, `pytest-rerunfailures`, and fixture scoping that `behave` cannot express. Version 9.0.1 requires **Python 3.10+**, which is a real constraint on legacy projects.

**Use `behave` if you want the Cucumber model to be the primary interface** — its own runner, its own `environment.py` hooks, `context` object, built-in `--jobs` parallelism, and 3,544 stars of community step definitions. It starts faster than pytest-bdd on tiny suites (0.13 s versus 0.38 s wall for 200 trivial scenarios) and ships a JUnit/JSON formatter without plugins.

**Do not use `lettuce`.** No release since 2020, no maintenance, no Python 3.12+ guarantees. Migration to either of the above is mechanical: the Gherkin files are compatible.

**`radish-bdd` is alive but tiny** — 191 stars, v0.18.4, last push September 2026. It has genuinely nice features (scenario preconditions, `--with-threads`), but the community is too small to bet a company's test suite on.

## The 2026 Comparison Table

Live GitHub and PyPI data, pulled 2026-11-06:

| | behave | pytest-bdd | lettuce | radish-bdd |
|---|---|---|---|---|
| Stars | 3,544 | 1,473 | 1,275 | 191 |
| Last push | 2026-11-05 | 2026-11-02 | 2020-12-29 | 2026-09-28 |
| Latest release | 1.3.3 | 9.0.1 | 0.2.23 | 0.18.4 |
| Python requirement | ≥2.7 (legacy supported) | ≥3.10 | unspecified | ≥3 |
| Runtime dependencies | cucumber-expressions, cucumber-tag-expressions, parse, parse-type | mako, parse, parse-type, pytest, typing-extensions | none declared | docopt, colorful, tag-expressions, parse-type |
| Test runner | its own (`behave`) | pytest | its own | its own |
| Parallel execution | built in (`--jobs N`) | via `pytest-xdist` | no | threads |
| Fixtures / dependency injection | `context` object only | full pytest fixture graph | `world` object | scenario preconditions |
| Tag filtering | `--tags=@wip` | `-m` markers plus `--bdd-features` | limited | tags |
| JUnit XML | built in (`-f junit`) | via `--junitxml` | plugin | partial |
| Actively maintained | yes | yes | **no** | yes, small team |
| License | BSD-3-Clause | MIT | MIT | MIT |

Two rows are worth reading twice. **Python requirement**: pytest-bdd 9 dropped everything below 3.10, so if you still run 3.9 anywhere you are pinned to pytest-bdd 7.x. **Fixtures**: `behave`'s `context` is a mutable bag shared across a scenario's steps; pytest-bdd gives you pytest fixtures, which means factories, teardown, scoping and `autouse` — a substantially different testing model.

## Real Timings: 200 Scenarios, Identical Steps

Method: a single generated feature file with 200 scenarios, each with three steps (`Given an invoice with N widget at PRICE`, `When tax of R percent is applied`, `Then the total is X`), implemented with `decimal.Decimal` arithmetic in both frameworks. Same interpreter, same machine, cold process each run, three runs per framework.

| Framework | Wall clock (3 runs) | Framework-reported | Notes |
|---|---|---|---|
| behave 1.3.3 | 0.18 s / 0.14 s / 0.13 s | 0.019 s | `behave -f plain` |
| pytest-bdd 9.0.1 | 0.55 s / 0.38 s / 0.38 s | 0.15 s | `pytest -q`, 0.03 s collection |

The interesting number is not the total — both are fast enough that it never matters at 200 scenarios. It is the **constant overhead**: pytest-bdd spends roughly 0.2–0.4 s more per invocation booting pytest, importing plugins and collecting. On a 200-scenario suite that is 60% of the runtime. On a 5,000-scenario suite it is invisible.

So do not choose on speed. Choose on what happens at 5,000 scenarios, which is where parallelism and fixture reuse decide your CI duration. `behave --jobs 8` works out of the box; pytest-bdd's `pytest -n 8` requires `pytest-xdist` but distributes far more evenly because pytest fixtures can be session-scoped and shared per worker.

## Decision Matrix: Pick by Use Case

| Use case | Pick | Why |
|---|---|---|
| Existing pytest suite, want Gherkin for a subset | pytest-bdd | Same runner, same fixtures, same coverage config |
| Business stakeholders read and edit feature files | behave | Standalone runner, cleaner CLI, Cucumber-like output |
| Need parallel BDD with no extra plugins | behave | `--jobs N` is built in |
| Need BDD results inside `pytest --junitxml` for CI | pytest-bdd | Native pytest reporting |
| Python 3.9 or older in production | behave | pytest-bdd 9 requires 3.10+ |
| Contract/acceptance tests that must share DB fixtures | pytest-bdd | Session-scoped fixtures beat a context bag |
| A codebase already on lettuce | migrate to behave | Feature files port unchanged; steps need rewriting |
| Want Gherkin without the Cucumber ceremony | radish-bdd | Lighter model, but a 191-star bus factor |

## behave — The Standalone Cucumber Runner

`behave` owns the whole process: it discovers `.feature` files, imports step modules, and runs scenarios in its own runner. The layout is fixed by convention, which is either a feature or a straitjacket depending on your taste.

```bash
pip install behave
```

```text
features/
├── invoice.feature
├── environment.py
└── steps/
    └── invoice_steps.py
```

```gherkin
# features/invoice.feature
Feature: Invoice totals
  In order to bill customers correctly
  As a billing engineer
  I want deterministic totals

  Scenario Outline: tax is applied to a widget order
    Given an invoice with <qty> widget at <price>
    When tax of <rate> percent is applied
    Then the total is <total>

    Examples:
      | qty | price | rate | total  |
      | 1   | 19.99 | 8.25 | 21.64  |
      | 3   | 19.99 | 8.25 | 64.92  |
      | 2   | 1234.56 | 20 | 2962.94 |
```

```python
# features/steps/invoice_steps.py
from decimal import Decimal
from behave import given, when, then


@given("an invoice with {qty:d} widget at {price}")
def step_invoice(context, qty, price):
    context.qty = qty
    context.price = Decimal(price)


@when("tax of {rate} percent is applied")
def step_tax(context, rate):
    context.rate = Decimal(rate)


@then("the total is {expected}")
def step_total(context, expected):
    total = (context.price * context.qty * (1 + context.rate / 100)).quantize(Decimal("0.01"))
    assert total == Decimal(expected), f"{total} != {expected}"
```

Hooks live in `environment.py` and are the closest thing behave has to fixtures:

```python
# features/environment.py
def before_all(context):
    context.db = connect(os.environ["DATABASE_URL"])

def before_scenario(context, scenario):
    context.db.begin()

def after_scenario(context, scenario):
    context.db.rollback()          # no state leaks between scenarios

def after_all(context):
    context.db.close()
```

Run it with tags, parallelism and a CI-friendly report:

```bash
behave --tags=@smoke --jobs 4 -f pretty -f junit -o reports/
behave -f json.pretty -o reports/behave.json
```

The `context` object is behave's biggest liability. It is a mutable namespace with no scoping rules: `before_all` values are visible in every scenario, `before_scenario` values are lost after it, and nothing stops one step from overwriting another's key. Teams that grow past ~200 scenarios usually end up writing their own `context.reset()` in `environment.py` and a naming convention for keys. pytest fixtures solve this problem properly, which is why most teams eventually move.

## pytest-bdd — Gherkin on Top of the pytest You Already Have

`pytest-bdd` translates each scenario into a pytest test item. You keep your `conftest.py`, your fixtures, your markers, your coverage config, your xdist workers — and gain feature files.

```bash
pip install pytest-bdd
```

```text
tests/
├── conftest.py
├── features/
│   └── invoice.feature
└── test_invoice.py
```

```python
# tests/test_invoice.py
from decimal import Decimal

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("features")          # binds every scenario in the directory to this module


@pytest.fixture
def ctx():
    return {}


@given(parsers.parse("an invoice with {qty:d} widget at {price}"))
def step_invoice(ctx, qty, price):
    ctx["qty"] = qty
    ctx["price"] = Decimal(price)


@when(parsers.parse("tax of {rate} percent is applied"))
def step_tax(ctx, rate):
    ctx["rate"] = Decimal(rate)


@then(parsers.parse("the total is {expected}"))
def step_total(ctx, expected):
    total = (ctx["price"] * ctx["qty"] * (1 + ctx["rate"] / 100)).quantize(Decimal("0.01"))
    assert total == Decimal(expected), f"{total} != {expected}"
```

For a single named scenario, use the decorator form:

```python
from pytest_bdd import scenario

@scenario("features/invoice.feature", "tax is applied to a widget order")
def test_invoice_total():
    pass
```

And for typed parsing beyond `{qty:d}`, `cfparse` handles converters:

```python
from pytest_bdd import parsers

@given(parsers.cfparse("the clock reads {iso_date:Date}", extra_types={"Date": date.fromisoformat}))
def step_clock(iso_date):
    ...
```

The real payoff is that everything else is pytest:

```bash
pytest -n 8 --junitxml=reports/bdd.xml --cov=app --cov-report=term
pytest -m "not slow" -k invoice
```

```python
# tests/conftest.py — real fixtures, real scoping, real teardown
@pytest.fixture(scope="session")
def db():
    engine = create_engine(os.environ["DATABASE_URL"])
    yield engine
    engine.dispose()

@pytest.fixture(autouse=True)
def tx(db):
    conn = db.connect()
    trans = conn.begin()
    yield conn
    trans.rollback()
    conn.close()
```

That `autouse` transactional fixture is the thing behave cannot do cleanly: it isolates every scenario automatically, with no per-scenario bookkeeping in `environment.py`, and it works identically for your unit tests. Our [pytest plugin guide](../2026-07-26-python-pytest-plugins-mock-cov-xdist-timeout-asyncio/) covers xdist, timeout and asyncio configuration in more depth, and the [Python benchmarking tooling comparison](../2026-07-02-python-benchmarking-pytest-benchmark-codspeed-pyperf-asv/) is the place to start if you want to measure the suite itself.

## lettuce and radish-bdd — What to Know Before You Gamble

`lettuce` was the original Python BDD tool and it is effectively finished. Last commit `2020-12-29`, last release `0.2.23`, no declared Python version support, and its `world` object predates modern fixture patterns. It still installs and still runs simple suites, which is exactly what makes it dangerous: green tests on Python 3.9 say nothing about whether it works on 3.13. If you inherit a lettuce suite, port the `.feature` files to `behave` — the Gherkin syntax is compatible — and rewrite the step modules, which is a day of mechanical work.

```text
# lettuce step style (legacy) — note the regex decorators and world object
from lettuce import step, world
from decimal import Decimal

@step(r"an invoice with (\d+) widget at ([\d.]+)")
def invoice(step, qty, price):
    world.qty = int(qty)
    world.price = Decimal(price)
```

`radish-bdd` is the opposite case: alive, maintained (v0.18.4, pushed 2026-09-28), and genuinely interesting — scenario preconditions, tag expressions, colorful output, and a thread-based runner. But it has 191 stars and a single maintainer. Its features are attractive enough that you might choose it for a side project; it is not a reasonable dependency for a team that needs someone else to have hit the bug first.

## The Pitfalls That Cost Real Days

**1. Step-definition collisions are silent in behave, fatal in pytest-bdd.** If two modules define the same step text, pytest-bdd raises "Step ... is already defined" at collection; behave simply uses whichever module was imported last. In a large suite the behave behaviour means a refactor can quietly start running a different implementation. Keep one step module per domain and grep for the step text before adding a new one.

**2. `scenarios()` must point at a real directory.** pytest-bdd binds scenarios at import time. A path typo produces no tests rather than an obvious failure in some configurations, and an empty run looks exactly like a passing run in CI. Assert the count: `pytest --collect-only -q | tail -1` should match the number of scenarios you expect.

**3. The `context` bag leaks between scenarios.** behave does not reset `context` attributes you set in `before_scenario` unless you do it, and attributes set in a step persist into the next scenario's `context` object. Any test that passes only because a previous scenario populated a value is a test that will fail in a different order. Always pair `before_scenario` with `after_scenario` cleanup.

**4. Parse expressions versus Cucumber expressions.** `{qty:d}` is typed; `{qty}` is a string. Mixing them produces assertion failures that look like arithmetic bugs. Use `parsers.parse` in pytest-bdd and the plain quoted string in behave, and write one scenario that exercises the type boundary.

**5. Parallel execution changes your fixtures.** `behave --jobs 4` forks scenarios across processes, so `before_all` runs per process, not once per run — a session-scoped database setup will run four times. With `pytest-xdist` the same applies: session fixtures are per worker. Budget for it when you migrate a slow suite to parallel.

**6. Gherkin that is really a test script.** The most common failure mode is not technical: teams write 40-step scenarios that encode implementation details, then discover a UI refactor breaks 300 feature files. Keep scenarios at the business level (three to five steps), push detail into step implementations, and use `Scenario Outline` for data variation instead of copying scenarios.

**7. No tag hygiene.** Tags are the only lever you have for suite partitioning. Establish them early (`@smoke`, `@slow`, `@wip`, `@integration`) and enforce them in CI, because retrofitting tags onto 800 untagged scenarios is a week nobody enjoys.

**8. HTML reports that nobody opens.** behave's JSON output and pytest's JUnit XML are what CI actually consumes. Decide the report format before you write the first scenario; converting historical results later is impossible.

## FAQ

### Is pytest-bdd or behave better in 2026?

pytest-bdd, for most teams. It runs inside pytest, so you keep fixtures, xdist parallelism, coverage and the entire plugin ecosystem, and it is actively maintained (v9.0.1, pushed 2026-11-02). Choose behave instead if you need a standalone runner, built-in `--jobs` parallelism, or Python 3.9 support — pytest-bdd 9 requires Python 3.10 or newer.

### Is lettuce still maintained?

No. The last commit to `gabrielfalcao/lettuce` was on 2020-12-29 and the last PyPI release is 0.2.23. It has no declared Python version support and no recent compatibility work. Port the feature files to behave or pytest-bdd; the Gherkin syntax carries over, only the step modules need rewriting.

### How much slower is pytest-bdd than behave?

In my measurement of 200 identical scenarios, behave completed in 0.13–0.18 s wall clock and pytest-bdd in 0.38–0.55 s, of which pytest's own report attributed 0.15–0.16 s to test execution. The difference is pytest's startup and collection cost, roughly 0.2–0.4 s per invocation. At 5,000 scenarios it is irrelevant; what matters at that scale is parallel distribution, where pytest-xdist is stronger.

### Can I run behave and pytest-bdd in the same repository?

Yes, and it is a reasonable migration strategy: keep the existing behave suite running while new scenarios are written against pytest-bdd, with both sharing the same `.feature` files. The risk is step-definition drift — two implementations of the same step text that behave differently. Migrate feature by feature and delete the old step module as each one moves.

### How do I get JUnit XML out of a Python BDD suite for CI?

With behave, use its built-in formatter: `behave -f junit -o reports/`. With pytest-bdd, pytest's own flag applies: `pytest --junitxml=reports/bdd.xml`. Both produce standard JUnit XML that Jenkins, GitLab CI and GitHub Actions can parse without extra plugins.

### Does BDD work for API tests, or only for browser tests?

Both frameworks are runner-agnostic — steps are plain Python. The common pattern for API suites is a `requests`/`httpx` client in a fixture, a database transaction per scenario, and steps that assert on response bodies. See our [HTTP mocking comparison](../2026-10-23-python-http-mocking-vcrpy-responses-httpretty-pytest-httpserver/) for the record/replay side of that setup.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "behave vs pytest-bdd vs lettuce in 2026: 200 Scenarios, Real Timings, One Dead Framework",
  "description": "Benchmarked comparison of Python BDD frameworks behave, pytest-bdd, lettuce and radish-bdd, with real timings for 200 scenarios, maintenance status and migration pitfalls.",
  "datePublished": "2026-11-06",
  "dateModified": "2026-11-06",
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
