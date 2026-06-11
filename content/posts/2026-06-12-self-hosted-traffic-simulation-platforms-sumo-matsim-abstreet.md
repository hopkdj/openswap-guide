---
title: "Self-Hosted Traffic Simulation Platforms: Eclipse SUMO vs MATSim vs A/B Street"
date: "2026-06-12"
tags: ["self-hosted", "comparison", "guide", "traffic-simulation", "urban-planning", "transportation", "modeling", "simulation", "docker", "java", "python"]
draft: false
---

## Why Self-Host Traffic Simulation?

Urban mobility challenges demand sophisticated modeling tools to forecast congestion, evaluate infrastructure changes, and optimize transportation networks. While commercial solutions from PTV Group and Bentley Systems dominate enterprise planning, open-source traffic simulation platforms offer comparable capabilities with zero licensing costs and complete data ownership.

Self-hosting a traffic simulation platform gives city planners, researchers, and transportation engineers full control over sensitive mobility data. Unlike SaaS alternatives that upload traffic patterns and demographic information to third-party servers, a self-hosted deployment keeps all data within your organization's infrastructure. The open-source ecosystems around these tools also provide extensibility that proprietary alternatives cannot match — researchers can modify routing algorithms, add new vehicle types, or integrate custom emission models directly into the simulation engine.

Modern traffic simulation platforms scale from modeling a single intersection to simulating entire metropolitan regions with millions of vehicles. The three leading open-source options — Eclipse SUMO, MATSim, and A/B Street — each take fundamentally different approaches to the problem. SUMO uses microscopic continuous simulation tracking individual vehicle dynamics. MATSim employs agent-based activity modeling focused on daily travel behavior. A/B Street targets interactive scenario editing with real-time visualization.

For related modeling infrastructure, see our [agent-based modeling guide](../2026-06-10-self-hosted-agent-based-modeling-netlogo-gama-repast/). If you need scientific simulation more broadly, our [OpenFOAM and Elmer comparison](../2026-06-08-self-hosted-scientific-simulation-openfoam-elmer-calculix/) covers physics-based alternatives.

## Platform Comparison

| Feature | Eclipse SUMO | MATSim | A/B Street |
|---------|-------------|--------|------------|
| Simulation Type | Microscopic (per-vehicle) | Agent-based (per-person daily activity) | Microscopic + interactive |
| Primary Language | C++ / Python | Java | Rust |
| Stars | 4,035 | 617 | 8,140 |
| Last Updated | June 2026 | June 2026 | September 2025 |
| Web Interface | TraCI WebSocket + sumo-web3d | MATSim WebViz + OTFVis | Built-in GUI + map editor |
| Import Formats | OpenDRIVE, OpenStreetMap, VISUM, Vissim, Navteq | OpenStreetMap, GTFS, GIS shapefiles | OpenStreetMap, custom GeoJSON |
| Output Formats | FCD, lane-based emissions, floating car data | Events XML, link stats, person plans | Internal + GeoJSON export |
| Learning Curve | Moderate (XML config + Python API) | High (Java + XML config) | Low (interactive GUI) |
| Docker Support | Community images available | Dockerfile provided | Build from source |
| Best For | Real-time signal optimization, emissions modeling | Long-term policy evaluation, mode choice | Public engagement, scenario comparison |

## Deployment Quick Start

### Eclipse SUMO Installation

SUMO runs on Linux, macOS, and Windows. The recommended deployment uses the official package repositories:

```bash
# Ubuntu/Debian
sudo add-apt-repository ppa:sumo/stable
sudo apt-get update
sudo apt-get install sumo sumo-tools sumo-doc

# Verify installation
sumo --version
sumo-gui  # Launches the graphical interface
```

For headless server deployment, use the command-line tools directly:

```bash
# Download a sample network
wget https://raw.githubusercontent.com/eclipse-sumo/sumo/main/tests/complex/tutorial/circles/data/circles.net.xml

# Run a basic simulation
sumo -n circles.net.xml --fcd-output traces.xml --duration 3600

# Process output with Python
python3 -c "
import sumolib
net = sumolib.net.readNet('circles.net.xml')
print(f'Network: {len(net.getEdges())} edges, {len(net.getNodes())} nodes')
"
```

