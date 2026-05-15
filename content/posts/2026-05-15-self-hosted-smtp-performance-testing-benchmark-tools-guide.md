---
title: "Self-Hosted SMTP Performance Testing: smtp-benchmark vs SmtpBench vs MailStorm"
date: "2026-05-15"
tags: ["smtp", "email", "performance-testing", "mail-server", "self-hosted", "comparison", "guide"]
draft: false
---

When deploying a self-hosted mail server — whether it's Postfix, Exim, Haraka, or a commercial MTA — one critical question always arises: how many concurrent connections can it handle, and at what throughput? SMTP performance testing answers this by simulating real-world mail traffic patterns, identifying bottlenecks, and validating capacity before production deployment.

In this guide, we compare three open-source SMTP benchmarking and testing tools: **smtp-benchmark**, **SmtpBench**, and **MailStorm**. Each provides a different approach to measuring SMTP server performance, from simple CLI benchmarks to Docker-based load testing frameworks.

## Why Test SMTP Performance?

SMTP servers are often the bottleneck in email infrastructure. A misconfigured or under-provisioned MTA can cause:

- **Message queue buildup** — messages sit in the queue waiting for processing
- **Connection timeouts** — senders retry and eventually bounce
- **Resource exhaustion** — file descriptor limits, memory pressure, CPU saturation
- **Delivery delays** — SLA violations for time-sensitive email

Performance testing helps you identify these limits before they impact users. By simulating realistic load patterns — hundreds of concurrent connections, varying message sizes, TLS overhead — you can right-size your infrastructure and tune configuration parameters.

## smtp-benchmark — Simple CLI SMTP Testing

