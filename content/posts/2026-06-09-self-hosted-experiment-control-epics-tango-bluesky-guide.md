---
title: "Self-Hosted Experiment Control & Data Acquisition: EPICS vs Tango Controls vs Bluesky Guide"
date: "2026-06-09"
tags: ["experiment-control", "data-acquisition", "epics", "tango-controls", "bluesky", "scientific-instrumentation", "lab-automation", "synchrotron", "particle-accelerator", "open-science"]
draft: false
---

## Introduction

Large-scale scientific facilities — particle accelerators, synchrotrons, fusion reactors, and astronomical observatories — depend on robust experiment control and data acquisition (DAQ) systems to orchestrate thousands of devices across distributed networks. Three open-source frameworks dominate this space: EPICS (Experimental Physics and Industrial Control System), originally developed at Los Alamos and Argonne National Laboratories; Tango Controls, created by European synchrotron facilities; and Bluesky, a modern Python-based experiment orchestration framework from Brookhaven National Laboratory's NSLS-II.

This guide compares their architectures, deployment patterns, and use cases for self-hosted laboratory automation.

## Architecture Comparison

| Feature | EPICS | Tango Controls | Bluesky |
|---------|-------|---------------|---------|
| **Origin** | LANL/ANL (1990s) | ESRF/ALBA/SOLEIL (2000s) | NSLS-II/BNL (2015+) |
| **Core Language** | C/C++ | C++ (with Java/Python bindings) | Python |
| **Protocol** | Channel Access (CA), PVAccess | CORBA, ZMQ (Tango V10+) | HTTP/ZeroMQ via databroker |
| **Stars** | 193+ (epics-base) | 41+ (cppTango, hosted on GitLab) | 228+ |
| **Deployment Model** | IOC (Input/Output Controller) per device | Device Server per device class | Python scripts with RunEngine |
| **Client Interfaces** | PyEpics, CS-Studio, EDM, Phoebus | Jive, ATKPanel, Taurus, PyTango | IPython, Jupyter, QueueServer |
| **Data Storage** | Archiver Appliance | HDB++, Tango Archiving | Databroker (MongoDB/SQLite) |
| **Web Interface** | Phoebus, WebOPI | Tango WebApp, Canone | JupyterLab, Tiled |
| **Real-time Support** | Native (RTEMS, vxWorks) | Events via ZMQ | Soft real-time via Python |
| **License** | EPICS Open License (BSD-like) | LGPLv3 | BSD-3-Clause |

## Self-Hosted Deployment

### EPICS Base Installation

EPICS uses a distributed model where each hardware interface runs as an Independent IOC (Input/Output Controller):

```bash
# Install EPICS Base from source
git clone --recursive https://github.com/epics-base/epics-base.git
cd epics-base

# Set EPICS environment
export EPICS_BASE=$(pwd)
export EPICS_HOST_ARCH=$(./startup/EpicsHostArch)
export PATH=$PATH:$EPICS_BASE/bin/$EPICS_HOST_ARCH

# Build
make -j$(nproc)

# Create a test IOC
makeBaseApp.pl -t example testIoc
makeBaseApp.pl -i -t example testIoc
cd testIoc
make
cd iocBoot/ioctestIoc
./st.cmd
```

### EPICS Docker Deployment

```yaml
# docker-compose.yml for EPICS soft IOC with Archiver Appliance
version: '3.8'
services:
  epics-soft-ioc:
    image: ghcr.io/epics-base/epics-base:7.0
    container_name: epics-ioc
    network_mode: host
    volumes:
      - ./ioc:/opt/epics/ioc
      - ./db:/opt/epics/db
    command: >
      bash -c "cd /opt/epics/ioc/iocBoot/ioctest &&
               ./st.cmd"
    
  archiver-appliance:
    image: slominskir/archiverappliance:latest
    container_name: epics-archiver
    ports:
      - "17665:17665"
      - "17668:17668"
    volumes:
      - archiver-data:/archiver/stores
    environment:
      - TZ=UTC

volumes:
  archiver-data:
```

### Tango Controls Setup

Tango Controls is primarily developed on GitLab. The core server requires ZeroMQ (V10+) or CORBA:

```bash
# Install Tango Controls on Ubuntu
sudo apt-get install tango-db tango-starter tango-test

# Create MySQL/MariaDB Tango database
mysql -u root -p << 'SQL'
CREATE DATABASE tango;
CREATE USER 'tango'@'localhost' IDENTIFIED BY 'tangopass';
GRANT ALL PRIVILEGES ON tango.* TO 'tango'@'localhost';
FLUSH PRIVILEGES;
SQL

# Start Tango database server
sudo systemctl start tango-db

# Register a test device server
tango_admin --add-server TestServer/dev TestServer test/dev
```

### Tango Docker Compose