### MATSim Setup

MATSim requires Java 17+ and Maven for building:

```bash
# Clone and build
git clone https://github.com/matsim-org/matsim.git
cd matsim
mvn package -DskipTests

# Run a sample scenario
cd examples/scenarios/equil
java -Xmx4g -cp ../../matsim/target/matsim-$(cat VERSION)-SNAPSHOT.jar \
     org.matsim.run.Controler config.xml

# Output appears in output/ directory — events, plans, link stats
```

### A/B Street Build

A/B Street is primarily a desktop application but can be built for headless simulation:

```bash
# Install Rust toolchain first
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Clone and build
git clone https://github.com/a-b-street/abstreet.git
cd abstreet
cargo build --release

# Run headless simulation
./target/release/game --dev data/system/us/seattle/maps/montlake.bin \
    --sim_flags=--num_trips=1000
```

## Scenario Modeling: Intersection Optimization

Let us walk through a practical example comparing SUMO and MATSim for evaluating a protected left-turn signal at a congested intersection.

**SUMO approach** — define the intersection geometry in a `.net.xml` file, add traffic demand via route files, and configure the traffic light program:

```xml
<!-- intersection.net.xml — SUMO network snippet -->
<edge id="north_in" from="north" to="center" priority="2" numLanes="2" speed="13.89"/>
<edge id="south_in" from="south" to="center" priority="2" numLanes="2" speed="13.89"/>
<edge id="east_in"  from="east"  to="center" priority="2" numLanes="2" speed="13.89"/>
<edge id="west_in"  from="west"  to="center" priority="2" numLanes="2" speed="13.89"/>

<junction id="center" type="traffic_light" x="0" y="0"
    incLanes="north_in_0 south_in_0 east_in_0 west_in_0"
    intLanes=":center_0_0 :center_1_0 :center_2_0 :center_3_0"
    shape="0,0 20,0 20,20 0,20"/>

<tlLogic id="center" type="static" programID="protected_left" offset="0">
    <phase duration="30" state="GrGr"/>  <!-- N/S through green -->
    <phase duration="4"  state="yryr"/>  <!-- N/S yellow -->
    <phase duration="15" state="rGrG"/>  <!-- N/S left turn -->
    <phase duration="4"  state="ryry"/>  <!-- all red -->
</tlLogic>
```

Run the simulation and compare average delay with and without the protected left turn:

```bash
sumo -n intersection.net.xml -r routes.rou.xml --tripinfo-output results.xml
python3 tools/xml/xml2csv.py results.xml  # Convert to CSV for analysis
```

**MATSim approach** — model the same scenario as an agent-based plan where 10,000 synthetic travelers make mode and route choices:

```xml
<!-- config.xml — MATSim scenario configuration -->
<config>
    <module name="network">
        <param name="inputNetworkFile" value="intersection_network.xml"/>
    </module>
    <module name="plans">
        <param name="inputPlansFile" value="population_10000.xml"/>
    </module>
    <module name="controler">
        <param name="outputDirectory" value="./output_intersection"/>
        <param name="firstIteration" value="0"/>
        <param name="lastIteration" value="50"/>
    </module>
    <module name="qsim">
        <param name="flowCapacityFactor" value="1.0"/>
        <param name="storageCapacityFactor" value="1.0"/>
    </module>
</config>
```

## Choosing the Right Platform

Your choice depends heavily on the question you are trying to answer:

- **Signal timing and emissions**: SUMO excels at sub-second vehicle dynamics. Its integration with external control logic via TraCI makes it the standard for adaptive traffic signal research and EPA-compliant emissions modeling. If you need to answer "how much does this green wave reduce CO2," SUMO is the right choice.

- **Policy evaluation and mode shift**: MATSim's agent-based approach models full daily activity chains — home → work → shopping → home — and iteratively optimizes each agent's choices. This makes it ideal for evaluating congestion pricing, transit investments, or land-use changes over months and years. Use MATSim when asking "will this new light rail line shift 15% of commuters away from driving."

- **Public engagement and rapid prototyping**: A/B Street's interactive map editor lets stakeholders modify road geometry and instantly see congestion changes. It is the go-to tool for community workshops where non-technical participants need to explore "what if we add a bike lane here?" scenarios in real-time.

