---
title: "Stirling-PDF: Complete Guide to Self-Hosted PDF Toolkit 2026"
date: 2026-04-12
tags: ["comparison", "guide", "self-hosted", "privacy"]
draft: false
description: "How to self-host Stirling-PDF, a free all-in-one PDF toolkit with 50+ tools for merging, splitting, converting, editing, and securing PDFs without sending your documents to the cloud."
---

If you regularly work with PDFs, you've probably visited at least one of those "free PDF tool" websites. You upload your document, wait for processing, and hope nothing sensitive leaks in the process. The reality is that many of these free services store your files on their servers — sometimes indefinitely — and some even use uploaded documents to train machine learning models.

There is a better way. **Stirling-PDF** is an open-source, self-hosted web application that gives you 50+ PDF tools running entirely on your own infrastructure. No uploads to third-party servers. No hidden data collection. No per-page limits or paywalls. Just a full-featured PDF toolkit under your control.

## Why Self-Host Your PDF Tools

Every time you use an online PDF service, you are making a trust decision. You are trusting that the service will:

- **Delete your files** after processing (most don't, at least not immediately)
- **Not read your documents** for analytics or training purposes
- **Secure your data** against breaches and unauthorized access
- **Remain available** when you need it, without changing their pricing model

For personal documents like bank statements, tax returns, medical records, or legal contracts, this trust is hard to justify. Even for business documents, sending files to unknown servers creates compliance risks under GDPR, HIPAA, and other data protection regulations.

Self-hosting Stirling-PDF eliminates these concerns entirely. Your documents never leave your machine. Processing happens locally in your Docker container. The only network traffic is your browser talking to your own server. And because the entire project is open-source under the MIT license, you can audit every line of code yourself.

Stirling-PDF has grown to become one of the most popular open-source document tools on GitHub, with over 50,000 stars. It supports a wide range of operations:

| Category | Operations |
|---|---|
| **Merge & Split** | Merge multiple PDFs, split by pages, extract specific page ranges |
| **Convert** | PDF to images, images to PDF, PDF to Word, PDF to Excel, Office to PDF |
| **Edit** | Add watermarks, rotate pages, reorder pages, crop PDFs |
| **Security** | Password-protect, remove passwords, add digital signatures, redact text |
| **Optimization** | Compress PDFs, repair corrupted files, OCR scanned documents |
| **Metadata** | View and edit metadata, flatten form fields, extract images from PDFs |

The web interface is clean and intuitive — no registration, no ads, no pop-ups. And for advanced users, Stirling-PDF offers a REST API for automation.

## Prerequisites

Before we begin, here's what you need:

- A machine running Linux, macOS, or Windows with **Docker** and **Docker Compose** installed
- At least **2 GB of RAM** (4 GB recommended for OCR processing)
- About **1 GB of disk space** for the container image and temporary files
- (Optional) A domain name and reverse proxy for remote access

If Docker is not yet installed on your system, here is a quick setup for Ubuntu/Debian:

```bash
# Install Docker
curl -fsSL https://get.docker.com | sh

# Add your user to the docker group
sudo usermod -aG docker $USER
newgrp docker

# Verify installation
docker --version
docker compose version
```

The last command should confirm that both Docker Engine and Docker Compose are available.

## Installing Stirling-PDF with Docker

The fastest way to get Stirling-PDF running is with a single `docker compose` file. Create a new directory for the project:

```bash
mkdir -p ~/stirling-pdf
cd ~/stirling-pdf
```

Create a `docker-compose.yml` file:

```yaml
services:
  stirling-pdf:
    image: frooodle/s-pdf:latest
    container_name: stirling-pdf
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - ./data:/usr/share/tessdata        # OCR language data
      - ./extraConfigs:/configs            # Optional custom configs
      - ./logs:/logs                       # Application logs
    environment:
      - DOCKER_ENABLE_SECURITY=false
      - INSTALL_BOOK_AND_ADVANCED_HTML_OPS=false
      - LANGS=en
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/api/v1/info/status"]
      interval: 30s
      timeout: 10s
      retries: 3
```

Save the file and start the container:

```bash
docker compose up -d
```

The first launch will pull the container image, which is approximately 800 MB. After it finishes, open your browser and navigate to `http://localhost:8080`. You should see the Stirling-PDF home page with all available tools displayed as a grid of tiles.

### Enabling OCR

Out of the box, Stirling-PDF can process text-based PDFs. If you need to work with scanned documents — images embedded in PDFs that contain no selectable text — you will want OCR (Optical Character Recognition). Stirling-PDF bundles Tesseract OCR, but it needs language data files.

To enable OCR with English language support, the volume mount `./data:/usr/share/tessdata` in the compose file above handles it. For additional languages, download the corresponding `.traineddata` files from the [Tesseract language data repository](https://github.com/tesseract-ocr/tessdata) and place them in the `data/` directory:

```bash
# Download French and German language packs
cd ~/stirling-pdf/data
wget https://github.com/tesseract-ocr/tessdata/raw/main/fra.traineddata
wget https://github.com/tesseract-ocr/tessdata/raw/main/deu.traineddata
```

Then update the environment variable in your compose file:

```yaml
environment:
  - LANGS=en,fr,de
```

Restart the container for changes to take effect:

```bash
docker compose down && docker compose up -d
```

### Enabling Security Features

The default configuration disables certain security-related features. If you need password protection, digital signatures, or certificate-based encryption, set `DOCKER_ENABLE_SECURITY=true` and install the full feature set:

```yaml
environment:
  - DOCKER_ENABLE_SECURITY=true
  - INSTALL_BOOK_AND_ADVANCED_HTML_OPS=true
```

This adds approximately 200 MB to the container size but unlocks all enterprise-grade features.

## Using Stirling-PDF

The interface is straightforward. The home page presents every available tool as a clickable tile with a short description. Click any tile to open that tool's dedicated page.

### Merging PDFs

One of the most common use cases. On the merge page:

1. Drag and drop your PDF files (or click to browse)
2. Reorder the files by dragging them into the desired sequence
3. Click "Merge" to process
4. Download the combined file

There is no file size limit imposed by the application — the only constraint is your server's available memory. In testing, Stirling-PDF handles files up to several hundred megabytes without issue on a machine with 4 GB of RAM.

### Converting Between Formats

Stirling-PDF supports bidirectional conversion between PDFs and several other formats:

| From | To |
|---|---|
| PDF | PNG, JPG, WebP |
| PNG/JPG | PDF |
| PDF | DOCX (Word) |
| PDF | XLSX (Excel) |
| DOCX, XLSX, PPTX | PDF |
| HTML | PDF |
| PDF | Markdown |
| PDF | Plain text |

The conversion pipeline uses LibreOffice under the hood for Office document formats, which ensures high-fidelity output that preserves formatting, fonts, and layout.

### Adding Watermarks

The watermark tool lets you add text or image watermarks to PDF pages with fine-grained control:

- **Position**: center, corners, or custom coordinates
- **Opacity**: adjustable transparency from 0% to 100%
- **Rotation**: any angle, with diagonal tiling option
- **Page range**: apply to all pages or a specific subset

This is particularly useful for marking drafts, adding company branding, or labeling confidential documents.

### Compressing PDFs

If you need to reduce file sizes — for email attachments, web uploads, or storage — the compression tool offers three quality levels:

- **Low compression** — minimal quality loss, moderate size reduction
- **Medium compression** — balanced quality and size (recommended for most use cases)
- **High compression** — maximum size reduction, visible quality degradation

The compression engine optimizes image resolution, removes unnecessary metadata, and re-encodes fonts where possible.

### Working with Sensitive Documents

For documents containing personal information, the redaction tool is essential. Unlike simply covering text with a black box (which can be trivially removed), proper redaction permanently removes the underlying text data from the PDF structure.

The workflow:
1. Upload the PDF
2. Draw rectangles over the content to remove
3. Click "Redact" to permanently erase the selected areas
4. Download the sanitized file

Always verify the output by opening the redacted PDF and searching for any remnants of the removed text.

## Setting Up Authentication

By default, anyone who can reach the Stirling-PDF web interface can use it. If you are running this on a server accessible from the internet, you should enable authentication.

Stirling-PDF supports several authentication methods. The simplest is basic username/password auth via environment variables:

```yaml
environment:
  - SECURITY_ENABLELOGIN=true
  - SECURITY_INITIALLOGIN_USERNAME=admin
  - SECURITY_INITIALLOGIN_PASSWORD=your-strong-password-here
```

For multi-user setups, Stirling-PDF integrates with:

- **LDAP / Active Directory** — for enterprise directory services
- **OAuth2 / OIDC** — compatible with Keycloak, Authelia, Authentik, and other identity providers
- **API key authentication** — for programmatic access

Here is an example configuration using Authentik as the OIDC provider:

```yaml
environment:
  - SECURITY_ENABLELOGIN=true
  - SECURITY_OAUTH2_ENABLED=true
  - SECURITY_OAUTH2_CLIENT_ID=stirling-pdf
  - SECURITY_OAUTH2_CLIENT_SECRET=your-client-secret
  - SECURITY_OAUTH2_ISSUER=https://auth.example.com/application/o/stirling-pdf/
  - SECURITY_OAUTH2_SCOPE=openid email profile
```

With authentication enabled, users must log in before accessing any tools. You can also configure role-based access to restrict specific tools to certain user groups.

## Putting Stirling-PDF Behind a Reverse Proxy

If you want to access your PDF toolkit from anywhere, exposing it through a reverse proxy with HTTPS is the standard approach. Here is a Caddy configuration example:

```caddy
pdf.example.com {
    reverse_proxy localhost:8080

    # Enforce HTTPS with automatic certificate management
    tls {
        protocols tls1.2 tls1.3
    }

    # Security headers
    header {
        X-Content-Type-Options nosniff
        X-Frame-Options DENY
        Referrer-Policy strict-origin-when-cross-origin
    }
}
```

If you use Nginx instead:

```nginx
server {
    listen 443 ssl http2;
    server_name pdf.example.com;

    ssl_certificate     /etc/letsencrypt/live/pdf.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/pdf.example.com/privkey.pem;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Increase upload limits
        client_max_body_size 500M;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }
}
```

The `client_max_body_size` directive is important — without it, Nginx will reject large file uploads with a 413 error.

## Using the REST API

Stirling-PDF includes a full REST API for programmatic access. This is useful for integrating PDF processing into scripts, CI/CD pipelines, or other applications.

The API documentation is available at `http://localhost:8080/swagger-ui/index.html` when the container is running. Here are a few common API operations using `curl`:

### Merge Two PDFs via API

```bash
curl -X POST http://localhost:8080/api/v1/general/merge \
  -F "file1=@document1.pdf" \
  -F "file2=@document2.pdf" \
  -o merged.pdf
```

### Convert PDF to Images

```bash
curl -X POST http://localhost:8080/api/v1/general/pdf-to-image \
  -F "fileInput=@document.pdf" \
  -F "imageType=png" \
  -o output.zip
```

### Compress a PDF

```bash
curl -X POST http://localhost:8080/api/v1/general/compress \
  -F "file=@large-document.pdf" \
  -F "compressionLevel=medium" \
  -o compressed.pdf
```

All API endpoints accept file uploads via multipart form data and return the processed file as a binary response. Error responses include a JSON body with details about what went wrong.

## Comparison: Stirling-PDF vs Alternatives

How does Stirling-PDF compare to other self-hosted PDF solutions and popular commercial services?

| Feature | Stirling-PDF | PDFtk (CLI) | iText (Library) | SmallPDF (SaaS) |
|---|---|---|---|---|
| **License** | MIT (free) | GPL (free) | AGPL (commercial) | Proprietary |
| **Interface** | Web UI | Command line | Code library | Web UI |
| **Merge/Split** | Yes | Yes | Yes | Yes |
| **OCR** | Built-in (Tesseract) | No | No | Yes |
| **Convert formats** | 10+ formats | No | Limited | 5+ formats |
| **API** | REST API | CLI only | Code API | REST API |
| **Self-hosted** | Yes | Yes | Yes | No |
| **Multi-user auth** | Yes | N/A | N/A | Yes |
| **File size limit** | None (server RAM) | None (disk) | None (memory) | 50 MB free |
| **Setup effort** | 5 minutes | 1 minute | Hours | None |
| **Maintenance** | Docker updates | Package updates | Dependency updates | None |

Stirling-PDF occupies a unique middle ground: it offers the convenience of a web-based interface with the privacy and control of self-hosting. PDFtk is lighter and faster for batch operations but lacks a GUI and OCR. Commercial SaaS tools are convenient but introduce the very privacy and cost concerns that motivated self-hosting in the first place.

## Maintenance and Updates

Keeping Stirling-PDF updated is straightforward with Docker. The project releases updates regularly, adding new tools and fixing bugs:

```bash
# Check for updates
docker compose pull

# Apply updates
docker compose up -d

# Clean up old images
docker image prune -f
```

To back up your configuration:

```bash
# Back up OCR data and configs
tar czf stirling-backup.tar.gz ~/stirling-pdf/data ~/stirling-pdf/extraConfigs ~/stirling-pdf/docker-compose.yml
```

Logs are available in the `logs/` directory or via Docker:

```bash
docker logs stirling-pdf
docker logs stirling-pdf --follow  # Live log streaming
```

If you run into issues, the Stirling-PDF GitHub repository has an active community and responsive maintainers. The project has been under continuous development since 2021, with releases every few weeks.

## When Stirling-PDF Is the Right Choice

Stirling-PDF is ideal for:

- **Individuals** who handle sensitive documents and want to avoid uploading them to unknown servers
- **Small businesses** that need PDF tools without per-user licensing costs
- **Developers** who need a PDF processing API for their applications
- **IT departments** that want to provide PDF tools to employees with centralized access control
- **Privacy-conscious users** who prefer open-source software they can audit

It may not be the best fit if you need enterprise-scale document workflow automation (consider Alfresco or Paperless-ngx for that) or if you simply need to merge two PDFs once a year (a command-line tool like `pdfunite` would suffice).

## Conclusion

Stirling-PDF proves that self-hosted software can match — and in many cases exceed — the capabilities of commercial cloud services. With over 50 PDF processing tools, a clean web interface, a full REST API, and strong authentication options, it is the most comprehensive open-source PDF toolkit available today.

The setup takes about five minutes with Docker. Your documents never leave your infrastructure. And because the project is MIT-licensed, you have the freedom to use, modify, and distribute it without restriction.

If you have been looking for a reason to consolidate more services on your home lab or personal server, Stirling-PDF is an excellent candidate. It runs on minimal hardware, requires almost no maintenance, and replaces an entire category of cloud services that you probably should not be trusting with your documents anyway.

---

*Looking for more self-hosted tools? Check out our guides on [Reverse Proxy Comparison](/reverse-proxy-comparison/) and [Docker Compose Guide](/docker-compose-guide/) for building out your home lab infrastructure.*
