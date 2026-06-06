---
title: "Self-Hosted Test Automation Frameworks: labgrid vs OpenHTF vs Testplan"
date: "2026-06-06"
tags: ["test-automation", "qa", "embedded-testing", "manufacturing-test", "ci-cd", "hardware-testing"]
draft: false
---

## Introduction

Testing is where engineering meets reality. While software testing frameworks have matured over decades (pytest, JUnit, Selenium), hardware and manufacturing testing has traditionally relied on proprietary, vendor-locked solutions. Open-source test automation frameworks are changing this — enabling teams to build self-hosted test infrastructure for embedded systems, manufacturing lines, and complex integration testing without per-seat licenses or cloud dependencies.

In this guide, we compare three open-source test frameworks designed for hardware-adjacent and distributed testing: **labgrid** (embedded Linux board testing infrastructure), **OpenHTF** (Google's hardware test framework for manufacturing), and **Testplan** (Morgan Stanley's multi-functional testing framework). Each takes a different approach to test orchestration, and the right choice depends on whether you're testing embedded boards, factory hardware, or complex software systems.

## Types of Test Automation

Test automation frameworks fall into three broad categories:

- **Embedded Testing**: Controlling physical hardware — power relays, serial consoles, USB relays — to automate board-level testing. labgrid excels here.
- **Manufacturing Test**: Running end-of-line tests on assembled products with pass/fail criteria, data collection, and traceability. OpenHTF was built for this.
- **Integration Testing**: Orchestrating multi-service, multi-process test scenarios across distributed systems. Testplan handles this with its multi-test framework.

## Tool Comparison

| Feature | labgrid | OpenHTF | Testplan |
|---------|---------|---------|----------|
| **GitHub Stars** | 475 | 690 | 209 |
| **Language** | Python | Python | Python |
| **Primary Use Case** | Embedded board testing | Manufacturing EOL test | Software integration test |
| **Resource Management** | Yes (built-in) | Yes (plug-based) | No (external) |
| **Physical Hardware Control** | Excellent (relays, USBSerial, PDUs) | Limited (plugin-based) | None (software-only) |
| **Web Dashboard** | No (CLI + pytest) | Yes (built-in frontend) | Yes (built-in UI) |
| **Remote Access** | Yes (SSH, serial, network) | Yes (station framework) | Yes (multi-process) |
| **Reporting** | pytest + JUnit XML | Built-in + exportable | Built-in (rich HTML/PDF) |
| **Docker Support** | Yes (dockerfiles available) | No (pip install) | No (pip install) |
| **Plug-in Architecture** | Driver-based | Plug-in system | Multi-test framework |
| **CI/CD Integration** | pytest (Jenkins, GitLab CI) | CLI + API | Native integrations |
| **Learning Curve** | High (hardware knowledge required) | Medium | Medium |
| **Last Update** | June 2026 | June 2026 | June 2026 |

## labgrid: Embedded Board Testing Infrastructure

labgrid is a Python-based testing framework designed specifically for embedded Linux board testing and hardware-in-the-loop (HIL) automation. It treats physical hardware resources — power relays, USB serial adapters, network switches, SD card muxes — as managed resources that tests can acquire and release.

**Key Features:**
- Resource management with automatic acquisition and release
- Drivers for common lab equipment: USBSerialPort, USBPowerDriver, USBSDWireDevice, NetworkPowerPort
- Remote resource access via SSH — tests can run on a CI server while accessing hardware in a remote lab
- Seamless pytest integration — tests are standard pytest functions
- Strategy-based resource matching (tests declare requirements, labgrid finds matching hardware)
- Built-in support for common embedded workflows: bootloader interaction, kernel boot, network provisioning

**Setting Up labgrid:**

```bash
# Install labgrid
pip install labgrid

# Create a labgrid environment configuration
cat > labgrid.yaml << 'EOF'
# Coordinator runs on the test server
coordinator:
  host: localhost
  port: 20408

# Resources represent physical hardware
resources:
  - name: "usb-relay-1"
    type: "USBPowerPort"
    match:
      ID_PATH: "pci-0000:00:14.0-usb-0:1"
    index: 0

  - name: "serial-console"
    type: "USBSerialPort"
    match:
      ID_SERIAL_SHORT: "FTDI1234"
    speed: 115200

# Places group resources by test target
places:
  - name: "test-board-1"
    resources:
      - "usb-relay-1"
      - "serial-console"
    acquire_timeout: 30
EOF

# Start the coordinator
labgrid-coordinator labgrid.yaml &

# Write a test
cat > test_board.py << 'EOF'
import pytest

@pytest.fixture(scope="session")
def target(labgrid_env):
    """Acquire a test target from labgrid."""
    place = labgrid_env.get_place("test-board-1")
    place.acquire()
    yield place
    place.release()

def test_boot_to_shell(target):
    """Test that the board boots to a shell prompt."""
    # Power cycle the board
    power = target.get_resource("usb-relay-1")
    power.cycle()
    
    # Wait for boot messages on serial console
    serial = target.get_resource("serial-console")
    serial.expect("U-Boot")
    serial.expect("Linux version")
    serial.expect("login:")
EOF

# Run tests
pytest test_board.py -v
```

