---
title: "Flaky Tests in 2026: Detect, Quarantine and Kill Them for Good"
date: "2026-11-11"
tags: ["testing", "ci-cd", "python", "rust", "developer-tools"]
draft: false
description: "A practical workflow for flaky tests: detect them with order randomization and repetition, contain them with bounded retries, and fix the seven root causes that actually produce them."
---

# Flaky Tests in 2026: Detect, Quarantine and Kill Them for Good

A flaky test is not a test problem. It is an *organizational* problem wearing a test's clothes. The first time someone clicks "re-run failed jobs" and the build goes green, every engineer on the team learns a durable lesson: **red does not mean broken.** From that moment your suite stops being a signal and becomes noise, and the real regression that ships next month walks past a reviewer who has been trained to ignore the alarm.

The fix is not "be more careful". It is a pipeline: detect flakiness deliberately, contain it with a bounded and *measured* retry policy, then fix root causes in the order that removes the most noise per hour of work. Here is the tooling and the workflow that actually holds up in 2026.

## TL;DR / Quick Verdict

- **Detect:** randomize test order every run (`pytest-randomly`, `go test -shuffle=on`) and repeat a suspect test N times locally (`pytest-repeat`, `-count=20`). A test that only fails in a different order is a state-leak bug, not a timing bug.
- **Contain:** retries are acceptable *only* when they emit a metric. `pytest-rerunfailures`, `cargo nextest --retries` and `gotestsum --rerun-fails` all support this — use them, but count every retry.
- **Localize:** `pytest-testmon` (1,034★) runs only the tests affected by your change, so the flaky 200-test suite stops being a 20-minute tax on every commit.
- **Never** quarantine silently. A quarantined test with no owner and no expiry date is a deleted test with extra steps.

## The containment toolkit

Star counts and last-push dates read from the GitHub API on **2026-11-11**.

| Tool | Ecosystem | Role | Key flags | Stars | Last push |
|---|---|---|---|---|---|
| pytest-randomly | Python | Randomize order, reseed `random` per test | `-p no:randomly`, `--randomly-seed=…` | 724 | 2026-11-08 |
| pytest-repeat | Python | Run a test N times to expose flakiness | `--count=20` | 196 | 2025-09-08 |
| pytest-rerunfailures | Python | Bounded retries with marker control | `--reruns 3`, `--reruns-delay 5` | 483 | 2026-10-07 |
| pytest-testmon | Python | Run only tests affected by the diff | `--testmon` | 1,034 | 2026-11-02 |
| gotestsum | Go | Human-readable runner, rerun-failed, JUnit export | `--rerun-fails=2`, `--jsonfile` | 2,738 | 2026-04-15 |
| nextest (Rust) | Rust | Per-test retries plus machine-readable output | `--retries 3`, `--no-fail-fast` | 3,391 | 2026-11-08 |
| `go test -shuffle` | Go | Randomize test order in-tree | `-shuffle=on`, `-count=20` | stdlib | Go 1.25 |
| pytest-flakefinder | Python | Legacy repeat-until-fail helper | `--flake-finder` | 159 | 2022-10-26 (stale) |

Note the stale entry: `pytest-flakefinder` has not been pushed since 2022 and `pytest-repeat` since 2025-09-08. They still work, but on Python 3.13+ test `pytest-repeat` in your matrix before making it a dependency; `--count` semantics do not interact well with some fixture-scoping plugins.

## Decision matrix: what to reach for, when

| Situation | Do this | Why |
|---|---|---|
| "This test fails once a week, no idea why" | `pytest-repeat --count=50` on that single test | Repetition converts a weekly event into a 30-second experiment |
| "It passes alone but fails in the full suite" | `pytest-randomly` with a fixed seed | Order dependence points at shared state, not timing |
| CI is red 3-4 times a day across many tests | `--reruns 2` plus a retry metric | Restores trust now; the metric stops it becoming permanent |
| Full suite takes 25 minutes and blocks every PR | `pytest-testmon --testmon` | Runs the subset touched by the diff, usually 5-15% |
| Go repo, failures across packages | `gotestsum --rerun-fails=2 --jsonfile results.json` | Rerun support plus structured output for trend analysis |
| Rust repo with 4,000 tests | `cargo nextest run --retries 3` | Retries are per-test, not per-run; failures stay attributed |
| A test is known-broken and blocks releases | Quarantine with owner + expiry | Containment without losing the signal forever |
| You cannot reproduce it at all | Producer-side logging: seed, time, host, order | You cannot fix what you cannot replay |

## Step 1 — Detect: change the order, then repeat

Most teams test flakiness by re-running the same command, which is the least informative experiment possible. Two knobs find far more bugs:

