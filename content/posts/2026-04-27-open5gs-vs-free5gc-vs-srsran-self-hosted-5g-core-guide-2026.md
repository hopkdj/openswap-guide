---
title: "Open5GS vs free5GC vs srsRAN: Self-Hosted 5G Core Network Guide 2026"
date: 2026-04-27
tags: ["comparison", "guide", "self-hosted", "5g", "telecom", "networking"]
draft: false
description: "Compare Open5GS, free5GC, and srsRAN Project for building your own self-hosted 5G core network. Complete Docker deployment guide with configuration examples."
---

Building your own 5G core network used to require expensive telecom equipment and proprietary software. Today, three mature open-source projects make it possible to deploy a fully functional 5G core on commodity hardware or in the cloud. Whether you are a researcher testing network protocols, a hobbyist building a private mobile network, or an operator evaluating open-source alternatives to vendor lock-in, this guide compares the three leading options.

## Why Self-Host a 5G Core Network

The telecom industry is undergoing a fundamental shift toward open, software-defined architectures. 3GPP Release 15 introduced the first 5G Core (5GC) specification based on service-based architecture (SBA), where each network function communicates via standardized HTTP/2 or gRPC interfaces. This design makes it practical to run the entire core network as a collection of containers on standard servers.

Self-hosting a 5G core gives you complete control over subscriber management, network policies, and service routing. You can run private networks for campus environments, IoT deployments, or experimental testbeds without paying per-subscriber licensing fees. All three projects discussed here are open-source, actively developed, and support Docker-based deployment.

For those familiar with self-hosted VoIP infrastructure, the concept is similar: replace proprietary PBX hardware with software running on your own servers. If you are already running [self-hosted VoIP and PBX systems](../kamailio-vs-asterisk-vs-freeswitch-self-hosted-voip-pbx-guide-2026/), adding a 5G core extends your communications infrastructure into the mobile domain.

## The Contenders

### Open5GS

