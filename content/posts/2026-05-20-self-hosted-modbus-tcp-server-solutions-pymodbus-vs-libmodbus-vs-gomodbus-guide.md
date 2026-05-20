---
title: "Self-Hosted Modbus TCP Server Solutions: pymodbus vs libmodbus vs GoModbus (Industrial IoT Guide)"
date: "2026-05-20"
tags: ["modbus", "industrial-iot", "scada", "self-hosted", "docker", "protocol", "guide"]
draft: false
---

**Modbus** is the de facto standard protocol for industrial automation, connecting programmable logic controllers (PLCs), sensors, motor drives, and supervisory control systems. Originally developed by Modicon in 1979, Modbus TCP (over Ethernet) has largely replaced the serial Modbus RTU variant in modern deployments.

This guide compares three self-hosted Modbus TCP server implementations for industrial IoT simulation, SCADA testing, and protocol gateway development.

## What Is Modbus TCP?

Modbus TCP encapsulates the Modbus protocol within TCP/IP packets, enabling communication over standard Ethernet networks. Unlike Modbus RTU (which requires RS-485 serial wiring), Modbus TCP leverages existing network infrastructure.

Key Modbus concepts:

- **Registers**: 16-bit data storage (Holding Registers, Input Registers, Coils, Discrete Inputs)
- **Function Codes**: Operations like Read Holding Registers (0x03), Write Single Register (0x06), Read Coils (0x01)
- **Unit ID**: Slave device identifier within a TCP connection
- **Master/Server**: The client (master) initiates requests; the server (slave) responds

A self-hosted Modbus TCP server lets you simulate PLCs, test SCADA systems, build IoT gateways, or develop Modbus monitoring tools without physical industrial hardware.

## pymodbus

