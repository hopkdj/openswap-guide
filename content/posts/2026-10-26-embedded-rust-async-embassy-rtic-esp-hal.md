---
title: "Embassy vs RTIC vs esp-hal in 2026: Which Async Runtime Should Run Your Embedded Rust?"
date: "2026-10-26"
tags: ["rust", "embedded", "async", "microcontrollers", "firmware"]
description: "Embassy, RTIC and esp-hal compared with real crate versions, working firmware examples, scheduling models and the failure modes that bite in production."
draft: false
---

Firmware written with a bare superloop plus a handful of interrupt handlers has a predictable failure mode: at 40 MHz everything works, and at 400 kHz of event traffic two handlers start corrupting the same state machine. The classic fix — a real-time operating system — costs you a scheduler tick, a heap, and a debugger workflow that no longer matches the silicon. Rust's answer is different: keep the single stack, drop the RTOS, and get concurrency from `async` plus compile-time priority analysis.

Three projects define that answer in 2026, and they disagree fundamentally about how tasks should be scheduled. **Embassy** runs an executor you drive from interrupts. **RTIC** generates a priority-based preemptive scheduler at compile time. **esp-hal** is a hardware abstraction layer that *hosts* an executor rather than being one. Picking wrong means rewriting your task model in month three.

## TL;DR: Quick Verdict

**Choose Embassy** for new projects on Cortex-M, RISC-V, or ESP32 where you want `async`/`await`, a large driver ecosystem, and one shared stack. **Choose RTIC** when you need hard real-time guarantees, provable worst-case execution time, and a scheduler that refuses to compile if two tasks share a resource without mediation. **Choose esp-hal** if you are on ESP32 silicon and want the vendor-maintained HAL that integrates with the Embassy executor rather than fighting it. They are not mutually exclusive: esp-hal + Embassy is the standard ESP32 stack, and RTIC now supports `async` tasks too.

## Side-by-Side Comparison

| Dimension | Embassy | RTIC | esp-hal |
|---|---|---|---|
| GitHub stars | **10,015** | 2,421 | 2,163 |
| Last commit | 2026-10-25 | 2026-10-21 | 2026-10-23 |
| Current version | `embassy-executor` **0.10.0** | `rtic` **2.4.0** | **1.2.0** |
| License | MIT / Apache-2.0 | MIT / Apache-2.0 | MIT / Apache-2.0 |
| Concurrency model | Cooperative executor, interrupt-driven wakeups | Priority-based preemptive scheduler (compile-time) | HAL + driver layer; runs Embassy executor |
| Supported silicon | Cortex-M, RISC-V, AVR, ESP32 | Cortex-M, RISC-V (MSP430 in progress upstream) | ESP32 family only (esp-hal 1.x) |
| Resource protection | `Mutex` / `Signal` from `embassy-sync` | Compile-time resource ceilings (SRP) | Peripheral ownership + `embassy-sync` |
| Heap required | No | No | No |
| Task stacks | One shared stack for all `#[embassy_executor::task]` | One stack per run-to-completion task, one for async tasks | Inherited from executor |
| Time driver | `embassy-time` (tickless) | `rtic-monotonics` | `embassy-time` on esp-hal timers |
| Debugging | `defmt` + `probe-rs` | `defmt` + `probe-rs` | `defmt` + `probe-rs` (ESP32 needs its own flash tooling) |

Star counts and commit dates come from the GitHub API at publish time; crate versions from each project's `Cargo.toml`.

## Decision Matrix: Pick in 10 Seconds

| Your situation | Recommended stack | Why |
|---|---|---|
| New Cortex-M project, mixed drivers, moderate timing demands | **Embassy** | Largest driver ecosystem (`embassy-stm32`, `embassy-nrf`, `embassy-rp`), one stack, tickless timers |
| Motor control, PWM loops, anything with WCET analysis | **RTIC** | Static priority scheduler with provable bounds, no dynamic dispatch |
| ESP32 / ESP32-C6 / ESP32-H2 firmware | **esp-hal + Embassy** | Vendor HAL with real async peripherals, `esp-rtos` provides the tick |
| Battery device that sleeps 99 % of the time | **Embassy** | `embassy-time` keeps timers running in low-power modes |
| Team already fluent in RTOS interrupt priorities | **RTIC** | The programming model maps directly onto priority ceilings |
| You need `std`-style blocking drivers on ESP32 | **esp-hal** (blocking APIs) | Every async API has a blocking counterpart |
| Hard deadline measured in microseconds | **RTIC** | Interrupt latency is bounded by hardware; the scheduler adds no queue |

