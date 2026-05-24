---
title: "Self-Hosted Disk Forensics: Autopsy vs The Sleuth Kit vs Guymager (2026)"
date: "2026-05-24"
tags: ["disk-forensics", "digital-forensics", "evidence-analysis", "data-recovery", "security-tools"]
draft: false
---

Disk forensics is the practice of recovering, analyzing, and preserving digital evidence from storage media. Whether investigating a security incident, recovering deleted files, or maintaining chain of custody for legal proceedings, having the right self-hosted forensics toolkit is essential.

This guide compares three established disk forensics tools: **Autopsy** (the most popular open-source digital forensics platform), **The Sleuth Kit** (the foundational CLI forensics toolkit), and **Guymager** (a fast forensic disk imager).

## What Is Disk Forensics?

Disk forensics involves extracting and analyzing data from storage devices while maintaining evidential integrity. The core workflow follows these stages:

1. **Imaging** — Create a bit-for-bit copy of the storage media (write-blocked)
2. **Analysis** — Examine the image for deleted files, artifacts, metadata, and patterns
3. **Reporting** — Document findings with chain-of-custody evidence
4. **Preservation** — Store evidence securely for future reference or legal proceedings

Self-hosted forensics tools give organizations complete control over sensitive evidence data, avoiding third-party cloud platforms that may introduce compliance risks or data sovereignty concerns.

## Comparison Overview

| Feature | Autopsy | The Sleuth Kit | Guymager |
|---------|---------|----------------|----------|
| **GitHub Stars** | 3,150+ | 3,070+ | ~400 |
| **Interface** | Web-based GUI | Command-line | Qt GUI |
| **Primary Role** | Forensics platform | CLI toolkit library | Disk imager |
| **Platform** | Linux, Windows, macOS | Linux, Windows, macOS | Linux only |
| **File System Support** | NTFS, FAT, ext, HFS+, APFS, exFAT | NTFS, FAT, ext, HFS+, UFS, ISO9660 | All (passthrough) |
| **Deleted File Recovery** | Yes (carving + metadata) | Yes (metadata + block analysis) | No (imaging only) |
| **Keyword Search** | Yes (indexed, Solr-backed) | Yes (grep-based) | No |
| **Timeline Analysis** | Yes (built-in) | Manual (via mactime) | No |
| **Hash Database** | Yes (NSRL integration) | Yes (hashcalc) | Yes (MD5/SHA256) |
| **Write Blocking** | Software-based | Software-based | Hardware-aware |
| **Imaging Format** | E01, AFF, raw | E01, AFF, raw | E01, raw |
| **Multi-threading** | Yes (Solr indexing) | Limited | Yes (parallel imaging) |
| **License** | Apache 2.0 | CPL/IPL | GPL v2 |

## Autopsy: Comprehensive Digital Forensics Platform

Autopsy is the most widely used open-source digital forensics platform. Built on top of The Sleuth Kit, it provides a web-based graphical interface for end-to-end forensic investigations.

### Architecture

Autopsy runs as a Java application with an embedded web server. The backend uses The Sleuth Kit library for low-level disk analysis and Apache Solr for full-text indexing and keyword search.

### Installation

```bash
# Ubuntu/Debian
sudo apt-get install -y autopsy
# Or download the standalone package from https://www.autopsy.com/download/

# Start the web interface
autopsy &
# Access at http://localhost:9999/autopsy
```

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  autopsy:
    image: ghcr.io/sleuthkit/autopsy:latest
    volumes:
      - /evidence:/evidence:ro
      - /autopsy-data:/root/.autopsy
    ports:
      - "9999:9999"
    environment:
      - AUTOPSY_PORT=9999
    deploy:
      resources:
        limits:
          memory: 4G
        reservations:
          memory: 2G

  solr:
    image: solr:9
    volumes:
      - solr-data:/var/solr
    ports:
      - "8983:8983"
    command: ["solr-precreate", "autopsy"]

volumes:
  solr-data:
```

### Key Features

```bash
# Create a new case via command line
mkdir /evidence/case-2026-001
# Then use the web interface to add evidence items

# Autopsy supports these analysis modules:
# - Hash lookup (NSRL known good/bad files)
# - Keyword search (regular expressions, literal strings)
# - File type identification (TRECVID signatures)
# - EXIF metadata extraction
# - Timeline generation (MAC times)
# - Web artifact extraction (browser history, bookmarks)
# - Email analysis (MBOX, PST, EML parsing)
# - Image gallery (thumbnail generation)
# - Data source visualization (tree, tag, result views)
```

### Strengths and Limitations

**Strengths:**
- Most comprehensive open-source forensics platform available
- Web-based interface accessible from any browser
- Rich plugin ecosystem (Ingest modules)
- Timeline analysis with multi-source correlation
- Solr-powered keyword search across entire disk images
- Active development community (Sleuth Kit org)

**Limitations:**
- Resource-heavy — requires 4 GB RAM minimum for Solr
- Java dependency can complicate deployment
- Web interface can be slow with large datasets (1 TB+)
- Less suitable for live incident response (designed for post-mortem)

## The Sleuth Kit: Foundational CLI Forensics Toolkit

The Sleuth Kit (TSK) is a collection of command-line forensics tools that analyze disk images and file systems. It is the foundation upon which Autopsy and many other forensics tools are built.

### Core Tools

TSK provides specialized commands for different forensic tasks:

```bash
# File system analysis
fsstat disk.img          # Display file system details
fls disk.img             # List files (including deleted)
icat disk.img <inode>    # Extract file content by inode
istat disk.img <inode>   # Show inode metadata

