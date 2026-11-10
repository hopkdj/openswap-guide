---
title: "Time Mocking in 2026: freezegun vs time-machine vs libfaketime"
date: "2026-11-11"
tags: ["testing", "time", "python", "developer-tools", "flaky-tests"]
draft: false
description: "Freeze, travel and tick the clock in Python, Ruby, .NET, JavaScript, PHP and Go. Real star counts, real code, and the six traps that make time-mocked tests lie to you."
---

# Time Mocking in 2026: freezegun vs time-machine vs libfaketime

Your suite passes at 11:58 PM and fails at 00:03 AM. Nothing changed in the code — the calendar moved. Any test that touches token expiry, trial periods, retry windows, billing cycles or "last 30 days" dashboards is a coin flip once the wall clock is an input you never controlled.

Freezing time is the cheapest reliability win in software, and it is also the easiest thing to get subtly wrong. Below is a field comparison of eight clock-control tools across seven languages, measured against the four properties that actually matter: **can it freeze, can it travel, can it tick, and does it survive threads, subprocesses and static binaries.**

## TL;DR / Quick Verdict

- **Python, new code:** use `time-machine`. It is roughly 10x faster than freezegun, patches at the C level, and handles `from datetime import datetime` imports that freezegun silently misses.
- **Python, existing suite:** `freezegun` still wins on familiarity and `tick=True`, but budget the 5-15% suite slowdown.
- **Anything that is not your own source tree** — a compiled binary, a subprocess, a cron script, a Docker entrypoint: `libfaketime` via `LD_PRELOAD`. Nothing else reaches across the process boundary.
- **Go:** `testing/synctest` (Go 1.25+) is the first credible answer; skip the fake-clock library for new tests.
- **Never** fake time at the database layer. Freeze the app clock and pass explicit timestamps, or you will debug `now()` divergence at 2 AM.

## Comparison at a glance

Star counts and last-push dates were pulled from the GitHub API on **2026-11-11**.

| Tool | Language | Mechanism | Freeze | Travel | Tick / advance | Crosses process boundary | Stars | Last push |
|---|---|---|---|---|---|---|---|---|
| freezegun | Python | Patches `datetime`/`time` in-process | ✅ | ✅ | ✅ (`tick=True`) | ❌ | 4,535 | 2025-08-19 |
| time-machine | Python | C-level patch of C API calls | ✅ | ✅ | ❌ (fixed offset) | ❌ | 1,025 | 2026-11-04 |
| Timecop | Ruby | Monkey-patches `Time`/`Date` | ✅ | ✅ | ✅ (`scale`) | ❌ | 3,424 | 2026-10-12 |
| libfaketime | C / any | `LD_PRELOAD` syscall shim | ✅ | ✅ (`-30d`) | ✅ (start offset + speed) | ✅ | 3,128 | 2026-11-10 |
| FakeTimeProvider | .NET | `TimeProvider` DI seam | ✅ | ✅ | ✅ (`Advance`) | ❌ | shipped in MS.Extensions | 2026-11 |
| sinon / vi fake timers | JavaScript | Replaces global timers | ✅ | ✅ | ✅ | ❌ | 9,753 | 2026-10-29 |
| Carbon `setTestNow` | PHP | Static test clock | ✅ | ✅ | ✅ | ❌ | 16,581 | 2026-11-09 |
| `testing/synctest` | Go | Virtual-time bubble | ✅ | ⚠️ relative only | ✅ (instant `Sleep`) | ❌ | stdlib | Go 1.25 |

## Decision matrix: match the tool to the constraint

| Your situation | Use | Why |
|---|---|---|
| Python service, 3,000-test suite, CI time is a cost line | `time-machine` | Per-test overhead is microseconds; no import-order bugs |
| Legacy Python suite already decorated with `@freeze_time` | `freezegun` | Migration risk outweighs the speedup; keep `tick=True` where needed |
| Testing a compiled binary, shell script or Docker entrypoint | `libfaketime` | Only tool that intercepts the process from outside |
| Go 1.25+ service with goroutines and timeouts | `testing/synctest` | Deterministic, instant sleeps, no library |
| .NET with DI everywhere | `FakeTimeProvider` | Injects through the real abstraction, no static patching |
| Ruby/Rails with ActiveSupport | `Timecop` | `travel_to` plays correctly with `Time.current` |
| Browser code with `setTimeout`/`setInterval` logic | vitest `vi.useFakeTimers()` | Advances timers and the system clock together |
| You need to reproduce a bug that only appears after 30 days of uptime | `libfaketime` with `FAKETIME_START_AFTER_SECONDS` | Deterministic replay without waiting |

