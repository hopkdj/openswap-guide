---
title: "Self-Hosted Email Disclaimer & Footer Management: alterMIME vs MIMEDefang vs Amavis"
date: "2026-06-03"
tags: ["email", "postfix", "smtp", "mail-server", "self-hosted", "compliance", "automation"]
draft: false
---

Email disclaimers, legal footers, and corporate signatures are mandatory requirements for many organizations. Whether you need to append legal notices to outbound emails, add confidentiality statements, or insert standardized signatures, a server-side disclaimer management tool handles this transparently without depending on end-user email clients.

## Why Self-Host Your Email Disclaimer System?

Organizations in regulated industries — legal, financial, healthcare — face strict requirements for email footers. Relying on each employee to manually configure signatures in their email client is unreliable and inconsistent. A server-side solution guarantees that every outbound message carries the required legal text, regardless of which device or client the sender used.

Centralized disclaimer management also simplifies compliance audits. Instead of verifying hundreds of individual client configurations, your IT team can confirm that a single Postfix milter or content filter is active and correctly configured. When legal requirements change, you update one configuration file and the new disclaimer propagates to all outbound email instantly.

Data sovereignty is another key advantage. Third-party email signature services (like Exclaimer or CodeTwo) route your email through their servers, creating a potential data leak vector. Self-hosting keeps all email content within your infrastructure. For organizations subject to GDPR, HIPAA, or SOC 2, this is often a non-negotiable requirement.

For broader email infrastructure context, see our [SMTP milter management guide](../2026-05-10-self-hosted-smtp-milter-management-milter-manager-rspamd-opendkim-guide/) and [mail queue management article](../2026-05-05-self-hosted-mail-queue-management-postfix-mailgraph-pflogsumm-guide/). If you're building your mail server from scratch, our [spam filtering comparison](../2026-04-26-spamassassin-vs-rspamd-vs-amavis-self-hosted-spam-filtering-guide-2026/) provides essential background on the milter ecosystem.

## How Email Disclaimer Tools Work

All three tools operate as Postfix content filters or milters that intercept outbound messages, parse the MIME structure, and inject disclaimer text before the message leaves your server. The key difference lies in their integration approach and feature scope.

**alterMIME** is a lightweight, purpose-built tool that modifies MIME-encoded email. It acts as a simple content filter in Postfix, called via a pipe in `master.cf`. It can add disclaimers, insert headers, replace attachments, and modify the message body. It is written in C and designed for high throughput with minimal resource consumption.

**MIMEDefang** is a more comprehensive milter framework written in Perl. It exposes the full MIME structure to customizable filter scripts, enabling complex processing logic beyond simple disclaimer insertion. It can scan attachments with ClamAV, reject messages based on policy, and modify headers and bodies through a flexible API. MIMEDefang supports multiplexed operations for high-volume mail servers.

**Amavis** (specifically amavisd-new) is a full email content filtering interface that bridges Postfix and external scanners. While primarily known for virus and spam scanning, Amavis supports disclaimer insertion via policy banks and can add per-domain or per-user signatures. It is the heaviest of the three options but offers the most comprehensive email processing pipeline.

## Comparison Table

| Feature | alterMIME | MIMEDefang | Amavis (amavisd-new) |
|---------|-----------|------------|---------------------|
| Integration Method | Postfix pipe filter | Milter protocol | SMTP/LMTP content filter |
| Language | C | Perl | Perl |
| Performance | Very high (C, minimal overhead) | High (multiplexed workers) | Moderate (full content scanning) |
| Disclaimer Insertion | HTML and plain text | HTML and plain text, template-based | HTML and plain text, per-domain policies |
| Attachment Handling | Replace, remove, or add | Full extraction, scanning, manipulation | Full extraction, virus scanning integration |
| Header Modification | Yes | Yes (full API) | Yes (via policy banks) |
| ClamAV Integration | No | Yes (native) | Yes (via helper) |
| DKIM Awareness | Signature-before-disclaimer aware | Full milter ordering control | Post-filter signing support |
| Resource Usage | Minimal (~5 MB RAM) | Moderate (~50-100 MB RAM) | Heavy (~200+ MB RAM) |
| Configuration Complexity | Simple (command-line flags) | Moderate (Perl filter scripts) | High (policy banks, SQL backends) |
| Active Development | Low (mature/stable) | Active (2024+ updates) | Active (2025+ releases) |
| Package Availability | apt, yum, ports | apt, yum, ports, CPAN | apt, yum, CPAN |

## Installing and Configuring alterMIME

alterMIME is available in most distribution repositories. On Debian/Ubuntu:

```bash
apt-get update && apt-get install -y altermime
```

On RHEL/Rocky Linux:

```bash
dnf install -y epel-release && dnf install -y altermime
```

Postfix master.cf configuration to pipe outbound mail through alterMIME:

```
# /etc/postfix/master.cf
smtp      inet  n       -       n       -       -       smtpd
  -o content_filter=disclaimer:dummy

disclaimer unix - n n - - pipe
  flags=Rq user=filter argv=/usr/bin/altermime --input=${sender} --disclaimer=/etc/altermime/disclaimer.txt --disclaimer-html=/etc/altermime/disclaimer.html --force-for-bad-html ${recipient}
```

Create your disclaimer text files:

```bash
cat > /etc/altermime/disclaimer.txt << 'EOF'
This email and any attachments are confidential and intended solely
for the use of the individual or entity to whom they are addressed.
If you have received this email in error, please notify the sender
immediately and delete it from your system.
EOF

cat > /etc/altermime/disclaimer.html << 'EOF'
<p style="font-size:12px;color:#666;border-top:1px solid #ccc;padding-top:8px;">
This email and any attachments are confidential and intended solely
for the use of the individual or entity to whom they are addressed.
</p>
EOF
```