**Docker Compose for a labgrid Coordinator:**

```yaml
version: "3.8"
services:
  labgrid-coordinator:
    image: python:3.12-slim
    container_name: labgrid-coordinator
    command: >
      sh -c "pip install labgrid &&
             labgrid-coordinator /config/labgrid.yaml"
    volumes:
      - ./config:/config
    ports:
      - "20408:20408"
    restart: unless-stopped
```

## OpenHTF: Manufacturing Test Framework

OpenHTF (Open Hardware Test Framework) was developed at Google for manufacturing end-of-line testing. It's designed for factory floors where test operators need clear pass/fail results, data collection for traceability, and minimal training requirements.

**Key Features:**
- Phase-based test execution with clear pass/fail/skip status
- Built-in web frontend for operator interaction
- Measurement declarations with units, validation, and documentation
- Plug system for extensions (data export, custom UIs, trigger actions)
- Station-based architecture for multi-station factory lines
- History tracking and result export

**Installing OpenHTF:**

```bash
pip install openhtf

# Create a simple manufacturing test
cat > test_product.py << 'EOF'
import openhtf as htf
from openhtf.plugs import user_input

@htf.measures(
    htf.Measurement('firmware_version').equals('2.1.0'),
    htf.Measurement('current_draw_ma').in_range(50, 500).with_units('mA'),
    htf.Measurement('bluetooth_mac').matches_regex(r'^([0-9A-F]{2}:){5}[0-9A-F]{2}$'),
)
def production_test(test):
    """End-of-line test for a connected IoT device."""
    # Test firmware version via serial
    test.measurements.firmware_version = '2.1.0'
    
    # Measure current draw
    test.measurements.current_draw_ma = 120
    
    # Read Bluetooth MAC address
    test.measurements.bluetooth_mac = 'AA:BB:CC:DD:EE:FF'

# Run the test with the built-in web UI
if __name__ == '__main__':
    test = htf.Test(production_test)
    test.add_output_callbacks(htf.output.callbacks.console_summary.ConsoleSummary())
    test.execute()
EOF

python test_product.py
```

## Testplan: Multi-Functional Testing

Testplan from Morgan Stanley is a Python testing framework that supports multiple testing paradigms in a unified system. Unlike labgrid (hardware-focused) and OpenHTF (manufacturing-focused), Testplan is a general-purpose framework that handles unit tests, integration tests, and even performance benchmarks.

**Key Features:**
- Multi-test framework: run unittest, pytest, GTest (C++), and custom tests in a single run
- Rich reporting: HTML reports, PDF export, JSON/XML output
- Interactive web UI for test exploration and debugging
- Multi-process execution for parallel test runs
- Built-in assertions with detailed failure context
- Programmatic test generation for data-driven testing

**Installing Testplan:**

```bash
pip install testplan

# Write a multi-type test suite
cat > test_plan.py << 'EOF'
import sys
from testplan import test_plan
from testplan.testing.multitest import MultiTest, testsuite, testcase
from testplan.report.testing.styles import Style

@testsuite
class HardwareIntegrationSuite:
    @testcase
    def test_api_health(self, env, result):
        """Verify the device API responds."""
        result.true(True, "API health check passed")
    
    @testcase
    def test_data_pipeline(self, env, result):
        """Verify sensor data flows correctly."""
        result.equal(42, 42, "Sensor data matches expected")

@testsuite
class PerformanceSuite:
    @testcase
    def test_response_time(self, env, result):
        """Verify response time is within SLA."""
        result.less(0.5, 1.0, "Response time within 1 second SLA")

@test_plan(name="DeviceIntegrationPlan")
def main(plan):
    plan.add(MultiTest(
        name="HardwareTests",
        suites=[HardwareIntegrationSuite()]
    ))
    plan.add(MultiTest(
        name="PerformanceTests",
        suites=[PerformanceSuite()]
    ))

if __name__ == '__main__':
    sys.exit(main())
EOF

python test_plan.py --ui  # Launches the interactive web UI
```

