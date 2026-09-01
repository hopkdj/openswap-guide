---
title: "Jakarta Mail vs Simple Java Mail vs Commons Email in 2026: Which Java Email Library Should You Actually Use?"
date: "2026-09-02"
tags: ["java", "email", "smtp", "libraries", "developer-tools"]
draft: false
cover: "/img/screenshots/simple-java-mail-cover.jpg"
---

Sending email from Java looks like a solved problem — until your first production incident. Every team that has debugged "messages silently lost in an SMTP queue" or fought Gmail's authentication changes knows the truth: the library you pick decides how much of that pain you eat. In 2026 the three serious options are **Jakarta Mail** (the platform standard, implemented by Eclipse Angus), **Simple Java Mail** (the fluent high-level wrapper), and **Apache Commons Email** (the thin convenience layer). All three send mail; they differ enormously in what they make easy.

## TL;DR: Quick Verdict

If you want a **minimal dependency for a batch job or utility**, use Apache Commons Email — it is Jakarta Mail with the ceremony removed. If you are building a **production service that sends transactional mail**, use Simple Java Mail: DKIM signing, S/MIME, OAuth2 token refresh, connection pooling, and batching are built in, not bolted on. If you need **protocol-level control — reading IMAP, debugging raw SMTP, or building a mail client** — Jakarta Mail with Angus Mail is the only real choice. Do not default to "whatever the legacy codebase uses"; the javax.mail → jakarta.mail migration decision is now mandatory anyway.

## Head-to-Head Comparison

| Dimension | Jakarta Mail (spec + Angus Mail) | Simple Java Mail | Apache Commons Email |
|---|---|---|---|
| API style | Low-level standard API (`Session`, `MimeMessage`, `Transport`) | Fluent builders (`EmailBuilder`, `MailerBuilder`) | Wrapper classes (`SimpleEmail`, `MultiPartEmail`) |
| Scope | Send + receive (SMTP, IMAP, POP3) | Send-focused, plus EML/`MimeMessage` conversion | Send-only |
| DKIM signing | Manual (needs extra libraries) | Built-in | Not supported |
| S/MIME encryption | Manual (Angus provides low-level support) | Built-in | Not supported |
| OAuth2 (Gmail/O365) | Manual via SASL | Built-in, with token refresh | Not supported |
| Connection pooling | Manual | Built-in | Manual |
| Batching / clusters | Manual | Built-in (batch module, SMTP clusters) | Manual |
| License | EPL-2.0 / GPL-2.0 (classpath exception) | Apache-2.0 | Apache-2.0 |
| GitHub stars (2026-09) | 284 (spec) + 86 (Angus RI) | 1,290 | 178 |
| Last push | 2026-08-28 (spec) / 2025-09 (RI) | 2026-09-01 | 2026-08-31 |

## Use Case Decision Matrix

| Use Case | Recommended Tool | Why |
|---|---|---|
| Quick send from a script, cron job, or admin tool | Apache Commons Email | 3 lines of setup, one dependency, zero boilerplate |
| Transactional email service (welcome mails, receipts, alerts) | Simple Java Mail | DKIM + OAuth2 + pooling + retries covered out of the box |
| Reading mailboxes (IMAP/POP3), building a mail client | Jakarta Mail + Angus | The only option that does receive-side protocols |
| Spring Boot application | Jakarta Mail (via `JavaMailSender`) or Simple Java Mail Spring module | Spring's own abstraction wraps Jakarta Mail; SJM offers direct Spring injection |
| High-volume marketing or relay workloads | Simple Java Mail | Batch module and multi-cluster SMTP configuration are first-class features |

## Jakarta Mail + Angus Mail: The Standard You Can't Avoid

Jakarta Mail (spec repo `jakartaee/mail-api`, 284 stars, active as of August 2026) is the evolution of JavaMail. Since the Jakarta EE 9 namespace switch, you import `jakarta.mail.*` instead of `javax.mail.*`, and the reference implementation is **Eclipse Angus Mail** (`eclipse-ee4j/angus-mail`, EPL-2.0). The spec is updated regularly — the 2.1 release line is current in 2026.

Its power is also its cost: you assemble everything yourself. A minimal TLS send looks like this:

```xml
<dependency>
    <groupId>org.eclipse.angus</groupId>
    <artifactId>angus-mail</artifactId>
    <version>2.0.x</version>
</dependency>
```

