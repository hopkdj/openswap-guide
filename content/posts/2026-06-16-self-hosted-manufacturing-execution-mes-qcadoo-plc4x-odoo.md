---
title: "Self-Hosted Manufacturing Execution Systems (MES): Qcadoo MES vs Apache PLC4X vs Odoo Manufacturing"
date: "2026-06-16"
tags: ["manufacturing", "mes", "industrial-automation", "production-management", "self-hosted", "industry-40"]
draft: false
---

## Why Self-Host Your Manufacturing Execution System?

Manufacturing Execution Systems (MES) bridge the gap between enterprise resource planning (ERP) and the factory floor. While ERP systems handle orders, inventory, and accounting, an MES tracks real-time production—what is being made right now, on which machine, by which operator, at what rate, with what quality metrics. For manufacturers committed to Industry 4.0 principles, an MES is the nervous system that connects planning to execution.

Self-hosting an MES gives manufacturers complete data sovereignty over their production information. Unlike cloud-based MES platforms that charge per-machine or per-user licensing fees that scale with growth, open-source MES solutions can be deployed on your own infrastructure with no recurring costs. This matters especially for small to medium manufacturers where every percentage point of margin counts, and for industries with strict data residency requirements like defense, medical devices, and aerospace.

A self-hosted MES also integrates more naturally with your existing shop floor equipment. Rather than forcing your machines to talk to a vendor's proprietary cloud, you can deploy the MES server on-premises with direct network access to PLCs, SCADA systems, and IoT sensors. This reduces latency (critical for real-time production control) and eliminates the risk of internet connectivity issues halting your production visibility. For related infrastructure, see our [self-hosted SCADA systems comparison guide](../2026-05-02-self-hosted-scada-systems-fuxa-scada-lts-rapidscada-guide/).

## Core MES Capabilities

A proper MES should provide these fundamental capabilities:

- **Production scheduling and dispatching**: Assign work orders to specific machines and operators based on availability and priority
- **Real-time OEE tracking**: Overall Equipment Effectiveness monitoring—availability, performance, and quality metrics per machine
- **Genealogy and traceability**: Track every component from raw material to finished product with full batch and serial number history
- **Quality management**: In-process inspections, SPC (Statistical Process Control), defect tracking, and corrective actions
- **Labor tracking**: Operator clock-in/out, skill matrix management, and labor cost allocation to work orders
- **Machine integration**: Direct communication with PLCs, CNC controllers, and sensors via OPC UA, Modbus, or MQTT

## Comparing Self-Hosted MES Platforms

| Feature | Qcadoo MES | Odoo Manufacturing | Apache PLC4X + Custom |
|---------|-----------|-------------------|----------------------|
| **GitHub Stars** | 913+ | 48,000+ (Odoo) | 1,582+ |
| **Type** | Dedicated MES | ERP with MES module | Industrial connectivity framework |
| **Web Interface** | Full web UI | Full web UI | API/library (build your own UI) |
| **Production Orders** | Full workflow | Full workflow | N/A (integration layer) |
| **OEE Dashboard** | Built-in | Via reporting | Requires custom build |
| **Quality Control** | Built-in | Via Quality module | N/A |
| **PLC/Machine Connect** | Modbus, REST API | IoT box, Modbus | OPC UA, Modbus, PLC4X protocols |
| **Deployment** | Docker, Tomcat | Docker, deb package | Java library, Docker |
| **Multi-site** | Yes | Yes | N/A |
| **Learning Curve** | Medium | Medium-High | High (development required) |
| **Best For** | Discrete manufacturing | General manufacturing + ERP | Custom integration projects |

### Qcadoo MES — Purpose-Built Production Execution

Qcadoo MES is a dedicated manufacturing execution system that focuses exclusively on shop floor operations. Unlike ERP modules that bolt manufacturing features onto an accounting platform, Qcadoo was designed from the ground up for production management. It provides visual production line dashboards, real-time OEE calculations, and a modular architecture where you enable only the features your factory needs.