```yaml
# docker-compose.yml for Tango Controls stack
version: '3.8'
services:
  tango-db:
    image: mariadb:10.6
    container_name: tango-mariadb
    environment:
      MYSQL_ROOT_PASSWORD: rootpass
      MYSQL_DATABASE: tango
      MYSQL_USER: tango
      MYSQL_PASSWORD: tangopass
    volumes:
      - tango-db:/var/lib/mysql

  tango-ds:
    image: tangocs/tango-cs:latest
    container_name: tango-databaseds
    depends_on:
      - tango-db
    environment:
      TANGO_HOST: tango-ds:10000
      MYSQL_HOST: tango-db
      MYSQL_DATABASE: tango
      MYSQL_USER: tango
      MYSQL_PASSWORD: tangopass
    ports:
      - "10000:10000"

volumes:
  tango-db:
```

### Bluesky Setup

Bluesky takes a fundamentally different approach — it's a Python library that orchestrates experiments programmatically:

```python
# bluesky_experiment.py
from bluesky import RunEngine
from bluesky.plans import scan, grid_scan
from ophyd import EpicsMotor, EpicsSignal
from databroker import Broker

# Connect to EPICS motors via PyEpics
motor_x = EpicsMotor('XF:06BM:MX01', name='motor_x')
motor_y = EpicsMotor('XF:06BM:MX02', name='motor_y')
detector = EpicsSignal('XF:06BM:DET01', name='detector')

# Initialize Bluesky RunEngine
RE = RunEngine({})
db = Broker.named('mongodb_config')
RE.subscribe(db.insert)

# Define and execute a 1D scan
RE(scan([detector], motor_x, -5, 5, 100))
```

### Bluesky in Production

```yaml
# docker-compose.yml for Bluesky Queue Server
version: '3.8'
services:
  bluesky-qs:
    image: python:3.11-slim
    container_name: bluesky-queue-server
    ports:
      - "60610:60610"
    volumes:
      - ./bluesky:/opt/bluesky
    environment:
      - EPICS_CA_ADDR_LIST=epics-gateway
      - DATABROKER_CONFIG=/opt/bluesky/databroker.yml
    command: >
      bash -c "pip install bluesky ophyd databroker &&
               start-re-manager --zmq-publish-console ON"

  mongodb:
    image: mongo:6
    container_name: bluesky-mongo
    volumes:
      - mongo-data:/data/db

volumes:
  mongo-data:
```

## Choosing the Right Control System

### EPICS: For Large Facilities with Hardware Diversity

EPICS is the gold standard for large-scale facilities with hundreds or thousands of heterogeneous devices. Its IOC model provides process isolation — a crashing motor controller won't affect vacuum gauge readings. The Channel Access protocol has proven reliability over 30+ years across facilities like ITER, LCLS, and ESS. If your lab has a mix of PLCs, motion controllers, power supplies, and custom hardware, EPICS provides the most mature driver ecosystem.

### Tango Controls: For European Synchrotron Ecosystems

Tango Controls excels in environments where device classification and object-oriented design make sense. Every hardware type becomes a Device Class with a well-defined interface. The Java-based GUI tools (ATKPanel, Jive) provide polished operator interfaces out of the box. European facilities (ESRF, MAX IV, SOLARIS) have standardized on Tango, making it the natural choice for EU-funded research infrastructure.

### Bluesky: For Flexible, Python-First Experiment Orchestration

Bluesky represents a paradigm shift — rather than being a control system itself, it orchestrates existing control systems (typically EPICS) to run experiments. Its strength is in **automated, reproducible experiment plans** — define a measurement procedure once in Python, then execute it identically thousands of times. For beamline scientists and researchers who want to write experiment logic in Python rather than configuring device servers, Bluesky dramatically reduces the barrier to automation.

## Why Self-Host Your Laboratory Control Infrastructure?

Scientific laboratories have unique data sovereignty requirements that cloud-based industrial control systems cannot satisfy. Proprietary research data — beamline configurations, sample parameters, detector calibrations — constitutes intellectual property that must remain on-premises. A self-hosted EPICS or Tango deployment ensures that your experiment metadata never traverses a public network.

Operational reliability is equally critical. Synchrotron beamtime costs $5,000–$20,000 per hour, and a network outage during a measurement campaign can waste irreplaceable experimental time. Self-hosted control systems with local area network architectures eliminate the single point of failure that cloud-dependent systems introduce. Pair your control infrastructure with [HPC MPI implementations](../2026-06-01-self-hosted-hpc-mpi-implementations-openmpi-mpich-mvapich-guide/) for distributed real-time processing of detector data streams.

Long-term data preservation is a growing concern in experimental science. The [scientific data management platforms](../2026-06-09-self-hosted-scientific-data-management-irods-rucio-datalad-guide/) ecosystem provides tools for cataloging and preserving petabytes of experiment data — but only if your DAQ system generates properly structured metadata from the start. Bluesky's databroker and EPICS Archiver Appliance both emit structured metadata that integrates with data management pipelines.