## Choosing the Right Framework

The choice between labgrid, OpenHTF, and Testplan depends on your testing domain:

- **Choose labgrid** if you're testing embedded Linux boards, IoT devices, or any scenario requiring physical hardware control (power cycling, serial console access, USB muxing). It's the only framework designed specifically for hardware resource management.

- **Choose OpenHTF** if you're running end-of-line tests on a manufacturing floor. The operator-facing UI, measurement validation, and phase-based execution make it ideal for production environments where non-engineers run the tests.

- **Choose Testplan** if you need a general-purpose testing framework that handles multiple test types (unit, integration, performance) and generates professional reports. It's the most flexible option for software-focused teams that occasionally interact with hardware APIs.

## Why Self-Host Your Test Infrastructure?

Self-hosting test automation gives you capabilities that cloud testing services can't provide:

**Hardware Access:** labgrid needs physical access to embedded boards. OpenHTF runs on factory floor machines connected to test fixtures. These are inherently self-hosted — no cloud service can physically power-cycle your development board.

**Confidentiality:** Manufacturing test data contains proprietary information about product yields, failure rates, and quality metrics. Keeping this data on-premises is often a contractual requirement with customers and regulators.

**Latency and Reliability:** Factory floor testing requires sub-second response times. A cloud dependency introduces network latency and a single point of failure — if the internet goes down, your production line doesn't have to stop.

For related testing infrastructure, see our [chaos engineering and fault injection guide](../2026-04-20-toxiproxy-vs-pumba-vs-chaosmonkey-self-hosted-fault-injection-chaos-testing-guide-2026/). For test environments, our [S3 testing tools comparison](../2026-04-23-localstack-vs-s3ninja-vs-s3mock-self-hosted-s3-testing-tools-2026/) covers cloud service emulation. For Kubernetes testing, check our [K8s testing orchestration guide](../2026-05-03-testkube-vs-kube-burner-vs-trow-self-hosted-kubernetes-testing-orchestration/).

## FAQ

### Can labgrid work without dedicated lab hardware?

You can start with minimal hardware — a single Raspberry Pi with a relay HAT and a USB serial adapter costs under $100 and provides enough infrastructure to test one embedded board. labgrid's resource model scales from one target to hundreds as your lab grows.

### Does OpenHTF require Google infrastructure?

No. OpenHTF is a standalone Python package that runs entirely on your infrastructure. Despite originating at Google, it has no dependency on Google Cloud, proprietary services, or external APIs. Install it with pip and run it on any machine with Python.

### How does Testplan compare to pytest?

Testplan can run pytest tests alongside other test types. It's not a replacement for pytest but a higher-level orchestration layer. Use Testplan when you need unified reporting across different test frameworks, programmatic test generation, or its interactive web UI. For simple test suites, pytest alone is sufficient.

### Can these frameworks integrate with CI/CD pipelines?

Yes, all three can. labgrid tests are standard pytest functions — they work natively with Jenkins, GitLab CI, GitHub Actions, and any pytest-compatible CI system. OpenHTF can be invoked from the command line with exit codes for pass/fail. Testplan provides JUnit XML output and built-in CI integration.

### What's the minimum team size for adopting these frameworks?

labgrid and OpenHTF are production-grade — they're worth adopting even for solo developers testing one board. The initial setup investment pays off within weeks through automated testing that catches regressions. Testplan is particularly valuable for teams of 3+ where test suite maintenance across multiple frameworks becomes a coordination challenge.

---

**💰 Want to test your market judgment? I use [Polymarket](https://polymarket.com/?r=fc8a0) for prediction market trading — the world's largest prediction market platform. From election results to technology regulation timelines, you can bet on anything. Unlike gambling, this is a real information market: the more you know, the better your odds. I've made significant returns predicting technology-related events. Sign up with my referral link:** [Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Test Automation Frameworks: labgrid vs OpenHTF vs Testplan",
  "description": "Compare three open-source test automation frameworks for hardware and manufacturing testing: labgrid for embedded board testing, OpenHTF for manufacturing end-of-line tests, and Testplan for multi-functional software integration testing. Includes setup guides and Docker deployment.",
  "datePublished": "2026-06-06",
  "dateModified": "2026-06-06",
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
