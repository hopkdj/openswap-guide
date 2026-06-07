---
title: "Self-Hosted JTAG/SWD Remote Debug Servers: OpenOCD vs pyOCD vs probe-rs"
date: "2026-06-07"
tags: ["embedded", "debugging", "jtag", "swd", "openocd", "arm", "microcontroller", "self-hosted"]
draft: false
---

Debugging embedded systems has traditionally meant connecting a hardware debug probe directly to your development machine via USB. But as embedded development teams grow and CI/CD pipelines extend to hardware-in-the-loop testing, the need for remote, network-accessible debug servers becomes critical. Three major open-source projects — **OpenOCD**, **pyOCD**, and **probe-rs** — each provide GDB server functionality over TCP, enabling remote debugging workflows where the debug probe is physically connected to one machine while developers connect from anywhere on the network.

## Why Self-Host a Remote Debug Server?

In a typical embedded development workflow, each developer plugs a physical debug probe into their laptop. This works for solo projects but breaks down at team scale. Hardware-in-the-loop (HIL) test rigs need programmatic flash and debug access. CI/CD pipelines that build firmware need to flash it onto physical devices and run test suites. Remote teams need access to shared development boards in a lab.

A self-hosted debug server solves all of these problems. The debug probe connects to a server (a Raspberry Pi, a dedicated Linux box, or a test rack machine) that runs the GDB server. Developers connect their GDB clients over the network, flash firmware, set breakpoints, and inspect registers — all as if the probe were plugged into their local machine. For CI/CD, build scripts can programmatically flash and test firmware on physical hardware without human intervention.

Security is another benefit. By centralizing debug access through a server, you can implement authentication, access logging, and session management — something impossible with a USB probe passed around the office. For teams working with proprietary firmware or secure elements, this audit trail is essential.

If you're deploying firmware to IoT devices at scale, see our [IoT firmware OTA update guide](../2026-05-07-self-hosted-firmware-ota-update-management-hawkbit-rauc-swupdate-guide/). For managing fleets of IoT devices, check our [IoT device management comparison](../2026-05-09-self-hosted-iot-device-management-kaa-vs-devicehive-vs-mainflux-guide/). And for building the firmware itself, our [ESPHome vs Tasmota vs ESPurna guide](../2026-05-09-self-hosted-iot-firmware-platforms-esphome-vs-tasmota-vs-espurna/) covers popular IoT firmware platforms.

## Comparison: OpenOCD vs pyOCD vs probe-rs

| Feature | OpenOCD | pyOCD | probe-rs |
|---------|---------|-------|----------|
| **Language** | C | Python | Rust |
| **GitHub Stars** | ~2,200 | ~1,400 | ~2,800 |
| **First Release** | 2005 | 2015 | 2020 |
| **Target Architectures** | ARM, RISC-V, MIPS, Xtensa, ARC | ARM Cortex-M only | ARM, RISC-V |
| **Debug Probes** | 50+ adapters | CMSIS-DAP, ST-Link, J-Link | CMSIS-DAP, ST-Link, J-Link, FTDI |
| **GDB Server** | Yes (TCP port 3333) | Yes (TCP port 3333) | Yes (TCP port 3333) |
| **Flash Programming** | Yes (all targets) | Yes (Cortex-M) | Yes |
| **Semihosting** | Yes | Yes | Yes |
| **RTT Support** | Via scripting | No (use SEGGER tools) | Yes (native) |
| **SWO Trace** | Yes | Via external tools | Planned |
| **RTOS Awareness** | Yes (FreeRTOS, Zephyr, etc.) | Via plugins | Yes (built-in detection) |
| **Scripting API** | Tcl | Python | Rust / Python bindings |
| **Configuration** | Script files (.cfg) | Python API or YAML | YAML or programmatic |
| **Docker Support** | Official Dockerfile | Community images | Community images |

### OpenOCD

OpenOCD (Open On-Chip Debugger) is the granddaddy of open-source debug servers, first released in 2005. It supports the widest range of target architectures — ARM (Cortex-M, Cortex-A, Cortex-R), RISC-V, MIPS, Xtensa (ESP32), and ARC — and an enormous catalog of debug adapters including FTDI-based probes, CMSIS-DAP, ST-Link, J-Link, and dozens of vendor-specific interfaces. If a debug probe exists, OpenOCD probably supports it.

