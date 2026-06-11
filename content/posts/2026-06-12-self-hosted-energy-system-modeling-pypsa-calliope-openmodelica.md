---
title: "Self-Hosted Energy System Modeling Frameworks: PyPSA vs Calliope vs OpenModelica"
date: "2026-06-12"
tags: ["self-hosted", "comparison", "guide", "energy-modeling", "power-systems", "renewable-energy", "optimization", "simulation", "docker", "python", "modelica"]
draft: false
---

## Why Self-Host Energy System Modeling?

The global energy transition demands sophisticated tools to model increasingly complex electricity systems. Grid operators, energy consultancies, and academic research groups need to simulate scenarios integrating renewables, storage, demand response, and sector coupling — from rooftop solar adoption rates to continent-scale transmission expansion. Commercial tools like PLEXOS and Aurora command five-figure annual licenses per seat, putting them out of reach for municipal planning agencies and university departments.

Self-hosting an energy system modeling framework provides three critical advantages: unlimited scenario runs without per-simulation licensing costs, full transparency into model algorithms for regulatory proceedings, and the ability to customize objective functions for local policy priorities. When a city council asks "what happens to electricity prices if we mandate heat pump adoption by 2030," a self-hosted modeling framework can deliver answers within hours rather than waiting weeks for a consultant's report.

The three leading open-source frameworks — PyPSA, Calliope, and OpenModelica — cover the full spectrum from linear optimization of power systems to multi-domain physical simulation. PyPSA specializes in power system and sector coupling optimization with high-performance solving. Calliope provides a declarative modeling interface that separates model definition from solver configuration. OpenModelica brings equation-based physical modeling for detailed component-level simulation.

For IoT-powered energy monitoring, see our [open energy monitor guide](../2026-06-11-self-hosted-energy-management-openenergymonitor-openems-wat/). For related optimization workflows, our [operations research guide](../self-hosted-process-automation-n8n-nodered-huginn-guide/) covers complementary automation tools.

## Framework Comparison

| Feature | PyPSA | Calliope | OpenModelica |
|---------|-------|----------|-------------|
| Modeling Approach | Linear optimal power flow + investment | Declarative linear optimization | Equation-based (acausal) physical modeling |
| Primary Language | Python | Python (YAML-defined models) | Modelica / C runtime |
| Stars | 2,011 | 365 | 1,320 |
| Last Updated | June 2026 | June 2026 | June 2026 |
| Solver Backends | Gurobi, CPLEX, HiGHS, GLPK | GLPK, Gurobi, CPLEX | DASSL, IDA, CVODE, Euler |
| Web Interface | Via Jupyter + Voila dashboards | Via Jupyter notebooks | OMEdit GUI + OMWebService |
| Temporal Resolution | Hourly (sub-hourly with linopy) | Hourly (configurable) | Continuous / event-driven |
| Spatial Resolution | N-bus transmission network | Regular grid / custom regions | Component-level |
| Docker Ready | PyPI + conda (CI Dockerfile) | PyPI + Dockerfile | Docker images available |
| Best For | Transmission expansion, sector coupling | Policy scenario comparison, renewables integration | Multi-physics component simulation |

## Installation and Setup

### PyPSA Quick Start

PyPSA installs via conda for optimal solver integration:

```bash
# Create a dedicated environment
conda create -n pypsa python=3.11
conda activate pypsa

# Install PyPSA with open-source solver
conda install -c conda-forge pypsa highs

# Verify installation
python3 -c "
import pypsa
n = pypsa.examples.ac_dc_meshed()
n.lopf()
print(f'Objective: {n.objective:.2f}')
print(f'Branches: {len(n.lines)} lines, {len(n.links)} links')
"
```

### Calliope Setup

Calliope uses YAML to define models — separating data from logic:

```bash
# Install with pip
pip install calliope

# Create a simple national-scale model
mkdir my_energy_model
cd my_energy_model
```

Define your model in YAML:

```yaml
# model.yaml — Simple two-region energy system
model:
  name: Two-Region Energy System
  calliope_version: 0.7.0
  timeseries_data_path: timeseries.csv

tech_groups:
  pv:
    essentials:
      name: Solar PV
      color: '#FFD700'
      parent: supply
    constraints:
      resource: file=timeseries.csv:pv_capacity_factor
      energy_cap_max: 5000  # MW
      lifetime: 25
    costs:
      monetary:
        energy_cap: 800000  # €/MW

  battery:
    essentials:
      name: Battery Storage
      parent: storage
    constraints:
      storage_cap_max: 2000  # MWh
      energy_cap_max: 1000   # MW
      storage_loss: 0.00001  # per hour
      charge_rate: 0.25
    costs:
      monetary:
        storage_cap: 150000   # €/MWh
        energy_cap: 300000    # €/MW

nodes:
  region_a:
    techs:
      demand_power:
        constraints:
          resource: file=timeseries.csv:demand_region_a
      pv:
      battery:
```

Run the optimization:

```python
import calliope

model = calliope.Model('model.yaml')
model.run()
model.plot.timeseries()
model.to_csv('results/optimal_dispatch.csv')
```

### OpenModelica Installation

OpenModelica provides both an interactive modeling environment (OMEdit) and a command-line compiler:

```bash
# Linux installation
sudo apt-get install openmodelica omedit

# Verify
omc --version
```

Create a basic power system model:

```modelica
// PowerSystem.mo — Simple generator and load model
model SimpleGrid
  Modelica.Electrical.Analog.Sources.SineVoltage generator(
    V=230*sqrt(2), freq=50
  );
  Modelica.Electrical.Analog.Basic.Resistor load(R=50);
  Modelica.Electrical.Analog.Basic.Ground ground;
equation
  connect(generator.p, load.p);
  connect(load.n, generator.n);
  connect(generator.n, ground.p);
end SimpleGrid;
```

```bash
# Compile and simulate
omc PowerSystem.mo
./SimpleGrid -override stopTime=1.0 -r results.mat
```

## Renewable Integration Scenario: 80% Wind + Solar

A real-world modeling challenge evaluates whether a grid can operate reliably with 80% renewable penetration. Here is how PyPSA and Calliope approach this:

**PyPSA formulation** — define a network of buses connected by transmission lines, attach generators and storage at each bus, then optimize dispatch and investment simultaneously:

```python
import pypsa
import pandas as pd

n = pypsa.Network()

# Add buses representing regions
for i in range(5):
    n.add("Bus", f"Region {i}")

# Add renewable generators
n.add("Generator", "Wind North",
      bus="Region 0",
      p_nom_extendable=True,
      capital_cost=1200000,  # €/MW
      marginal_cost=0,
      p_max_pu=pd.Series([0.3, 0.35, 0.4, 0.38, 0.25], 
                         index=range(8760)))

# Add storage
n.add("StorageUnit", "Battery",
      bus="Region 0",
      p_nom_extendable=True,
      capital_cost=300000,
      efficiency_store=0.95,
      efficiency_dispatch=0.95)

# Add transmission lines
n.add("Line", "North-South",
      bus0="Region 0", bus1="Region 1",
      s_nom_extendable=True,
      length=150, capital_cost=400000)

# Run optimization
n.optimize(solver_name="highs")
print(f"Wind capacity: {n.generators.at['Wind North','p_nom_opt']:.0f} MW")
print(f"Storage capacity: {n.storage_units.at['Battery','p_nom_opt']:.0f} MW")
```

## Choosing the Right Framework

**Use PyPSA when**: You need to optimize transmission expansion across a meshed network with coupled electricity, heating, and transport sectors. PyPSA's linear optimal power flow (LOPF) formulation scales to continental European networks with thousands of buses. Research groups at TU Berlin, KTH Stockholm, and ETH Zurich use PyPSA for published energy policy studies. The framework integrates with the atlite library for automated weather data conversion to renewable generation profiles.

**Use Calliope when**: Policy scenario comparison and model transparency are priorities. Calliope's YAML-based model definitions create self-documenting scenarios that non-programmers can review and modify. The framework deliberately constrains modelers to linear optimization — ensuring models remain solvable and interpretable. Calliope is widely used in UK energy policy analysis, including studies for the Committee on Climate Change.

**Use OpenModelica when**: Dynamic physical behavior matters — generator ramp rates, turbine governor response, voltage transients. OpenModelica models electromagnetic and thermodynamic behavior that linear optimization frameworks abstract away. It is the open-source alternative to MATLAB/Simulink for power systems and is used in industrial control system development.

