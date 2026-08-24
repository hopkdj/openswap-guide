---
title: "PHP Email Libraries in 2026: PHPMailer vs Symfony Mailer vs SwiftMailer"
date: "2026-08-24"
tags: ["php", "email", "backend", "libraries"]
draft: false
cover: "/img/screenshots/phpmailer-cover.png"
---

SwiftMailer is dead. Not "in maintenance mode" — the project's own README says it stopped being maintained at the end of November 2021, and the repository has been archived on GitHub ever since. Yet millions of lines of legacy PHP still call `Swift_Message` today, and every security scan flags them. If you are on SwiftMailer, you are running unpatched mail-sending code, and if you are starting a new PHP project in 2026, you have two real choices: **PHPMailer**, the world's most-installed email class (WordPress, Drupal, Joomla all use it), and **Symfony Mailer**, the component that SwiftMailer's own maintainers tell you to migrate to. This guide compares all three, including exactly how to move off the dead one.

The stakes are higher than most libraries because email sending sits at the intersection of security and deliverability. A header-injection hole in your mailer is remote code execution; a misconfigured SMTP client is your domain landing in spam folders forever. The good news: all three libraries are thin wrappers over the same SMTP protocol, so the decision comes down to ecosystem fit, API design, and maintenance reality — not raw capability.

## TL;DR: Which PHP Email Library Should You Use?

If you are **not on Symfony and just want a bulletproof mailer with zero framework dependencies**, use **PHPMailer** — 22,280 stars, LGPL-2.1, actively maintained, and the default in WordPress and Drupal for a reason. If you are **on Symfony or building modern PHP with Twig templates and event-driven architecture**, use **Symfony Mailer** — it is the official successor to SwiftMailer, supports SMTP plus 40+ third-party transports through DSN strings, and its API is a joy. **Do not start a new project on SwiftMailer, and migrate existing SwiftMailer code now** — it has been unmaintained since 2021, it does not support modern PHP best practices, and the migration is a two-hour job, not a rewrite.

## Feature Comparison Table

Data fetched from GitHub on 2026-08-24.

| Feature | PHPMailer | Symfony Mailer | SwiftMailer |
|---|---|---|---|
| GitHub stars | 22,280 | 1,594 (monorepo: symfony/symfony ~35k) | 9,432 |
| Last push | 2026-08 | 2026-08 | 2021-10 (archived) |
| License | LGPL-2.1 | MIT | MIT |
| Maintenance status | ✅ Active | ✅ Active | ❌ EOL since 2021 |
| Framework dependency | None (standalone) | Symfony components | None |
| SMTP with auth | ✅ LOGIN/PLAIN/CRAM-MD5/XOAUTH2 | ✅ (via EsmtpTransport) | ✅ |
| Third-party API transports | ⚠️ Manual (OAuth2 add-on) | ✅ 40+ (Mailgun, SendGrid, SES...) | ❌ |
| HTML + text multipart | ✅ | ✅ | ✅ |
| Attachments (inline) | ✅ | ✅ | ✅ |
| DKIM signing | ✅ | ✅ | ⚠️ Limited |
| S/MIME | ✅ | ✅ | ❌ |
| Templating | ❌ (string-based) | ✅ Twig integration | ❌ |
| Async/sent events | ❌ | ✅ Event dispatcher | ❌ |
| Error messages localized | ✅ 50+ languages | ❌ | ✅ |
| PHP support | 5.5 → 8.5 | 8.1+ | Legacy only |

## Use-Case Decision Matrix

| Use case | Recommendation | Why |
|---|---|---|
| WordPress/Drupal plugin or standalone script | **PHPMailer** | Zero framework deps; already loaded by the CMS |
| Symfony or Laravel app | **Symfony Mailer** | Native Symfony component; Laravel's mail layer wraps it |
| Twig-rendered transactional emails | **Symfony Mailer** | `TemplatedEmail` + `BodyRenderer` is purpose-built for this |
| Legacy app on SwiftMailer | **Migrate to Symfony Mailer** | Same Symfony family lineage, documented migration path |
| Sending via SES/Mailgun/SendGrid APIs | **Symfony Mailer** | DSN transports (`ses+smtp://`, `mailgun+api://`) out of the box |
| Maximum compatibility with old PHP (5.x) | **PHPMailer** | Still supports PHP 5.5+; only active option for legacy runtimes |
| Security-critical public forms | **Either active library** | Never `mail()` directly — see pitfalls below |