## Embassy: The Executor You Build Around

Embassy's model is simple to state and surprising in practice: tasks are `async fn`s compiled into a static task pool, all sharing **one** stack. Wakeups come from interrupts; the executor only runs when something is ready. There is no timer tick, no heap, and no preemption between tasks.

Real firmware from Embassy's own STM32 examples:

```rust
#![no_std]
#![no_main]

use defmt::*;
use defmt_rtt as _;
use embassy_executor::Spawner;
use embassy_stm32::gpio::{Level, Output, Speed};
use embassy_time::Timer;
use panic_probe as _;

#[embassy_executor::main]
async fn main(_spawner: Spawner) {
    let p = embassy_stm32::init(Default::default());
    info!("Hello World!");

    let mut led = Output::new(p.PA5, Level::High, Speed::Low);

    loop {
        led.set_high();
        Timer::after_millis(500).await;
        led.set_low();
        Timer::after_millis(500).await;
    }
}
```

Adding a second task is a macro and a spawn call, and the dependency is a single line in `Cargo.toml`:

```toml
[dependencies]
embassy-executor = { version = "0.10", features = ["arch-cortex-m", "executor-thread", "task-arena-size-32768"] }
embassy-time = { version = "0.5", features = ["tick-hz-32_768"] }
```

```rust
#[embassy_executor::task]
async fn sensor_loop(mut adc: AdcChannel) {
    loop {
        let sample = adc.read().await;
        defmt::info!("adc={}", sample);
        Timer::after_millis(10).await;
    }
}

// inside main:
spawner.spawn(sensor_loop(adc_channel).unwrap()).unwrap();
```

`task-arena-size-32768` is not a tuning knob you can ignore. Tasks are stored in a fixed arena, and `spawn` returns `Err` when it is full — a runtime failure that only shows up when every task is started. Size it deliberately and check every `spawn` result.

**Where Embassy hurts:** cooperative scheduling means a task that never awaits blocks everything. Long computations must be chunked with `yield_now()` or moved into an interrupt. Because all tasks share one stack, a deeply recursive function in any task raises stack pressure for all of them.

## RTIC: Compile-Time Priority, Provable Deadlines

RTIC 2.x generates a scheduler: every `#[task]` gets a static priority derived from its interrupt binding, and shared resources are protected by the Stack Resource Policy, which makes priority inversion structurally impossible. If two tasks share a resource without a proper ceiling, the build fails — not the field unit.

Real example from RTIC's `stm32f1_bluepill_blinky` (RTIC 2.4 with `rtic-monotonics`):

```rust
#![no_std]
#![no_main]

use rtic::app;
use rtic_monotonics::systick::prelude::*;

systick_monotonic!(Mono, 1000);

#[app(device = stm32f1xx_hal::pac, peripherals = true, dispatchers = [SPI1])]
mod app {
    use super::*;

    #[shared]
    struct Shared {}

    #[local]
    struct Local {
        led: PC13<Output<PushPull>>,
        state: bool,
    }

    #[init]
    fn init(cx: init::Context) -> (Shared, Local) {
        Mono::start(cx.core.SYST, 36_000_000);
        let mut gpioc = cx.device.GPIOC.split();
        let led = gpioc.pc13.into_push_pull_output_with_state(&mut gpioc.crh, PinState::Low);
        blink::spawn().ok();
        (Shared {}, Local { led, state: false })
    }

    #[task(local = [led, state])]
    async fn blink(cx: blink::Context) {
        loop {
            // toggle LED
            Mono::delay(1000.millis()).await;
        }
    }
}
```

Two details matter. `dispatchers = [SPI1]` reserves a hardware interrupt for software tasks — RTIC cannot invent priorities the silicon does not have. And `Mono::start(...)` with the actual core clock frequency is mandatory: a wrong value silently stretches every delay proportionally.