```java
Properties props = new Properties();
props.put("mail.smtp.host", "smtp.example.com");
props.put("mail.smtp.port", "587");
props.put("mail.smtp.auth", "true");
props.put("mail.smtp.starttls.enable", "true");

Session session = Session.getInstance(props, new Authenticator() {
    @Override
    protected PasswordAuthentication getPasswordAuthentication() {
        return new PasswordAuthentication("user", "password");
    }
});

MimeMessage message = new MimeMessage(session);
message.setFrom(new InternetAddress("sender@example.com"));
message.setRecipients(Message.RecipientType.TO,
        InternetAddress.parse("recipient@example.com"));
message.setSubject("Test from Jakarta Mail");
message.setText("Hello, Jakarta Mail!");

Transport.send(message);
```

Where Jakarta Mail shines is the receive side and debugging: `Session.setDebug(true)` prints the entire SMTP conversation to stdout, and the IMAP support lets you build sync clients, search folders, and handle `Message` flags without a single external dependency. Use it when you need the whole protocol, not just "send this string".

## Simple Java Mail: The Production Default

Simple Java Mail (`bbottema/simple-java-mail`, 1,290 stars, actively maintained — pushed September 2026, current release 9.3.2) is a fluent wrapper around Jakarta Mail that makes the hard 20% of email actually manageable. The official README's minimal example shows the philosophy: build the email, build the mailer, send.

```java
Email email = EmailBuilder.startingBlank()
    .from("Sender", "sender@example.org")
    .to("Recipient", "recipient@example.net")
    .withSubject("It works")
    .withPlainText("Your first Simple Java Mail message.")
    .buildEmail();

Mailer mailer = MailerBuilder.withSMTPServer(
        System.getenv("SMTP_HOST"),
        587,
        System.getenv("SMTP_USER"),
        System.getenv("SMTP_PASSWORD"))
    .withTransportStrategy(TransportStrategy.SMTP_TLS)
    .buildMailer();

mailer.sendMail(email);
```

The features that matter in production are all in `MailerBuilder`: DKIM signing (`withSigningKey`), S/MIME (`withSigningConfig`/`withEncryptionConfig`), OAuth2 with token refresh for Gmail and Microsoft 365, authenticated SOCKS proxies, connection pooling, async sending, simple batches, and independently configured SMTP clusters for multi-tenant setups. The same builders scale from "one dev machine" to "six SMTP clusters with per-tenant keys" — that is the strongest argument for adopting it before you need it, because migrating later means rewriting every call site.

## Apache Commons Email: Small Jobs, Minimal Friction

Apache Commons Email (`apache/commons-email`, 178 stars, still receiving commits as of August 2026) is the oldest wrapper in this comparison. It does not reinvent the protocol — under the hood it is a thin layer over Jakarta Mail — but it collapses the boilerplate into a few setters. The canonical example from the official user guide:

```java
SimpleEmail email = new SimpleEmail();
email.setHostName("smtp.googlemail.com");
email.setSmtpPort(465);
email.setAuthenticator(new DefaultAuthenticator("username", "password"));
email.setSSLOnConnect(true);
email.setFrom("user@gmail.com");
email.setSubject("TestMail");
email.setMsg("This is a test mail ... :-)");
email.addTo("foo@bar.com");
email.send();
```

`MultiPartEmail` adds attachments, `ImageHtmlEmail` handles HTML with embedded images, and `HtmlEmail` covers HTML bodies. That is the whole feature set — no DKIM, no OAuth2, no IMAP. Note that the 2.0 line is still in milestone stage (`commons-email2-parent 2.0.0-M1`); most projects run the stable 1.6.x artifact. If your need is "send a notification from an internal tool", this is the least code you will ever write. If your roadmap includes deliverability work, you will outgrow it quickly.

Email sending is a cross-language problem, and the same trade-offs appear everywhere. If you build in Go, our [Go email libraries comparison](../2026-07-03-go-email-libraries-gomail-mailgun-go-sendgrid-go-simple-mail/) walks through Gomail and its alternatives, and the [JavaScript email libraries guide](../2026-07-21-javascript-email-libraries-nodemailer-emailjs-postmark/) covers the Node.js side of the same decision.

## Pitfalls: Six Ways Java Email Goes Wrong in Production