## Sector Coupling: Beyond Electricity

Modern energy system models increasingly integrate electricity, heating, cooling, and transport into unified optimization frameworks — a methodology called sector coupling. PyPSA has the most mature sector coupling capabilities among the three frameworks, with built-in support for combined heat and power (CHP) plants, heat pumps, district heating networks, and electric vehicle charging profiles.

A fully coupled PyPSA model of Germany with 4,500 buses across electricity, heating, and transport sectors can optimize the coordinated investment in wind turbines, heat pumps, battery storage, and hydrogen electrolyzers simultaneously. The computational cost is significant — approximately 45 million variables and 30 million constraints for a full-year hourly resolution model — but the open-source HiGHS solver handles it on a workstation with 64 GB RAM in approximately 6 hours.

Calliope supports multi-vector modeling through its carrier system, where electricity, heat, and hydrogen are defined as separate carriers with conversion technologies (heat pumps, electrolyzers, fuel cells) linking them. However, Calliope does not currently model networked heating or gas grids — energy is balanced at the node level. For district heating network design, OpenModelica's thermo-fluid library provides the detailed pipe flow, heat loss, and pressure drop calculations that linear optimization frameworks cannot capture.

The emerging standard for sharing sector-coupled models is the Open Energy Modelling Framework (oemof), which provides a graph-based abstraction that PyPSA and Calliope can both consume. Organizations investing in energy modeling today should evaluate whether their chosen framework can consume and export oemof-structured data to future-proof their modeling investments.


## FAQ

### What programming skills do I need?

PyPSA and Calliope require intermediate Python proficiency — comfortable with pandas DataFrames, numpy arrays, and basic optimization concepts. OpenModelica uses the Modelica language, which is declarative (like SQL) rather than procedural — easier for domain engineers without software backgrounds to learn. All three frameworks provide Jupyter notebook tutorials covering their core workflows.

### Can these tools handle real-time grid operations?

Not directly. These frameworks are designed for planning studies (years ahead) and policy analysis, not real-time SCADA integration. For real-time grid monitoring and control, pair them with data acquisition tools like GridAPPS-D or the VOLTTRON platform. PyPSA models can be embedded in dashboards via Voila to provide "what-if" analysis during operations, but the optimization time (minutes to hours) precludes real-time use.

### What solver license do I need?

For academic and small-scale commercial use, the open-source HiGHS solver (Apache 2.0 license) handles PyPSA models up to ~5,000 buses with acceptable performance. Calliope ships with GLPK for small models. For production-scale European network models, a commercial solver (Gurobi with free academic license, or CPLEX) reduces optimization time from hours to minutes. OpenModelica uses its own numerical solvers with no external licensing requirements.

### How do I integrate weather data for renewable forecasting?

All three frameworks consume standard meteorological formats. PyPSA integrates with the atlite library, which automatically converts ERA5 reanalysis data to wind/solar generation profiles:

```python
import atlite
cutout = atlite.Cutout("europe_2024.nc",
    module="era5",
    x=slice(-12, 35), y=slice(35, 72),
    time="2024")
# Convert wind speeds to capacity factors
wind_cf = cutout.wind(turbine="Vestas_V112_3MW")
```

Calliope accepts CSV time series directly. OpenModelica can read weather data through the Modelica Standard Library's weather file reader component.

### Are there pre-built national-scale models available?

Yes. PyPSA-Eur provides a complete open model of the European electricity system at transmission level with one node per country, including existing generation capacities, transmission networks, and renewable potentials. The model is maintained by TU Berlin and used in peer-reviewed energy policy research. Load it directly:

```python
import pypsa
n = pypsa.Network("https://github.com/PyPSA/pypsa-eur/raw/master/resources/networks/elec_s_37.nc")
n.lopf()
```

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Energy System Modeling Frameworks: PyPSA vs Calliope vs OpenModelica",
  "description": "Comprehensive comparison of open-source energy system modeling frameworks: PyPSA for linear optimal power flow and sector coupling, Calliope for declarative policy scenario modeling, and OpenModelica for equation-based multi-physics simulation. Includes installation guides, YAML model definitions, Python optimization code, and renewable integration scenarios.",
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