`#[shared]` resources are the heart of the model. Access requires a lock whose critical section is computed from priority ceilings, so a low-priority task cannot be preempted while holding a shared resource by anything that also needs it. That is what makes WCET analysis tractable: the number of preemption points is known at compile time.

**Where RTIC hurts:** the memory model is stricter than newcomers expect — each run-to-completion task has its own stack, so RAM adds up fast on a 20 KB part. And the ecosystem is smaller than Embassy's; you will often pair RTIC with `stm32f1xx-hal`-style HALs instead of a unified async driver stack.

## esp-hal: The Vendor HAL That Happens to Be Async

esp-hal 1.2.0 is not a scheduling framework — it is the Espressif-maintained HAL, and it ships first-class `async` peripheral drivers plus `#[esp_hal::main]`, which wires the Embassy executor to the chip's timer group.

Real example from `examples/async/embassy_hello_world`:

```rust
#![no_std]
#![no_main]

use embassy_executor::Spawner;
use embassy_time::{Duration, Timer};
use esp_hal::timer::timg::TimerGroup;
use esp_backtrace as _;

#[embassy_executor::task]
async fn run() {
    loop {
        esp_println::println!("Hello world from embassy!");
        Timer::after(Duration::from_millis(1_000)).await;
    }
}

#[esp_hal::main]
async fn main(spawner: Spawner) {
    let peripherals = esp_hal::init(esp_hal::Config::default());
    let timg0 = TimerGroup::new(peripherals.TIMG0);
    esp_rtos::start(timg0.timer0);

    spawner.spawn(run().unwrap());

    loop {
        Timer::after(Duration::from_millis(5_000)).await;
    }
}
```

```toml
[dependencies]
esp-hal = { version = "1.2", features = ["esp32c6"] }
esp-rtos = "0.3"
embassy-executor = { version = "0.10", features = ["arch-riscv32", "executor-thread"] }
embassy-time = "0.5"
```

`esp_rtos::start(timg0.timer0)` is the line people forget. Without it the executor has no time source: `Timer::after` completes immediately or never, depending on the chip. The ESP32-C6 and H2 parts are RISC-V, so the `arch-riscv32` executor feature is required — building with `arch-cortex-m` produces typically cryptic linker errors about missing interrupt vectors.

**Where esp-hal hurts:** it is single-vendor by design. If your product line mixes STM32 and ESP32, you maintain two driver stacks and two sets of `cfg` gates. Its 1.x API also moved fast through 2026; pin exact versions and read the migration notes between minors.

## Memory and Latency: What Actually Differs

The marketing difference is "async vs RTOS". The engineering difference is where memory goes and where latency comes from.

**Stack.** Embassy allocates one stack for all tasks; the cost is bounded regardless of task count, and the risk is a single deep call path. RTIC allocates one stack per run-to-completion task; predictable but linear in task count. On a 32 KB part with six tasks, this is the difference between fitting and not fitting.

**Latency.** RTIC's interrupt path is hardware priority plus a short generated trampoline — the scheduler never queues. Embassy's wake path goes through the executor's ready queue, which is fast but cooperative: a higher-priority *logical* task cannot preempt a running one. If you need sub-10 µs response to an event, bind an interrupt or use RTIC.

**Power.** Embassy's tickless time driver is the strongest of the three for battery devices: no periodic wakeup means the core stays asleep until the next deadline. RTIC with `rtic-monotonics` on SysTick wakes every tick, which is fine at 1 kHz and wasteful at 32 kHz.

**Measure it yourself.** Do not trust latency claims from any blog, including this one. Instrument with a GPIO toggle and a logic analyzer or scope:

```rust
// start of interrupt handler
let _ = gpio.set_high();   // marker channel
// ... work
let _ = gpio.set_low();
```

Comparing rising-edge to rising-edge across firmware variants gives you real numbers on your silicon, your clock tree, and your flash wait states.

## Pitfalls That Cost Debugging Days

**Wrong clock frequency in the monotonic start.** `Mono::start(cx.core.SYST, 36_000_000)` with a 72 MHz clock halves every delay. Symptom: everything works, timings are silently 2× off.

**Forgetting `esp_rtos::start()`.** `Timer::after` misbehaves in ways that look like a driver bug. Start the tick before spawning anything that awaits time.

