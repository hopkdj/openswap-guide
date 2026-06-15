---
title: "Self-Hosted Water Infrastructure Modeling: EPANET vs SWMM vs WNTR"
date: "2026-06-15"
tags: ["water-modeling", "hydraulic-simulation", "stormwater", "infrastructure", "epanet", "scientific-computing"]
draft: false
---

## Introduction

The world's water infrastructure — 2.2 million miles of drinking water pipes in the US alone, plus countless stormwater and wastewater systems — requires continuous modeling and analysis to ensure reliability, water quality, and flood resilience. Aging infrastructure, climate change intensifying extreme weather, and growing urban populations make hydraulic modeling more critical than ever.

Fortunately, the US Environmental Protection Agency (EPA) has developed and maintains a suite of open-source water modeling tools that rival commercial packages costing $10,000+ per seat. This guide covers three essential platforms: **EPANET** (water distribution system modeling), **SWMM** (Storm Water Management Model), and **WNTR** (Water Network Tool for Resilience). Together they form a complete water infrastructure analysis toolkit.

## Comparison Table

| Feature | EPANET | SWMM | WNTR |
|---------|--------|------|------|
| **Primary Focus** | Drinking water distribution systems | Stormwater & wastewater collection | Water network resilience & disaster response |
| **Language** | C (engine), various GUIs | C (engine), Python (pyswmm) | Python |
| **License** | MIT (public domain engine) | Public domain | Custom open-source |
| **GitHub Stars** | 12 (GUI), widespread use | 346 | 436 |
| **Last Updated** | March 2026 | May 2025 | June 2026 |
| **Developer** | US EPA | US EPA | US EPA / Sandia National Labs |
| **Hydraulic Solver** | Demand-driven, gradient method | Dynamic wave, kinematic wave | EPANET-compatible, extended capabilities |
| **Water Quality** | Yes (tracer, age, reactions) | Yes (pollutant buildup/washoff) | Yes (contamination, resilience metrics) |
| **Container Support** | Docker + pyEPANET | Docker + pyswmm | Pip install, Docker configurable |
| **Best For** | Pipe network design, pump scheduling, chlorine decay | Flood modeling, LID design, CSO analysis | Pipe failure analysis, disaster response, network resilience |

## EPANET: Drinking Water Distribution Analysis

EPANET, first released by the US EPA in 1993 and continuously updated, is the global standard for modeling pressurized water distribution systems. Despite its simple GUI repository having only 12 GitHub stars, EPANET's computational engine has been integrated into nearly every commercial water modeling package (WaterGEMS, InfoWater, MIKE URBAN) and powers thousands of municipal water system models worldwide.

EPANET models:
- **Hydraulic behavior** — pipe flows, pressures, pump operations, tank levels
- **Water quality** — chlorine decay, water age, contaminant transport, disinfection byproduct formation
- **Extended period simulation** — time-varying demands, pump schedules, tank filling/draining cycles
- **Scenario analysis** — fire flow, pipe breaks, pump failures, demand projections

### Installing EPANET with Python

The pyEPANET (Open Water Analytics) package provides a modern Python interface:

```bash
# Install via pip
pip install epynet

# Or use owa-epanet (Open Water Analytics fork)
pip install owa-epanet
```

A complete water distribution analysis in Python:

```python
from epynet import Network

# Load an EPANET input file
ws = Network('data/Net3.inp')

# Run hydraulic simulation
ws.solve()

# Get results
for link in ws.links:
    flow = ws.get_link_flow(link.uid)
    velocity = ws.get_link_velocity(link.uid)
    if abs(flow) > 1.0:  # Only show significant flows
        print(f"Pipe {link.uid}: Flow={flow:.1f} GPM, Velocity={velocity:.2f} ft/s")

# Get node pressures
for node in ws.junctions:
    pressure = ws.get_node_pressure(node.uid)
    head = ws.get_node_head(node.uid)
    print(f"Junction {node.uid}: Pressure={pressure:.1f} psi, Head={head:.1f} ft")

# Water quality analysis
print(f"\nTank water age: {[ws.get_node_quality(t.uid) for t in ws.tanks]}")
print(f"System demand: {sum(abs(ws.get_link_flow(l.uid)) for l in ws.links if ws.get_link_flow(l.uid) > 0):.1f} GPM")
```

