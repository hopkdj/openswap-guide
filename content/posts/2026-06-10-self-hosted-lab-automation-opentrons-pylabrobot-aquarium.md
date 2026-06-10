---
title: "Self-Hosted Lab Automation Platforms: OpenTrons vs PyLabRobot vs Aquarium"
date: "2026-06-10"
tags: ["lab-automation", "scientific-computing", "robotics", "lims", "research", "python"]
draft: false
---

## Introduction

Modern biology and chemistry laboratories increasingly rely on automated liquid handlers, robotic arms, and integrated workcells to achieve the throughput demanded by drug discovery, genomics, and synthetic biology workflows. However, the software stack controlling these instruments has historically been closed, proprietary, and locked to specific hardware vendors — creating costly vendor dependency and limiting reproducibility.

Three open-source platforms are changing this landscape: **OpenTrons** provides a complete hardware-plus-software ecosystem with its OT-2 and Flex robots and a Python API for protocol authoring; **PyLabRobot** offers a hardware-agnostic SDK that can control liquid handlers from multiple manufacturers including Hamilton, Tecan, and Beckman Coulter; and **Aquarium Lab OS** takes a higher-level approach as a laboratory operating system that manages protocols, inventory, and workflows across diverse equipment.

This guide compares these three self-hosted lab automation platforms, covering their architecture, deployment, and ideal use cases to help research teams select the right foundation for their automated laboratories.

## Why Self-Host Your Lab Automation Software?

Academic labs, biotech startups, and core facilities face unique challenges that make self-hosted lab automation platforms particularly compelling:

**Protocol Reproducibility**: Scientific reproducibility demands that experiments be described precisely enough to be repeated. Self-hosted platforms store protocols as version-controlled code (Python scripts, YAML configurations), enabling peer review, sharing, and exact reproduction — something impossible with vendor-specific GUI-based protocol editors.

**Multi-Vendor Orchestration**: Most labs operate instruments from multiple manufacturers. PyLabRobot's hardware-agnostic abstraction layer lets you write one protocol that works across Hamilton STAR, Tecan Fluent, and OpenTrons hardware, avoiding vendor lock-in and enabling cross-platform protocol portability.

**Custom Workflow Integration**: Research workflows often require custom logic — dynamic volume calculations based on real-time measurements, conditional branching based on previous results, and integration with external databases. Python-based platforms enable this complexity in ways that point-and-click vendor software cannot.

For labs building comprehensive digital infrastructure, see our guide on [self-hosted electronic lab notebooks](../2026-05-04-self-hosted-electronic-lab-notebook-elabftw-chemotion-labkey-guide/) and the comparison of [reproducible research environments](../2026-06-10-self-hosted-reproducible-research-binderhub-renku-stencila-guide/).

## Comparison Table

| Feature | OpenTrons | PyLabRobot | Aquarium |
|---------|-----------|------------|----------|
| **Hardware Support** | OpenTrons OT-2, Flex | Hamilton, Tecan, Beckman, OpenTrons | Hardware-agnostic |
| **Protocol Language** | Python API | Python API | Web UI + Ruby |
| **Deployment** | Desktop app + OT-2 server | Python package (pip) | Docker + Kubernetes |
| **Web Interface** | OpenTrons App (desktop) | None (library) | Full web application |
| **Inventory Management** | Labware definitions | Via resource classes | Built-in sample tracking |
| **Scheduling** | Basic queue | Not included | Built-in workflow scheduler |
| **Multi-User Support** | Limited | N/A | Full RBAC |
| **Protocol Versioning** | Local files | Git-based | Built-in version control |
| **REST API** | Yes (robot server) | Via custom wrapper | Full REST API |
| **License** | Apache 2.0 | MIT | MIT |
| **GitHub Stars** | 502+ | 465+ | 68+ |
| **Latest Update** | 2026 (active) | 2026 (active) | 2025 (stable) |

## OpenTrons: The Integrated Ecosystem

OpenTrons takes the most vertically integrated approach, providing both the hardware (OT-2 and Flex liquid handlers) and the open-source software to control them. The Python API is well-documented and intuitive, making it accessible to biologists with basic programming skills.