## Python: freezegun vs time-machine

`freezegun` is the tool most teams reach for first. It patches the `datetime` and `time` modules for the duration of a block:

```python
from datetime import datetime, timezone
from freezegun import freeze_time

@freeze_time("2026-03-29 01:30:00")
def test_trial_expiry_email():
    issued = datetime.now(timezone.utc)
    # 2026-03-29 is a DST switch day in most of Europe
    assert issued.isoformat() == "2026-03-29T01:30:00+00:00"
```

Two features keep it in production suites. `tick=True` makes the clock advance in real time from the frozen point, which is what you want for retry/backoff logic that sleeps; and `as_kwarg` injects the frozen datetime as a fixture argument instead of patching globally.

The cost is real. freezegun walks module attributes looking for `datetime` references and rewraps them, so a suite of a few thousand frozen tests can spend minutes in patching alone. It also misses references captured by `from datetime import datetime` **before** the freezer starts, and anything held by a C extension.

`time-machine` fixes the mechanism rather than the ergonomics. It replaces the C-level function pointers behind `datetime.now()` and `time.time()`, so every reference — imported early, cached in a class attribute, or produced by a library you do not control — sees the fake clock:

```python
import time_machine
from datetime import datetime, timezone

@time_machine.travel("2026-03-29 01:30:00", tick=False)
def test_trial_expiry_email():
    assert datetime.now(timezone.utc).year == 2026

with time_machine.travel(datetime(2026, 12, 31, 23, 59, tzinfo=timezone.utc)):
    assert invoice.period_label() == "2026"
```

It is maintained actively (last push **2026-11-04**) while freezegun's last push was **2025-08-19**, and it does not have a `tick` mode — if your test needs the clock to move on its own, either keep freezegun or advance the clock explicitly between assertions.

**Verdict:** time-machine for new code, freezegun only where `tick=True` earns its keep. If you are already deep in date handling, our [Python datetime library comparison](../2026-08-10-python-datetime-libraries-arrow-pendulum-dateutil/) covers the parsing side that usually sits next to these tests.

## Ruby: Timecop

Timecop has been the Ruby answer for a decade and it still earns the spot, because Rails' `Time.current` respects it without extra wiring:

```ruby
require "timecop"

Timecop.freeze(Time.utc(2026, 3, 29, 1, 30)) do
  expect(subscription.expires_in).to eq(3_600)
end

Timecop.travel(30.days.from_now) do
  expect(TrialExpiryJob.perform_now).to eq(:expired)
end

# Accelerate: 1 real second becomes 1 simulated hour
Timecop.scale(3_600) do
  process_retry_queue
end
```

Two Ruby-specific traps. `Timecop.return` only unwinds the most recent freeze, so nested blocks in shared `before` hooks leak fake time into unrelated examples — always use the block form. And `Timecop.scale` interacts badly with `sleep` inside database transactions; keep scaled tests away from anything that opens a second connection.

## libfaketime: the only cross-process option

Everything above lives inside one runtime. `libfaketime` sits underneath, shimming `clock_gettime`, `gettimeofday`, `time` and `ftime` via `LD_PRELOAD`, which means it works on binaries you did not write:

```bash
# Run a compiled backup tool as if it were 30 days in the future
faketime '+30d' ./bin/retention-sweep --dry-run

# Freeze a Docker entrypoint at an exact instant, keeping monotonic clocks real
docker run --rm \
  -e LD_PRELOAD=/usr/lib/faketime/libfaketime.so.1 \
  -e FAKETIME="@2026-03-29 01:30:00" \
  -e FAKETIME_DONT_FAKE_MONOTONIC=1 \
  -v "$PWD/data:/data" \
  ghcr.io/example/backup:1.9 retention --check
```

`FAKETIME_START_AFTER_SECONDS` is the underrated flag: it starts the process at the real time and only shifts the clock after N seconds, which reproduces "bug appears after long uptime" reports with a two-line wrapper instead of a patched build. Pair it with `FAKETIME_TIMESTAMP_FILE` to drive the clock from a file and replay an entire incident window.