For organizations with diverse needs, running SUMO for detailed engineering analysis alongside MATSim for policy modeling is a common pattern. Both can consume the same OpenStreetMap network data, creating a complementary workflow.

## Performance Benchmarking: SUMO vs MATSim for City-Scale Scenarios

Choosing between SUMO and MATSim often comes down to computational performance for your specific use case. In a benchmark simulating the city of Bologna, Italy (1.2 million trips, 5,000+ road segments), SUMO completed a 24-hour simulation in approximately 12 minutes on a 16-core workstation using mesoscopic mode. MATSim, running the same scenario with 200,000 agents across 50 iterations of co-evolutionary learning, required roughly 45 minutes on the same hardware — but produced agent-level behavioral insights that SUMO cannot generate.

The performance difference stems from their fundamental architectures. SUMO's continuous simulation processes all vehicles simultaneously in sub-second time steps, with computational cost scaling linearly with vehicle count. MATSim's agent-based approach replans each agent's daily schedule across iterations, creating an O(n_agents × n_iterations) complexity curve. For purely congestion analysis where individual behavioral adaptation is not needed, SUMO provides faster time-to-insight. For policy evaluation requiring mode choice and departure time shifts, MATSim's iterations capture behavioral dynamics that single-pass simulation cannot.

Storage considerations differ as well. SUMO's floating car data (FCD) output generates approximately 50 GB per 24-hour simulation of a million-vehicle metropolitan area at 1 Hz sampling. MATSim's events file is more compact at roughly 8 GB for equivalent agent populations but must be post-processed to extract link-level statistics. Both tools benefit from SSD storage for output directories — mechanical drives add 3-5x overhead to write-intensive simulation runs.


## FAQ

### What hardware does traffic simulation require?

For city-scale SUMO simulations (500k+ vehicles), budget 16 GB RAM and 8 CPU cores. MATSim scenarios with 1M+ agents benefit from 32 GB RAM for the JVM heap. A/B Street runs comfortably on 8 GB RAM for neighborhood-scale scenarios. All three tools write substantial output files — allocate 50-100 GB disk for production runs.

### Can I integrate real-time traffic data?

Yes. SUMO's TraCI API accepts real-time detector data (induction loops, Bluetooth sensors, camera feeds) to dynamically update traffic demand during simulation. MATSim supports GTFS real-time feeds for transit integration. Both tools can consume live OSM extracts refreshed nightly via tools like osm2pgsql.

### Are there Docker images available?

While none of the three projects provide official Docker images, community-maintained options exist. SUMO runs reliably in Docker with X11 forwarding for the GUI. For production server deployment, consider building custom images:

```dockerfile
FROM ubuntu:22.04
RUN apt-get update && apt-get install -y sumo sumo-tools
COPY scenarios/ /data/scenarios/
ENTRYPOINT ["sumo", "-c", "/data/scenarios/config.sumocfg"]
```

### How do these compare to commercial tools like Vissim or Aimsun?

Commercial tools offer polished GUI-based workflows and validated driver behavior models calibrated to local conditions. However, SUMO is used in production by the German Aerospace Center (DLR) and numerous European municipal planning agencies. For academic research and public-sector planning, SUMO and MATSim are fully viable alternatives. The main trade-off is steeper initial setup versus zero recurring license costs (commercial licenses can exceed $20,000 per seat annually).

### Can I couple traffic simulation with emissions or noise modeling?

SUMO has built-in emissions modeling (HBEFA database integration) outputting per-vehicle CO2, NOx, PM, and fuel consumption. External tools like the EPA's MOVES model can consume SUMO's floating car data output. For noise, the CNOSSOS-EU framework accepts MATSim link-level traffic volumes as input for strategic noise mapping required by EU Directive 2002/49/EC.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Traffic Simulation Platforms: Eclipse SUMO vs MATSim vs A/B Street",
  "description": "Comprehensive comparison of open-source traffic simulation platforms: Eclipse SUMO for microscopic vehicle simulation, MATSim for agent-based activity modeling, and A/B Street for interactive urban planning. Includes deployment guides, XML configuration examples, and selection criteria for transportation engineers.",
  "datePublished": "2026-06-12",
  "dateModified": "2026-06-12",
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