**Key Capabilities:**
- **Opentrons Python Protocol API** — write protocols as Python scripts with explicit volume, position, and timing control
- **Opentrons App** — desktop application for protocol upload, execution monitoring, and calibration
- **Labware Library** — extensive database of labware definitions covering plates, tips, tubes, and reservoirs from major manufacturers
- **Protocol Designer** — drag-and-drop interface for common operations (serial dilution, PCR setup, plate replication)

### Docker Compose for OT-2 Server

The OT-2 robot itself runs a Raspberry Pi-based server, but you can replicate the development environment for protocol testing:

```yaml
version: "3.8"
services:
  opentrons-dev:
    image: opentrons/opentrons:latest
    container_name: opentrons-simulator
    ports:
      - "31950:31950"
    volumes:
      - ./protocols:/data/protocols
      - ./labware:/data/labware
    environment:
      - OT_API_FF_ENABLE_CALIBRATION_CHECK=false
      - RUNNING_ON_PI=false
    command: ["python", "-m", "opentrons", "simulate", "/data/protocols/my_protocol.py"]
```

**Basic Protocol Example:**

```python
from opentrons import protocol_api

metadata = {
    'protocolName': 'PCR Setup',
    'author': 'Lab Team',
    'description': '96-well PCR plate preparation'
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tips = protocol.load_labware('opentrons_96_tiprack_300ul', 1)
    plate = protocol.load_labware('biorad_96_wellplate_200ul_pcr', 2)
    reservoir = protocol.load_labware('nest_12_reservoir_15ml', 3)

    # Load pipette
    p300 = protocol.load_instrument('p300_single', 'right', tip_racks=[tips])

    # Transfer master mix
    p300.transfer(18, reservoir['A1'], plate.wells(), new_tip='once')

    # Add DNA template
    p300.transfer(2, reservoir['A2'], plate.wells(), mix_after=(3, 10))
```

## PyLabRobot: The Universal Controller

PyLabRobot takes a fundamentally different approach — rather than being tied to specific hardware, it provides a universal abstraction layer that works across Hamilton STAR, Tecan EVO/Fluent, Beckman Biomek, and OpenTrons robots. This makes it invaluable for core facilities and CROs operating mixed-vendor fleets.

**Key Capabilities:**
- **Unified Resource API** — define tips, plates, and reagents once, then execute across any supported hardware
- **Cross-platform protocol portability** — write a protocol for a Hamilton STAR and run it on a Tecan Fluent with minimal changes
- **Simulation mode** — test protocols without physical hardware using the virtual deck
- **Async execution** — control multiple robots simultaneously from a single Python process

**Installation and Basic Usage:**

```bash
pip install pylabrobot
```

```python
from pylabrobot.liquid_handling import LiquidHandler
from pylabrobot.liquid_handling.backends import STAR
from pylabrobot.resources import (
    TIP_CAR_480_A00,
    PLT_CAR_L5AC_A00,
    Cos_96_EZWash,
    TIP_300ul_STD_L
)

# Initialize robot backend (Hamilton STAR in this example)
backend = STAR(ip_address="192.168.1.100", port=8080)
lh = LiquidHandler(backend=backend)

# Define deck layout
lh.deck.assign_child_resource(TIP_CAR_480_A00, location=(0, 0, 0))
lh.deck.assign_child_resource(PLT_CAR_L5AC_A00, location=(1, 0, 0))

# Setup and run
await lh.setup()
await lh.pick_up_tips(TIP_300ul_STD_L["A1":"H1"])
await lh.aspirate(plate["A1"], vols=100)
await lh.dispense(destination["A1"], vols=100)
await lh.return_tips()
```

## Aquarium Lab OS: The Laboratory Operating System

Aquarium takes the highest-level approach, functioning as a complete laboratory operating system rather than just a robot controller. It manages the entire experimental lifecycle: protocol definition, sample tracking, inventory management, workflow scheduling, and data association.