[smtp-benchmark](https://github.com/lbeeon/smtp-benchmark) is a straightforward command-line tool for testing SMTP server performance. It connects to a target SMTP server and sends a configurable number of messages, measuring connection times, throughput, and success rates.

**Stars:** 5 | **Last Updated:** 2018

### Key Features

- **Simple CLI interface** — single command to run benchmark tests
- **Configurable parameters** — control concurrent connections, message count, and target server
- **Lightweight** — no dependencies, runs anywhere Go compiles
- **Real-time metrics** — reports connection time, send time, and overall throughput

### Installation and Usage

```bash
# Clone and build
git clone https://github.com/lbeeon/smtp-benchmark.git
cd smtp-benchmark
go build -o smtp-benchmark

# Run a benchmark
./smtp-benchmark -host smtp.example.com -port 25 -concurrent 50 -count 1000
```

### How It Works

smtp-benchmark opens concurrent SMTP connections to the target server, sends test messages, and tracks metrics for each connection. It reports aggregate statistics including average connection time, messages per second, and success/failure rates.

The tool is designed for quick capacity checks rather than sustained load testing. It's ideal for validating a mail server configuration before going live or after making significant changes.

### When to Use smtp-benchmark

- You need a **quick capacity check** of a mail server
- You want to **compare configurations** (before/after tuning)
- You need a **lightweight tool** with no dependencies
- You're testing on a **development or staging** server

### Limitations

- Minimal feature set — no TLS testing, no authentication
- No Docker support — requires Go toolchain to build
- Last updated in 2018 — may not support modern SMTP extensions
- Limited reporting — no detailed metrics or export options

## SmtpBench — Diennea's SMTP Testing Framework

[SmtpBench](https://github.com/NiccoMlt/diennea-smtp-benchmark) is an SMTP benchmark exercise developed as part of the Diennea interview process. It provides a structured approach to SMTP performance measurement with configurable test scenarios.

**Stars:** 1 | **Last Updated:** 2024

### Key Features

- **Structured testing** — configurable test scenarios for different load patterns
- **Docker support** — can be deployed as a containerized testing service
- **Extensible** — designed to be extended with custom test scenarios
- **Interview-tested** — battle-tested as a technical assessment tool

### Docker Deployment

```yaml
version: "3"
services:
  smtpbench:
    image: niccomlt/smtp-bench:latest
    container_name: smtpbench
    environment:
      - SMTP_HOST=mail.example.com
      - SMTP_PORT=25
      - CONCURRENT_CONNECTIONS=100
      - TOTAL_MESSAGES=5000
    networks:
      - mailnet
    restart: unless-stopped

networks:
  mailnet:
    driver: bridge
```

### Architecture

SmtpBench follows a client-server testing pattern where the benchmark client connects to the target SMTP server and executes a predefined test plan. The test plan specifies the number of concurrent connections, message sizes, and any authentication requirements. Results are collected and reported in a structured format.

The tool's design as an interview exercise means it emphasizes clean architecture and extensibility over feature completeness. You can extend it with custom test scenarios by implementing the benchmark interface.

### When to Use SmtpBench

- You want a **containerized** testing tool for CI/CD pipelines
- You need **structured test scenarios** with reproducible results
- You're building **custom test scenarios** on a clean codebase
- You want to integrate SMTP testing into your **deployment pipeline**

### Limitations

- Very small community (1 star)
- Primarily designed as an interview exercise, not a production tool
- Limited documentation for production use
- No built-in TLS or authentication testing

## MailStorm — Python SMTP Load Testing

[MailStorm](https://github.com/skeeved/mailstorm) is a Python-based SMTP load testing tool designed to simulate high-volume email traffic against a target SMTP server. It's built for sustained load testing rather than quick benchmarks.

**Stars:** Minimal | **Last Updated:** 2017

### Key Features

- **Python-based** — easy to customize and extend
- **Sustained load testing** — designed for long-running tests
- **Configurable load profiles** — ramp up, steady state, and ramp down phases
- **Simple installation** — pip install from source

### Installation

```bash
# Install from source
git clone https://github.com/skeeved/mailstorm.git
cd mailstorm
pip install -r requirements.txt

# Run load test
python mailstorm.py --host smtp.example.com --port 25     --connections 200 --duration 300 --rate 50
```

### Docker Deployment

```yaml
version: "3"
services:
  mailstorm:
    build: .
    container_name: mailstorm
    environment:
      - SMTP_HOST=mail.example.com
      - SMTP_PORT=587
      - SMTP_TLS=true
      - CONNECTIONS=200
      - DURATION=600
      - RATE=100
    restart: "no"
```

### Architecture

MailStorm uses Python's asynchronous I/O to manage hundreds of concurrent SMTP connections efficiently. It establishes connections, performs the SMTP handshake, sends test messages, and collects timing data for each phase of the transaction.

The tool supports different load profiles: a ramp-up phase where connections increase gradually, a steady-state phase where the target connection count is maintained, and a ramp-down phase where connections are gracefully closed.

### When to Use MailStorm

- You need **sustained load testing** (minutes to hours)
- You want to **customize test logic** in Python
- You need **load profiling** with ramp-up and ramp-down
- You're comfortable with **Python tooling**

### Limitations

- Last updated in 2017 — may need updates for Python 3.x
- No active community or maintenance
- Limited documentation
- No built-in TLS certificate validation

## Comparison Table

| Feature | smtp-benchmark | SmtpBench | MailStorm |
|---------|---------------|-----------|-----------|
| **Language** | Go | Go/Java | Python |
| **Docker Support** | No | Yes | Yes (custom) |
| **TLS Testing** | No | Limited | Configurable |
| **Authentication** | No | No | Configurable |
| **Load Profiling** | No | Basic | Yes (ramp/steady/down) |
| **Concurrent Connections** | Configurable | Configurable | Configurable |
| **Duration Control** | Message count | Message count | Time-based |
| **Active Development** | No (2018) | Yes (2024) | No (2017) |
| **Best For** | Quick capacity checks | CI/CD integration | Sustained load testing |

## Key SMTP Performance Metrics

When benchmarking your mail server, focus on these metrics:

- **Connections per second** — how many new SMTP connections the server can accept
- **Messages per second** — sustained message throughput
- **Connection latency** — time from TCP connect to SMTP banner
- **Message latency** — time from DATA command to 250 OK response
- **Error rate** — percentage of failed connections or rejected messages
- **Resource utilization** — CPU, memory, and file descriptor usage during the test

## Tuning Your SMTP Server for Performance

Before running benchmarks, ensure your mail server is configured for performance:

```bash
# Postfix key tuning parameters
postconf -e "default_process_limit = 300"
postconf -e "smtpd_client_connection_count_limit = 50"
postconf -e "smtpd_client_message_rate_limit = 0"
postconf -e "maximal_queue_lifetime = 1d"
postconf -e "minimal_backoff_time = 100s"

# Increase file descriptor limit
ulimit -n 65536
```

## Why Self-Host SMTP Performance Testing?

Running your own SMTP benchmark tools gives you complete control over test scenarios, load patterns, and data privacy. Unlike commercial load testing services, self-hosted tools:

- **Keep testing data private** — no third-party access to your mail server metrics
- **Allow unlimited testing** — no per-test or per-hour charges
- **Support custom scenarios** — adapt tests to your specific workload patterns
- **Integrate with CI/CD** — run automated performance tests on every deployment
- **Enable regression testing** — track performance changes across server upgrades

For related reading, see our [SMTP bounce and DSN management guide](../2026-05-10-self-hosted-smtp-bounce-dsn-management-postal-bouncr-postfix-guide/), [email authentication with OpenDKIM and Rspamd](../2026-05-18-self-hosted-email-authentication-opendkim-rspamd-opendmarc-guide/), and [self-hosted mail server comparison](../2026-04-17-self-hosted-email-servers-postfix-exim-haraka-comparison-guide/).


<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted SMTP Performance Testing: smtp-benchmark vs SmtpBench vs MailStorm",
  "description": "Compare three open-source SMTP benchmarking tools for testing mail server performance and capacity.",
  "datePublished": "2026-05-15",
  "dateModified": "2026-05-15",
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

## FAQ

### Why do I need to test SMTP server performance?

SMTP servers handle critical communication for your organization. Without performance testing, you may discover capacity issues only after they cause production outages — bounced emails, delayed notifications, and SLA violations. Testing identifies bottlenecks before they impact users and helps you right-size your infrastructure.

### What is a good messages-per-second rate for an SMTP server?

It depends on your server hardware and configuration. A well-tuned Postfix server on modern hardware can handle 500-2000+ messages per second. For smaller deployments (single VPS), 100-500 messages per second is typical. The key metric is whether your server can handle your peak load with headroom — aim for 50% capacity utilization at peak.

### Can I test SMTP performance in production?

Only with caution. Running load tests against a production mail server can impact real email delivery. Best practice is to test against a staging server with identical configuration and hardware. If you must test in production, use a small fraction of your target load during off-peak hours and monitor carefully.

### Should I test with or without TLS?

Both. TLS adds cryptographic overhead to every connection — key exchange, certificate verification, and encrypted data transfer. Test without TLS to measure baseline throughput, then test with TLS to understand the real-world impact. The difference is typically 10-30% lower throughput with TLS enabled.

### How many concurrent connections should I test?

Start with a low number (10-50 concurrent connections) and gradually increase until you see performance degradation. The point where messages per second stops increasing or error rates start climbing is your server's capacity limit. Test both below and above this threshold to understand your server's behavior under different load conditions.

### How do I interpret SMTP benchmark results?

Focus on three key numbers: throughput (messages/second), latency (average time per message), and error rate (failed connections). A good result shows consistent throughput with low latency and near-zero errors. If throughput drops as connections increase, your server is hitting a resource limit — check file descriptors, process limits, and connection handling configuration.