**Order randomization.** Many "flaky" tests are order-dependent: test A leaves a row in the database, test B asserts the table is empty, and pytest's default file-order collection makes the pair pass by luck. `pytest-randomly` shuffles collection and prints the seed in the header, so any failure is one `--randomly-seed=<value>` away from reproduction:

```bash
# Run the suite in a new random order every time, log the seed
pytest -p randomly

# Reproduce exactly
pytest --randomly-seed=847192

# Suspect a specific ordering bug? Disable randomization to compare
pytest -p no:randomly
```

In Go the equivalent is built in — and `-count` is the repetition knob:

```bash
# Randomize order, print the seed, repeat each test 20 times
go test -shuffle=on -count=20 ./... 2>&1 | tee flaky.log
```

**Repetition.** A test that passes 50 times and fails on the 51st is not "flaky"; it is a race or a resource leak, and 50 iterations is a cheap way to find out which:

```bash
pytest tests/test_billing.py::test_proration --count=50 -x
```

If that reproduces it, you now have a *local* failure — the single most valuable artifact in debugging, and the thing re-running CI never gives you.

## Step 2 — Localize: stop paying twenty minutes per commit

Once you know a suite is flaky, the temptation is to retry the whole thing. Better: run less. `pytest-testmon` records which tests exercise which lines and runs only the tests affected by your diff:

```bash
pip install pytest-testmon

# First run builds the map (full suite, slower)
pytest --testmon

# Subsequent runs execute only affected tests
pytest --testmon
```

In practice that turns a 20-minute suite into a 1-3 minute one, which changes the economics of flakiness: when the feedback loop is short, engineers are willing to re-run for information rather than to make red disappear. The trade-off is real — testmon's map is line-based and blind to dynamic imports and plugin behavior, so **run the full suite on main and on release branches**, and use testmon for the inner loop only.

## Step 3 — Contain: retries, but with a receipt

Retries are not evil. Unmeasured retries are. The rule that keeps a suite honest: *every retry emits an event you can chart.*

```bash
# Python: up to 3 retries, 5s apart, JUnit XML for the dashboard
pytest --reruns 3 --reruns-delay 5 --junitxml=report.xml

# Scope retries to a known-suspect test instead of the whole suite
# @pytest.mark.flaky(reruns=5, reruns_delay=2)
```

```bash
# Rust: per-test retries, failures still attributed to the test
cargo nextest run --retries 3 --no-fail-fast

# Go: rerun failed tests, emit JSON for trend analysis
gotestsum --rerun-fails=2 --jsonfile results.json -- ./...
```

Then chart two numbers: **tests that needed a retry** and **tests that failed all attempts**. The first number is your flakiness budget. If it rises week over week, you are accumulating debt; if it falls after a fix sprint, the policy is working. A team with a 1,200-test suite and 4% retried tests is in better shape than a team with zero retries and three ignored failures — the second team just does not know its number yet.

## Step 4 — Quarantine with an expiry date

Quarantine is how you keep a known-flaky test from blocking releases without deleting the coverage. It only works with three fields attached:

1. **Owner** — a person, not a team channel.
2. **Expiry** — 30 or 90 days, after which the test is deleted rather than renewed.
3. **Evidence** — a link to at least one failing run with seed, host and timestamp.

```python
# conftest.py — quarantine without losing the signal
import os
import pytest

def pytest_collection_modifyitems(config, items):
    if os.getenv("RUN_QUARANTINE") == "1":
        return
    skip_quarantine = pytest.mark.skip(reason="quarantined: see FLAKY-142 (owner: @db-team, expires 2027-01-15)")
    for item in items:
        if "quarantine" in item.keywords:
            item.add_marker(skip_quarantine)
```

```python
# tests/test_reports.py
@pytest.mark.quarantine
def test_monthly_report_totals():
    ...
```

Run the quarantine subset on a nightly schedule with `RUN_QUARANTINE=1` so a fix gets noticed. Without that job, quarantine is a graveyard — and once a test has been skipped for six months, nobody will ever un-skip it.

## The seven root causes, and the fix for each

| Root cause | Typical symptom | Fix |
|---|---|---|
| Wall-clock dependence | Fails near midnight, month-end, or DST switch | Freeze the clock in tests, never call `now()` directly |
| Shared state between tests | Passes alone, fails in suite | Fresh fixture scope per test; truncate tables between tests |
| Async wait too short | Fails under load, passes locally | Poll with a deadline, never `sleep(1)` |
| Unseeded randomness | Fails 1 in 200 runs | Seed explicitly, log the seed, assert on invariants not values |
| Real network or external service | Fails during deploy windows | Record/replay fixtures; no live endpoints in unit tests |
| Port and resource collisions | Fails only with `-n auto` | Ephemeral ports, per-worker temp dirs, per-worker databases |
| Fixed timeouts vs slow CI | Fails only on shared runners | Timeout budgets scaled by environment, not constants |

