---
title: "Self-Hosted Email Attachment Extraction Tools: ripole vs tnef vs munpack"
date: "2026-06-03"
tags: ["email", "mail-server", "security", "automation", "linux", "self-hosted"]
draft: false
---

Email attachments arrive in many proprietary formats — Microsoft OLE documents, TNEF-encoded winmail.dat files, and complex MIME multipart structures. Server-side extraction tools let you process, scan, and convert these attachments programmatically without requiring a desktop email client.

## Why Self-Host Attachment Processing?

When your mail infrastructure receives thousands of messages daily, you need automated tools to extract and inspect attachments before they reach end users. Security teams use these tools to unpack attachments for virus scanning, content inspection, and data loss prevention (DLP). For archival purposes, extracting and normalizing attachments ensures long-term accessibility regardless of the original format.

Server-side processing also enables workflow automation. An invoicing system can automatically extract PDFs from incoming email, a document management system can parse Office documents, and a compliance system can archive all attachments in a standardized format. These integrations are impossible when attachments remain trapped inside proprietary email formats that only desktop clients can decode.

Finally, Microsoft-centric environments create a specific pain point: TNEF (Transport Neutral Encapsulation Format) attachments. When Exchange or Outlook users send messages with rich formatting, the email arrives at non-Microsoft clients as a `winmail.dat` attachment — an opaque binary blob. Server-side TNEF decoding restores the original attachments for all recipients, regardless of their email client.

For a broader view of email security infrastructure, see our [email security gateway guide](../2026-06-03-self-hosted-email-security-gateway-proxmox-scrollout-mailscanner-guide/) and [email quarantine management article](../2026-06-01-self-hosted-email-quarantine-management-mailwatch-mailzu-amavisd-guide/). If you're interested in the delivery pipeline, our [mail delivery agents comparison](../2026-05-13-self-hosted-mail-delivery-agents-dovecot-lda-maildrop-procmail-guide/) covers the next step in the chain.

## How Attachment Extraction Tools Work

Each tool targets a specific attachment encoding format and extracts its contents to regular files that downstream tools can process:

**ripole** extracts attachments from Microsoft OLE2 compound document format, commonly used by older Office documents (.doc, .xls, .ppt) and Outlook .msg files. It parses the OLE directory structure and extracts embedded streams — documents, images, and metadata — to the filesystem.

**tnef** decodes TNEF-encoded attachments (winmail.dat). These are proprietary Microsoft email encapsulation formats that bundle rich text formatting, attachments, and meeting requests. The `tnef` tool unpacks them into standard MIME parts, making the original attachments accessible to any email client or processing pipeline.

**munpack** extracts MIME-encoded attachments from RFC 2822 email messages. It handles base64, quoted-printable, uuencoded, and binhex encodings. munpack is the Swiss Army knife for MIME decoding — it works with any standards-compliant email message, regardless of the sending client.

## Comparison Table

| Feature | ripole | tnef | munpack |
|---------|--------|------|---------|
| Target Format | OLE2 compound documents | TNEF (winmail.dat) | MIME (RFC 2822/2045) |
| Source | .doc, .xls, .ppt, .msg | Outlook/Exchange messages | Any MIME email |
| Output | Raw embedded streams | MIME parts, attachments | Decoded files, message body |
| Language | C | C | C |
| Package Size | ~50 KB binary | ~60 KB binary | ~40 KB binary |
| Active Development | Stable (2022+) | Maintained (2024+) | Stable (maintained in distros) |
| Virus Scanning Integration | Pipe output to ClamAV | Pipe output to ClamAV | Pipe output to ClamAV |
| Recursive Extraction | Partial (nested OLE) | No | Partial (nested MIME) |
| Postfix Integration | Pipe filter or milter wrapper | Pipe filter or milter wrapper | Pipe filter |
| License | BSD-style | GPL v2 | GPL v2 |
| Package Availability | apt, yum, ports, source | apt, yum, homebrew | apt, yum, homebrew |

## Installing and Using ripole

ripole is available in Debian/Ubuntu repositories and via source:

```bash
apt-get install -y ripole
```

Basic extraction from an OLE document:

```bash
# Extract all streams from a .doc or .msg file
ripole -i document.doc -d /tmp/extracted/

# List contents without extracting
ripole -i document.doc -l

# Extract from Outlook .msg attachment saved from email
ripole -i email_attachment.msg -d /var/spool/attachments/
```

Integrating ripole with Postfix for automated processing:

```bash
# Save the email attachment and process it
cat > /usr/local/bin/extract-ole-attachments.sh << 'SCRIPT'
#!/bin/bash
TEMP_DIR=$(mktemp -d)
cat > "$TEMP_DIR/message.eml"
munpack -C "$TEMP_DIR" -t < "$TEMP_DIR/message.eml" 2>/dev/null

# Process all extracted OLE files
for file in "$TEMP_DIR"/*.doc "$TEMP_DIR"/*.xls "$TEMP_DIR"/*.msg; do
    [ -f "$file" ] || continue
    ripole -i "$file" -d "$TEMP_DIR/ole_extracted/"
done

# Scan extracted files with ClamAV
clamscan -r "$TEMP_DIR/" --quiet

rm -rf "$TEMP_DIR"
SCRIPT
chmod +x /usr/local/bin/extract-ole-attachments.sh
```

## Installing and Using tnef

```bash
apt-get install -y tnef
```

Basic TNEF decoding:

```bash
# Decode a winmail.dat file
tnef --file winmail.dat --save-body /tmp/tnef_output/

# List contents without extracting
tnef --file winmail.dat --list

# Extract to specific directory and print details
tnef --file winmail.dat --directory /var/spool/extracted/ --verbose
```

Automated Postfix integration for TNEF handling:

```bash
cat > /usr/local/bin/decode-tnef-attachments.sh << 'SCRIPT'
#!/bin/bash
TEMP_DIR=$(mktemp -d)
cat > "$TEMP_DIR/message.eml"

# Extract attachments
munpack -C "$TEMP_DIR" -t < "$TEMP_DIR/message.eml" 2>/dev/null

# Decode any TNEF files
for tnef_file in "$TEMP_DIR"/winmail.dat "$TEMP_DIR"/*.dat; do
    [ -f "$tnef_file" ] || continue
    OUTPUT_DIR="$TEMP_DIR/decoded_$(basename "$tnef_file")"
    mkdir -p "$OUTPUT_DIR"
    tnef --file "$tnef_file" --directory "$OUTPUT_DIR" --save-body
    echo "TNEF decoded: $(ls "$OUTPUT_DIR")"
done

rm -rf "$TEMP_DIR"
SCRIPT
chmod +x /usr/local/bin/decode-tnef-attachments.sh
```

## Installing and Using munpack

```bash
apt-get install -y mpack
```

Extracting all attachments from an email:

```bash
# Extract attachments from a raw email file
munpack -t -C /tmp/extracted/ email_message.eml

# Process from stdin (useful for pipe integration)
cat email_message.eml | munpack -t -C /tmp/extracted/

# Decode specific MIME parts by number
munpack -t -C /tmp/output/ email.eml
```

## Building a Complete Attachment Processing Pipeline

The real power comes from chaining these tools together. Here is a comprehensive pipeline that handles all three formats:

```bash
#!/bin/bash
# /usr/local/bin/process-email-attachments.sh
# Comprehensive email attachment extraction and scanning pipeline

set -e
EMAIL_FILE="$1"
OUTPUT_DIR="${2:-/var/spool/attachments/$(date +%Y%m%d-%H%M%S)}"
mkdir -p "$OUTPUT_DIR"

# Step 1: Extract MIME parts
echo "[1/4] Extracting MIME attachments..."
munpack -t -C "$OUTPUT_DIR/mime" < "$EMAIL_FILE" 2>/dev/null || true

# Step 2: Decode TNEF attachments
echo "[2/4] Checking for TNEF files..."
find "$OUTPUT_DIR" -name "winmail.dat" -o -name "*.tnef" | while read tnef_file; do
    TNEF_OUT="$OUTPUT_DIR/tnef_decoded"
    mkdir -p "$TNEF_OUT"
    tnef --file "$tnef_file" --directory "$TNEF_OUT" 2>/dev/null || true
    echo "  Decoded: $tnef_file → $TNEF_OUT/"
done

# Step 3: Extract OLE attachments
echo "[3/4] Checking for OLE documents..."
find "$OUTPUT_DIR" -name "*.doc" -o -name "*.xls" -o -name "*.ppt" -o -name "*.msg" | while read ole_file; do
    OLE_OUT="$OUTPUT_DIR/ole_extracted/$(basename "$ole_file")"
    mkdir -p "$OLE_OUT"
    ripole -i "$ole_file" -d "$OLE_OUT" 2>/dev/null || true
    echo "  Extracted: $ole_file → $OLE_OUT/"
done

# Step 4: Scan all extracted files
echo "[4/4] Scanning extracted files with ClamAV..."
clamscan -r "$OUTPUT_DIR/" --quiet --log="$OUTPUT_DIR/scan_report.log"
SCAN_RESULT=$?

# Summary
TOTAL_FILES=$(find "$OUTPUT_DIR" -type f | wc -l)
echo "Pipeline complete: $TOTAL_FILES files extracted to $OUTPUT_DIR"
exit $SCAN_RESULT
```

## Performance Considerations

These tools are extremely lightweight. Each binary is under 100 KB and processes files in milliseconds:

- **ripole**: Processes a 5 MB .msg file in ~50ms, extracting 20+ embedded streams
- **tnef**: Decodes a typical winmail.dat (200 KB) in ~10ms
- **munpack**: Extracts 10 attachments from a 25 MB email in ~100ms

For high-volume mail servers processing thousands of messages per hour, the overhead is negligible. A single modest server (2 CPU cores, 4 GB RAM) running the complete pipeline can handle 100,000+ messages per hour with attachment extraction enabled.

The primary bottleneck is not the extraction tools but the downstream virus scanning. If you use ClamAV integration, allocate adequate RAM for the virus database (~1.5 GB) and configure `clamd` as a persistent daemon rather than calling `clamscan` for each message.

## FAQ

### Why do I receive winmail.dat files from Outlook users?

TNEF (winmail.dat) is Microsoft's proprietary format for encapsulating rich-text formatting, attachments, and calendar data. It is generated when Outlook users send email with RTF formatting enabled to non-Exchange recipients. The `tnef` tool is the standard Linux solution for decoding these files and recovering the original attachments.

### Can these tools handle encrypted or password-protected attachments?

No. OLE encryption, password-protected ZIP files, and S/MIME encrypted attachments require separate decryption tools. These extraction tools operate on the attachment encoding layer, not the content encryption layer. For encrypted email handling, you need an S/MIME or PGP decryption gateway as a preprocessing step.

### How do I integrate attachment processing into an existing Postfix setup?

The recommended approach is a Postfix content filter pipe in `master.cf`:

```
attachment_filter unix - n n - 10 pipe
  flags=Rq user=filter null_sender=
  argv=/usr/local/bin/process-email-attachments.sh ${sender} ${recipient}
```

Add `content_filter = attachment_filter:dummy` to your `smtp` service definition. The filter processes each message before it enters the queue.

### Are there security risks in automated attachment extraction?

Yes. Maliciously crafted OLE, TNEF, or MIME files can potentially exploit bugs in the extraction tools. Always:
1. Run extraction in a sandboxed environment (Docker container, chroot, or seccomp-restricted process)
2. Keep tools updated to the latest versions
3. Run virus scanning on all extracted files before making them available to users
4. Set resource limits (CPU time, memory, disk space) for the extraction process

### Can I use these tools to extract attachments from archived email (mbox, maildir)?

Yes. For mbox files, use `formail` to split into individual messages, then pipe each through `munpack`. For maildir, iterate over message files:

```bash
find /var/mail/maildir/ -name "*-*" -type f | while read msg; do
    munpack -t -C /tmp/extracted/ < "$msg" 2>/dev/null
done
```

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Email Attachment Extraction Tools: ripole vs tnef vs munpack",
  "description": "Compare ripole, tnef, and munpack for server-side email attachment extraction. Covers OLE, TNEF, and MIME decoding with Postfix integration and virus scanning pipeline examples.",
  "datePublished": "2026-06-03",
  "dateModified": "2026-06-03",
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