**Docker Compose Deployment:**

```yaml
version: "3.8"
services:
  qcadoo-db:
    image: postgres:15
    container_name: qcadoo-db
    restart: unless-stopped
    environment:
      POSTGRES_DB: qcadoo
      POSTGRES_USER: qcadoo
      POSTGRES_PASSWORD: change_this_password
    volumes:
      - ./qcadoo-db:/var/lib/postgresql/data

  qcadoo-app:
    image: qcadoo/mes:latest
    container_name: qcadoo-app
    restart: unless-stopped
    ports:
      - "8080:8080"
    depends_on:
      - qcadoo-db
    environment:
      DB_HOST: qcadoo-db
      DB_PORT: 5432
      DB_NAME: qcadoo
      DB_USER: qcadoo
      DB_PASS: change_this_password
    volumes:
      - ./qcadoo-files:/opt/qcadoo/files
```

Qcadoo's modular design means you can start with basic production order tracking and gradually enable modules for quality control, maintenance management, and advanced planning. The visual shop floor dashboard provides drag-and-drop scheduling of operations across workstations.

### Odoo Manufacturing — The ERP-Integrated Approach

Odoo's Manufacturing module is part of the broader Odoo ERP ecosystem, which means it comes with seamless integration to inventory, purchasing, accounting, and HR modules. For manufacturers who want a single platform for their entire business, Odoo eliminates the data synchronization headaches between separate MES and ERP systems.

**Odoo Docker Deployment:**

```yaml
version: "3.8"
services:
  odoo-db:
    image: postgres:15
    container_name: odoo-db
    restart: unless-stopped
    environment:
      POSTGRES_DB: odoo
      POSTGRES_USER: odoo
      POSTGRES_PASSWORD: change_this_password
    volumes:
      - ./odoo-db:/var/lib/postgresql/data

  odoo:
    image: odoo:17
    container_name: odoo
    restart: unless-stopped
    ports:
      - "8069:8069"
    depends_on:
      - odoo-db
    environment:
      HOST: odoo-db
      USER: odoo
      PASSWORD: change_this_password
    volumes:
      - ./odoo-data:/var/lib/odoo
      - ./odoo-addons:/mnt/extra-addons
```

Odoo's manufacturing capabilities include bills of materials with multi-level routing, work center capacity planning, and maintenance management. The IoT box connects to shop floor devices, and the quality module handles inspections and alerts. The trade-off is complexity—you are deploying a full ERP even if you only need the MES features.

### Apache PLC4X — The Industrial Integration Layer

Apache PLC4X is not a traditional MES but rather a universal industrial protocol integration library that can serve as the connectivity foundation for a custom MES. It provides a unified API for communicating with PLCs via protocols including Modbus, OPC UA, Siemens S7, Allen-Bradley EtherNet/IP, Beckhoff ADS, and many more—all through a single consistent interface.

**Using PLC4X with Python for Production Monitoring:**

```python
from plc4py.PlcDriverManager import PlcDriverManager

# Connect to a PLC via Modbus TCP
driver_manager = PlcDriverManager()
connection = driver_manager.get_connection("modbus-tcp://192.168.1.100:502")

# Read production counter from PLC register
with connection.read_request_builder() as builder:
    builder.add_item("production_count", "holding-register:100[2]")
    response = connection.execute(builder.build())

count = response.get_integer("production_count", 0)
print(f"Units produced today: {count}")

# Read machine status
with connection.read_request_builder() as builder:
    builder.add_item("machine_status", "coil:50")
    response = connection.execute(builder.build())

status = response.get_boolean("machine_status", False)
print(f"Machine running: {status}")
```

This approach requires software development effort but provides unlimited flexibility. You can build exactly the production monitoring dashboards, alerting rules, and data historians your factory needs, without being constrained by a vendor's feature set.

## Deployment Architecture

For a typical small to medium manufacturing operation, the recommended architecture combines these components:

```
┌─────────────────────────────────────────────┐
│                  ERP Layer                    │
│          (Odoo / ERPNext / Custom)            │
└─────────────────┬───────────────────────────┘
                  │ REST API / Database Sync
┌─────────────────▼───────────────────────────┐
│                  MES Layer                    │
│       (Qcadoo MES / Custom Application)      │
│   - Production Orders  - OEE Tracking        │
│   - Quality Control    - Labor Tracking      │
└─────────────────┬───────────────────────────┘
                  │ OPC UA / Modbus / MQTT
┌─────────────────▼───────────────────────────┐
│           Industrial Connectivity             │
│    (Apache PLC4X / Eclipse Milo / Node-RED)  │
└─────────────────┬───────────────────────────┘
                  │ Fieldbus Protocols
┌─────────────────▼───────────────────────────┐
│              Shop Floor Devices              │
│     PLCs | CNC Controllers | Sensors | HMI   │
└─────────────────────────────────────────────┘
```

This layered approach lets each component focus on its strength: ERP for business processes, MES for production execution, and PLC4X for universal machine connectivity. For managing the warehouse operations that feed your production lines, see our [self-hosted warehouse management systems guide](../2026-05-04-self-hosted-warehouse-management-systems-openboxes-partdb-grocy-guide/).

## FAQ

### What is the difference between MES and SCADA?
SCADA (Supervisory Control and Data Acquisition) focuses on real-time monitoring and control of physical processes—reading sensor values, triggering alarms, and displaying process graphics. MES operates one level above SCADA, focusing on production management: which work orders to run, tracking completion against schedule, measuring quality metrics, and computing OEE. In practice, MES often consumes data from SCADA systems to populate its dashboards.

### Can I use Qcadoo MES without a full ERP?
Yes. Qcadoo MES is designed to operate independently with its own production order management. You can import orders from an external ERP via REST API or CSV files, or create them directly in Qcadoo. This makes it suitable for manufacturers who want to start with MES and add ERP later, or who use a separate accounting-only system.

### How does Odoo Manufacturing compare to a dedicated MES?
Odoo Manufacturing provides about 70-80% of what a dedicated MES offers, with the advantage of zero integration work between manufacturing, inventory, purchasing, and accounting. The trade-offs: OEE tracking is less real-time, machine connectivity requires the IoT box add-on, and deep customization requires Odoo development skills. For manufacturers where the ERP integration benefit outweighs the need for advanced MES features, Odoo is a strong choice.

### Do I need PLC4X if my machines already support OPC UA?
If all your shop floor devices support OPC UA and you have an OPC UA client in your MES, you may not need PLC4X. However, in most real factories, devices span multiple generations and protocols—a newer machine speaks OPC UA while an older one only has Modbus RTU, a packaging line uses EtherNet/IP, and a legacy system uses Siemens S7. PLC4X's value is providing one consistent API across all these protocols, reducing integration complexity.

### What hardware do I need for an on-premises MES server?
For small operations (under 20 machines, under 50 operators), a single server with 8GB RAM, 4 CPU cores, and SSD storage is sufficient for Qcadoo MES or Odoo. Industrial environments benefit from fanless industrial PCs or rack-mounted servers with redundant power supplies. Always use UPS backup—losing your MES during a power outage means losing production visibility when you need it most.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Manufacturing Execution Systems (MES): Qcadoo MES vs Apache PLC4X vs Odoo Manufacturing",
  "description": "Compare self-hosted Manufacturing Execution Systems: Qcadoo MES, Odoo Manufacturing, and Apache PLC4X. Learn how to deploy production management, track OEE, and integrate shop floor PLCs with open-source MES platforms.",
  "datePublished": "2026-06-16",
  "dateModified": "2026-06-16",
  "author": {
    "@type": "Organization",
    "name": "OpenSwap Guide"
  },
  "publisher": {
    "@type": "Organization",
    "name": "OpenSwap Guide",
    "logo": {
      "@type": "ImageObject",
      "url": "https://pistack.xyz/logo.png"
    }
  }
}
</script>
