---
title: "dnsperf vs kdig vs queryperf: Best DNS Benchmarking Tools 2026"
date: 2026-04-24
tags: ["comparison", "guide", "self-hosted", "dns", "performance", "benchmarking"]
draft: false
description: "Compare dnsperf, kdig, and queryperf for DNS performance benchmarking. Complete guide with Docker setup, benchmark commands, and configuration examples for self-hosted DNS infrastructure testing."
---

When you run your own DNS infrastructure — whether it's an authoritative server, recursive resolver, or DNS-over-HTTPS forwarder — you need a reliable way to measure its performance. Benchmarks tell you if your server can handle the query volume you expect, how latency changes under load, and whether configuration tweaks actually improve throughput.

In this guide, we compare three of the most widely used DNS performance testing tools: **dnsperf** from DNS-OARC, **queryperf** from the BIND9 project (ISC), and **kdig** from the Knot DNS project. Each tool has a different philosophy and feature set, and choosing the right one depends on your testing goals.

## Why Benchmark Your DNS Infrastructure

DNS performance directly impacts every service that depends on name resolution. A slow or overloaded resolver adds latency to web requests, delays email delivery, and can cause timeouts in microservice architectures. Before deploying a DNS server to production — or after making configuration changes like enabling DNSSEC validation, adding response policy zones, or tuning thread counts — you should benchmark to establish a baseline and verify improvements.

Common scenarios where DNS benchmarking is essential:

- **Capacity planning**: Determine how many queries per second (QPS) your resolver can sustain before latency degrades
- **Configuration tuning**: Compare performance with different cache sizes, thread pools, and recursion depth limits
- **Hardware selection**: Test whether a CPU upgrade or additional RAM improves DNS throughput
- **DDoS resilience testing**: Verify your server's behavior under sudden query spikes
- **Migration validation**: Confirm that a new DNS server matches or exceeds the performance of your current setup

## Tool Overview and GitHub Stats

| Feature | dnsperf | queryperf | kdig |
|---------|---------|-----------|------|
| **Project** | DNS-OARC/dnsperf | BIND9/ISC | CZ-NIC/knot-resolver |
| **Language** | C | C | C |
| **Stars** | 480+ | Part of BIND (738+) | 432+ |
| **Last Updated** | Feb 2026 (Codeberg) | Aug 2025 | Apr 2026 (active) |
| **Query Types** | Any via input file | Any via input file | Interactive / batch |
| **Protocol Support** | UDP, TCP, DoT, DoH | UDP, TCP | UDP, TCP, DoT, DoH, DoQ |
| **EDNS Support** | Yes | Yes | Yes |
| **DNSSEC Testing** | Yes (CD/AD flags) | Yes (CD/AD flags) | Yes (full DNSSEC) |
| **Latency Reporting** | Min/Avg/Max/stddev | Min/Avg/Max | Per-query timing |
| **Rate Limiting** | Configurable QPS | None (sends as fast as possible) | None |
| **Multi-threaded** | Yes (parallel workers) | Single-threaded | Single-threaded |
| **Packet Size Testing** | Yes (`-d` data size) | No | Yes (`-b` buffer size) |
| **Output Format** | Summary stats + per-query CSV | Summary stats only | Verbose DNS response |

## dnsperf: The Industry Standard

