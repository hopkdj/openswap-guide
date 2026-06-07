---
title: "Self-Hosted GPIO Web Control Dashboards: pigpiod vs gpiozero vs libgpiod"
date: "2026-06-07"
tags: ["gpio", "raspberry-pi", "embedded", "iot", "hardware-control", "home-automation", "self-hosted"]
draft: false
---

General Purpose Input/Output (GPIO) pins are the bridge between software and the physical world. Whether you're controlling relays, reading sensors, driving motors, or blinking LEDs, your application needs a reliable way to talk to GPIO hardware. When that control needs to happen over a network — a web dashboard toggling lights, a monitoring system reading temperature sensors, or a test automation framework manipulating hardware — you need a GPIO server that exposes pins through a network-accessible API. Three Linux-based open-source frameworks — **pigpiod**, **gpiozero**, and **libgpiod** — each take a different approach to this challenge.

## Why Self-Host GPIO Control Over the Network?

The most obvious use case is home automation. A Raspberry Pi tucked away in a closet controls relays for lights, reads door sensors, and monitors temperature — but you want to access and control everything from a web dashboard or mobile app. Running a GPIO server on the Pi and connecting to it from a separate web application server is a clean architecture that separates hardware control from user interface logic.

For industrial and lab automation, networked GPIO control enables centralized management of distributed I/O. A test rack might have five Raspberry Pis, each connected to different sensors and actuators. Rather than SSH'ing into each one individually, a central controller communicates with all of them through their GPIO APIs — reading sensor values, toggling relays, and coordinating multi-device test sequences programmatically.

Remote GPIO also enables hardware-in-the-loop (HIL) testing at scale. CI/CD pipelines that test firmware on physical hardware need to control power relays, reset lines, and signal inputs. A self-hosted GPIO server exposes these control surfaces as REST or socket APIs that any programming language can consume.

For getting started with home automation on microcontrollers, see our [ESPHome vs Tasmota vs ESPurna comparison](../2026-05-09-self-hosted-iot-firmware-platforms-esphome-vs-tasmota-vs-espurna/). For a broader IoT platform perspective, our [IoT device management guide](../2026-05-09-self-hosted-iot-device-management-kaa-vs-devicehive-vs-mainflux-guide/) covers platforms for managing fleets of connected devices.

## Comparison: pigpiod vs gpiozero vs libgpiod

| Feature | pigpiod | gpiozero | libgpiod |
|---------|---------|----------|----------|
| **Language** | C (daemon), Python (client) | Python | C (library), Python (bindings) |
| **Architecture** | Client-server daemon | Direct hardware access | Kernel character device |
| **Remote GPIO** | Yes (built-in TCP) | Yes (via pigpio backend) | Yes (via gpioset/gpiofind over SSH) |
| **Raspberry Pi Support** | Excellent (native) | Excellent (RPi.GPIO or pigpio) | Good (via kernel drivers) |
| **Non-RPi Boards** | Limited | Supported via pin factories | Excellent (any Linux GPIO) |
| **PWM** | Hardware & software PWM | Hardware PWM only | No (use PWM sysfs) |
| **I2C/SPI** | Yes (built-in) | Via separate libraries | No (use kernel drivers) |
| **WebSocket API** | Yes (pigpio-wifi) | No (build your own) | No |
| **Waveform Generation** | Yes (DMA-based) | No | No |
| **Callback/Interrupt** | Yes (alert system) | Yes (event-driven API) | Yes (line events) |
| **Python API** | Comprehensive | Most Pythonic | Via python3-libgpiod |
| **Docker Support** | Yes (privileged) | Yes (privileged) | Yes (needs /dev/gpiochip) |
| **Active Maintenance** | Yes | Yes | Yes (kernel project) |

### pigpiod

pigpiod is a daemon-based GPIO server that provides network-accessible GPIO control via a TCP socket. Originally developed for Raspberry Pi by Joan (the same developer behind the popular pigpio C library), pigpiod runs as a background service and exposes a simple text-based protocol on port 8888. Any language that can open a TCP socket — Python, JavaScript, C, Go, even curl — can control GPIO pins remotely.

The killer feature of pigpiod is its DMA-based waveform generation. For applications that need precise timing — servo control, WS2812 LED strips, IR remote transmission — pigpio uses the Pi's DMA controller to generate waveforms with microsecond accuracy without CPU involvement. No other GPIO library offers this level of hardware-level timing precision.

```bash
# Install and run pigpiod
sudo apt install pigpio
sudo systemctl enable pigpiod
sudo systemctl start pigpiod

# Control GPIO from Python (local)
python3 -c "
import pigpio
pi = pigpio.pi()
pi.set_mode(17, pigpio.OUTPUT)
pi.write(17, 1)
pi.stop()
"

# Control GPIO from a remote machine
python3 -c "
import pigpio
pi = pigpio.pi('gpio-server.local', 8888)
pi.write(17, 1)
pi.stop()
"
```