## PHPMailer: The Battle-Tested Standalone

PHPMailer (PHPMailer/PHPMailer, **22,280 stars**, LGPL-2.1, last push August 2026) describes itself as "probably the world's most popular code for sending email from PHP", and the claim holds: it is embedded in WordPress, Drupal, Joomla, SugarCRM, and countless frameworks. The pitch is that PHP's built-in `mail()` function is both feature-poor (no auth, no HTML, no attachments) and dangerous — the README links to a public exploit paper on turning `mail()` header injection into remote code execution. PHPMailer's integrated SMTP client replaces `mail()` entirely and works on every platform, including Windows, without a local mail server.

```bash
composer require phpmailer/phpmailer
```

```php
<?php
use PHPMailer\PHPMailer\PHPMailer;
use PHPMailer\PHPMailer\SMTP;
use PHPMailer\PHPMailer\Exception;

require 'vendor/autoload.php';

$mail = new PHPMailer(true);          // `true` enables exceptions

try {
    $mail->isSMTP();
    $mail->Host       = 'smtp.example.com';
    $mail->SMTPAuth   = true;
    $mail->Username   = 'user@example.com';
    $mail->Password   = 'secret';
    $mail->SMTPSecure = PHPMailer::ENCRYPTION_SMTPS;   // implicit TLS, port 465
    $mail->Port       = 465;                          // use 587 + STARTTLS for some hosts

    $mail->setFrom('from@example.com', 'Mailer');
    $mail->addAddress('joe@example.net', 'Joe User');
    $mail->addReplyTo('info@example.com', 'Information');

    $mail->isHTML(true);
    $mail->Subject = 'Here is the subject';
    $mail->Body    = 'This is the HTML message body <b>in bold!</b>';
    $mail->AltBody = 'This is the plain-text body for non-HTML mail clients';

    $mail->send();
    echo 'Message has been sent';
} catch (Exception $e) {
    echo "Message could not be sent. Mailer Error: {$mail->ErrorInfo}";
}
```

The API is imperative and explicit — every transport detail is a property. That verbosity is also its strength: nothing is hidden, the SMTP conversation is debuggable via `SMTPDebug`, and errors come back in over 50 languages. It supports DKIM and S/MIME signing, inline attachments, iCal events in multiparts, and XOAUTH2 for Google/Microsoft accounts (via the `league/oauth2-client` add-on). The license is LGPL-2.1 with the GPL Cooperation Commitment — fine for proprietary apps when used as a library, which the PHP ecosystem has done for fifteen years without issue.

**Where it hurts:** no templating layer (you build HTML strings yourself), no event system, no async, and no first-party API transports for SES/SendGrid — you speak raw SMTP or wire OAuth2 yourself. For a standalone script it is perfect; for a large application it leaves the plumbing to you.

## Symfony Mailer: The Modern Successor

Symfony Mailer (symfony/mailer, **1,594 stars** as a standalone repo — part of the Symfony monorepo, MIT, last push August 2026) is what SwiftMailer's maintainers explicitly recommend as the migration target: "Symfony Mailer is the next evolution of Swiftmailer. It provides the same features with support for modern PHP code and support for third-party providers." Where PHPMailer is a class you configure property by property, Symfony Mailer is a component with an object model: a `Transport` (how the mail is sent), a `Mailer` (the sender), and an `Email` message builder.

```bash
composer require symfony/mailer
```

```php
use Symfony\Component\Mailer\Transport;
use Symfony\Component\Mailer\Mailer;
use Symfony\Component\Mime\Email;

$transport = Transport::fromDsn('smtp://localhost');
$mailer = new Mailer($transport);

$email = (new Email())
    ->from('hello@example.com')
    ->to('you@example.com')
    ->subject('Time for Symfony Mailer!')
    ->text('Sending emails is fun again!')
    ->html('<p>See Twig integration for better HTML integration!</p>');

$mailer->send($email);
```

The DSN string is the killer feature: `Transport::fromDsn('smtp://user:pass@smtp.example.com:587')` swaps to `'ses+smtp://...'`, `'mailgun+api://...'`, or `'sendgrid+smtp://...'` without changing a line of application code — over 40 third-party transports ship with the ecosystem. Twig integration is first-class: `TemplatedEmail` renders an HTML template with a context array, exactly like rendering a web page, which is how production transactional email should be built.