# Volume/partition analysis
mmls disk.img            # Display partition layout
mmstat disk.img          # Volume system statistics

# Timeline generation
mactime -b bodyfile.csv  # Generate MAC time timeline
bodyfile disk.img        # Create body file from disk image

# Data carving
blkls disk.img           # List allocated/unallocated blocks
blkstat disk.img <block> # Show block statistics
blkcalc disk.img         # Calculate original block number

# Hash computation
md5sum disk.img          # Generate MD5 hash
sha256sum disk.img       # Generate SHA-256 hash
```

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  sleuthkit:
    image: ghcr.io/sleuthkit/sleuthkit:latest
    volumes:
      - /evidence:/evidence:ro
      - /output:/output
    entrypoint: ["fls", "-r", "-p", "/evidence/disk.img"]
    deploy:
      resources:
        limits:
          memory: 2G
```

### Typical Forensic Workflow

```bash
# Step 1: Identify partition layout
mmls /evidence/disk.img
# Offset  Type        Size       Description
# 0000000:  Primary     512       -
# 0002048:  NTFS        499 GB    Windows

# Step 2: List all files (including deleted)
fls -r -p -o 2048 /evidence/disk.img > bodyfile.csv

# Step 3: Generate timeline
mactime -b bodyfile.csv -d > timeline.csv

# Step 4: Search for specific files
fls -r -p -o 2048 /evidence/disk.img | grep -i "\.exe$"

# Step 5: Extract a specific file
icat -r -o 2048 /evidence/disk.img <inode_number> > recovered_file.exe
```

### Strengths and Limitations

**Strengths:**
- Lightweight — no GUI, no database, no JVM required
- Scriptable — every tool is a CLI command, perfect for automation
- Foundation for other tools — Autopsy, Autopsy Server, and many forensic scripts use TSK
- Fast — direct block-level access without abstraction layers
- Well-documented — each tool has comprehensive man pages

**Limitations:**
- CLI-only — requires expertise in forensics concepts
- No built-in reporting — output is raw data that must be interpreted
- Limited file carving — focuses on metadata, not content recovery
- No keyword search across entire images (requires external tools like grep)

## Guymager: Fast Forensic Disk Imager

Guymager is a forensic disk imager designed for speed and reliability. It creates bit-for-bit copies of storage media with cryptographic verification, supporting multiple output formats.

### Features

Guymager focuses on one task and does it well: creating forensically sound disk images.

- **Multi-threaded imaging** — parallel read/write for maximum throughput
- **Multiple output formats** — raw (dd), E01 (EnCase), AFF (Advanced Forensics Format)
- **Hardware write-blocker awareness** — detects and respects write-blocking devices
- **Acquisition verification** — automatic MD5 and SHA-256 hash verification
- **Bad sector handling** — configurable strategies for damaged media
- **Network imaging** — pipe output over SSH to remote storage
- **Detailed logging** — acquisition log with timestamps and hash values

### Installation

```bash
# Ubuntu/Debian
sudo apt-get install -y guymager

# Or build from source
git clone https://github.com/GuymagerGuymager/guymager.git
cd guymager
qmake && make && sudo make install
```

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  guymager:
    image: ghcr.io/guymager/guymager:latest
    privileged: true
    volumes:
      - /dev:/dev
      - /evidence:/evidence
      - /tmp/guymager:/root/.config/Guymager
    environment:
      - DISPLAY=:0
    deploy:
      resources:
        limits:
          memory: 2G
    # Note: Requires X11 forwarding or VNC for GUI access
```

### Command-Line Usage (Acquire Mode)

```bash
# Create an E01 image with verification
guymager -i /dev/sda -o /evidence/case-001/sda_image.e01 -f encase

# Create a raw image with SHA-256 verification
guymager -i /dev/sda -o /evidence/case-001/sda_image.raw -f raw

# Image over network to remote server
guymager -i /dev/sda -o /dev/stdout | ssh forensics-server "cat > /evidence/sda_image.raw"