[dnsperf](https://github.com/DNS-OARC/dnsperf) (now maintained at [Codeberg](https://codeberg.org/DNS-OARC/dnsperf)) is the most widely used DNS benchmarking tool. Originally developed by Nominet and now maintained by DNS-OARC, it is designed for professional-grade DNS performance testing.

### Key Features

- **Rate-controlled testing**: Send queries at a specific QPS to test sustained performance, not just peak burst capacity
- **Multi-threaded**: Parallel query workers simulate realistic concurrent load
- **Multiple transport protocols**: Supports UDP, TCP, DNS-over-TLS (DoT), and DNS-over-HTTPS (DoH)
- **Detailed statistics**: Reports minimum, average, maximum, and standard deviation of response latency, plus drop rates and timeout counts
- **CSV output**: Per-query timing data for post-analysis and graphing
- **EDNS client subnet and DNSSEC flag testing**: Validate resolver behavior with complex query extensions

### Installation

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install -y dnsperf
```

**From source (latest version):**
```bash
sudo apt install -y build-essential libssl-dev libcap-dev libuv1-dev libnghttp2-dev
git clone https://codeberg.org/DNS-OARC/dnsperf.git
cd dnsperf
autoreconf -fi
./configure
make -j$(nproc)
sudo make install
```

**Docker Compose (for containerized testing):**
```yaml
version: "3.8"
services:
  dnsperf:
    image: ghcr.io/dns-oarc/dnsperf:latest
    volumes:
      - ./queryfile.txt:/tmp/queryfile.txt
    command: >
      dnsperf -s 10.0.0.53 -d /tmp/queryfile.txt -c 10 -l 60 -Q 5000
    network_mode: "host"
```

### Benchmark Examples

**Basic UDP benchmark:**
```bash
# Generate a query file with 10,000 random domains
dnsperf-gen -s 10000 -o queryfile.txt

# Run benchmark at 5,000 QPS for 60 seconds with 10 concurrent connections
dnsperf -s 192.168.1.53 -d queryfile.txt -c 10 -l 60 -Q 5000
```

**DNS-over-TLS testing:**
```bash
dnsperf -s 10.0.0.53 -d queryfile.txt -T -l 30 -Q 1000 \
  -y hmac-sha256:mykey:base64key==
```

**With EDNS and DNSSEC flags:**
```bash
dnsperf -s 10.0.0.53 -d queryfile.txt -e 4096 -D -l 30 -Q 2000
```

**Output format for analysis:**
```bash
dnsperf -s 10.0.0.53 -d queryfile.txt -l 60 -Q 3000 \
  -v 2>&1 | tee benchmark.log
```

## queryperf: The BIND9 Built-in Benchmark

[queryperf](https://gitlab.isc.org/isc-projects/bind9) ships as part of the BIND9 source distribution. While BIND's GitHub mirror is archived at 738+ stars, active development continues on GitLab. queryperf is a lightweight, no-frills benchmarking tool that focuses on raw throughput testing.

### Key Features

- **Zero dependencies**: Ships with BIND9, no separate installation needed
- **Simple and fast**: Sends queries as fast as possible — ideal for measuring maximum theoretical QPS
- **Flexible query types**: Supports any DNS record type (A, AAAA, MX, TXT, etc.)
- **Minimal output**: Clean summary statistics without overhead

### Installation

queryperf is included in the BIND9 source tree. To build it:

```bash
sudo apt install -y build-essential libssl-dev libuv1-dev libnghttp2-dev \
  libcap-dev libxml2-dev libjemalloc-dev pkg-config

# Clone from GitLab (active development)
git clone https://gitlab.isc.org/isc-projects/bind9.git
cd bind9

# Build only queryperf (faster than full BIND9 build)
cd contrib/queryperf
./configure
make -j$(nproc)
sudo cp queryperf /usr/local/bin/
```

**Docker setup using LinuxServer.io pattern:**
```bash
# queryperf is not available as a standalone Docker image,
# but you can build it into a lightweight Alpine container:
FROM alpine:3.19
RUN apk add --no-cache build-base openssl-dev libuv-dev nghttp2-dev \
    bind-tools
COPY bind9/contrib/queryperf/ /tmp/queryperf/
WORKDIR /tmp/queryperf
RUN ./configure && make && cp queryperf /usr/local/bin/
ENTRYPOINT ["queryperf"]
```

### Benchmark Examples

**Basic benchmark:**
```bash
# Prepare query file (one query per line)
cat > queryfile.txt << 'EOF'
example.com A
google.com A
cloudflare.com AAAA
test.example.org MX
EOF

# Run benchmark against local resolver
queryperf -d queryfile.txt -s 127.0.0.1
```

**Large-scale throughput test:**
```bash
# Generate 100,000 queries
dnsperf-gen -s 100000 -o large-queryfile.txt

# Run at maximum speed
queryperf -d large-queryfile.txt -s 192.168.1.53
```

**Expected output:**
```
Statistics:

  Queries sent:         100000
  Queries completed:    99847 (99.85%)
  Queries lost:         153 (0.15%)
  Queries delayed(?):   0

  RTT max:              0.045123 sec
  RTT min:              0.000087 sec
  RTT average:          0.001234 sec
  RTT std deviation:    0.002345 sec

  Queries per second:   15432.1
```

## kdig: The Knot DNS Utility

[kdig](https://github.com/CZ-NIC/knot-resolver) is part of the Knot DNS project by CZ-NIC. While primarily a DNS lookup utility (similar to `dig`), kdig supports batch query mode and can be used for performance testing. It has the broadest protocol support of the three tools, including DNS-over-QUIC (DoQ).

### Key Features

- **Broadest protocol support**: UDP, TCP, DoT, DoH, and DNS-over-QUIC (DoQ)
- **DNSSEC validation**: Full DNSSEC verification with detailed output
- **Interactive mode**: Use for individual queries or batch testing
- **TLS/QUIC certificates**: Built-in certificate verification and pinning
- **Part of Knot ecosystem**: Works seamlessly with Knot Resolver and Knot DNS authoritative server

### Installation

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install -y kdig
```

**From source:**
```bash
sudo apt install -y build-essential libgnutls28-dev liblmdb-dev \
  libuv1-dev libdns1-dev libfstrm-dev libngtcp2-dev
git clone https://github.com/CZ-NIC/knot.git
cd knot
autoreconf -fi
./configure --with-tools
make -j$(nproc)
sudo make install
```

**Docker Compose for Knot Resolver with kdig:**
```yaml
version: "3.8"
services:
  knot-resolver:
    image: cznic/knot-resolver:latest
    ports:
      - "53:53/udp"
      - "53:53/tcp"
      - "853:853/tcp"   # DoT
      - "443:443/tcp"   # DoH
    volumes:
      - ./kresd.conf:/etc/knot-resolver/kresd.conf
      - ./root.keys:/etc/knot-resolver/root.keys

  kdig-test:
    image: cznic/knot:latest
    depends_on:
      - knot-resolver
    entrypoint: ["kdig", "@knot-resolver", "example.com", "A"]
```

### Benchmark Examples

**Batch query mode:**
```bash
# Single query timing
kdig @192.168.1.53 example.com A +stats

# Batch mode with input file
while read domain type; do
  kdig @192.168.1.53 "$domain" "$type" +stats
done < queryfile.txt

# DNS-over-TLS query
kdig @tls://10.0.0.53 example.com A +dnssec

# DNS-over-QUIC query (cutting-edge)
kdig @quic://10.0.0.53 example.com A +dnssec
```

**Measuring individual query latency:**
```bash
# Time 100 queries and calculate average
for i in $(seq 1 100); do
  kdig @192.168.1.53 example.com A +time=5 2>&1 | \
    grep "Query time" | awk '{print $4}'
done | awk '{sum+=$1; count++} END {print "Avg:", sum/count, "ms"}'
```

## Performance Comparison Summary

| Metric | dnsperf | queryperf | kdig |
|--------|---------|-----------|------|
| **Best Use Case** | Sustained load testing | Max throughput testing | Protocol-specific testing |
| **Realistic Simulation** | Excellent (rate-limited) | Poor (unlimited burst) | Moderate (manual loops) |
| **Protocol Coverage** | UDP/TCP/DoT/DoH | UDP/TCP only | UDP/TCP/DoT/DoH/DoQ |
| **Statistical Depth** | Full distribution | Basic min/avg/max | Per-query manual |
| **Ease of Setup** | Package manager | Compile from source | Package manager |
| **Automation Friendly** | Yes (CSV output) | Yes (simple output) | Partial (script needed) |

## Choosing the Right Tool

**Use dnsperf when:**
- You need rate-controlled, sustained load testing that mirrors production traffic patterns
- Statistical analysis matters (standard deviation, drop rates, percentiles)
- You are testing DoT or DoH endpoints
- You need CSV output for integration with monitoring dashboards

**Use queryperf when:**
- You want to measure the absolute maximum QPS a server can handle
- You are already running BIND9 and want a zero-dependency tool
- You need a quick, simple benchmark without complex setup
- Raw throughput is your only metric of interest

**Use kdig when:**
- You need to test DNS-over-QUIC (DoQ) endpoints — it is the only tool of the three with native DoQ support
- You are evaluating Knot Resolver and want ecosystem-consistent tooling
- You need detailed DNSSEC validation output alongside timing data
- You want a single tool for both ad-hoc queries and batch performance testing

For a comprehensive benchmarking strategy, consider using dnsperf for sustained load testing and kdig for protocol-specific validation (especially DoQ). queryperf is useful for quick sanity checks and maximum throughput numbers.

## Related Reading

For related DNS infrastructure topics, see our [PowerDNS vs BIND9 vs NSD authoritative DNS comparison](../2026-04-18-powerdns-vs-bind9-vs-nsd-vs-knot-self-hosted-authoritative-dns-2026/), the [dnsdist load balancing guide](../dnsdist-vs-powerdns-recursor-vs-unbound-self-hosted-dns-load-balancing-guide/), and our guide to [Knot Resolver vs Blocky for DNS-over-QUIC](../2026-04-21-knot-resolver-vs-blocky-vs-dnscrypt-proxy-self-hosted-dns-over-quic-guide-2026/).

## FAQ

### What is the difference between dnsperf and queryperf?

dnsperf supports rate-controlled testing with configurable QPS limits, multi-threaded query workers, and detailed statistical output including standard deviation. queryperf sends queries as fast as possible with no rate limiting, making it suitable only for measuring maximum theoretical throughput. dnsperf is the better choice for realistic load simulation.

### Can I use these tools to test DNS-over-HTTPS (DoH) servers?

dnsperf supports DoH testing natively with the `-T` flag (TLS) and HTTPS endpoint configuration. kdig can test DoH endpoints using `@https://server/dns-query` syntax. queryperf only supports UDP and TCP — it cannot test encrypted DNS protocols.

### How many queries should I send for a reliable benchmark?

For statistical reliability, aim for at least 10,000 queries at your target QPS. Run the test for a minimum of 60 seconds to account for DNS cache warming effects and transient network fluctuations. For production capacity planning, run tests at 50%, 75%, 90%, and 100% of your expected peak load.

### Does dnsperf work with DNSSEC-enabled resolvers?

Yes. dnsperf supports the `+dnssec` flag (`-D`) to set the DNSSEC OK (DO) bit in queries, and the `+cdflag` to set the Checking Disabled bit. This allows you to test how DNSSEC validation impacts resolver latency and throughput — a critical measurement for production deployments.

### How do I generate a realistic query file for benchmarking?

Use the `dnsperf-gen` utility (included with dnsperf) to generate random query files:

```bash
dnsperf-gen -s 50000 -o queryfile.txt
```

For production-accurate testing, capture real query logs from your DNS server and convert them to queryperf/dnsperf input format. This preserves your actual query distribution (record types, domain popularity, EDNS usage).

### Is kdig a suitable replacement for dig in benchmarking scripts?

kdig is primarily a diagnostic tool like dig, not a dedicated benchmarking tool. While you can script kdig in a loop to measure individual query latency, it lacks the built-in statistical aggregation and rate control of dnsperf. Use kdig for protocol-specific testing (especially DoQ) and dnsperf for comprehensive load benchmarks.

### What does QPS mean in DNS benchmarking?

QPS stands for "queries per second" — the primary throughput metric for DNS servers. A resolver handling 10,000 QPS can process 10,000 individual DNS queries every second. Benchmarking at different QPS levels helps identify the point where latency begins to degrade (the "knee" of the performance curve), which determines your safe operational capacity.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "dnsperf vs kdig vs queryperf: Best DNS Benchmarking Tools 2026",
  "description": "Compare dnsperf, kdig, and queryperf for DNS performance benchmarking. Complete guide with Docker setup, benchmark commands, and configuration examples for self-hosted DNS infrastructure testing.",
  "datePublished": "2026-04-24",
  "dateModified": "2026-04-24",
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