```php
use Symfony\Bridge\Twig\Mime\BodyRenderer;
use Symfony\Bridge\Twig\Mime\TemplatedEmail;

$email = (new TemplatedEmail())
    ->from('hello@example.com')
    ->to('you@example.com')
    ->subject('Your account is ready')
    ->htmlTemplate('emails/signup.html.twig')
    ->context([
        'expiration_date' => new \DateTimeImmutable('+7 days'),
    ]);
```

Events (`MessageEvent`, `SentMessageEvent`) let you log, queue, or rate-limit sends centrally. If you are on Laravel, note that Laravel's built-in mail layer already uses Symfony Mailer under the hood — you are getting it either way.

**Where it hurts:** it assumes Symfony components (autowiring, DI) for the full experience; the standalone usage above works but you reimplement wiring yourself. It requires PHP 8.1+, so legacy runtimes are out. And the standalone repo's star count looks small next to PHPMailer — but that is monorepo skew, not adoption (symfony/symfony itself has ~35k stars).

## SwiftMailer: The Archive You Are Probably Still Running

SwiftMailer (swiftmailer/swiftmailer, **9,432 stars**, MIT) is the cautionary tale. The README — which has not changed since 2021 — reads: "Swiftmailer will stop being maintained at the end of November 2021. Please, move to Symfony Mailer at your earliest convenience." The repository is archived; there have been zero commits since October 2021. Legacy code looks like this:

```php
// Legacy SwiftMailer (EOL since 2021 — do not use for new code)
require_once '/path/to/vendor/autoload.php';

$transport = (new Swift_SmtpTransport('smtp.example.com', 465, 'ssl'))
    ->setUsername('user@example.com')
    ->setPassword('secret');

$mailer = new Swift_Mailer($transport);

$message = (new Swift_Message('Wonderful Subject'))
    ->setFrom(['from@example.com' => 'Mailer'])
    ->setTo(['recipient@example.com'])
    ->setBody('Here is the message itself');

$mailer->send($message);
```

Nothing in that API is worth preserving: it does not support current PHP idioms, it predates typed properties and named arguments, and — critically — **it receives no security fixes**. A vulnerability found in SwiftMailer in 2026 is a vulnerability forever. The migration path is well documented because Symfony Mailer is its direct descendant: `Swift_Message` → `Email`, `Swift_Mailer::send()` → `$mailer->send($email)`, `Swift_SmtpTransport` → `Transport::fromDsn()`. The conceptual mapping is one-to-one, which is exactly why the maintainers could make the successor a drop-in replacement for the mental model.

## Pitfalls and Migration Guide

**1. Never use `mail()` for anything user-facing.** The README of PHPMailer links to a real-world exploit where `mail()`'s fifth parameter (`-t`) enabled header injection leading to remote code execution. SMTP-to-localhost is both faster and safer; a library is not a convenience, it is a security boundary.

**2. SwiftMailer is a security liability today.** Archived since 2021, zero fixes possible. Composer-based audits (`composer audit`, which flags abandoned packages) will mark it, and so will every serious security scanner. If a security review has not flagged your SwiftMailer dependency yet, it will.

**3. Port 465 vs 587 is not a style choice.** 465 is implicit TLS (SMTPS); 587 is plaintext-with-STARTTLS. Google, Microsoft, and nearly every provider reject credentials over the wrong mode. PHPMailer's example sets `ENCRYPTION_SMTPS` + 465; switch to `ENCRYPTION_STARTTLS` + 587 if your host requires it.

**4. Gmail/Outlook are killing password auth.** Basic SMTP passwords for consumer accounts are being phased out in favor of OAuth2. Both PHPMailer (XOAUTH2 + `league/oauth2-client`) and Symfony Mailer (native `xoauth2://` DSN support) handle this — but your old `setPassword('gmail-app-password')` config may stop working without warning.

**5. DKIM is deliverability, not just signing.** Signing with PHPMailer or Symfony Mailer is only half the battle: your domain needs SPF, DKIM, and DMARC DNS records, or providers quietly file your mail in spam. For the full stack, see our [self-hosted email security guide](../2026-04-28-self-hosted-mta-sts-smtp-dane-email-security-guide-2026/) covering MTA-STS and DANE.