For laboratories considering hardware-in-the-loop simulation before deploying to physical instruments, [robotics simulation environments](../2026-06-09-self-hosted-robotics-simulation-gazebo-webots-coppeliasim-guide/) provide digital twin capabilities that can validate control logic before it reaches expensive hardware.


## Integration with Laboratory Information Systems

Modern experimental facilities generate metadata at every stage of the measurement pipeline — sample preparation logs, environmental sensor readings, beamline configuration snapshots, and detector calibration parameters. Integrating experiment control frameworks with laboratory information management systems (LIMS) and electronic lab notebooks (ELNs) ensures complete data provenance from sample to publication.

EPICS provides the Archiver Appliance for long-term storage of process variables, with exports to HDF5 and Apache Parquet formats that integrate with scientific data lakes. The Channel Finder service enables dynamic discovery of EPICS channels across distributed IOCs — essential for facilities where beamlines are reconfigured between experiments. Facilities like the European Spallation Source use EPICS combined with Kafka streaming to process 50 GB of control system data per hour.

Tango Controls' event system uses ZeroMQ pub-sub for efficient distribution of device state changes. The Tango REST API (V11+) enables web-based monitoring dashboards built with Grafana, providing operations teams with real-time visibility into facility-wide device health. The HDB++ historical database, based on Cassandra or TimescaleDB, stores years of control system telemetry for long-term trend analysis and anomaly detection.

Bluesky's databroker component stores experiment metadata as structured documents in MongoDB, making it directly queryable via Python analysis scripts. Each Bluesky "run" captures the complete experimental context — motor positions, detector configurations, sample metadata, and environmental conditions — in a self-describing format that satisfies FAIR (Findable, Accessible, Interoperable, Reusable) data principles. This tight coupling between experiment execution and metadata capture eliminates the manual data entry that plagues traditional lab workflows and improves reproducibility.


## FAQ

### Can EPICS and Bluesky be used together?

Absolutely — this is the most common deployment pattern at modern facilities. EPICS provides the low-level device drivers and real-time control, while Bluesky orchestrates experiment plans on top. The NSLS-II facility at Brookhaven runs EPICS IOCs for all hardware and uses Bluesky for all experiment automation. Bluesky speaks EPICS Channel Access natively through the ophyd library.

### What is the learning curve for each system?

EPICS has the steepest initial learning curve — it requires understanding IOCs, databases (`.db` files), Channel Access, and the build system. Budget 2–4 weeks for basic proficiency. Tango Controls has a moderate learning curve focused on object-oriented device modeling. Bluesky has the gentlest learning curve for Python-proficient scientists — you can run a scan in under an hour.

### How do these systems handle real-time requirements?

EPICS provides the strongest real-time guarantees, supporting RTEMS and vxWorks real-time operating systems for microsecond-precision timing. Tango relies on ZMQ for event distribution with millisecond latency. Bluesky is soft real-time — it's suitable for sub-second control loops but not for hard real-time applications like fast orbit feedback (<1 kHz).

### Are there any facility-scale reference deployments?

EPICS runs the ITER fusion reactor (10,000+ IOCs), the LCLS X-ray laser at SLAC, and the ESS neutron source. Tango Controls operates at ESRF (European Synchrotron), MAX IV, and ELI Beamlines. Bluesky is the experiment orchestration layer at NSLS-II and is being adopted at APS-U (Advanced Photon Source Upgrade) and LCLS-II.

### What hardware interfaces are supported?

All three systems support the major industrial protocols: Modbus, OPC-UA, Ethernet/IP, GPIB, and serial. EPICS has the largest driver library (thousands of community-contributed device supports). Tango integrates well with PLC-based systems. Bluesky relies on lower-level drivers from EPICS or Tango and adds Python-level abstraction — any hardware with a Python library can be integrated.

### What about smaller laboratories with limited IT support?

Bluesky on a single workstation with simulated hardware is an excellent starting point. Once comfortable, add EPICS IOCs on Raspberry Pi devices for physical hardware control. Start with one motor and one detector, then scale horizontally. The [HPC container runtimes guide](../2026-06-01-self-hosted-hpc-container-runtimes-apptainer-charliecloud-podman-hpc-guide/) covers containerization strategies that simplify deployment across heterogeneous lab hardware.


<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Experiment Control and Data Acquisition: EPICS vs Tango Controls vs Bluesky Guide",
  "description": "Compare EPICS, Tango Controls, and Bluesky for self-hosted laboratory experiment control and data acquisition. Includes Docker deployment, architecture comparison, and facility-scale reference deployments.",
  "datePublished": "2026-06-09",
  "dateModified": "2026-06-09",
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