**GitHub**: [pymodbus-dev/pymodbus](https://github.com/pymodbus-dev/pymodbus) | ⭐ 2,100+ | Last active: May 2026

**pymodbus** is a full Modbus protocol implementation in Python, supporting both server (slave) and client (master) modes. It is the most popular Python Modbus library and is widely used for industrial IoT prototyping.

### Key Features

- Complete Modbus TCP, RTU, and ASCII support
- Asynchronous server and client using Python asyncio
- Built-in Modbus simulator with configurable register maps
- Django and Twisted integration options
- Rich diagnostic tools and logging
- Active development with regular releases

### Docker Deployment

```yaml
services:
  pymodbus-server:
    image: pymodbus/pymodbus-server:latest
    container_name: pymodbus-server
    ports:
      - "5020:5020"
    environment:
      - MODBUS_PORT=5020
      - MODBUS_LOG_LEVEL=INFO
      - SIMULATOR_CONFIG=/config/simulator.json
    volumes:
      - ./config:/config
    command: pymodbus server --simulator /config/simulator.json
    restart: unless-stopped
```

The pymodbus simulator configuration defines register maps, coil states, and data types for realistic device emulation:

```json
{
  "server_list": {
    "server": {
      "host": "0.0.0.0",
      "port": 5020,
      "type": "tcp"
    }
  },
  "device_list": {
    "plc-01": {
      "type": "PLC",
      "starting_address": 0,
      "register_values": {
        "holding_registers": [100, 200, 300, 400],
        "input_registers": [50, 60, 70, 80],
        "coils": [true, false, true, false],
        "discrete_inputs": [false, true, false, true]
      }
    }
  }
}
```

### Use Cases

- **SCADA testing**: Simulate hundreds of PLCs for SCADA system validation
- **IoT prototyping**: Quick Python scripts to bridge Modbus to MQTT or REST APIs
- **Education**: Readable Python codebase ideal for learning Modbus protocol internals
- **Data logging**: Collect Modbus register data and store in time-series databases

## libmodbus

**GitHub**: [stephane/libmodbus](https://github.com/stephane/libmodbus) | ⭐ 1,300+ | Last active: 2026

**libmodbus** is a C library for Modbus communication, supporting both Modbus TCP and Modbus RTU/ASCII. It is the most widely used native Modbus library in industrial applications and embedded systems.

### Key Features

- High-performance C library with minimal overhead
- Modbus TCP and RTU/ASCII support
- Cross-platform: Linux, Windows, macOS, RTOS
- Thread-safe client and server implementations
- Comprehensive error handling and timeout management
- Used by Node-RED, Home Assistant, and many industrial platforms

### Docker Deployment

```yaml
services:
  libmodbus-server:
    image: ozmartian/libmodbus-server:latest
    container_name: libmodbus-server
    ports:
      - "1502:1502"
    environment:
      - MODBUS_PORT=1502
      - NUM_HOLDING_REGISTERS=1000
      - LOG_LEVEL=debug
    volumes:
      - ./libmodbus-data:/data
    restart: unless-stopped
```

libmodbus is typically compiled into custom applications rather than run as a standalone server. However, community Docker images wrap it with configurable server implementations.

### Use Cases

- **Embedded systems**: Minimal footprint ideal for PLC firmware and gateway devices
- **High-throughput applications**: C performance for real-time data acquisition
- **Platform integration**: Underlying library for Home Assistant, Node-RED Modbus nodes
- **Production systems**: Battle-tested in thousands of industrial deployments

## GoModbus (gosun/modbus)

**GitHub**: [gosun/modbus](https://github.com/gosun/modbus) | ⭐ 180+ | Last active: 2026

**GoModbus** is a Go (Golang) implementation of the Modbus protocol, providing both TCP server and client functionality with Go's native concurrency model. It is designed for building high-performance, concurrent Modbus applications.

### Key Features

- Native Go implementation with goroutine-based concurrency
- Modbus TCP server with configurable register maps
- Asynchronous client with connection pooling
- Built-in data type conversion (INT16, UINT32, FLOAT32, etc.)
- Clean API for programmatic register manipulation
- Single binary deployment (no runtime dependencies)

### Docker Deployment

```yaml
services:
  gomodbus-server:
    image: gosun/modbus-server:latest
    container_name: gomodbus-server
    ports:
      - "502:502"
    environment:
      - MODBUS_ADDR=:502
      - REGISTER_COUNT=5000
      - DATA_FILE=/data/registers.json
    volumes:
      - ./gomodbus-data:/data
    restart: unless-stopped
```

GoModbus compiles to a single static binary, making it ideal for minimal Docker containers (typically < 15MB) and edge deployments.

### Use Cases

- **Microservices**: Go-based Modbus services in containerized architectures
- **Edge computing**: Small binary footprint for resource-constrained devices
- **Concurrent polling**: Goroutine model for efficient multi-device data collection
- **API gateways**: Build REST or gRPC gateways around Modbus devices

## Comparison Table

| Feature | pymodbus | libmodbus | GoModbus |
|---------|----------|-----------|----------|
| **Language** | Python | C | Go |
| **Modbus TCP** | ✅ Full | ✅ Full | ✅ Full |
| **Modbus RTU** | ✅ Full | ✅ Full | ❌ TCP only |
| **Async Support** | ✅ asyncio | ❌ Threading | ✅ Goroutines |
| **Simulator** | ✅ Built-in | ❌ Custom | ❌ Custom |
| **Docker Image** | ✅ Official | ✅ Community | ✅ Community |
| **Binary Size** | ~30MB (Python) | ~200KB (shared lib) | ~10MB (static) |
| **GitHub Stars** | 2,100+ | 1,300+ | 180+ |
| **Best For** | Prototyping, SCADA testing | Production, embedded | Microservices, edge |

## Choosing the Right Modbus Server

**Use pymodbus when:**
- You need rapid prototyping with Python's rich ecosystem
- Built-in device simulation saves development time
- You're building SCADA test harnesses or educational tools
- Asyncio integration fits your application architecture

**Use libmodbus when:**
- Performance and minimal resource usage are critical
- You need Modbus RTU (serial) support alongside TCP
- You're building embedded firmware or gateway appliances
- Integration with existing C/C++ industrial systems

**Use GoModbus when:**
- You're building Go-based microservices or API gateways
- Single-binary deployment simplifies your infrastructure
- Concurrent device polling with goroutines matches your workload
- You need a balance of performance and developer productivity

## Why Self-Host Modbus Infrastructure?

Proprietary Modbus simulation and testing tools from vendors like Kepware, Moxa, and Advantech can cost thousands of dollars. Self-hosted Modbus servers provide:

- **Cost savings**: Eliminate expensive commercial PLC simulators and testing licenses
- **Development agility**: Prototype IoT integrations without waiting for physical hardware
- **Testing scalability**: Simulate hundreds or thousands of virtual PLCs for load testing
- **Data sovereignty**: Keep industrial data on-premises without cloud telemetry dependencies
- **Protocol research**: Study Modbus internals with open, readable source code

For related industrial IoT topics, see our guides on [self-hosted gNMI telemetry streaming](../2026-05-23-self-hosted-gnmi-telemetry-streaming-telegraf-vs-opentelemetry-collector-vs-gnmic-guide/) for network device monitoring, and [self-hosted CoAP protocol servers](../2026-05-23-self-hosted-coap-protocol-servers-eclipse-californium-vs-leshan-vs-copper-guide/) for lightweight IoT alternatives to Modbus.

## FAQ

### What is the difference between Modbus TCP and Modbus RTU?

Modbus TCP encapsulates Modbus frames within TCP/IP packets, running over standard Ethernet networks on port 502. Modbus RTU uses serial communication (typically RS-485) with binary encoding and CRC checksums. Modbus TCP is faster and easier to deploy on modern networks, while RTU remains common in legacy industrial installations.

### Can I run a Modbus server on port 502 in Docker?

Port 502 is the standard Modbus TCP port. However, it requires root privileges on most Linux systems. For Docker deployments, it is common to use an alternate port (e.g., 5020 or 1502) and map it in the Docker Compose configuration. If you must use port 502, run the container with appropriate capabilities or use `network_mode: host`.

### How do I simulate Modbus registers for testing?

pymodbus provides a built-in simulator where you define register maps in JSON configuration. libmodbus and GoModbus require you to write custom server code that maintains register state. For quick testing, pymodbus is the most convenient option with its pre-built simulator.

### Is Modbus secure?

Modbus has no built-in encryption, authentication, or integrity checking. All communication is plaintext. For secure deployments, place Modbus devices on isolated VLANs, use VPN tunnels for remote access, or deploy Modbus-over-TLS gateways. Never expose Modbus directly to the public internet.

### What data types does Modbus support?

Modbus natively supports 16-bit integers (registers) and single-bit values (coils). Larger data types are constructed from multiple registers: 32-bit integers (2 registers), 32-bit floats/IEEE 754 (2 registers), and 64-bit values (4 registers). The byte order (endianness) must be agreed upon between client and server.

### How many registers can a Modbus server support?

The Modbus protocol supports up to 65,536 registers (addresses 0-65535) per data type (holding, input, coils, discrete). In practice, most devices support far fewer — typically 100-1000 registers. Self-hosted servers can support the full range, limited only by available memory.

### Can I bridge Modbus to MQTT?

Yes. This is one of the most common industrial IoT patterns. You can use pymodbus to poll Modbus registers and publish values to MQTT topics, or use Node-RED with its Modbus and MQTT nodes for a no-code approach. libmodbus is commonly used in C-based gateway firmware for this purpose.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Modbus TCP Server Solutions: pymodbus vs libmodbus vs GoModbus (Industrial IoT Guide)",
  "description": "Compare open-source Modbus TCP server implementations: pymodbus, libmodbus, and GoModbus. Includes Docker deployment configs, use cases, and feature comparison.",
  "datePublished": "2026-05-21",
  "dateModified": "2026-05-21",
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