**6. Test against a local SMTP sink before sending.** Every new integration should run against a local capture server first — our [SMTP test server comparison](../2026-05-24-self-hosted-smtp-test-servers-smtp4dev-maildev-fakesmtp-guide/) covers Mailpit, MailHog, and MailCatcher, which let you inspect rendered HTML, headers, and attachments before a single real email goes out.

**7. Upgrade from PHPMailer 5.2.** The 5.2 line (PHP 5.0–7.0) is unsupported, even for security updates. Modern PHPMailer is namespaced (`PHPMailer\PHPMailer\PHPMailer`) with sources in `src/`; the upgrade guide covers the changes, and Composer gets you to `^7.0` in minutes.

**8. Do not build on raw sockets.** Hand-rolling SMTP (or copying a "simple mailer" snippet from a blog) reproduces every encoding bug the libraries fixed over fifteen years: quoted-printable line breaks, UTF-8 headers, CRLF injection, MIME boundary collisions. The PHP ecosystem has spent a decade telling you to use a library — the Go and Node ecosystems reached the same conclusion; see our [Go email library comparison](../2026-07-03-go-email-libraries-gomail-mailgun-go-sendgrid-go-simple-mail/) and [Node email comparison](../2026-07-21-javascript-email-libraries-nodemailer-emailjs-postmark/).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "PHP Email Libraries in 2026: PHPMailer vs Symfony Mailer vs SwiftMailer",
  "description": "Comprehensive 2026 comparison of PHP email libraries: PHPMailer (22,280 stars, LGPL-2.1, active), Symfony Mailer (official SwiftMailer successor, DSN transports, Twig templating), and SwiftMailer (archived/EOL since 2021). Includes migration guide, SMTP security pitfalls, and a use-case decision matrix.",
  "datePublished": "2026-08-24",
  "dateModified": "2026-08-24",
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

### Is SwiftMailer still supported in 2026?

No. SwiftMailer was archived and stopped receiving maintenance at the end of November 2021. The repository's README explicitly tells users to migrate to Symfony Mailer. It receives no bug fixes and no security patches — treat it as an active security liability and plan the migration.

### What is the difference between PHPMailer and Symfony Mailer?

PHPMailer is a standalone, dependency-free class that you configure property by property — the pragmatic choice for scripts, CMS plugins, and legacy PHP. Symfony Mailer is a component-based system with DSN-based transports, Twig templating, event-driven architecture, and first-class support for 40+ third-party email providers — the modern choice for Symfony and Laravel applications.

### Which PHP mail library is the most popular?

PHPMailer, by a wide margin: 22,280 GitHub stars, and it ships inside WordPress, Drupal, and Joomla. Its npm-equivalent install base (Packagist downloads) is the largest of any PHP email package. Symfony Mailer's standalone repo shows 1,594 stars but is part of the Symfony monorepo (~35k stars) and powers Laravel's mail layer.

### How do I migrate from SwiftMailer to Symfony Mailer?

The mapping is direct: `Swift_Message` becomes `Email`, `Swift_Mailer::send($message)` becomes `$mailer->send($email)`, and `Swift_SmtpTransport` becomes `Transport::fromDsn('smtp://...')`. Templated emails use `TemplatedEmail` with a Twig template. A typical application migrates in a few hours — the API shapes were designed to match.

### Does PHPMailer support modern authentication like OAuth2?

Yes. PHPMailer supports the XOAUTH2 SMTP authentication mechanism via the `league/oauth2-client` package and service adapters, which is the path for Google Workspace and Microsoft 365 as they phase out basic password auth.

### What license is PHPMailer under and can I use it commercially?

PHPMailer is LGPL-2.1 with the GPL Cooperation Commitment. LGPL is fine for commercial use — linking against it as a library does not force your application open source — which is why WordPress and countless proprietary apps ship it without issue.

### Which library should I use for sending via SendGrid or Amazon SES?

Symfony Mailer is the strongest choice: its DSN system supports `sendgrid+smtp://`, `ses+smtp://`, and `mailgun+api://` style transports out of the box, so switching providers is a config change rather than a code change. With PHPMailer you handle the provider's SMTP credentials and API quirks manually.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