**Key Capabilities:**
- **Protocol-based workflow engine** — define experiments as composable protocol modules with explicit inputs/outputs
- **Sample and inventory tracking** — every sample, reagent, and consumable is tracked through its entire lifecycle
- **Web-based interface** — protocols are designed and executed through a browser, no local software installation required
- **Kubernetes-native deployment** — designed for production deployment on lab Kubernetes clusters

### Docker Compose for Aquarium

```yaml
version: "3.8"
services:
  aquarium:
    image: klavinslab/aquarium:latest
    container_name: aquarium
    ports:
      - "3000:3000"
    volumes:
      - ./aquarium-data:/usr/src/app/data
      - ./aquarium-uploads:/usr/src/app/public/uploads
    environment:
      - DATABASE_URL=postgresql://aquarium:changeme@postgres:5432/aquarium
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY_BASE=your-secret-key-here
    depends_on:
      - postgres
      - redis

  postgres:
    image: postgres:16
    environment:
      - POSTGRES_DB=aquarium
      - POSTGRES_USER=aquarium
      - POSTGRES_PASSWORD=changeme
    volumes:
      - ./postgres-data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - ./redis-data:/data
```

## Choosing the Right Lab Automation Platform

| Laboratory Profile | Recommended Platform | Rationale |
|-------------------|---------------------|-----------|
| Small academic lab with 1-2 OT-2s | OpenTrons | Integrated ecosystem, lowest complexity |
| Core facility with mixed-vendor fleet | PyLabRobot | Hardware-agnostic, universal protocol portability |
| Large lab with complex workflows | Aquarium | Full workflow management, sample tracking, multi-user |
| Biotech startup scaling automation | PyLabRobot + Aquarium | PyLabRobot for robot control, Aquarium for workflow orchestration |
| Teaching lab / training | OpenTrons | Best documentation, Protocol Designer for beginners |

## Frequently Asked Questions

### Can I use PyLabRobot with OpenTrons hardware?

Yes. PyLabRobot includes an OpenTrons backend that can control OT-2 and Flex robots. This means you can write protocols using PyLabRobot's universal API and execute them on OpenTrons hardware — useful if you plan to add non-OpenTrons instruments to your lab in the future.

### How does Aquarium handle actual robot control?

Aquarium is primarily a workflow management and scheduling layer. For physical robot execution, it interfaces with robot-specific drivers (including OpenTrons and Hamilton Venus) through a plugin architecture. The protocol module defines "what" to do; backend drivers handle "how" to execute it on specific hardware.

### What programming skills are needed?

OpenTrons and PyLabRobot require basic Python proficiency — roughly the level of a one-semester programming course for scientists. Aquarium's protocol design is primarily web-based (point-and-click) but advanced customization requires Ruby knowledge. All three platforms are designed for biologists and chemists who code, not professional software engineers.

### Can these platforms integrate with electronic lab notebooks?

Absolutely. OpenTrons has a REST API that can be triggered by ELN workflows. PyLabRobot can be wrapped in a FastAPI/Flask server for ELN integration. Aquarium has a full REST API designed for external system integration. See our guide on [self-hosted electronic lab notebooks](../2026-05-04-self-hosted-electronic-lab-notebook-elabftw-chemotion-labkey-guide/) for compatible ELN options.

### What about regulatory compliance (GLP, GxP)?

For regulated environments, all three platforms can be deployed with additional controls. OpenTrons provides audit logs in the OT-2 server. PyLabRobot protocols can be version-controlled in Git with signed commits for chain-of-custody. Aquarium includes built-in version control and user action logging. However, for full GxP compliance, you'll need to add validation documentation, electronic signatures, and access controls specific to your regulatory framework.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Lab Automation Platforms: OpenTrons vs PyLabRobot vs Aquarium",
  "description": "Compare three open-source lab automation platforms: OpenTrons (integrated hardware+software), PyLabRobot (hardware-agnostic SDK), and Aquarium (laboratory operating system). Includes Docker Compose deployment, Python protocol examples, and selection guidance for academic, biotech, and core facility labs.",
  "datePublished": "2026-06-10",
  "dateModified": "2026-06-10",
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