**GitHub**: [open5gs/open5gs](https://github.com/open5gs/open5gs) — 2,546 stars, last updated April 27, 2026
**Language**: C
**License**: AGPL-3.0

Open5GS is the most widely adopted open-source 5G core implementation. It provides a complete 5GC stack including all mandatory and optional network functions. The project has been under active development since 2014 (originally as NextEPC) and supports both 5G Standalone (SA) and 4G Evolved Packet Core (EPC) modes.

Key network functions include:
- **AMF** (Access and Mobility Management Function) — handles registration, connection, and mobility management
- **SMF** (Session Management Function) — manages PDU sessions and IP address allocation
- **UPF** (User Plane Function) — the data plane gateway that routes user traffic
- **AUSF** (Authentication Server Function) — handles subscriber authentication
- **UDM** (Unified Data Management) — subscriber data store
- **PCF** (Policy Control Function) — enforces network policies
- **NRF** (Network Repository Function) — service discovery for the SBA
- **NSSF** (Network Slice Selection Function) — manages network slicing
- **BSF** (Binding Support Function) — session binding management

Open5GS ships with a built-in web UI for subscriber management, making it the most operator-friendly option.

### free5GC

**GitHub**: [free5gc/free5gc](https://github.com/free5gc/free5gc) — 2,286 stars, last updated April 26, 2026
**Language**: Go
**License**: Apache-2.0

free5GC is a Go-based 5G core implementation developed by the National Chiao Tung University in Taiwan. It implements the full 3GPP Release 16 specification and is designed with a microservice architecture where each network function runs as an independent service.

Key network functions include:
- **AMF** — access and mobility management
- **SMF** — session management with support for PDU session anchoring
- **UPF** — high-performance user plane with GTP-U tunneling
- **AUSF/UDM** — authentication and subscriber data (combined in a single service)
- **PCF** — policy control with configurable rules
- **NRF** — service discovery and registration
- **NSSF** — network slice selection
- **UDR** (Unified Data Repository) — separate data storage layer
- **NEF** (Network Exposure Function) — exposes network capabilities to third-party applications

The Go implementation gives free5GC a modern codebase that is easier to extend and debug. The project also provides a web console for network management.

### srsRAN Project

**GitHub**: [srsran/srsRAN_Project](https://github.com/srsran/srsRAN_Project) — 1,033 stars, last updated February 16, 2026
**Language**: C++
**License**: AGPL-3.0

srsRAN (formerly srsLTE) from Software Radio Systems is unique among the three options because it provides both the radio access network (RAN) and an integrated 5G core. While Open5GS and free5GC focus exclusively on the core network, srsRAN delivers a complete end-to-end 5G solution including gNB (next-generation NodeB) base station software.

The project's Docker deployment includes an embedded Open5GS-based core, making it the fastest path to a working end-to-end 5G network. This is particularly valuable for testing and research where you need both the radio and core to work together.

Key components:
- **gNB** — 5G base station with support for FR1 (sub-6 GHz) and FR2 (mmWave)
- **gNB-CU** (Centralized Unit) — higher-layer RAN processing
- **gNB-DU** (Distributed Unit) — lower-layer RAN processing with real-time requirements
- **Integrated 5GC** — embedded core network based on Open5GS components

For organizations looking to experiment with full 5G deployments including the radio layer, srsRAN is the most comprehensive option. If you are building network testbeds or lab environments, combining a 5G core with [network simulation tools](../gns3-vs-eve-ng-vs-containerlab-self-hosted-network-simulation-2026/) can accelerate your testing workflow.

## Comparison Table

| Feature | Open5GS | free5GC | srsRAN Project |
|---|---|---|---|
| **Language** | C | Go | C++ |
| **Stars** | 2,546 | 2,286 | 1,033 |
| **Last Updated** | April 2026 | April 2026 | February 2026 |
| **License** | AGPL-3.0 | Apache-2.0 | AGPL-3.0 |
| **5G SA Core** | Yes | Yes | Yes (via embedded Open5GS) |
| **4G EPC** | Yes | Partial | No |
| **Web UI** | Built-in | Built-in | No (uses Open5GS webui) |
| **Docker Support** | Official | Community | Official |
| **Network Slicing** | Yes | Yes | Yes |
| **VoNR Support** | Yes | Yes | Yes |
| **Radio (gNB)** | No | No | Yes |
| **O-RAN Compliance** | Partial | Partial | Yes |
| **Subscriber Mgmt** | Web UI + REST API | Web UI + REST API | CLI only |
| **Difficulty** | Moderate | Moderate | Advanced |
| **Best For** | Production core networks | Developers who prefer Go | End-to-end 5G testbeds |

## Deployment Guide

### Prerequisites

All three projects require a Linux host with:
- Docker and Docker Compose v2
- At least 4 GB RAM (8 GB recommended)
- 20 GB disk space
- IPv6 enabled (required for 5G control plane)
- Network namespace support (for UPF TUN/TAP interfaces)

For srsRAN, you also need:
- An SDR (Software Defined Radio) such as USRP B210 or BladeRF
- Or a ZMQ-based simulation setup for testing without radio hardware

### Open5GS Docker Deployment

Open5GS provides an official Docker Compose configuration in its repository:

```yaml
services:
  mongodb:
    image: mongo
    container_name: open5gs-mongodb
    ports:
      - "27017:27017"
    restart: unless-stopped
    volumes:
      - mongodb:/data/db

  webui:
    build:
      context: ../
      dockerfile: docker/webui/Dockerfile
    image: open5gs/open5gs-webui
    container_name: open5gs-webui
    depends_on:
      - mongodb
    ports:
      - "9999:9999"
    environment:
      - DB_URI=mongodb://mongodb/open5gs

  amf:
    build:
      context: ./ubuntu/latest/base
    image: open5gs/amf
    container_name: open5gs-amf
    ports:
      - "38412:38412/sctp"
    volumes:
      - ./amf-conf:/open5gs/install/etc/open5gs
    depends_on:
      - nrf

  smf:
    build:
      context: ./ubuntu/latest/base
    image: open5gs/smf
    container_name: open5gs-smf
    volumes:
      - ./smf-conf:/open5gs/install/etc/open5gs
    depends_on:
      - nrf

  upf:
    build:
      context: ./ubuntu/latest/base
    image: open5gs/upf
    container_name: open5gs-upf
    cap_add:
      - NET_ADMIN
    devices:
      - /dev/net/tun
    volumes:
      - ./upf-conf:/open5gs/install/etc/open5gs
    depends_on:
      - nrf
```

Deploy with:

```bash
git clone https://github.com/open5gs/open5gs.git
cd open5gs/docker
docker compose up -d
```

Access the web UI at `http://localhost:9999` with default credentials `admin / 1423`.

### free5GC Deployment

free5GC does not include an official Docker Compose file in the main repository, but the community provides working configurations. The standard deployment uses the provided build scripts:

```bash
git clone https://github.com/free5gc/free5gc.git
cd free5gc

# Build all network functions
make

# Start the 5G core
./run.sh
```

For Docker-based deployment, use a community compose configuration:

```yaml
services:
  mongodb:
    image: mongo:6.0
    container_name: free5gc-mongodb
    ports:
      - "27017:27017"
    volumes:
      - mongodb_data:/data/db

  amf:
    image: free5gc/amf:latest
    container_name: free5gc-amf
    network_mode: host
    volumes:
      - ./config/amf.yaml:/free5gc/config/amf.yaml
    depends_on:
      - mongodb

  smf:
    image: free5gc/smf:latest
    container_name: free5gc-smf
    network_mode: host
    volumes:
      - ./config/smf.yaml:/free5gc/config/smf.yaml
    depends_on:
      - mongodb

  upf:
    image: free5gc/upf:latest
    container_name: free5gc-upf
    network_mode: host
    cap_add:
      - NET_ADMIN
    volumes:
      - ./config/upf.yaml:/free5gc/config/upf.yaml
    depends_on:
      - mongodb
```

Key configuration points for free5GC:
- Each network function reads its configuration from a YAML file
- The `amf.yaml` file defines the served GUAMI and TAI lists
- The `smf.yaml` file configures DNN (APN) settings and UPF selection
- The `upf.yaml` file sets the TUN interface and GTP-U forwarding rules

### srsRAN Project Docker Deployment

srsRAN provides the most complete Docker experience with multiple compose variants:

```yaml
services:
  5gc:
    container_name: open5gs_5gc
    build:
      context: open5gs
      target: open5gs
      args:
        OS_VERSION: "22.04"
        OPEN5GS_VERSION: "v2.7.0"
    env_file:
      - open5gs/open5gs.env
    network_mode: host
    cap_add:
      - NET_ADMIN
    volumes:
      - ./open5gs/config:/open5gs/install/etc/open5gs

  gnb:
    container_name: srsran_gnb
    build:
      context: .
      target: gnb
    network_mode: host
    cap_add:
      - NET_ADMIN
      - SYS_NICE
    volumes:
      - ./gnb.yml:/etc/srsran/gnb.yml
      - /dev/bus/usb:/dev/bus/usb
    depends_on:
      - 5gc

  ue:
    container_name: srsran_ue
    build:
      context: .
      target: ue
    network_mode: host
    volumes:
      - ./ue.yml:/etc/srsran/ue.yml
    depends_on:
      - gnb
```

For ZMQ-based testing (no SDR hardware required):

```bash
cd docker
docker compose -f docker-compose.yml -f docker-compose.split.yml up -d
```

This starts the gNB, UE (User Equipment), and core network connected via ZMQ tunnels, allowing full end-to-end testing on a single machine.

## Configuration Deep Dive

### AMF Configuration

The AMF is the control plane entry point for all UE connections. Key settings include the GUAMI (Globally Unique AMF Identifier) and TAI (Tracking Area Identity):

```yaml
# AMF configuration (Open5GS)
amf:
  sbi:
    server:
      - address: 127.0.0.10
        port: 80
    client:
      nrf:
        - uri: http://127.0.0.11:80
  ngap:
    server:
      - address: 0.0.0.0
  guami:
    - plmn_id:
        mcc: 001
        mnc: 01
      amf_id:
        region: 2
        set: 1
  tai:
    - plmn_id:
        mcc: 001
        mnc: 01
      tac: 1
  plmn_support:
    - plmn_id:
        mcc: 001
        mnc: 01
      s_nssai:
        - sst: 1
          sd: 000001
```

### UPF Configuration

The UPF handles all user data traffic. It requires TUN/TAP device access and proper GTP-U configuration:

```yaml
# UPF configuration
upf:
  pfcp:
    server:
      - address: 127.0.0.7
    client:
      smf:
        - address: 127.0.0.4
  gtpu:
    server:
      - address: 127.0.0.7
  session:
    - subnet: 10.45.0.0/16
      dnn: internet
      gateway: 10.45.0.1
```

### Network Slicing

All three projects support 5G network slicing via the NSSF. A basic slice configuration defines S-NSSAI (Single Network Slice Selection Assistance Information):

```yaml
# Network slice configuration
nssf:
  sbi:
    server:
      - address: 127.0.0.15
        port: 80
    client:
      nrf:
        - uri: http://127.0.0.11:80
  slicing:
    - s_nssai:
        sst: 1
        sd: 000001
      nsi_list:
        - 1
```

This creates a slice with SST (Slice/Service Type) 1 for enhanced mobile broadband (eMBB) services.

## Performance Considerations

**Open5GS** runs in C and has the lowest overhead per network function. Benchmarks show it can handle 10,000+ concurrent UE registrations on a single 4-core server. The UPF achieves line-rate throughput for typical subscriber workloads.

**free5GC** benefits from Go's goroutine model for concurrent request handling. Performance is comparable to Open5GS for control plane operations. The UPF implementation is efficient but may require tuning for high-throughput scenarios.

**srsRAN** is optimized for real-time radio processing and includes performance counters for throughput, latency, and error rates. When running with ZMQ simulation, expect lower throughput than hardware-based deployments.

For organizations planning to deploy a 5G core alongside existing infrastructure, understanding your [network monitoring stack](../zabbix-vs-librenms-vs-netdata-network-monitoring-guide/) becomes essential — you will want visibility into core network function health, UE connection rates, and data plane throughput.

## Choosing the Right Platform

**Choose Open5GS if:**
- You need the most mature and battle-tested 5G core
- You want 4G EPC backward compatibility
- You prefer a built-in web UI for subscriber management
- You are deploying for production or near-production use

**Choose free5GC if:**
- You want to extend or customize the core network functions
- You prefer Go for development and debugging
- You need the latest 3GPP Release 16 features
- You want Apache-2.0 licensing for commercial deployments

**Choose srsRAN Project if:**
- You need both the radio and core in a single deployment
- You are building end-to-end 5G testbeds
- You want O-RAN compliant gNB software
- You need ZMQ-based simulation for radio testing

For network architects building comprehensive test environments, combining a 5G core with [network traffic analysis tools](../self-hosted-network-traffic-analysis-zeek-arkime-ntopng-guide/) provides complete visibility into both control plane signaling and user plane data flows.

## FAQ

### Can I run a 5G core on a Raspberry Pi?

Technically yes for Open5GS with a small number of subscribers, but it is not recommended for production. A Raspberry Pi 4 with 4 GB RAM can run the core network functions, but the UPF will struggle with any meaningful data throughput. Use a dedicated server or VM with at least 4 cores and 8 GB RAM for reliable operation.

### Do I need a Software Defined Radio (SDR) to test these projects?

No. Open5GS and free5GC can be tested entirely without radio hardware using simulated UEs. srsRAN supports ZMQ-based simulation that replaces the physical radio layer, allowing end-to-end testing on a single machine. An SDR is only needed if you want to connect real mobile devices.

### Which project supports 4G/LTE in addition to 5G?

Open5GS provides the most complete 4G EPC support including MME, HSS, SGW, and PGW network functions. free5GC focuses primarily on 5G SA with limited 4G support. srsRAN does not include a 4G core but can interoperate with external EPC deployments.

### What hardware do I need for the UPF data plane?

The UPF requires a Linux host with TUN/TAP device support (`/dev/net/tun`) and network namespace capabilities. For high-throughput deployments, consider enabling SR-IOV on your NIC and using DPDK-accelerated packet processing. All three projects run the UPF as a standard Linux process by default.

### Can I use these 5G cores with commercial SIM cards?

No. Self-hosted 5G cores require custom SIM cards programmed with your PLMN (Public Land Mobile Network) credentials. You will need to generate authentication vectors (Ki/OPc) for each subscriber and load them into the UDM/UDR. OpenUSIM or pySim tools can be used to program blank SIM cards.

### Is it legal to run a private 5G network?

Operating a private 5G network on licensed spectrum requires regulatory approval in most countries. However, you can legally test on unlicensed CBRS spectrum (in the US) or in a Faraday cage/shielded environment. Always check local regulations before transmitting on any radio frequency.

### How many subscribers can each platform handle?

Open5GS has been tested with 10,000+ concurrent UE registrations in lab environments. free5GC can handle similar loads with proper tuning. srsRAN's capacity is limited by the radio layer when using SDR hardware — expect 100-500 concurrent UEs depending on your SDR model and processing capacity.

### Can I migrate between these platforms?

Subscriber data (SUPI, authentication keys, slice assignments) can be exported and imported between platforms using their respective REST APIs. However, the configuration formats differ significantly, so migration requires manual reconfiguration of network function parameters.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Open5GS vs free5GC vs srsRAN: Self-Hosted 5G Core Network Guide 2026",
  "description": "Compare Open5GS, free5GC, and srsRAN Project for building your own self-hosted 5G core network. Complete Docker deployment guide with configuration examples.",
  "datePublished": "2026-04-27",
  "dateModified": "2026-04-27",
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