### EPANET with Docker

```yaml
version: '3.8'
services:
  epanet-api:
    image: python:3.11-slim
    working_dir: /app
    volumes:
      - ./models:/app/models
      - ./results:/app/results
    command: >
      bash -c "pip install epynet &&
               python3 -c 'from epynet import Network;
               ws = Network("/app/models/network.inp");
               ws.solve();
               print("Simulation complete")'"
```

## SWMM: Stormwater and Wastewater Management

SWMM (Storm Water Management Model), also from the US EPA, is the dominant open-source platform for urban drainage system modeling. Used by municipalities and engineering firms globally, SWMM simulates:

- **Stormwater runoff** quantity and quality from urban catchments
- **Pipe and channel hydraulics** using dynamic wave routing
- **Low Impact Development (LID)** controls: rain gardens, permeable pavement, green roofs, rain barrels
- **Combined sewer overflow (CSO)** analysis and mitigation design
- **Continuous simulation** over months or years with rainfall time series

### Installing SWMM with Docker

```bash
# Pull the pyswmm Docker image
docker pull pyswmm/pyswmm:latest

# Run a SWMM simulation
docker run -it --rm \
  -v $(pwd)/models:/app/models \
  -v $(pwd)/results:/app/results \
  pyswmm/pyswmm:latest \
  python3 /app/models/run_swmm.py
```

A SWMM simulation with LID controls using pyswmm:

```python
from pyswmm import Simulation, Nodes, Links

with Simulation('models/urban_catchment.inp') as sim:
    # Monitor node flooding
    node_depths = {}
    node_flooding = {}
    
    for node_name in ['J1', 'J2', 'J3', 'Outfall']:
        node_depths[node_name] = []
        node_flooding[node_name] = 0
    
    for step in sim:
        for name in node_depths:
            depth = Nodes(sim)[name].depth
            flooding = Nodes(sim)[name].flooding
            node_depths[name].append(depth)
            if flooding > 0:
                node_flooding[name] += flooding
    
    # Report flooding statistics
    for name, total_flood in node_flooding.items():
        max_depth = max(node_depths[name])
        print(f"Node {name}: Max depth={max_depth:.2f} ft, Total flood={total_flood/1000:.1f} MG")
    
    # System statistics
    total_inflow = sum(Nodes(sim)[n].total_inflow for n in ['J1', 'J2', 'J3'])
    print(f"\nTotal system inflow: {total_inflow:.1f} cfs")
    
    # LID performance
    for lid in sim._model.getLidUnits():
        print(f"LID {lid}: Surface depth={lid.surfaceDepth:.2f} in")
```

## WNTR: Water Network Resilience and Disaster Response

WNTR (Water Network Tool for Resilience), developed by the EPA and Sandia National Laboratories, extends EPANET's capabilities for resilience analysis. With 436 GitHub stars and continuous development, WNTR adds:

- **Pipe failure simulation** — probabilistic pipe breaks, leak modeling
- **Disaster scenarios** — earthquakes, power outages, contamination events
- **Resilience metrics** — population impacted, time to restore service, water service availability
- **Response strategies** — isolation valve operations, emergency interconnections, mobile treatment
- **Advanced hydraulics** — pressure-dependent demand, which EPANET doesn't natively support

### Installing and Using WNTR

```bash
# Install via pip
pip install wntr

# Verify
python3 -c "import wntr; print(wntr.__version__)"
```

Resilience analysis with WNTR:

```python
import wntr
import matplotlib.pyplot as plt

# Load a water network model
wn = wntr.network.WaterNetworkModel('models/Net3.inp')

# Simulate an earthquake scenario
# Close valves to isolate damaged pipes
wn.options.duration = 24 * 3600  # 24-hour simulation

# Add pipe leaks (simulating earthquake damage)
for pipe_name in ['10', '12', '15', '20']:
    if pipe_name in wn.pipe_name_list:
        pipe = wn.get_link(pipe_name)
        pipe.status = 'OPEN'  # Pipe remains open
        # Add a leak node at midpoint
        wn = wntr.network.split_pipe(wn, pipe_name, f'{pipe_name}_leak', f'{pipe_name}_B')

# Run pressure-dependent demand simulation
sim = wntr.sim.WNTRSimulator(wn)
results = sim.run_sim()

# Analyze resilience metrics
pressure = results.node['pressure']
pressure_below_20psi = (pressure < 20 * 6894.76).astype(int)  # 20 psi threshold

# Population impacted
for junction in wn.junction_name_list:
    # Count time steps with pressure below threshold
    time_below = pressure_below_20psi.loc[:, junction].sum()
    if time_below > 0:
        base_demand = wn.get_node(junction).base_demand
        print(f"Junction {junction}: {time_below} hours below 20 psi, base demand={base_demand*15850:.0f} GPD")

# Water service availability
normal_pressure = (pressure >= 40 * 6894.76).sum().sum()
total_checks = pressure.size
service_availability = normal_pressure / total_checks * 100
print(f"\nWater service availability: {service_availability:.1f}%")
```

## Deployment Architecture

For municipal-scale water infrastructure modeling, consider:

### Integration Workflow

Municipalities typically chain these tools:
1. **SWMM** models stormwater runoff and LID effectiveness
2. **EPANET** analyzes drinking water distribution hydraulics and quality
3. **WNTR** evaluates network resilience under pipe failure and disaster scenarios

Together, they form a comprehensive platform for water infrastructure planning, capital improvement prioritization, and emergency preparedness.

For managing the Docker deployment of these simulation environments, see our [container orchestration guide](../docker-compose-vs-podman-compose-vs-nerdctl-container-compose-tools-2026/). For teams managing complex infrastructure configurations, our [drift detection guide](../self-hosted-infrastructure-drift-detection-driftctl-cloud-custodian-opentofu-guide-2026/) covers maintaining consistent simulation environments.

## FAQ

### Are EPANET and SWMM accurate enough for real engineering projects?

Yes. EPANET's hydraulic engine has been validated against physical pipe networks for over 30 years and is embedded in commercial packages used by thousands of municipalities. SWMM's dynamic wave routing and LID modeling are peer-reviewed and accepted by regulatory agencies including the EPA, FEMA, and state environmental departments. The key to accuracy is high-quality input data, not the solver.

### How do these compare to commercial tools like WaterGEMS or InfoWorks?

The EPA engines power the hydraulic cores of many commercial tools. WaterGEMS (Bentley), InfoWater (Innovyze/Autodesk), and MIKE URBAN (DHI) all integrate EPANET's computational engine. You're essentially paying $8,000-15,000 per seat for the GUI, GIS integration, and calibration tools — the hydraulic solver is the same open-source engine.

### Can I handle large-scale models with thousands of pipes?

Yes. EPANET handles networks of 100,000+ pipes efficiently. SWMM with dynamic wave routing is more computationally intensive but handles city-scale models (10,000+ nodes) on modern hardware. For the largest regional models, consider parallel simulation with pyswmm's multiprocessing support or cloud-based batch simulation.

### What's the best way to learn these tools?

Start with EPANET's graphical interface (downloadable from epa.gov) to understand the modeling concepts visually. Then move to the Python APIs (epynet, pyswmm, wntr) for automation and batch analysis. The Open Water Analytics (OWA) community provides excellent Jupyter notebook tutorials and example models. Expect 1-2 weeks to become productive with the basic tools.

### Do I need GIS integration for these tools?

While the command-line tools work without GIS, most real-world projects benefit from GIS integration. QGIS (open source) has plugins for EPANET and SWMM model creation. For automated workflows, Python libraries like geopandas and shapely can generate input files from shapefiles or GeoJSON. Commercial packages primarily differentiate on GUI/GIS features, not hydraulic accuracy.

---

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Water Infrastructure Modeling: EPANET vs SWMM vs WNTR",
  "description": "Complete guide to open-source water infrastructure modeling platforms from the US EPA: EPANET for drinking water distribution, SWMM for stormwater management, and WNTR for water network resilience analysis. Includes Docker Compose, Python code examples, and deployment architecture.",
  "datePublished": "2026-06-15",
  "dateModified": "2026-06-15",
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