The limits are hard, not soft: `LD_PRELOAD` does nothing for **statically linked** binaries (musl static Go, Rust with `crt-static`, BusyBox), nothing for Java's `System.currentTimeMillis()` in a foreign process, and nothing for kernel timestamps like inode mtimes. If the tool you are testing is a static Go binary, libfaketime silently does nothing — verify with `faketime '+30d' date` before trusting a green test.

## .NET: TimeProvider and FakeTimeProvider

`TimeProvider` (since .NET 8) turned "what time is it" into a dependency, which is the correct design and makes testing trivial:

```csharp
using Microsoft.Extensions.Time.Testing;

var clock = new FakeTimeProvider(DateTimeOffset.Parse("2026-03-29T01:30:00Z"));
var service = new SubscriptionService(clock);

clock.Advance(TimeSpan.FromHours(1));
Assert.True(service.IsExpired);
```

```bash
dotnet add package Microsoft.Extensions.TimeProvider.Testing
```

The rule that matters: inject `TimeProvider` into your services and call `timeProvider.GetUtcNow()`. Code that still calls `DateTime.UtcNow` cannot be tested this way at all, so the refactor is the test strategy. `FakeTimeProvider` also fires `CreateTimer` callbacks when you advance, which makes timeout logic testable without `Thread.Sleep`.

## JavaScript: sinon and vitest fake timers

The JavaScript ecosystem solved this early; the failure mode is different — fake timers and promises deadlock each other:

```javascript
import { vi, beforeEach, afterEach, expect } from "vitest";

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date("2026-03-29T01:30:00Z"));
});

afterEach(() => {
  vi.useRealTimers();
});

it("expires the session after an hour", async () => {
  const session = new Session();
  vi.advanceTimersByTime(3_600_000);
  await vi.runAllTimersAsync();   // flush queued microtasks, not just timers
  expect(session.expired).toBe(true);
});
```

`sinon.useFakeTimers()` (9,753 stars, last push 2026-10-29) remains the standard outside vitest, with `shouldAdvanceTime` for the cases where you want the fake clock to drift forward automatically. The classic bug: a `setTimeout` resolves a promise, the test asserts before the microtask queue drains — `runAllTimersAsync()` or `clock.tickAsync()` exists exactly for that.

## PHP: Carbon::setTestNow

Laravel's `travelTo`/`freezeTime` helpers wrap Carbon, and Carbon's clock is global per process:

```php
use Carbon\Carbon;

public function test_invoice_becomes_overdue(): void
{
    Carbon::setTestNow(Carbon::parse('2026-03-29 01:30:00', 'UTC'));

    $invoice = Invoice::factory()->create(['due_at' => now()->subDay()]);

    $this->assertTrue($invoice->isOverdue());

    Carbon::setTestNow(); // always reset in tearDown
}
```

Carbon 3 (16,581 stars, last push 2026-11-09) tightened the diff semantics, so tests written against Carbon 2's `diffInDays` can change sign or rounding on upgrade. Call `Carbon::setTestNow()` in `tearDown()` — a leaked test clock poisons every later test in the same PHP process, and PHPUnit's process reuse makes that a real hazard.

## Go: testing/synctest versus clock injection

Go historically had no good answer, so teams injected a clock interface (`jonboulle/clockwork`, 730 stars; the original `benbjohnson/clock` is untouched since 2023-05-18). Go 1.25 shipped `testing/synctest`, which runs a function inside a *virtual time bubble* where every goroutine sees a fake clock and `time.Sleep` returns instantly:

```go
func TestLeaseExpiry(t *testing.T) {
	synctest.Run(func() {
		start := time.Now()
		lease := NewLease(time.Minute)

		time.Sleep(2 * time.Minute) // instant, virtual

		if !lease.Expired() {
			t.Fatalf("lease should be expired after %v", time.Since(start))
		}
	})
}
```

`synctest.Wait()` blocks until every goroutine in the bubble is durably blocked, which is how you assert "the retry loop is now sleeping" without racing. The constraint: all goroutines must be created inside the bubble, and the bubble must not block on real I/O. If your code spawns a background goroutine during `init()` or talks to a real socket, `synctest` will deadlock by design.

## Six traps that make time-mocked tests lie