# Verify an existing image
guymager -v /evidence/case-001/sda_image.e01
```

### Strengths and Limitations

**Strengths:**
- Fastest open-source disk imager available
- Multi-threaded for maximum throughput on modern hardware
- Clean GUI with real-time progress and statistics
- Supports E01 format (industry standard for legal proceedings)
- Automatic hash verification ensures acquisition integrity

**Limitations:**
- Linux only — no Windows or macOS support
- GUI-only (no headless CLI mode for scripting)
- Imaging only — no analysis capabilities (use TSK or Autopsy afterward)
- Qt dependency — requires X11 display server
- Smaller community compared to Autopsy/TSK

## Why Self-Host Disk Forensics Tools?

Running forensics tools on your own infrastructure is critical for organizations handling sensitive evidence.

**Chain of custody control.** When evidence data leaves your infrastructure, chain of custody becomes harder to prove. Self-hosted forensics tools ensure evidence never traverses third-party networks or storage. All imaging, analysis, and reporting happens within your controlled environment, making legal admissibility straightforward.

**Compliance and data sovereignty.** Many regulatory frameworks (GDPR, HIPAA, PCI DSS) require forensic data to remain within specific jurisdictions. Cloud-based forensics platforms may store evidence in data centers outside your legal boundaries. Self-hosting guarantees complete geographic control over evidence storage and processing.

**Cost efficiency for large investigations.** Cloud forensics platforms charge per GB of storage and per hour of compute. A single 4 TB disk image can cost hundreds of dollars to store and analyze in the cloud. Self-hosted tools run on your existing hardware with no per-case fees.

**Custom tool integration.** Self-hosted forensics environments can integrate with internal SIEM platforms, ticketing systems, and case management databases. Cloud platforms offer limited customization.

For organizations building a complete forensics pipeline, see our [Digital Forensics Toolkit guide](../2026-04-30-timesketch-vs-plaso-vs-cyberchef-self-hosted-digital-forensics-toolkit-guide-2026/) covering Timesketch, Plaso, and CyberChef. For network-level evidence collection, our [Packet Capture guide](../2026-04-27-tcpdump-vs-tshark-vs-termshark-self-hosted-packet-capture-guide-2026/) covers tcpdump, tshark, and Termshark.

## Recommended Forensics Workflow

For a complete forensic investigation, combine all three tools:

1. **Image with Guymager** — Create a forensically sound E01 image of the source media
2. **Analyze with Autopsy** — Import the E01 image into Autopsy for GUI-based investigation
3. **Script with Sleuth Kit** — Use TSK CLI tools for automated analysis, timeline generation, and bulk operations

This combination covers imaging, analysis, and automation — the three pillars of digital forensics.

## FAQ

### What is the difference between disk imaging and forensic analysis?

Disk imaging creates a bit-for-bit copy of storage media (the acquisition phase). Forensic analysis examines the image for evidence (the investigation phase). Guymager handles imaging, while Autopsy and The Sleuth Kit handle analysis. Always image first — never analyze the original media directly, as this can alter timestamps and metadata.

### Can these tools handle encrypted drives?

Autopsy and The Sleuth Kit can analyze encrypted drives if you provide the decryption key or password. They cannot crack encryption. For BitLocker-encrypted drives, Autopsy can decrypt using the recovery key. For LUKS-encrypted Linux drives, you must unlock the volume before imaging. Guymager images the raw encrypted data — decryption happens during analysis.

### What is the E01 format and why is it preferred in forensics?

E01 (EnCase Evidence File Format) is the industry-standard format for forensic disk images. It includes compressed data, metadata, case information, examiner notes, and embedded hash verification. Unlike raw (dd) images, E01 files are self-documenting and legally admissible in court. Both Guymager and Autopsy support E01 import/export.

### How large a disk image can Autopsy handle?

Autopsy can handle disk images of any size, but performance degrades with images larger than 2-4 TB. The Solr indexing engine requires significant memory for large datasets. For very large investigations, consider processing the image in stages or using The Sleuth Kit CLI tools, which have lower memory requirements.

### Can I automate forensic analysis with these tools?

The Sleuth Kit is designed for automation — every tool is a CLI command that can be scripted. Autopsy provides an Ingest Module API (Java) for custom analysis plugins. Guymager has limited scripting support but can be invoked from shell scripts for batch imaging. For full pipeline automation, combine TSK CLI tools with shell scripts or Python wrappers.

### Are these tools suitable for incident response?

Guymager is suitable for live incident response imaging (run from a bootable USB). The Sleuth Kit can analyze memory dumps and disk images collected during response. Autopsy is designed for post-incident analysis rather than live response. For live incident response, combine these with memory forensics tools (see Volatility 3) and network forensics platforms.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Disk Forensics: Autopsy vs The Sleuth Kit vs Guymager (2026)",
  "description": "Compare three open-source disk forensics tools: Autopsy, The Sleuth Kit, and Guymager. Learn forensic imaging, analysis, and reporting with Docker Compose configs.",
  "datePublished": "2026-05-24",
  "dateModified": "2026-05-24",
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