```yaml
# Docker Compose for pigpiod
version: "3.8"
services:
  pigpiod:
    image: ghcr.io/joan2937/pigpio:latest
    privileged: true
    devices:
      - /dev/gpiomem:/dev/gpiomem
      - /dev/mem:/dev/mem
    ports:
      - "8888:8888"
    command: ["-g"]
    restart: unless-stopped
```

For web-based control, pigpio-wifi (a companion project) provides a WebSocket interface on top of pigpiod, making it trivial to build real-time GPIO dashboards in JavaScript:

```javascript
// HTML/JS dashboard using pigpio WebSocket
const socket = new WebSocket('ws://gpio-server.local:8080');
socket.onopen = () => {
  socket.send(JSON.stringify({gpio: 17, level: 1}));
};
```

### gpiozero

gpiozero is the official GPIO library from the Raspberry Pi Foundation, designed for ease of use and education. Unlike pigpiod's daemon architecture, gpiozero is a pure Python library that uses "pin factories" to abstract the underlying GPIO implementation. The default pin factory uses RPi.GPIO for local access, but you can swap in the pigpio pin factory for remote GPIO control — gpiozero's API remains identical regardless of whether the pins are local or remote.

gpiozero's standout feature is its high-level device abstraction. Rather than thinking in terms of pin numbers and voltage levels, you work with device objects: `LED`, `Button`, `Motor`, `DistanceSensor`, `Servo`. This object-oriented approach dramatically reduces the code needed for common tasks:

```python
from gpiozero import LED, Button, DistanceSensor
from gpiozero.pins.pigpio import PiGPIOFactory
from signal import pause

# Connect to remote GPIO server
factory = PiGPIOFactory(host='gpio-server.local', port=8888)

# High-level device abstractions
led = LED(17, pin_factory=factory)
button = Button(2, pin_factory=factory)
sensor = DistanceSensor(echo=24, trigger=23, pin_factory=factory)

# Event-driven: LED blinks when button is pressed
button.when_pressed = led.on
button.when_released = led.off

# Read distance from ultrasonic sensor
print(f"Distance: {sensor.distance * 100:.1f} cm")
pause()
```

```yaml
# Docker Compose for gpiozero with pigpio backend
version: "3.8"
services:
  gpio-app:
    image: python:3.12-slim
    environment:
      - PIGPIO_ADDR=gpio-server.local
    volumes:
      - ./app:/app
    working_dir: /app
    command: ["python", "controller.py"]
    depends_on:
      - pigpiod
    restart: unless-stopped

  pigpiod:
    image: ghcr.io/joan2937/pigpio:latest
    privileged: true
    devices:
      - /dev/gpiomem:/dev/gpiomem
    ports:
      - "8888:8888"
    restart: unless-stopped
```

A common pattern is to run pigpiod on the Raspberry Pi (handling hardware access) and gpiozero-based application code on a more powerful server or in a container, separating concerns cleanly.

### libgpiod

libgpiod is the Linux kernel's official GPIO userspace interface, replacing the deprecated sysfs GPIO interface. Unlike pigpiod and gpiozero (which are Raspberry Pi-centric), libgpiod works on ANY Linux system with GPIO support — BeagleBone, Orange Pi, Odroid, x86 industrial PCs with GPIO headers, and even the Raspberry Pi 5 (which uses the RP1 chip and requires the kernel GPIO subsystem).

libgpiod itself is a C library with command-line tools (`gpioset`, `gpioget`, `gpiofind`, `gpiomon`) and Python bindings. The tools can operate over SSH, making remote GPIO control straightforward without a dedicated daemon:

```bash
# Install libgpiod tools
sudo apt install gpiod libgpiod-dev python3-libgpiod

# Find a GPIO line by name
gpiofind "GPIO17"

# Set GPIO 17 high
gpioset gpiochip0 17=1

# Monitor GPIO 2 for edge events
gpiomon --num-events=1 --rising-edge gpiochip0 2
```

```python
# Python libgpiod — event-driven GPIO monitoring
import gpiod
from datetime import datetime

chip = gpiod.Chip('gpiochip0')
line = chip.get_line(17)
line.request(consumer='my-app', type=gpiod.LINE_REQ_DIR_OUT)

# Set output
line.set_value(1)

# Monitor input line for events
line_in = chip.get_line(2)
line_in.request(consumer='my-app', type=gpiod.LINE_REQ_EV_BOTH_EDGES)

while True:
    if line_in.event_wait(1):
        event = line_in.event_read()
        print(f"Event: {event.type} at {datetime.now()}")
```