Notice that five of the seven are *determinism* problems, not timing problems. That is why clock control and scheduling control belong in the same toolbox: our [time mocking comparison](../2026-11-11-time-mocking-libraries-freezegun-time-machine-libfaketime/) covers the clock half, and [deterministic simulation testing](../2026-11-11-deterministic-simulation-testing-madsim-turmoil-loom-shuttle/) covers the interleaving half. If your flake is a genuine race rather than a test hygiene issue, simulation will find it in seconds while retries will hide it for years.

For the reporting layer — dashboards, JUnit ingestion, historical trends — our [self-hosted test coverage dashboards comparison](../2026-06-01-self-hosted-test-coverage-dashboards-reportportal-allure-codecov/) covers what to put behind the retry metric. And if the plumbing around pytest is where you spend your time, the [pytest plugins roundup](../2026-07-26-python-pytest-plugins-mock-cov-xdist-timeout-asyncio/) covers xdist, timeouts and the rest of the parallel-execution surface that produces half of these failures.

## Pitfalls that keep teams stuck

1. **Retrying without attributing.** `--reruns 3` on the whole suite, with no JUnit export, converts a visible flake into an invisible one. If you cannot chart it, do not enable it.
2. **Retry counts that creep.** Someone bumps `--reruns` from 2 to 5 to "stabilize" CI. Now a genuinely broken test needs five failures to be reported, and your suite takes 40% longer. Cap retries at 2-3 and treat increases as an incident.
3. **Quarantine without expiry.** Tracked in a spreadsheet nobody opens, the quarantined test outlives the feature it covered. Delete on expiry; re-add if still relevant.
4. **Reproducing with a different seed.** `pytest-randomly` prints the seed for a reason. Logging it and then re-running with a fresh seed means you are testing the RNG, not the bug.
5. **Assuming parallelism is safe.** Failures that appear only with `pytest-xdist -n 8` are almost always shared resources: a fixed test database name, a hardcoded port, a shared temp directory. Fix the isolation, do not reduce workers.
6. **Fixing symptoms with sleeps.** Replacing `assert eventually(...)` with `time.sleep(5)` trades a 1-in-100 flake for a permanent 5-second tax on every run, and it still fails on the slowest runner.

## FAQ

**How many retries are acceptable in CI?**
Two is the practical ceiling for a healthy suite, three for a large one with known third-party flakiness. Anything beyond that is a policy saying "we do not intend to fix this". More important than the number is the ratio: if more than 2-3% of tests need a retry, the retry budget is hiding a systemic isolation problem.

**Should flaky tests be deleted?**
Only after quarantine expiry with no owner. Deleting a flaky test immediately removes real coverage, and the bug it was catching — usually a race that also affects production — becomes invisible. Quarantine buys you time to fix the cause; deletion is the admission that the coverage was fake.

**Does pytest-randomly make failures non-reproducible?**
No — it makes them reproducible *if you keep the seed*. Each run prints `Using --randomly-seed=…`, and `pytest --randomly-seed=<value>` replays exactly. Store the seed in the CI log and in your failure report; without it, randomization is a liability rather than a diagnostic.

**Is retrying compatible with `pytest-xdist`?**
Yes, with `pytest-rerunfailures` 16+ and `pytest-xdist` 2.3+, and reruns are distributed across workers. Watch for the interaction with testmon: retried tests re-execute out of order, so a suite that depends on ordering will look more flaky under `-n auto --reruns 2` than under either alone.

**How do I detect flakiness in a test that only fails in production-like conditions?**
Local repetition will not find it. Instrument the code under test to log the seed, clock reading and ordering key at failure time, then replay with the same inputs. If the failure depends on thread interleaving rather than inputs, no amount of retrying helps — move that test to a deterministic simulation harness.

**What is a reasonable time budget for fixing flakes?**
Treat it as a fixed slice of engineering time, not an emergency: one afternoon per sprint, chosen by frequency-weighted impact (failures per week × minutes lost). Teams that wait for a "flaky test week" never do it, because there is always a feature deadline closer than the cleanup.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Flaky Tests in 2026: Detect, Quarantine and Kill Them for Good",
  "description": "A four-step workflow for flaky tests: detect with order randomization and repetition, localize with testmon, contain with measured retries in pytest, nextest and gotestsum, and fix the seven root causes.",
  "datePublished": "2026-11-11",
  "dateModified": "2026-11-11",
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