**Arena overflow in Embassy.** `spawn` returns `Err(SpawnError::NoCapacity)` and the task simply never runs. Log it; do not `unwrap()` into a silent no-boot.

**Blocking inside an async task.** `embedded-hal` blocking calls (delay loops, blocking SPI transfers) stall every other task in the executor. Use the async driver variants, or run blocking work in a dedicated interrupt.

**Mixing interrupt priorities blindly.** On Cortex-M, an interrupt that calls into the executor must have a priority numerically greater than (lower urgency than) the executor's own — otherwise you get a `HardFault` from the NVIC, not a compiler error.

**RTIC resource ceiling errors interpreted as compiler bugs.** "Resource conflict" build failures are the scheduler telling you a shared resource is reachable from two priorities without a lock. The fix is a `#[shared]` resource or a `lock()`, never `unsafe`.

**Flash and bootloader mismatches on ESP32.** `espflash` vs `probe-rs` vs vendor tooling differ per chip and per bootloader version; pick one per project and document it, because reflashing mid-debug with the wrong tool can brick a dev board's partition table.

**Not pinning versions.** All three projects shipped breaking minor releases during 2026. `version = "0.10"` on embassy-executor is fine; `version = "*"` in firmware is not.

## Which Stack to Start With Tomorrow

If you have a Cortex-M board on your desk: `cargo generate` an Embassy project, get `defmt` + `probe-rs` working, and add one async task per peripheral. If your product has a deadline contract, port the same firmware to RTIC and compare stacks and latency on a scope — the exercise takes an afternoon and settles the argument permanently. If you are on ESP32, use esp-hal with the Embassy executor and stop reading comparisons; the vendor HAL is the only viable driver layer anyway.

For adjacent decisions, our [embedded RTOS comparison](../2026-09-23-embedded-rtos-zephyr-nuttx-riot-os-comparison/) covers the C-side alternatives, the [embedded Rust HAL comparison](../2026-10-15-rust-embedded-hal-esp-hal-rp-hal-comparison/) goes deeper on peripheral abstractions, and [embedded key-value engines for Rust](../2026-09-18-rust-embedded-key-value-engines-sled-redb-fjall/) covers the storage layer you will eventually need for configuration and logs.

## FAQ

**Is Embassy an RTOS?**
No. Embassy is an executor plus driver crates. There is no preemptive scheduler, no periodic tick, and no dynamic task creation — tasks are compiled into a static arena. It solves concurrency, not scheduling guarantees.

**Can RTIC and Embassy be used together?**
Yes, and it is a common pattern: RTIC can run Embassy's executor as a low-priority task, letting hard real-time interrupts preempt cooperative async work. RTIC 2.4's own `async fn` tasks also require a monotonic time source, so the boundary is well defined.

**Which one has better ESP32 support?**
esp-hal. It is maintained by Espressif, tracks new chips (C6, H2, P4) quickly, and provides both blocking and async drivers. Embassy's `embassy-stm32`/`embassy-nrf` crates do not target ESP32 at all; the ESP32 path is esp-hal hosting the Embassy executor.

**Do I need a heap for async firmware?**
No, in all three cases. Embassy tasks live in a static arena sized at compile time, RTIC allocates per-task stacks statically, and esp-hal's drivers own peripherals through the type system. Avoid `alloc` if you can — fragmentation on a 512 KB part is a support burden.

**How do I debug without `printf`?**
`defmt` plus `probe-rs` (`probe-rs run --chip <chip>`) gives deferred formatting over RTT with minimal flash cost. On ESP32, `esp-println` over the built-in USB-serial-JTAG works with the same `defmt` macros.

**What about `no_std` `async` on AVR or MSP430?**
Embassy has AVR support and RTIC has community ports, but driver coverage is thin. For 8-bit parts, a superloop plus interrupts remains the pragmatic choice; async buys you little when RAM is measured in kilobytes.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Embassy vs RTIC vs esp-hal in 2026: Which Async Runtime Should Run Your Embedded Rust?",
  "description": "Embassy, RTIC and esp-hal compared with real crate versions, working firmware examples, scheduling models and production failure modes.",
  "datePublished": "2026-10-26",
  "dateModified": "2026-10-26",
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