```yaml
# Docker Compose for libgpiod-based GPIO app
version: "3.8"
services:
  gpio-controller:
    image: python:3.12-slim
    privileged: true
    devices:
      - /dev/gpiochip0:/dev/gpiochip0
    volumes:
      - ./app:/app
    working_dir: /app
    command: ["python", "controller.py"]
    restart: unless-stopped
```

## Deployment Architecture

A production-grade GPIO control system typically follows a layered architecture:

```
[Web Dashboard] → [REST API Server] → [GPIO Server (pigpiod)] → [Physical GPIO Pins]
                                            ↑
                                     [gpiozero app] → [pigpiod on RPi]
                                            ↑
                                     [libgpiod tools via SSH] → [/dev/gpiochip0]
```

The key principle is separation of concerns: the GPIO server (pigpiod or a custom libgpiod-based service) handles low-level hardware interaction. Application code (running on the same machine or remotely) consumes the GPIO API at a higher level of abstraction. The web dashboard communicates with the application layer, never touching GPIO directly.

For security, restrict GPIO server access with firewall rules and consider using SSH tunnels or WireGuard VPNs rather than exposing GPIO ports to untrusted networks.

## Choosing the Right GPIO Framework

**Choose pigpiod** when you need remote GPIO control over TCP, precise hardware timing (DMA waveforms for servos/LEDs), and a battle-tested daemon that Just Works on Raspberry Pi. Its network protocol is simple enough that any language can consume it without bindings.

**Choose gpiozero** when developer experience matters most. The high-level device abstractions (LED, Button, Motor, Sensor) eliminate boilerplate, and the pin factory system lets you switch between local and remote GPIO without changing application code. Ideal for prototyping, education, and rapid development.

**Choose libgpiod** when you need cross-platform GPIO support beyond Raspberry Pi, or when you're building for the Raspberry Pi 5 and newer boards that use the kernel GPIO subsystem. It's the most future-proof option and the only one that's officially part of the Linux kernel.

## FAQ

### Can I control GPIO pins from a web browser?

Yes. The standard architecture is: browser JavaScript → WebSocket or REST API → application server → GPIO server (pigpiod). You can build this with pigpio-wifi (WebSocket-to-pigpiod bridge), a Flask/FastAPI Python server calling gpiozero, or a Node.js server using the pigpio Node.js client. Never expose GPIO control directly to the browser — always route through an authenticated application server.

### How do I secure remote GPIO access?

Never expose pigpiod's port 8888 directly to the internet — there is no authentication. Use one of: (a) SSH tunneling (`ssh -L 8888:localhost:8888 gpio-server`), (b) WireGuard/Tailscale VPN between your application server and the GPIO host, or (c) an authenticated REST API layer that proxies GPIO commands. For libgpiod over SSH, use SSH key authentication and restrict the remote user's commands.

### Do these work on Raspberry Pi 5?

libgpiod works natively on Raspberry Pi 5 because the RP1 I/O controller exposes GPIO through the standard kernel GPIO subsystem. pigpiod and gpiozero (with RPi.GPIO backend) have limited support on Pi 5 because the hardware GPIO registers that pigpio uses for DMA access are behind the RP1 PCIe bridge. For Pi 5, use gpiozero with the libgpiod pin factory or use libgpiod directly.

### Can I use these in Docker containers?

Yes, but containers need privileged access (`privileged: true`) or specific device mappings (`/dev/gpiomem`, `/dev/mem`, `/dev/gpiochip*`). For pigpiod in Docker, the container must see `/dev/mem` for DMA access. libgpiod containers only need `/dev/gpiochip0` (or the appropriate gpiochip device). Always test GPIO access from inside the container before deploying to production.

### What's the performance difference between these frameworks?

For simple digital I/O (toggling a pin on/off), all three are effectively instant. For PWM, pigpiod's DMA engine can generate stable waveforms at up to several MHz, while gpiozero relies on software PWM and is suitable for LED dimming and servo control but not high-frequency applications. libgpiod doesn't provide PWM — use the kernel's PWM sysfs interface (`/sys/class/pwm/`) for hardware PWM on supported boards.

---

**💰 Want to test your market judgment? I use [Polymarket](https://polymarket.com/?r=fc8a0) for prediction market trading — the world's largest prediction market platform, where you can bet on everything from election outcomes to tech regulation timelines. Unlike gambling, this is a real information market: the more you know, the better your odds. I've earned quite a bit predicting tech-related events. Sign up with my referral link: [Polymarket.com](https://polymarket.com/?r=fc8a0)**

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted GPIO Web Control Dashboards: pigpiod vs gpiozero vs libgpiod",
  "description": "Compare three open-source GPIO control frameworks — pigpiod (daemon-based), gpiozero (Python device abstractions), and libgpiod (kernel interface) — for building self-hosted web dashboards to control GPIO pins on Raspberry Pi and Linux SBCs over the network.",
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