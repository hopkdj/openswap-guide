---
title: "Self-Hosted Web Push Notification Servers — Complete Deployment Guide"
date: 2026-05-01T15:00:00+00:00
tags: ["web-push", "notifications", "self-hosted", "push-service", "onesignal-alternative"]
draft: false
---

Delivering real-time notifications to users' browsers without relying on third-party services like OneSignal or Firebase Cloud Messaging is increasingly important for privacy-focused applications. The Web Push Protocol, standardized by the IETF, allows any server to send push notifications to browsers that support the Notification API. In this guide, we explore how to self-host web push notification infrastructure using open-source tools, and compare the key components you need to build your own notification stack.

## What Is the Web Push Protocol?

The Web Push Protocol enables servers to send notifications to users' browsers through a standardized push service. Unlike proprietary notification services, the protocol is open and interoperable:

- **Browser support** — Chrome, Firefox, Safari, and Edge all support Web Push
- **Service worker-based** — notifications are handled by browser service workers, even when your app is closed
- **Encrypted** — end-to-end encryption between your server and the user's browser
- **No vendor lock-in** — any server implementing the protocol can send notifications to any supporting browser

Self-hosting your push notification server means you control user data, avoid rate limits imposed by third-party services, and eliminate dependency on external infrastructure.

## Web Push Architecture

A self-hosted web push notification system has three main components:

1. **Application Server** — your backend that generates notifications and manages subscriptions
2. **Push Service** — the browser vendor's push service (FCM for Chrome, Mozilla Push for Firefox) that delivers messages
3. **Service Worker** — runs in the user's browser and receives/displays notifications

Unlike centralized services like OneSignal, you can self-host the application server and subscription management while still using the browser vendors' push services for delivery. Alternatively, community projects like PushBits provide a full self-hosted stack.

## Self-Hosted Push Notification Options

### Web Push Libraries (Application Server Side)

The most common approach is to use a Web Push library in your application server. These handle subscription management, encryption, and the Web Push Protocol.

| Library | Language | GitHub Stars | Last Updated |
|---------|----------|-------------|-------------|
| web-push-libs/web-push | Node.js | 3,504 | March 2025 |
| Minishlink/web-push | PHP | 1,869 | March 2026 |
| web-push-libs/web-push-java | Java | Community | Active |

### PushBits — Full Self-Hosted Push Server

PushBits is a standalone Go server that implements the Web Push Protocol server-side, providing a complete self-hosted push notification backend.

| Feature | PushBits | web-push (Node.js) | Minishlink/web-push (PHP) |
|---------|----------|--------------------|--------------------------|
| **Type** | Standalone server | Library | Library |
| **Language** | Go | Node.js | PHP |
| **GitHub Stars** | 357 | 3,504 | 1,869 |
| **Subscription API** | REST API | Custom implementation | Custom implementation |
| **VAPID Support** | Yes | Yes | Yes |
| **Multi-tenant** | Yes | Depends on implementation | Depends on implementation |
| **Docker Support** | Available | Community images | N/A |

### Deploying PushBits with Docker Compose

```yaml
services:
  pushbits:
    image: ghcr.io/pushbits/server:latest
    container_name: pushbits
    ports:
      - "8080:8080"
    environment:
      - PUSHBITS_DB_PATH=/data/pushbits.db
      - PUSHBITS_VAPID_PUBLIC_KEY=${VAPID_PUBLIC_KEY}
      - PUSHBITS_VAPID_PRIVATE_KEY=${VAPID_PRIVATE_KEY}
      - PUSHBITS_VAPID_SUBJECT=mailto:admin@your-domain.com
    volumes:
      - ./pushbits/data:/data
    restart: unless-stopped
```

Generate VAPID keys using the `web-push` CLI tool:

```bash
npm install web-push -g
web-push generate-vapid-keys
```

### Using Web Push Libraries in Your Application

For most applications, integrating a Web Push library into your existing backend is the simplest approach. Here's how to set up the Node.js library:

```javascript
const webpush = require('web-push');

// Configure VAPID keys
webpush.setVapidDetails(
  'mailto:admin@your-domain.com',
  process.env.VAPID_PUBLIC_KEY,
  process.env.VAPID_PRIVATE_KEY
);

// Send a push notification
const pushSubscription = {
  endpoint: 'https://fcm.googleapis.com/fcm/send/...',
  keys: {
    p256dh: 'user_public_key',
    auth: 'user_auth_secret'
  }
};

const notification = JSON.stringify({
  title: 'New Update Available',
  body: 'A new version has been deployed.',
  icon: '/icon.png',
  badge: '/badge.png'
});

webpush.sendNotification(pushSubscription, notification)
  .then(response => console.log('Sent:', response.statusCode))
  .catch(err => console.error('Error:', err));
```

### Service Worker for Receiving Notifications

Every web push implementation requires a service worker in the user's browser:

```javascript
// sw.js
self.addEventListener('push', event => {
  const data = event.data ? event.data.json() : {};
  
  self.registration.showNotification(data.title || 'Notification', {
    body: data.body || '',
    icon: data.icon || '/icon.png',
    badge: data.badge || '/badge.png',
    tag: data.tag || 'default',
    requireInteraction: data.requireInteraction || false,
    actions: data.actions || []
  });
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  event.waitUntil(
    clients.openWindow(event.notification.data?.url || '/')
  );
});
```

## Comparing Self-Hosted Push to Third-Party Services

| Feature | Self-Hosted (PushBits/Libraries) | OneSignal | Firebase Cloud Messaging |
|---------|--------------------------------|-----------|------------------------|
| **Data Ownership** | Full | Shared with OneSignal | Shared with Google |
| **Cost** | Server cost only | Free tier, paid plans | Free |
| **Rate Limits** | Self-determined | Platform-imposed | Platform-imposed |
| **Customization** | Unlimited | Platform-limited | Platform-limited |
| **Setup Complexity** | Moderate | Low | Moderate |
| **Analytics** | Self-implemented | Built-in | Built-in via Firebase |
| **A/B Testing** | Self-implemented | Built-in | Built-in |

For organizations that also need email notification delivery alongside web push, integrating with a self-hosted SMTP relay provides a complete notification infrastructure — see our [SMTP relay comparison](../2026-04-26-postal-vs-stalwart-vs-haraka-self-hosted-smtp-relay-guide-2026/) for Postal and Stalwart options.

## Why Self-Host Your Push Notifications?

Third-party push notification services collect extensive data about your users: which notifications they receive, when they open them, what devices they use, and their engagement patterns. For privacy-focused applications, this data collection is unacceptable.

Self-hosting your push notification infrastructure gives you:
- **Complete privacy** — user notification data never leaves your servers
- **No rate limits** — send as many notifications as your infrastructure can handle
- **Custom logic** — implement sophisticated targeting, scheduling, and A/B testing
- **Regulatory compliance** — easier to meet GDPR, CCPA, and other data protection requirements
- **Independence** — no risk of service changes, price increases, or platform shutdowns

When building a comprehensive self-hosted notification stack, consider pairing web push with other communication channels. Our [email marketing platforms guide](../self-hosted-email-marketing-listmonk-mautic-postal-guide/) covers Listmonk and Mautic for email campaigns, while our [form builders comparison](../2026-04-29-typebot-vs-formbricks-vs-ohmyform-self-hosted-form-builder-comparison/) shows how to collect user notification preferences through self-hosted forms.

## FAQ

### Do I need to self-host the actual push delivery service?

No. The Web Push Protocol uses the browser vendor's push service (FCM for Chrome, Mozilla Push for Firefox) for actual message delivery. What you self-host is the application server that manages subscriptions and sends messages to these push services. This is sufficient for privacy — your server knows which users get which notifications, but the browser vendor doesn't know the content.

### What are VAPID keys and why do I need them?

VAPID (Voluntary Application Server Identification) keys identify your application to the push service. They consist of a public/private key pair that proves your server is authorized to send notifications to subscribed users. Generate them once and store them securely — changing them invalidates all existing subscriptions.

### Can I self-host the push delivery service too?

Technically, yes, but it's rarely practical. You'd need to implement the push protocol for each browser vendor, which is complex. The standard approach is to self-host subscription management and notification generation while using browser vendors' push services for delivery. Projects like PushBits handle this split elegantly.

### How do I handle notification delivery when the user's browser is closed?

The Web Push Protocol stores messages on the browser vendor's push service until the browser comes online. Messages are delivered when the browser next connects. You can set a TTL (Time To Live) to control how long messages are stored — expired messages are discarded.

### Is web push supported on mobile browsers?

Yes, but with limitations. Chrome on Android fully supports Web Push. Safari on iOS supports push notifications starting with iOS 16.4 (when the website is added to the home screen). Firefox on Android supports Web Push. Samsung Internet also has Web Push support.

### How do I manage push notification subscriptions at scale?

Store subscriptions in a database with user associations. Track subscription validity (endpoints can expire), implement retry logic for failed deliveries, and periodically clean up invalid subscriptions. PushBits provides a REST API for subscription management out of the box.

### Can I send rich notifications with images and actions?

Yes. The Web Push Protocol supports notification payloads with titles, body text, icons, badges, action buttons, and custom data. However, the payload size is limited (typically 4KB for Chrome, 8KB for Firefox). For larger payloads, send a minimal notification that triggers the service worker to fetch full content from your server.

### How does self-hosted web push compare to OneSignal?

OneSignal provides a managed service with analytics, A/B testing, segmentation, and multi-channel support (web push, email, SMS). Self-hosting gives you full data control, no rate limits, and unlimited customization, but requires you to build analytics and management features yourself. For privacy-focused applications, self-hosting is the clear choice.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Web Push Notification Servers — Complete Deployment Guide",
  "description": "Build self-hosted web push notification infrastructure as an alternative to OneSignal and Firebase. Compare PushBits, web-push libraries, and deployment guides with Docker Compose.",
  "datePublished": "2026-05-01",
  "dateModified": "2026-05-01",
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