OpenOCD's architecture uses Tcl as its configuration and scripting language. Board and target configuration files describe the JTAG/SWD chain, flash layout, and memory regions. This Tcl foundation gives OpenOCD tremendous flexibility — you can script complex multi-step flash sequences, automate testing, and even create custom debug commands — but the learning curve is steep compared to the programmatic APIs of pyOCD and probe-rs.

```bash
# Install OpenOCD
sudo apt install openocd

# Start GDB server for an STM32 target
openocd -f interface/stlink.cfg -f target/stm32f4x.cfg

# Connect with GDB
arm-none-eabi-gdb -ex "target extended-remote localhost:3333" firmware.elf
```

```yaml
# Docker Compose for a remote debug server
version: "3.8"
services:
  openocd:
    image: ghcr.io/openocd-org/openocd:latest
    privileged: true
    devices:
      - /dev/bus/usb:/dev/bus/usb
    ports:
      - "3333:3333"
      - "4444:4444"
      - "6666:6666"
    command:
      - "-f"
      - "interface/stlink.cfg"
      - "-f"
      - "target/stm32f4x.cfg"
    restart: unless-stopped
```

OpenOCD exposes three TCP ports: 3333 for GDB, 4444 for the Tcl telnet console, and 6666 for the Tcl server. The telnet port allows you to run arbitrary OpenOCD commands remotely — flash programming, register inspection, memory dumps — without needing a GDB client. This is particularly useful for CI/CD scripts:

```bash
# Flash firmware via OpenOCD telnet
echo "program firmware.elf verify reset exit" | nc localhost 4444
```

### pyOCD

pyOCD takes a radically different approach: rather than Tcl scripts, everything is Python. It was originally developed by Arm as part of the Mbed OS ecosystem and supports Arm Cortex-M microcontrollers exclusively. This narrower focus means pyOCD provides a cleaner, more Pythonic experience for Arm Cortex-M development — but you cannot use it for RISC-V, MIPS, or other architectures.

pyOCD's killer feature is its Python API, which makes programmatic debugging and flash programming trivial. CI/CD pipelines, automated test frameworks, and hardware-in-the-loop systems can control the debug probe directly from Python without shelling out to external commands:

```python
from pyocd.core.helpers import ConnectHelper
from pyocd.flash.file_programmer import FileProgrammer

# Connect to target
with ConnectHelper.session_with_chosen_probe() as session:
    board = session.board
    target = board.target

    # Flash firmware
    programmer = FileProgrammer(session)
    programmer.program("firmware.hex")

    # Read memory
    value = target.read32(0x20000000)
    print(f"Stack pointer: {hex(value)}")

    # Reset and run
    target.reset_and_halt()
    target.resume()
```

```bash
# Install pyOCD
pip install pyocd

# List connected probes
pyocd list

# Start GDB server
pyocd gdbserver --target stm32f407vg

# Flash firmware from command line
pyocd flash --target stm32f407vg firmware.hex
```

```yaml
# Docker Compose for pyOCD remote debug server
version: "3.8"
services:
  pyocd:
    image: pyocd/pyocd:latest
    privileged: true
    devices:
      - /dev/bus/usb:/dev/bus/usb
    ports:
      - "3333:3333"
    command:
      - "gdbserver"
      - "--target=stm32f407vg"
      - "--port=3333"
    restart: unless-stopped
```

pyOCD also supports CMSIS-Pack device descriptions, meaning it automatically discovers flash algorithms and memory layouts from the silicon vendor's pack files. For teams working exclusively with Arm Cortex-M devices, pyOCD's tighter integration with the Arm ecosystem is a significant productivity boost.

### probe-rs

probe-rs is the newest entrant, written in Rust with a focus on speed, safety, and modern tooling. It supports both Arm and RISC-V targets and can use CMSIS-DAP, ST-Link, and J-Link probes. Despite being the youngest project, probe-rs has quickly gained traction due to its exceptional performance — flash programming is 2-5x faster than OpenOCD for many targets — and its built-in RTT (Real-Time Transfer) support for high-speed logging without a separate debug channel.

probe-rs is more than just a GDB server. It includes `cargo-flash` and `cargo-embed` for Rust embedded development, a `probe-rs-cli` tool for command-line operations, and a Python package (`probe-rs-python`) that exposes the full debugging API. The project also powers the debugger backend for Visual Studio Code's `cortex-debug` and `probe-rs-debugger` extensions.