## Installing and Configuring MIMEDefang

MIMEDefang requires several Perl modules and works as a milter:

```bash
apt-get install -y mimedefang libmilter-dev libmailtools-perl   libmime-tools-perl libio-stringy-perl libdigest-sha-perl   libunix-syslog-perl spamassassin clamav-daemon
```

Basic milter configuration in Postfix main.cf:

```
# /etc/postfix/main.cf
milter_default_action = accept
milter_protocol = 6
smtpd_milters = unix:/var/spool/MIMEDefang/mimedefang.sock
non_smtpd_milters = unix:/var/spool/MIMEDefang/mimedefang.sock
```

The filter logic lives in `/etc/mail/mimedefang-filter`. Here is a basic disclaimer insertion filter:

```perl
# /etc/mail/mimedefang-filter
sub filter_end {
    my($entity) = @_;

    # Only process outbound messages
    return if (message_contains_virus());

    my $disclaimer_text = "CONFIDENTIAL: This email is intended only for the named recipient.";
    my $disclaimer_html = "<hr><p><small>CONFIDENTIAL: This email is intended only for the named recipient.</small></p>";

    # Append text disclaimer
    append_text_boilerplate($entity, $disclaimer_text, 0);

    # Append HTML disclaimer
    append_html_boilerplate($entity, $disclaimer_html, 0);

    return;
}

sub filter_initialize {
    # Initialize ClamAV
    clamav_init();
}
```

## Installing Amavis for Disclaimer Management

Amavis is typically configured with a dedicated policy bank for outbound disclaimer insertion:

```bash
apt-get install -y amavisd-new spamassassin clamav-daemon
```

Configure disclaimer policies in `/etc/amavis/conf.d/50-user`:

```perl
# /etc/amavis/conf.d/50-user
$policy_bank{'ORIGINATING'} = {
    originating => 1,
    final_destiny => D_PASS,
    bypass_spam_checks_maps => [1],
    disclaimer_options => 'legal',
};

# Define disclaimer text
$defang_maps_by_ccat{+CC_CLEAN} = ['disclaimer'];

@disclaimer_options_bysender_maps = ({
    '.' => {
        'legal' => new Automake::Disclaimers(
            text => '/etc/amavis/disclaimer.txt',
            html => '/etc/amavis/disclaimer.html',
        ),
    },
});

1;
```

For integration with Postfix, Amavis runs on a dedicated LMTP port:

```
# /etc/postfix/main.cf
content_filter = smtp-amavis:[127.0.0.1]:10024

# /etc/postfix/master.cf
smtp-amavis unix - - n - 2 smtp
  -o smtp_data_done_timeout=1200
  -o smtp_send_xforward_command=yes
  -o disable_dns_lookups=yes
```

## Choosing the Right Tool

**Choose alterMIME** if you need a minimal, fast disclaimer injection tool with near-zero resource overhead. It is ideal for smaller mail servers or when you only need to add legal footers without any content scanning requirements. The C implementation means it processes thousands of messages per second with negligible CPU impact.

**Choose MIMEDefang** if you need flexible, programmable email filtering alongside disclaimer insertion. Its Perl filter scripts give you complete control over the MIME structure, making it suitable for complex processing rules. The built-in ClamAV integration adds virus scanning at no extra cost. MIMEDefang strikes the best balance between power and performance for mid-size deployments.

**Choose Amavis** if you are already running a full email security gateway with spam and virus scanning. Since Amavis already processes every message, enabling disclaimer insertion is just a configuration change rather than adding a separate tool. However, the resource overhead is significant — ensure your server has at least 2 GB RAM dedicated to Amavis before enabling additional processing.

## FAQ

### Can I use different disclaimers for different domains?

Yes, all three tools support per-domain disclaimer policies. With alterMIME, you can run multiple instances configured with different disclaimer files. MIMEDefang and Amavis offer native per-domain configuration through their filter scripts and policy banks, making multi-tenant deployments straightforward.

### Will the disclaimer break DKIM signatures?

This is a common concern. The key is **signing order**: the disclaimer tool must process the message **before** DKIM signing. In Postfix, milters execute in order — configure your DKIM milter (OpenDKIM) to run after MIMEDefang. With alterMIME (pipe-based), use `-a` flag to signal that signing should happen after alteration. Amavis supports `originating => 1` policy banks that release the message back to Postfix for DKIM signing after content filtering.

### Can I add images or company logos to the disclaimer?

Yes. HTML disclaimers support inline images using CID references or data URIs. However, be aware that many email clients block external images by default, and very large disclaimers can inflate message size. A good practice is to use simple HTML with CSS-styled text rather than logo images, ensuring the disclaimer renders consistently across all email clients.

### How do I test that disclaimers are being applied?

The simplest method is to send a test email to an external address (like Gmail) and inspect the raw message source. You can also use `swaks` to test locally:

```bash
swaks --to test@example.com --from sender@yourdomain.com   --server localhost --body "Test message body"   --header "Subject: Disclaimer Test"
```

Check `/var/log/mail.log` for any milter or filter errors, and verify the received message includes your disclaimer.

### Do these tools work with other MTAs besides Postfix?

alterMIME works as a generic pipe filter compatible with any MTA that supports content filtering (Exim, Sendmail, qmail). MIMEDefang uses the Sendmail milter protocol, which is supported by Postfix, Sendmail, and partially by Exim. Amavis communicates via SMTP/LMTP and works with any MTA, making it the most portable option.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Email Disclaimer & Footer Management: alterMIME vs MIMEDefang vs Amavis",
  "description": "Compare alterMIME, MIMEDefang, and Amavis for self-hosted email disclaimer and legal footer management on Postfix mail servers. Includes configuration examples and DKIM compatibility guidance.",
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
