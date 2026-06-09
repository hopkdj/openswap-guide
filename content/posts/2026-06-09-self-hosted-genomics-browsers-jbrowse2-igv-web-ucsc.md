---
title: "Self-Hosted Genomics Browsers: JBrowse 2 vs IGV Web vs UCSC Genome Browser"
date: "2026-06-09"
tags: ["genomics", "bioinformatics", "genome-browser", "research", "visualization", "self-hosted"]
draft: false
---

Genomics data is exploding — a single whole-genome sequencing run can produce hundreds of gigabytes of data that needs interactive visualization. While cloud-hosted genome browsers like the UCSC Genome Browser and Ensembl provide excellent public resources, research labs and clinical organizations increasingly need self-hosted solutions for proprietary data, custom annotation tracks, and HIPAA-compliant environments. In this comparison, we evaluate three open-source genome browsers you can run on your own infrastructure: **JBrowse 2**, **IGV Web App**, and the **UCSC Genome Browser (self-hosted mirror)**.

## Why Self-Host Your Genome Browser?

Public genome browsers are invaluable reference tools, but they are not designed for your private data. When you upload sensitive patient genomic data to a public server, you lose control over where that data resides and who can access it. A self-hosted genome browser keeps all data within your institutional network, meeting HIPAA, GDPR, and institutional review board requirements.

Self-hosted browsers also offer performance advantages. Instead of uploading multi-gigabyte BAM, VCF, or BigWig files over the internet and waiting for remote servers to process them, a local browser accesses files directly from your network storage or HPC cluster. This is critical for clinical genomics where turnaround time matters. You can also pre-compute and cache data tracks for instant loading — something public browsers cannot offer for your custom datasets.

For related bioinformatics infrastructure, see our [guide to genomics workflow pipelines](../2026-06-04-genomics-workflow-pipelines-nextflow-snakemake-cromwell-guide/). If you are building broader research data management, our [electronic lab notebook comparison](../2026-05-04-self-hosted-electronic-lab-notebook-elabftw-chemotion-labkey-guide/) covers platforms for tracking experimental records. For version-controlled research data, our [data versioning guide](../apache-iceberg-vs-hudi-vs-delta-lake-open-data-lakehouse-formats-2026/) explores modern data lake approaches.

## Comparison at a Glance

| Feature | JBrowse 2 | IGV Web App | UCSC GB (Self-Hosted) |
|---------|-----------|-------------|----------------------|
| **GitHub Stars** | 286 | 125 | N/A (not on GitHub) |
| **Architecture** | React + Web Workers | Java (GWT) + servlet | C + CGI-BIN + MySQL |
| **Data Formats** | BAM, CRAM, VCF, BigWig, BigBed, GFF3, BED, FASTA | BAM, VCF, BigWig, BED, GFF, FASTA | All standard formats |
| **Plugin System** | Extensive (React components) | Limited | Track hubs |
| **Mobile Support** | Yes (responsive) | Limited | Limited |
| **Authentication** | Via reverse proxy | Via reverse proxy | Apache auth |
| **Session Sharing** | URL-based | JSON export | Session cart |
| **Search Index** | SPARQL/trix gene search | Built-in locus search | MySQL gene tables |
| **Deployment** | Static files + nginx | Tomcat servlet | CGI + Apache + MySQL |

## JBrowse 2: The Modern React-Based Browser

JBrowse 2 is a complete rewrite of the original JBrowse genome browser, rebuilt from the ground up using React and modern web technologies. It runs entirely in the browser using Web Workers for computation, making it the easiest of the three to deploy and the most responsive for end users.

**Key Strengths:**
- No server-side computation required — all rendering happens in the browser
- Rich plugin ecosystem with community-contributed view types
- Supports linear genome views, circular views, dot plots, and synteny views
- URL-based session sharing enables collaboration without server state
- Excellent documentation and active development community

**Deployment:** JBrowse 2 is distributed as static files that can be served by any web server:

```bash
# Download and deploy JBrowse 2
wget https://github.com/GMOD/jbrowse-components/releases/latest/download/jbrowse-web.zip
unzip jbrowse-web.zip -d /var/www/jbrowse2

# Configure nginx
cat > /etc/nginx/sites-available/jbrowse2 << 'NGINX'
server {
    listen 80;
    server_name genome.yourdomain.com;

    root /var/www/jbrowse2;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # Serve large genomic data files
    location /data/ {
        alias /data/genomics/;
        add_header Access-Control-Allow-Origin "*";
        add_header Accept-Ranges bytes;
    }
}
NGINX

# Enable and start
ln -s /etc/nginx/sites-available/jbrowse2 /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
```

**Adding Data Tracks:**

```bash
# Index a FASTA reference
samtools faidx reference.fa

# Index BAM alignment file
samtools index alignments.bam

# Load assembly and tracks in JBrowse 2 config
# config.json
{
  "assembly": {
    "name": "hg38",
    "sequence": {
      "type": "ReferenceSequenceTrack",
      "trackId": "reference",
      "adapter": {
        "type": "IndexedFastaAdapter",
        "fastaLocation": { "uri": "/data/reference.fa" },
        "faiLocation": { "uri": "/data/reference.fa.fai" }
      }
    }
  },
  "tracks": [
    {
      "type": "AlignmentsTrack",
      "trackId": "alignments",
      "name": "Sample BAM",
      "adapter": {
        "type": "BamAdapter",
        "bamLocation": { "uri": "/data/alignments.bam" },
        "index": { "location": { "uri": "/data/alignments.bam.bai" } }
      }
    }
  ]
}
```

## IGV Web App: Desktop Power in the Browser

IGV (Integrative Genomics Viewer) is the gold standard for desktop genome visualization, and the IGV Web App brings that same visualization engine to the browser. Developed by the Broad Institute, it is widely trusted in clinical genomics settings.

**Key Strengths:**
- Same rendering engine as the desktop IGV — pixel-perfect, publication-quality views
- Built-in support for split-screen and multi-locus views
- Session files (JSON) for reproducible analysis workflows
- Strong support for variant calling formats (VCF) and copy number data

**Deployment:** IGV Web requires a Java servlet container:

```bash
# Install Tomcat
apt install -y tomcat10 openjdk-17-jdk

# Deploy IGV Web
wget https://github.com/igvteam/igv-webapp/releases/latest/download/igv-webapp.war
cp igv-webapp.war /var/lib/tomcat10/webapps/

# Configure for large file support
cat >> /etc/default/tomcat10 << 'EOF'
JAVA_OPTS="-Xmx16g -Djava.awt.headless=true"
EOF

# Enable Byte-Range requests for genomic data
# Add to Tomcat server.xml or use nginx as reverse proxy
cat > /etc/nginx/sites-available/igv-web << 'NGINX'
server {
    listen 80;
    server_name igv.yourdomain.com;

    location / {
        proxy_pass http://localhost:8080/igv-webapp/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /data/ {
        alias /data/genomics/;
        add_header Access-Control-Allow-Origin "*";
    }
}
NGINX

systemctl restart tomcat10 nginx
```

## UCSC Genome Browser (Self-Hosted Mirror): The Institutional Standard

The UCSC Genome Browser has been the reference genome visualization tool for over two decades. While the public instance at genome.ucsc.edu serves millions of researchers, UCSC provides a complete downloadable version that can be self-hosted — commonly referred to as a "Genome Browser in a Box" (GBiB) or the full mirror installation.

**Key Strengths:**
- Largest collection of annotation tracks available — thousands of public datasets
- Mature, well-documented system with decades of institutional knowledge
- Table Browser for programmatic data access
- BLAT sequence alignment server integration for quick sequence searches
- Custom track hubs for organizing private annotation data

**Deployment:** The simplest approach is the GBiB virtual machine, but for full control, install natively:

```bash
# Install prerequisites (Ubuntu 22.04)
sudo apt update
sudo apt install -y apache2 mysql-server libmysqlclient-dev   libssl-dev libpng-dev libgd-dev uuid-dev   libcurl4-openssl-dev libz-dev build-essential

# Download Kent source utilities (UCSC tools)
mkdir ~/ucsc && cd ~/ucsc
rsync -aP rsync://hgdownload.soe.ucsc.edu/genome/admin/exe/linux.x86_64/ ./

# Set up MySQL with genome databases
mysql -u root -e "CREATE USER 'browser'@'localhost' IDENTIFIED BY 'genome';"
mysql -u root -e "GRANT ALL PRIVILEGES ON *.* TO 'browser'@'localhost';"

# Download a genome assembly (example: sacCer3)
# Full mirror requires ~5 TB of disk for all assemblies
wget http://hgdownload.soe.ucsc.edu/goldenPath/sacCer3/database/
```

For production deployments, a full UCSC mirror with the major genome assemblies requires significant storage (5-10 TB) and benefits from SSD storage for the MySQL database hosting annotation tables. Many research institutions run a partial mirror with only the assemblies and annotation tracks relevant to their research focus.

### Hardware Recommendations

| Deployment Scale | RAM | Storage | Notes |
|-----------------|-----|---------|-------|
| Lab (5-10 users) | 16 GB | 500 GB SSD | 2-3 genome assemblies |
| Department (10-50 users) | 32 GB | 2 TB SSD | 5-10 assemblies |
| Institutional (50+ users) | 64+ GB | 10+ TB | Full mirror, multiple assemblies |

For JBrowse 2 and IGV Web, the server primarily serves static files and does not require significant computation. The bottleneck is typically disk I/O for large genomic data files — use SSD storage or a high-performance NAS.

## FAQ

### Can these browsers handle clinical-grade WGS (whole genome sequencing) data?

Yes, all three can visualize WGS data, but performance depends on your data preprocessing. BAM files should be sorted and indexed, and VCF files should be compressed and indexed. For very deep sequencing (100x+ coverage), consider downsampling for visualization or pre-computing coverage tracks as BigWig files, which are much faster to load than raw BAM files.

### How do I secure patient genomic data in a self-hosted browser?

Place the browser behind a reverse proxy (nginx or Apache) with HTTPS and configure authentication — either HTTP Basic Auth, OAuth2 via your institutional SSO, or client certificate authentication. The genomic data files themselves should be on a volume with appropriate filesystem permissions and, ideally, encrypted at rest. For JBrowse 2, authentication headers pass through to the data API since it runs client-side. For IGV Web and UCSC GB, the server-side components must also be protected.

### What formats are supported for annotation tracks?

All three browsers support the standard bioinformatics formats: BED (simple annotations), GFF3/GTF (gene annotations), BigBed (indexed BED), BigWig (coverage/continuous data), and VCF (variants). JBrowse 2 additionally supports GFF3Tabix, VCFTabix, and SPARQL-based gene searches. UCSC GB supports the widest range of legacy formats including PSL, chain/net, and MAF for comparative genomics.

### Can multiple users collaborate on the same browser session?

JBrowse 2 supports URL-based session sharing — the entire view state (position, open tracks, zoom level) is encoded in the URL, so copying the URL shares the exact view with colleagues. IGV Web supports JSON session file export and import. UCSC GB has a session cart system that requires MySQL-backed user accounts for persistent sessions.

### Is JBrowse 2 a drop-in replacement for the original JBrowse?

JBrowse 2 is a complete rewrite with a different architecture, configuration format, and plugin API. While it supports the same core data formats (BAM, VCF, BigWig, etc.), configuration files need to be migrated. The original JBrowse (v1) remains available and is still maintained, but new deployments should start with JBrowse 2 for its modern architecture and active development.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Genomics Browsers: JBrowse 2 vs IGV Web vs UCSC Genome Browser",
  "description": "Compare three self-hosted genome browsers for private genomic data visualization — JBrowse 2 (React), IGV Web App, and UCSC Genome Browser mirror.",
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
      "url": "https://pistack.xyz/logo.png"
    }
  }
}
</script>

---

**💡 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
