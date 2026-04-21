---
title: "Best Self-Hosted File Converters 2026: CloudConvert & ILovePDF Alternatives"
date: 2026-04-15
tags: ["comparison", "guide", "self-hosted", "privacy", "productivity"]
draft: false
description: "Complete guide to self-hosted file conversion tools in 2026. Compare Gotenberg, Pandoc, LibreOffice headless, FFmpeg, ImageMagick, and Calibre to replace CloudConvert and ILovePDF with private, unlimited alternatives."
---

Every day, millions of people upload sensitive documents, spreadsheets, photos, and videos to cloud conversion services like CloudConvert, ILovePDF, and Zamzar. These tools are convenient — until you need to convert a confidential contract, a batch of client invoices, or a library of proprietary images. Do you really want those files passing through someone else's servers?

Self-hosted file converters give you unlimited conversions, zero file limits, complete privacy, and no subscription fees. This guide covers the best open-source tools for document, image, media, and ebook conversion — with step-by-step [docker](https://www.docker.com/) setups you can deploy in minutes.

## Why Self-Host Your File Converters?

Cloud-based conversion services come with real trade-offs that affect both privacy and productivity:

- **Data privacy**: Every file you upload is processed on infrastructure you don't control. Even with privacy policies, files may be cached, logged, or scanned.
- **File size limits**: Free tiers typically cap uploads at 25–100 MB. Paid plans raise limits but add monthly costs.
- **Rate limits and queues**: Batch conversions are throttled. Convert 50 files and you'll wait in line.
- **Internet dependency**: No connection means no conversions — a problem for large media files on slow networks.
- **Vendor lock-in**: APIs and workflows are tied to specific providers.

Running your own conversion stack eliminates all of these problems. Your files never leave your machine, there are no artificial limits, and you can process thousands of files in parallel. For teams handling sensitive data — legal documents, financial reports, medical records, or intellectual property — self-hosting is not just a convenience, it's a security requirement.

## Top Tools at a Glance

The self-hosted conversion landscape isn't dominated by a single all-in-one tool. Instead, different tools excel at different file types. Here's how the leading options compare:

| Tool | Best For | API | Docker | Batch | Formats Supported |
|------|----------|-----|--------|-------|-------------------|
| **Gotenberg** | Document to PDF | REST | ✅ One-line | ✅ Queue | DOCX, XLSX, PPTX, HTML, Markdown → PDF |
| **Pandoc** | Universal doc conversion | CLI | ✅ Available | ✅ Parallel | 40+ formats (Markdown, LaTeX, DOCX, HTML, EPUB, and more) |
| **LibreOffice Headless** | Office suite conversions | CLI | ✅ Available | ✅ Parallel | ODT, DOCX, XLSX, PPTX, CSV, PDF, and 30+ formats |
| **FFmpeg** | Audio & video | CLI | ✅ Official | ✅ Parallel | 400+ codecs (MP4, MKV, AVI, MP3, AAC, WebM, and more) |
| **ImageMagick** | Image processing | CLI / MagickWand | ✅ Available | ✅ Parallel | 200+ formats (PNG, JPEG, TIFF, SVG, WebP, HEIC, and more) |
| **Calibre** | Ebook conversion | CLI | ✅ Available | ✅ Parallel | EPUB, MOBI, AZW3, PDF, DOCX, HTML, and 20+ formats |

No single tool covers everything. A production-ready self-hosted conversion stack typically combines 3–4 of these tools, each handling the file types where it performs best.

## Gotenberg: The CloudConvert Killer for Documents

[Gotenberg](https://gotenberg.dev/) is a Docker-native API that converts documents to PDF. It wraps LibreOffice and Chromium under the hood, giving you a clean REST API that behaves like a private CloudConvert for office documents and web pages.

### What Gotenberg Converts

- Microsoft Office files (`.docx`, `.xlsx`, `.pptx`) → PDF
- OpenDocument formats (`.odt`, `.ods`, `.odp`) → PDF
- HTML and Markdown → PDF (with full CSS support)
- PDF merging, splitting, and watermarking
- PDF/A compliance for archiving

### Docker Deployment

Gotenberg is designed to run as a single container. Start it with one command:

```bash
docker run --rm -p 3000:3000 gotenberg/gotenberg:8
```

That's it. The API is now listening on `http://localhost:3000`. Here's a production-grade `docker-compose.yml`:

```yaml
version: "3.8"

services:
  gotenberg:
    image: gotenberg/gotenberg:8
    container_name: gotenberg
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      # Limit concurrent conversions to control resource usage
      - GOTENBERG_API_PORT=3000
      - GOTENBERG_CHROMIUM_RESTART_ABOVE_DURATION=30s
      - GOTENBERG_API_TIMEOUT=60s
      # Security: restrict allowed file uploads to a temp directory
      - GOTENBERG_API_DISABLE_DOWNLOAD_ROUTE=true
    volumes:
      - ./uploads:/tmp/gotenberg
    # Restrict memory to prevent runaway conversions
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: "2.0"
```

### Converting a DOCX to PDF

Use `curl` to send a file to the API:

```bash
curl -X POST http://localhost:3000/forms/libreoffice/convert \
  -F "file=@/path/to/document.docx" \
  -F "landscape=false" \
  -o output.pdf
```

### Converting HTML to PDF

Gotenberg renders HTML with Chromium, so CSS, fonts, and JavaScript all work:

```bash
curl -X POST http://localhost:3000/forms/chromium/convert/html \
  -F "file=@/path/to/page.html" \
  -F "file=@/path/to/styles.css" \
  -F "marginTop=0.5" \
  -F "marginBottom=0.5" \
  -F "marginLeft=0.5" \
  -F "marginRight=0.5" \
  -o page.pdf
```

You can also pass raw HTML directly:

```bash
curl -X POST http://localhost:3000/forms/chromium/convert/url \
  -F "url=https://example.com/report" \
  -F "paperWidth=8.5" \
  -F "paperHeight=11" \
  -o report.pdf
```

### Merging and Watermarking PDFs

Gotenberg can combine multiple PDFs and add watermarks in a single request:

```bash
curl -X POST http://localhost:3000/pdf/merge \
  -F "files=@/path/to/first.pdf" \
  -F "files=@/path/to/second.pdf" \
  -o merged.pdf

curl -X POST http://localhost:3000/pdf/convert \
  -F "file=@/path/to/document.pdf" \
  -F "watermarkPath=@/path/to/watermark.pdf" \
  -o watermarked.pdf
```

Gotenberg is the closest self-hosted equivalent to CloudConvert for document workflows. It handles the most common conversion needs — office documents, web pages, and PDF manipulation — through a clean, well-documented API that integrates easily into any application or script.

## Pandoc: The Universal Document Converter

[Pandoc](https://pandoc.org/) is often called the "Swiss army knife" of document conversion. It supports over 40 input and output formats, making it the most versatile single converter available. If you need to transform documents between formats that Gotenberg doesn't handle — Markdown to LaTeX, HTML to EPUB, DOCX to Markdown — Pandoc is the tool.

### Installation

Pandoc is available as a standalone binary, a Docker image, or through most package managers:

```bash
# Ubuntu / Debian
sudo apt install pandoc

# macOS
brew install pandoc

# Docker
docker run --rm -v "$(pwd):/data" pandoc/core --help
```

### Common Conversion Workflows

**Markdown to PDF** (with custom template):

```bash
pandoc input.md -o output.pdf \
  --pdf-engine=xelatex \
  --template=eisvogel \
  --toc \
  --toc-depth=2 \
  --number-sections
```

**DOCX to Markdown** (preserving formatting):

```bash
pandoc input.docx -o output.md \
  --wrap=preserve \
  --extract-media=./images
```

**HTML to EPUB** (for ebook publishing):

```bash
pandoc chapter1.html chapter2.html chapter3.html \
  -o book.epub \
  --epub-metadata=metadata.xml \
  --epub-cover-image=cover.jpg \
  --toc
```

**Batch converting a directory of Markdown files to DOCX**:

```bash
for file in docs/*.md; do
  pandoc "$file" -o "${file%.md}.docx" \
    --reference-doc=template.docx
done
```

### Pandoc vs Gotenberg: When to Use Which

Gotenberg and Pandoc overlap on document conversion but serve different purposes:

- Use **Gotenberg** when you need a REST API for on-demand conversions, especially DOCX/XLSX/PPTX → PDF, or HTML → PDF with pixel-perfect rendering.
- Use **Pandoc** when you need format flexibility — converting between markup languages, generating ebooks, or processing documents where layout precision matters less than format fidelity.

In a complete conversion stack, you'll use both: Gotenberg for PDF generation from office documents, and Pandoc for everything else.

## LibreOffice Headless: The Office Suite Powerhouse

LibreOffice can run without a graphical interface, making it ideal for server-side document conversion. It supports more file formats than Gotenberg's LibreOffice backend alone, because you have direct access to every conversion filter.

### Docker Setup

```yaml
version: "3.8"

services:
  libreoffice:
    image: linuxserver/libreoffice:latest
    container_name: libreoffice-convert
    restart: unless-stopped
    volumes:
      - ./documents:/documents
      - ./output:/output
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=Etc/UTC
    # Run conversions directly in the container
    entrypoint: ["soffice", "--headless", "--convert-to", "pdf", "--outdir", "/output", "/documents/*.docx"]
```

For a more flexible setup, run LibreOffice headless on demand:

```bash
docker run --rm \
  -v "$(pwd)/input:/input" \
  -v "$(pwd)/output:/output" \
  linuxserver/libreoffice \
  soffice --headless \
  --convert-to pdf \
  --outdir /output \
  /input/*.xlsx
```

### Converting Between Office Formats

LibreOffice headless supports all major office format conversions:

```bash
# DOCX to PDF
libreoffice --headless --convert-to pdf document.docx

# XLSX to CSV
libreoffice --headless --convert-to csv:"Text - txt - csv (StarCalc)" spreadsheet.xlsx

# PPTX to PDF (one slide per page)
libreoffice --headless --convert-to pdf presentation.pptx

# ODT to DOCX
libreoffice --headless --convert-to docx document.odt

# Batch: convert all DOCX files in a directory
libreoffice --headless --convert-to pdf *.docx
```

### Why Use LibreOffice Headless Instea[actual](https://actualbudget.org/)otenberg?

Gotenberg actually uses LibreOffice internally for office document conversions. But running LibreOffice headless directly gives you:

- **More output formats**: Gotenberg primarily outputs PDF. LibreOffice headless can convert between any supported format.
- **No API overhead**: Direct CLI execution is faster for batch jobs.
- **Custom extensions**: You can install LibreOffice extensions for additional conversion filters (barcode generation, specialized export formats, etc.).
- **Lower resource usage**: No HTTP server layer means less memory and CPU overhead.

For a conversion service with an API, use Gotenberg. For batch processing scripts or when you need format options beyond PDF, use LibreOffice headless directly.

## FFmpeg: Audio and Video Conversion

[FFmpeg](https://ffmpeg.org/) is the undisputed standard for media conversion. It handles over 400 codecs and every common media format. If you need to convert video or audio files, FFmpeg is the only tool you need.

### Docker Setup

```yaml
version: "3.8"

services:
  ffmpeg:
    image: linuxserver/ffmpeg:latest
    container_name: ffmpeg-convert
    restart: unless-stopped
    volumes:
      - ./media:/media
      - ./output:/output
    environment:
      - PUID=1000
      - PGID=1000
    # GPU acceleration (NVIDIA)
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

### Common Conversion Commands

**Convert video format** (MKV to MP4):

```bash
ffmpeg -i input.mkv -c:v copy -c:a aac output.mp4
```

The `-c:v copy` flag copies the video stream without re-encoding, making the conversion nearly instant. Only the audio is re-encoded.

**Resize and compress video**:

```bash
ffmpeg -i input.mp4 \
  -vf "scale=1280:720" \
  -c:v libx264 \
  -crf 23 \
  -preset medium \
  -c:a aac \
  -b:a 128k \
  output_720p.mp4
```

The CRF (Constant Rate Factor) value controls quality: 18 is visually lossless, 23 is the default, and 28 is acceptable for archives.

**Extract audio from video**:

```bash
ffmpeg -i video.mp4 -vn -c:a libmp3lame -q:a 2 audio.mp3
```

**Convert audio format** (FLAC to MP3):

```bash
ffmpeg -i input.flac -c:a libmp3lame -b:a 320k output.mp3
```

**Batch convert an entire video library to H.265** (better compression):

```bash
#!/bin/bash
mkdir -p converted
for file in *.mp4; do
  ffmpeg -i "$file" \
    -c:v libx265 \
    -crf 26 \
    -preset slow \
    -c:a aac \
    -b:a 128k \
    "converted/${file%.mp4}_h265.mp4"
done
```

FFmpeg alone replaces CloudConvert's entire media conversion capability. It's faster, supports more formats, and gives you granular control over quality, codecs, and output parameters.

## ImageMagick: Image Conversion and Processing

[ImageMagick](https://imagemagick.org/) handles over 200 image formats and provides powerful batch processing capabilities. It converts between formats, resizes, crops, applies filters, and generates thumbnails.

### Docker Setup

```yaml
version: "3.8"

services:
  imagemagick:
    image: dpokidov/imagemagick:latest
    container_name: imagemagick
    restart: unless-stopped
    volumes:
      - ./images:/images
      - ./output:/output
    working_dir: /images
```

### Common Conversion Commands

**Convert between formats**:

```bash
# HEIC to JPEG (common for iPhone photos)
magick input.HEIC output.jpg

# PNG to WebP (web optimization)
magick input.png -quality 85 output.webp

# TIFF to JPEG with compression
magick input.tiff -quality 90 output.jpg

# Batch: convert all PNG files to WebP
for file in *.png; do
  magick "$file" -quality 85 "${file%.png}.webp"
done
```

**Resize and optimize for web**:

```bash
magick input.jpg \
  -resize 1920x1080\> \
  -strip \
  -quality 85 \
  -interlace JPEG \
  output.jpg
```

The `\>` flag ensures images are only scaled down, never up. `-strip` removes metadata to reduce file size.

**Generate thumbnails**:

```bash
magick input.jpg -thumbnail 200x200^ -gravity center -extent 200x200 thumb.jpg
```

**Convert SVG to PNG** (for rendering vector graphics):

```bash
magick -background none -density 300 input.svg output.png
```

ImageMagick is the most capable self-hosted image converter available. Combined with FFmpeg for media and Gotenberg for documents, you have a complete replacement for any cloud conversion service.

## Calibre: Ebook Conversion and Management

[Calibre](https://calibre-ebook.com/) is best known as an ebook library manager, but its command-line conversion engine (`ebook-convert`) is one of the most powerful document converters for ebook formats.

### Docker Setup

```yaml
version: "3.8"

services:
  calibre:
    image: linuxserver/calibre:latest
    container_name: calibre-convert
    restart: unless-stopped
    volumes:
      - ./books:/books
      - ./output:/output
      - ./config:/config
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=Etc/UTC
```

### Ebook Conversion Commands

**EPUB to MOBI** (for older Kindle devices):

```bash
ebook-convert input.epub output.mobi
```

**HTML to EPUB** (with metadata):

```bash
ebook-convert input.html output.epub \
  --title "My Book Title" \
  --authors "Author Name" \
  --cover cover.jpg \
  --language en \
  --chapter "//h:h1" \
  --level1-toc "//h:h1" \
  --level2-toc "//h:h2"
```

**PDF to EPUB** (reflowable format):

```bash
ebook-convert input.pdf output.epub \
  --linearize-tables \
  --unwrap-factor 0.45 \
  --pretty-print
```

**Batch convert an ebook library to EPUB**:

```bash
mkdir -p converted
for file in *.mobi *.azw3; do
  ebook-convert "$file" "converted/${file%.*}.epub"
done
```

Calibre's conversion engine handles the com[plex](https://www.plex.tv/) layout and typography challenges that general-purpose converters struggle with — table of contents generation, chapter detection, metadata embedding, and cover image handling. If you work with ebooks, Calibre is essential.

## Building a Complete Self-Hosted Conversion Stack

The most powerful approach combines these tools into a unified service. Here's a `docker-compose.yml` that brings everything together:

```yaml
version: "3.8"

services:
  # Document to PDF conversion API
  gotenberg:
    image: gotenberg/gotenberg:8
    container_name: gotenberg
    restart: unless-stopped
    ports:
      - "3000:3000"
    volumes:
      - ./uploads:/tmp/gotenberg
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: "2.0"

  # Media conversion (video/audio)
  ffmpeg:
    image: linuxserver/ffmpeg:latest
    container_name: ffmpeg
    restart: unless-stopped
    volumes:
      - ./media:/media
      - ./output:/output
    environment:
      - PUID=1000
      - PGID=1000

  # Image conversion and processing
  imagemagick:
    image: dpokidov/imagemagick:latest
    container_name: imagemagick
    restart: unless-stopped
    volumes:
      - ./images:/images
      - ./output:/output

  # Universal document conversion
  pandoc:
    image: pandoc/core:latest
    container_name: pandoc
    restart: unless-stopped
    volumes:
      - ./documents:/data
    working_dir: /data

  # Ebook conversion
  calibre:
    image: linuxserver/calibre:latest
    container_name: calibre
    restart: unless-stopped
    volumes:
      - ./books:/books
      - ./output:/output
      - ./calibre-config:/config
    environment:
      - PUID=1000
      - PGID=1000

  # Shared volume for conversion results
volumes:
  gotenberg-uploads:
  calibre-config:
```

Start the entire stack with `docker compose up -d`. Each service handles its specialty:

| Service | Handles | API / Access |
|---------|---------|-------------|
| Gotenberg | DOCX, XLSX, PPTX, HTML → PDF | REST API on port 3000 |
| FFmpeg | Video and audio conversion | CLI in container |
| ImageMagick | Image format conversion | CLI in container |
| Pandoc | Universal document conversion | CLI in container |
| Calibre | Ebook format conversion | CLI in container |

## Cost Comparison: CloudConvert vs Self-Hosted

| Feature | CloudConvert (Business) | Self-Hosted Stack |
|---------|------------------------|-------------------|
| Monthly cost | $60–$150/month | $0 (open source) |
| File size limit | 4 GB | Unlimited (disk space) |
| Concurrent conversions | 5–25 | Unlimited (CPU bound) |
| API calls | 5,000–50,000/month | Unlimited |
| Data privacy | Provider's servers | Your server |
| Supported formats | 200+ | 400+ (FFmpeg alone) |
| Customization | Limited | Full control |
| Offline access | No | Yes |

A basic VPS with 4 CPU cores and 8 GB RAM costs $20–40/month and can handle thousands of daily conversions across all formats. The break-even point is typically the first month.

## Getting Started Today

1. **Install Docker** on your server or workstation if you haven't already.
2. **Pick your priority**: Start with the tool that solves your most frequent conversion need. Gotenberg for documents, FFmpeg for media, ImageMagick for images.
3. **Deploy with Docker**: Use the `docker-compose.yml` above or start individual containers as needed.
4. **Integrate into workflows**: Replace cloud API calls with your local Gotenberg endpoint. Swap `curl` commands to CloudConvert with local FFmpeg and ImageMagick commands.
5. **Scale as needed**: Add GPU support for FFmpeg video encoding, increase memory limits for Gotenberg, or deploy additional containers for higher throughput.

Self-hosted file converters are mature, well-documented, and production-ready. The tools covered here — Gotenberg, Pandoc, LibreOffice headless, FFmpeg, ImageMagick, and Calibre — collectively handle every file conversion need that services like CloudConvert and ILovePDF address, with better privacy, no limits, and zero ongoing costs.

Your files stay on your infrastructure. Your conversions run on your schedule. And you never have to worry about upload limits again.

## Frequently Asked Questions (FAQ)

### Which one should I choose in 2026?

The best choice depends on your specific requirements:

- **For beginners**: Start with the simplest option that covers your core use case
- **For production**: Choose the solution with the most active community and documentation
- **For teams**: Look for collaboration features and user management
- **For privacy**: Prefer fully open-source, self-hosted options with no telemetry

Refer to the comparison table above for detailed feature breakdowns.

### Can I migrate between these tools?

Most tools support data import/export. Always:
1. Backup your current data
2. Test the migration on a staging environment
3. Check official migration guides in the documentation

### Are there free versions available?

All tools in this guide offer free, open-source editions. Some also provide paid plans with additional features, priority support, or managed hosting.

### How do I get started?

1. Review the comparison table to identify your requirements
2. Visit the official documentation (links provided above)
3. Start with a Docker Compose setup for easy testing
4. Join the community forums for troubleshooting