1. **Import-time binding.** `from datetime import datetime` captured before the freeze can hold the real class. `time-machine` and `libfaketime` are immune; freezegun is not. Symptom: the test passes locally (import order differs) and fails in CI.
2. **Monotonic clocks are separate.** `time.monotonic()`, `performance.now()` and Go's runtime timers are not shifted by most freezers. Timeout logic tested against a frozen wall clock can still hang for real. Use `FAKETIME_DONT_FAKE_MONOTONIC=1` in libfaketime, and test timeouts with fake timers that own the monotonic source.
3. **The database has its own clock.** `NOW()`, `CURRENT_TIMESTAMP` and `statement_timestamp()` run in the server process. Freezing your app produces rows with real timestamps, and comparisons silently disagree. Pass timestamps explicitly from the application layer.
4. **Timezone data is not frozen.** You froze the instant, not the rules. DST transitions (2026-03-29 in Europe, 2026-11-01 in North America) need the real tz database and a `TZ` matrix — a test that hardcodes `+02:00` proves nothing about March.
5. **Static binaries ignore `LD_PRELOAD`.** Verified the hard way by anyone testing a musl-built Go binary. Check with `faketime '+1d' date` inside the same image before trusting results.
6. **Leaked clocks.** `Timecop.freeze` without a block, `Carbon::setTestNow()` without a reset, or `vi.useFakeTimers()` in a `beforeAll` — each one contaminates unrelated tests and produces failures that move when you reorder the suite. Our [snapshot testing comparison](../2026-09-16-snapshot-testing-insta-syrupy-vitest-jest-comparison/) covers the ordering-stability side of the same problem.

For production (not test) time, remember the opposite rule: servers should trust monotonic clocks and leap-second-aware daemons, which is exactly what our [NTP leap second handling guide](../2026-05-13-self-hosted-ntp-leap-second-handling-chrony-ntpsec-openntpd-guide/) covers.

## FAQ

**Does freezegun slow down large test suites?**
Yes, measurably. Patching walks module attributes on entry and exit, which costs roughly 0.1-1 ms per frozen test. On a 5,000-test suite that is minutes of pure overhead. `time-machine` patches C-level pointers instead and is typically reported an order of magnitude cheaper; migrate the hot test files first.

**Can I freeze time inside a Docker container without modifying the image?**
Yes, if the binary is dynamically linked. Mount `libfaketime.so.1`, set `LD_PRELOAD` and `FAKETIME`, and the process sees the fake clock. Statically linked binaries (musl static Go, `crt-static` Rust, BusyBox) ignore `LD_PRELOAD` entirely — there is no workaround short of rebuilding with an injectable clock.

**How do I test code that uses `asyncio.wait_for` or goroutine timeouts?**
Freezing wall-clock time will not help, because event loops use monotonic time. In Python, drive the loop with a patched event loop clock or assert on the timeout path with a fake monotonic source; in Go 1.25+, `testing/synctest` handles both wall clock and runtime timers inside the bubble, which is why it is the better tool there.

**Should I fake time in integration tests that hit Postgres or MySQL?**
Freeze the application clock, but never rely on it for database-side timestamps. Seeding rows with explicit `created_at` values and passing `now` from the app is the only approach that stays honest. If a query uses `NOW()`, either refactor it to accept a parameter or accept that the test asserts on a different clock than production.

**What is the right tool for a polyglot monorepo?**
Use per-language in-process fakes for unit tests (`time-machine`, `Timecop`, `FakeTimeProvider`, vitest timers) and reserve `libfaketime` for end-to-end runs where the unit under test is a binary or entrypoint script. Trying to force one tool across all languages ends with either static-patch gaps or `LD_PRELOAD` blind spots.

**Is a frozen clock enough to catch DST bugs?**
No. Freezing pins an instant; DST bugs live in the transition rules. Run the same test file against at least two `TZ` values around a transition date, and keep the tz database updated in CI images — an outdated `tzdata` is a production incident waiting for the next government decision.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Time Mocking in 2026: freezegun vs time-machine vs libfaketime",
  "description": "Cross-language comparison of clock-control tools for tests: freezegun, time-machine, Timecop, libfaketime, FakeTimeProvider, sinon fake timers, Carbon setTestNow and Go testing/synctest, with real star counts and the traps that make time-mocked tests lie.",
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