```bash
# Install probe-rs CLI
cargo install probe-rs-tools

# List connected probes
probe-rs list

# Flash firmware (fast)
probe-rs download --chip STM32F407VG firmware.elf

# Start GDB server
probe-rs gdb --chip STM32F407VG

# Run with RTT logging
probe-rs run --chip STM32F407VG firmware.elf
```

```yaml
# Docker Compose for probe-rs remote debug server
version: "3.8"
services:
  probe-rs:
    image: ghcr.io/probe-rs/probe-rs:latest
    privileged: true
    devices:
      - /dev/bus/usb:/dev/bus/usb
    ports:
      - "3333:3333"
    command:
      - "gdb"
      - "--chip=STM32F407VG"
    restart: unless-stopped
```

## Choosing the Right Debug Server

**Choose OpenOCD** for maximum hardware and architecture coverage. If your lab has a mix of ARM, RISC-V, MIPS, and Xtensa targets connected through various debug probes, OpenOCD is the only option that supports everything. Its Tcl scripting, while verbose, gives you unmatched flexibility for complex debugging scenarios.

**Choose pyOCD** if your development is exclusively ARM Cortex-M and you want seamless Python integration. The Python API makes CI/CD automation straightforward, and CMSIS-Pack support means you spend less time writing target configuration files. It's the most polished experience for Arm-focused teams.

**Choose probe-rs** for the best raw performance and if you're doing Rust embedded development. Flash speeds are industry-leading, native RTT support eliminates the need for separate logging channels, and the Rust ecosystem integration (cargo-flash, cargo-embed, defmt) makes it the natural choice for Rust firmware projects. Its VS Code extension support also provides the best IDE debugging experience.

## FAQ

### Can I use these debug servers over the internet?

Technically yes, but it's not recommended without a VPN or SSH tunnel. GDB protocol traffic is unencrypted and unauthenticated — anyone who can connect to port 3333 can read memory, set breakpoints, and flash firmware. Always place debug servers behind a VPN (WireGuard, Tailscale) or use SSH port forwarding: `ssh -L 3333:localhost:3333 debug-server.example.com`.

### How do I share one debug probe among multiple developers?

Run the GDB server on a dedicated machine (a Raspberry Pi 4 works great for this). Multiple developers can connect their GDB clients to the same server, but only one can control execution at a time — GDB's remote protocol doesn't support concurrent sessions. For shared lab setups, consider using a test automation framework that queues debug access requests.

### Do I need a physical debug probe for each target?

Yes, each microcontroller needs its own physical debug connection. For multi-target test racks, use a USB hub with individual CMSIS-DAP or ST-Link probes, or invest in a multi-channel debug probe like the SEGGER J-Trace or a JTAG multiplexer. Alternatively, run multiple OpenOCD instances on different ports, each connected to a different probe.

### Can these tools be used in GitHub Actions or GitLab CI?

Absolutely. All three can run in Docker containers in CI pipelines, assuming the runner has USB passthrough or the probe is connected to a networked debug server. probe-rs and pyOCD are particularly CI-friendly because they support programmatic flash and test operations via CLI or API without interactive prompts.

### What about Black Magic Probe?

Black Magic Probe (BMP) is a firmware project that turns a standard development board (like an STM32 Blue Pill or a Raspberry Pi Pico) into a debug probe with a built-in GDB server — no additional software needed on the host. It's an excellent option for portable debugging, but it lacks the multi-architecture support and scripting capabilities of OpenOCD, pyOCD, or probe-rs. BMP shines as a field debugging tool; the three tools compared here are better suited for lab server deployments.

---

**💰 Want to test your market judgment? I use [Polymarket](https://polymarket.com/?r=fc8a0) for prediction market trading — the world's largest prediction market platform, where you can bet on everything from election outcomes to tech regulation timelines. Unlike gambling, this is a real information market: the more you know, the better your odds. I've earned quite a bit predicting tech-related events. Sign up with my referral link: [Polymarket.com](https://polymarket.com/?r=fc8a0)**

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted JTAG/SWD Remote Debug Servers: OpenOCD vs pyOCD vs probe-rs",
  "description": "Compare three open-source remote debug servers — OpenOCD (C/Tcl), pyOCD (Python), and probe-rs (Rust) — for self-hosting JTAG and SWD debugging of ARM, RISC-V, and other microcontrollers over TCP. Includes Docker Compose setups and CI/CD integration patterns.",
  "datePublished": "2026-06-07",
  "dateModified": "2026-06-07",
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