---
title: "iCalendar & vCard Libraries in 2026: ical4j vs ical.js vs libical vs ez-vcard"
date: "2026-10-10"
tags: ["calendar", "developer-libraries", "icalendar", "vcard", "synchronisation"]
draft: false
cover: "/img/screenshots/ical4j-logo.jpg"
description: "Comparing the iCalendar and vCard parsing libraries that survive real-world calendar sync in 2026 — ical4j, ical.js, libical, ez-vcard and Python's icalendar — with working code and the RRULE/timezone traps."
---

Calendar synchronisation looks like a solved problem until you ship it. Then you discover that "repeat every second Tuesday until December" is a recurrence rule with its own grammar, that a recurring event's timezone lives in a `VTIMEZONE` block that some clients omit, that an all-day event is a `DATE` while a timed event is a `DATE-TIME` and mixing them shifts everything by a day, and that one vendor writes vCard 3.0 while another writes 4.0 with the photo embedded as base64 and a third expects a URI.

The parsing library you choose decides which of those problems you inherit. Here is how the five libraries that matter in 2026 actually compare, with real GitHub figures and code you can run today.

## TL;DR: The Verdict

**Use `ical.js` for JavaScript/TypeScript or browser work** — it parses both iCalendar and vCard, expands recurrence rules with timezone awareness, and is battle-tested inside Thunderbird. **Use `ical4j` on the JVM** if you want the most complete data model with validation and a fluent builder. **Use `libical` when you are in C, C++ or Python** and need the implementation that GNOME and KDE have shipped for two decades. **Use `ez-vcard` when vCard is the actual product** — it is the only library here with first-class jCard and HTML output. In Python, `icalendar` handles the iCalendar side well, but bring `dateutil` for recurrence expansion.

## The Contenders At A Glance

Live GitHub figures from 2026-10-09/10:

| Property | ical.js | ical4j | libical | ez-vcard | icalendar (Python) |
| --- | --- | --- | --- | --- | --- |
| Repository | [kewisch/ical.js](https://github.com/kewisch/ical.js) | [ical4j/ical4j](https://github.com/ical4j/ical4j) | [libical/libical](https://github.com/libical/libical) | [mangstadt/ez-vcard](https://github.com/mangstadt/ez-vcard) | [collective/icalendar](https://github.com/collective/icalendar) |
| Stars | **1,181 ⭐** | **837 ⭐** | **366 ⭐** | **434 ⭐** | **1,181 ⭐** |
| Last push | 2026-10-05 | 2026-10-09 | 2026-10-06 | 2026-10-06 | 2026-10-09 |
| Language | JavaScript (browser + Node) | Java | C (with bindings) | Java | Python |
| iCalendar (RFC 5545) | Yes | Yes | Yes | No | Yes |
| vCard (RFC 6350) | Yes | Partial (v4.0 group) | Yes | **Yes, primary focus** | Separate `vobject` |
| RRULE expansion built in | **Yes, iterator with timezones** | Yes, `Recur` helper | Yes, `icalrecur` | n/a | No — pair with `dateutil` |
| Builder / write-back | Yes (`Component`, `Property`) | **Yes, fluent `CalendarBuilder`** | Yes (C API) | **Yes, fluent + HTML/jCard output** | Yes |
| License | MPL-2.0 / Apache-2.0 | BSD-3-Clause | LGPL / MPL-2.0 | BSD-3-Clause | BSD-2-Clause |
| Notable users | Thunderbird | Enterprise Java stacks | GNOME, KDE | Java contact apps | Django/Plone ecosystem |

The decision matrix, in ten seconds:

| Your situation | Pick | Why |
| --- | --- | --- |
| Browser or Node app rendering a calendar | **ical.js** | Recurrence iterator and timezone handling in one package |
| Java service that validates calendars before storing them | **ical4j** | Strictest data model; builder catches invalid components early |
| Native desktop app or Python binding | **libical** | Reference-grade C implementation, decades of real-world input |
| Contact import/export product, jCard, HTML previews | **ez-vcard** | vCard 2.1 → 4.0 with jCard and HTML serialisers built in |
| Python API returning calendars as JSON | **icalendar** + `dateutil` | Simple, readable, well-maintained; expand RRULEs with `rrule` |

## ical.js — JavaScript and the Browser

`ical.js` (**1,181 ⭐**, MPL-2.0/Apache-2.0) was extracted from Thunderbird, which is the strongest possible argument for its real-world coverage: it has parsed a decade of mail-attached calendar invitations. It handles both jCal (RFC 7265) and jCard (RFC 7095) as intermediate representations, and it expands recurrence rules with the timezone context attached.

```js
const ICAL = require('ical.js');

const jcal = ICAL.parse(icsText);
const comp = new ICAL.Component(jcal);
const vevent = comp.getFirstSubcomponent('vevent');

const event = new ICAL.Event(vevent);
console.log(event.summary, event.startDate.toJSDate());

// Recurrence expansion — honours RRULE, EXDATE and TZID
const iterator = event.iterator();
let next, count = 0;
while ((next = iterator.next()) && count < 10) {
  console.log(next.toJSDate().toISOString());
  count++;
}
```

Because it speaks jCal, the same parser handles vCard text — which is why ical.js is the pragmatic choice for an address-book feature you did not budget for:

```js
const vcard = new ICAL.Component(ICAL.parse(vcardText));
console.log(vcard.getFirstPropertyValue('fn'));
console.log(vcard.getFirstPropertyValue('email'));
```

**Watch out:** `ical.js` gives you a low-level component tree. There is no schema validation beyond what you write, so a malformed `VEVENT` yields properties you must check yourself.

## ical4j — The JVM's Strictest Model

`ical4j` (**837 ⭐**, BSD-3-Clause, pushed 2026-10-09) is the Java reference implementation. It models components and properties as typed objects, so an invalid date or an unknown parameter surfaces as an exception at parse time rather than a surprise at query time — exactly what you want when a calendar arrives from an untrusted third-party API.

```java
import net.fortuna.ical4j.data.CalendarBuilder;
import net.fortuna.ical4j.model.Calendar;
import net.fortuna.ical4j.model.Component;
import net.fortuna.ical4j.model.component.VEvent;

CalendarBuilder builder = new CalendarBuilder();
Calendar calendar;
try (InputStream in = new FileInputStream("calendar.ics")) {
    calendar = builder.build(in);          // validates structure as it parses
}

for (Object o : calendar.getComponents(Component.VEVENT)) {
    VEvent event = (VEvent) o;
    System.out.println(event.getSummary().getValue());
    System.out.println(event.getStartDate().getDate());   // typed DateTime
}
```

For recurrence, ical4j ships a `Recur` helper that expands a rule against a start date, and the builder API lets you construct calendars programmatically — convenient when you are generating `.ics` files for invitations:

```java
Calendar out = new Calendar();
out.getComponents().add(new VEvent(new DateTime(), "Release window"));
```

The trade-off is weight: ical4j expects you to understand the RFC's object model. That is a feature if you are building a server, and a tax if you are writing a 40-line script.

## libical — The C Reference Implementation

`libical` (**366 ⭐**, LGPL/MPL-2.0) is what GNOME's Evolution and KDE's Kontact have used for years. Its C API is stable and its parser has been fed every broken calendar that Linux desktop users have ever received from Outlook.

```c
#include <libical/ical.h>

icalcomponent *root = icalparser_parse_string(ics_text);
icalcomponent *ev = icalcomponent_get_first_component(root, ICAL_VEVENT_COMPONENT);

if (ev) {
    const char *summary = icalcomponent_get_summary(ev);
    struct icaltimetype start = icalcomponent_get_dtstart(ev);
    printf("%s @ %s\n", summary, icaltime_as_ical_string(start));
}
icalcomponent_free(root);
```

It also exposes `icalrecur.h` for recurrence iteration and `icaltime` for timezone conversion, and the same library is reachable from Python through the `icalendar`/`libical` bindings if you want C-level parsing without writing C. The star count is low because desktop projects do not advertise their dependencies — not because the implementation is thin.

## ez-vcard — When Contacts Are the Product

`mangstadt/ez-vcard` (**434 ⭐**, BSD-3-Clause, pushed 2026-10-06) does one thing and does it thoroughly: vCard. It supports versions 2.1, 3.0 and 4.0, parses and writes jCard (RFC 7095), and can render a card to HTML — which turns a "show this contact" screen into a one-liner.

```java
import ezvcard.Ezvcard;
import ezvcard.VCard;
import ezvcard.VCardVersion;
import ezvcard.property.Email;

VCard card = Ezvcard.parse(vcardText).first();

System.out.println(card.getFormattedName().getValue());
for (Email email : card.getEmails()) {
    System.out.println(email.getValue() + " (" + email.getType() + ")");
}

// Convert a legacy 3.0 card to 4.0 on the way out
String normalized = Ezvcard.write(card).version(VCardVersion.V4_0).go();
```

That version-conversion line is the killer feature in practice. Address books are a swamp of 2.1-era exports, and being able to upgrade them on import — or downgrade for a client that refuses 4.0 — removes a whole category of support tickets.

## Python — icalendar Plus dateutil

`collective/icalendar` (**1,181 ⭐**, pushed 2026-10-09) is the Python default for the iCalendar side: fast, readable, and it returns real `datetime` objects for `dtstart` and `dtend`.

```python
from icalendar import Calendar
from dateutil.rrule import rrulestr

cal = Calendar.from_ical(open("calendar.ics", "rb").read())

for event in cal.walk("vevent"):
    print(event.get("summary"), event.get("dtstart").dt)
    rule = event.get("rrule")
    if rule:
        # expand the recurrence with the same semantics clients use
        for occurrence in rrulestr(rule.to_ical().decode(), dtstart=event.get("dtstart").dt):
            print("  ->", occurrence)
```

The one honest caveat: recurrence expansion lives in `dateutil`, not in the library, so you own the timezone handling. If your calendar data leans heavily on `RRULE` with `TZID`, ical.js or ical4j will save you a week of edge cases.

## Pitfalls: The Traps That Cost Days

- **Bundle `VTIMEZONE` or your event times will shift.** A `DTSTART;TZID=Europe/Berlin` means nothing without the matching `VTIMEZONE` block. When generating `.ics` files, always include the timezone definition — Thunderbird and Outlook will silently fall back to local time otherwise.
- **All-day events use `DATE`, timed events use `DATE-TIME`.** Treating an all-day event's value as a timestamp shifts it by a day for anyone west of UTC. Check the value type before converting.
- **`RRULE` semantics depend on `DTSTART`.** `COUNT` counts occurrences including the first, `UNTIL` is compared in the event's timezone, and `INTERVAL` applies to the frequency unit. Never re-implement this; call the library.
- **`EXDATE` removes, but the UID must match.** Cancelled instances are excluded by date value, not by index — a subtle source of "the deleted meeting came back" bugs.
- **Floating times are not UTC.** A time with no `Z` and no `TZID` is "floating" and should stay in the user's local zone. Forcing it to UTC to normalise your database is a correctness bug.
- **Line folding is 75 octets, not characters.** Multi-byte UTF-8 in a long `SUMMARY` will be split mid-character by naive encoders, producing mojibake that only appears for non-Latin text.
- **Escape commas, semicolons, backslashes and newlines.** vCard and iCalendar both reserve those characters; unescaped user input will corrupt the whole property.
- **Sync needs `UID` + `SEQUENCE` + `ETag`.** For CalDAV-style sync, `UID` identifies an object, `SEQUENCE` orders revisions and the HTTP `ETag` decides conflicts. Parsing alone will not give you convergent sync — see the storage side in our [self-hosted CardDAV comparison](../2026-05-01-baikal-vs-sabredav-vs-nextcloud-contacts-self-hosted-carddav-guide-2026/) and the [WebDAV server guide](../2026-05-10-webdav-servers-radicale-webdav-go-nextcloud-comparison/). If you are rendering the result in a browser, the [calendar UI library comparison](../2026-08-25-calendar-ui-libraries-fullcalendar-react-big-calendar-toast-ui-comparison/) picks up where the parser stops.
- **vCard 4.0 is not universally supported.** Apple and Android clients are inconsistent about `PHOTO` as a URI versus embedded base64; ez-vcard's version conversion is the cleanest mitigation.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "iCalendar & vCard Libraries in 2026: ical4j vs ical.js vs libical vs ez-vcard",
  "description": "A 2026 comparison of iCalendar and vCard parsing libraries — ical.js, ical4j, libical, ez-vcard and Python icalendar — with working code, RRULE expansion and timezone pitfalls.",
  "datePublished": "2026-10-10",
  "dateModified": "2026-10-10",
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

**Which library should I use to parse iCalendar files in JavaScript?**
`ical.js` (kewisch/ical.js). It is the parser extracted from Thunderbird, it handles jCal and jCard, and its iterator expands `RRULE` rules with timezone awareness — which is the part you cannot reasonably write yourself.

**How do I expand a recurring event into individual occurrences?**
Use the library's recurrence engine: `ICAL.Event.iterator()` in ical.js, the `Recur` helper in ical4j, `icalrecur` in libical, and `dateutil.rrule` paired with Python's `icalendar`. Recurrence rules have their own grammar and timezone semantics, so hand-rolled expansion will disagree with clients.

**Why are my events showing up one day early?**
Almost always an all-day event problem. All-day events store a `DATE` value while timed events store a `DATE-TIME`; converting the former to a UTC timestamp shifts it depending on the reader's offset. Check the value type before converting, and render all-day events in the user's local zone.

**Should I store calendar data as raw ICS or as parsed JSON?**
Store the raw ICS text as the source of truth and keep a parsed projection for querying. Round-tripping through a parser is lossy for unknown properties, and calendars from real clients frequently contain non-standard extensions that you want to preserve.

**Is vCard 4.0 safe to use for contact export?**
It is the current standard (RFC 6350) and the best default for new exports, but client support is uneven — especially for embedded photos. Support 3.0 as an export option, and use a library such as ez-vcard that converts between versions rather than a hand-rolled serialiser.

**Do I need a CalDAV server if I already parse iCalendar?**
Yes, for synchronisation. Parsing gives you objects; CalDAV adds the HTTP verbs, `ETag` conflict handling and change-tracking that make multiple clients converge on the same state. Parsing alone is enough only for one-way import or export.

**Can I parse these formats with the language's standard library?**
No. Neither iCalendar nor vCard ships a usable parser in any standard library. Python has none, Java has none, and every implementation in this comparison exists precisely because the grammar — with its folded lines, parameter lists and escaped values — is unforgiving.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