1. **The namespace migration is not optional anymore.** Anything still on `javax.mail` is running software from the Java EE 8 era. Jakarta EE 9+ requires `jakarta.mail`, and dependency conflicts (two copies of the API on the classpath) are the #1 cause of `ClassNotFoundException: javax/mail/...` in 2026 deployments.
2. **Gmail and Microsoft 365 killed basic auth.** Plain `setAuthenticator(username, password)` with Gmail fails with `535-5.7.8 Username and Password not accepted` unless you use an app password or OAuth2. Simple Java Mail's built-in OAuth2 with token refresh is the least painful path; with Jakarta Mail you wire SASL yourself.
3. **Port confusion:** 465 is implicit TLS (SMTPS), 587 is STARTTLS. `withTransportStrategy(SMTP_TLS)` on 587, `SMTP_SSL` on 465. Getting this wrong produces "connection reset" errors that look like network issues.
4. **Shared IPs and missing DKIM kill deliverability.** If you send from a shared SMTP relay without DKIM alignment, Gmail marks you spam regardless of library choice. Only Simple Java Mail of the three signs DKIM in-process.
5. **No connection pooling under load.** Jakarta Mail and Commons Email create a new SMTP connection per send by default. At hundreds of messages per minute this turns into TCP handshake storms and provider throttling. Simple Java Mail pools connections by default.
6. **Testing without a mail server is broken testing.** Spin up GreenMail (an in-memory SMTP/IMAP server) in your integration tests so you assert on received messages instead of hoping the send "worked". It works with all three libraries since they all speak the same protocol. If your workload is inbound rather than outbound — parsing and extracting from incoming mail — our [MIME parsing libraries comparison](../2026-06-20-email-mime-parsing-libraries-mailparser-mimekit-gmime/) is the right starting point, and for deliverability infrastructure check the [self-hosted SMTP relay guide](../2026-04-26-postal-vs-stalwart-vs-haraka-self-hosted-smtp-relay-guide-2026/).

## JSON-LD Structured Data

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Jakarta Mail vs Simple Java Mail vs Commons Email in 2026: Which Java Email Library Should You Actually Use?",
  "description": "Deep comparison of the three serious Java email libraries in 2026: Jakarta Mail + Eclipse Angus, Simple Java Mail, and Apache Commons Email. Real code examples, DKIM/OAuth2 coverage, and a use-case decision matrix.",
  "datePublished": "2026-09-02",
  "dateModified": "2026-09-02",
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

### Is Jakarta Mail still maintained in 2026?

Yes. The specification project (`jakartaee/mail-api`) is active — last push August 2026, with the 2.1 release line current. The reference implementation, Eclipse Angus Mail, has been quieter (last major activity 2025), but it remains the standard implementation most applications run.

### What is the difference between javax.mail and jakarta.mail?

The same API under two namespaces. `javax.mail` is the Java EE 8 era package; since Jakarta EE 9 the API lives under `jakarta.mail`. The Maven coordinates also changed (`jakarta.mail:jakarta.mail-api` plus an implementation like `org.eclipse.angus:angus-mail`). Mixing both on the classpath causes runtime class-not-found errors.

### Which Java email library is best for Gmail or Microsoft 365?

Simple Java Mail, because it ships OAuth2 support with automatic token refresh. Gmail and M365 have deprecated basic username/password SMTP auth for most accounts, so a library that manages tokens natively saves you from writing (and debugging) SASL code yourself.

### Can these libraries send HTML emails with embedded images?

All three can. Jakarta Mail requires you to build a `Multipart` with `MimeBodyPart` instances manually. Commons Email provides `HtmlEmail` and `ImageHtmlEmail` for the common cases. Simple Java Mail handles HTML alternatives, embedded images, and attachments through builder methods (`withHTMLText`, `withEmbeddedImage`) with no manual MIME structure.

### Do I need a separate library to read email (IMAP)?

For Java, no — Jakarta Mail (via Angus Mail) is the standard IMAP/POP3 client and the other two libraries are send-only. If you need to read mailboxes, filter folders, or build a sync client, use Jakarta Mail directly.

### Which one should I use with Spring Boot?

Spring Boot's `JavaMailSender` abstraction wraps Jakarta Mail, so any Jakarta Mail-compatible implementation works out of the box. Simple Java Mail also ships a dedicated Spring module that injects a configured `Mailer` bean. For most Spring services, the SJM Spring module gives you the best of both: Spring-style configuration with production features like DKIM and OAuth2.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
