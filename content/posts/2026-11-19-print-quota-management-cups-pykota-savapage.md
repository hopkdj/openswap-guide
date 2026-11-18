---
title: "Print Quotas on Linux in 2026: Native CUPS Limits vs PyKota vs SavaPage"
date: "2026-11-19"
tags: ["printing", "cups", "sysadmin", "self-hosted", "office-it"]
draft: false
cover: "/img/screenshots/savapage-official.jpg"
description: "How to enforce print quotas and cost accounting on Linux in 2026: native CUPS quota attributes, PyKota's balance-based accounting, and SavaPage's web print portal, with real commands and the traps nobody documents."
---

A shared office printer without accounting is a money leak with a paper tray. One department prints 4,000 pages of draft invoices, another prints nothing, and at the end of the quarter nobody can say who consumed the toner budget. The fix is not a bigger printer — it is a quota layer, and on Linux you have exactly three realistic options: the quota attributes baked into CUPS, PyKota's per-user accounting backend, and SavaPage's full web-based print portal.

Each one answers a different question. CUPS answers "how do I cap pages per user per week". PyKota answers "how do I charge each user from a balance". SavaPage answers "how do I run a managed print service with release stations, cost centers, and a web upload portal". Picking the wrong layer is why so many print-quota projects get abandoned halfway.

## TL;DR: the 30-second verdict

- **Small office, one or two printers, just need a hard page cap?** Use **native CUPS quotas**. Two attributes per printer, no extra daemon, no database.
- **You need per-user balances, per-page charging, and printable reports, and you are comfortable with a legacy Python tool?** Use **PyKota**. It still works, it is still packaged, and it is frozen upstream.
- **You need secure pull printing, badge release, cost centers, and a self-service web portal for 50+ users?** Use **SavaPage**. It is the only one of the three that is a product rather than a script collection.
- **You need per-department chargeback with an external billing system?** None of them do that out of the box; export CUPS `page_log` and join it to your own cost model.

## Side-by-side comparison

| Dimension | Native CUPS quotas | PyKota | SavaPage |
|---|---|---|---|
| What it is | printer attributes enforced by cupsd | CUPS backend wrapper + accounting database | Java web application, IPP proxy, print portal |
| Official source | **`OpenPrinting/cups` (1,799 stars, active 2026-11-18)** | upstream frozen, code still in Debian archive | distributed from savapage.org, no official GitHub repository |
| Extra daemon / database | none | PostgreSQL or SQLite for the quota DB | PostgreSQL + servlet container |
| Enforcement point | scheduler refuses the job | backend rejects the job after filtering | IPP proxy holds the job until release |
| Granularity | pages and KB per user per printer per period | pages, money balance, per user/group/printer | pages, money, cost centers, shared accounts |
| Reporting | `page_log` only | `repykota`, `dumpykota` (text/CSV/XML) | web dashboards, statements, CSV export |
| Secure pull printing | no | no | **yes** (release station, card, web) |
| Web upload portal | no | no | **yes** (`Web Print`) |
| Setup effort | minutes | hours | days |
| Best fit | page caps | balance-based charging | managed print services |

## Scenario decision matrix

| Your situation | Pick | Why |
|---|---|---|
| 8 people, one colour printer, "nobody prints more than 200 pages/week" | **CUPS quotas** | Two `lpadmin` attributes and you are done |
| Student lab where each account has a €10 print credit | **PyKota** | Balance accounting is exactly its model |
| Law firm with badge release at the copier and client-billable cost centres | **SavaPage** | Release stations and cost centres are built in |
| You need to bill printing to an external ERP | **CUPS `page_log` + your own ETL** | All three store data, but none integrate with your ERP |
| Printers are scattered across 20 branches | **SavaPage** | Central IPP proxy and per-branch accounting |
| You cannot add any service to the print server | **CUPS quotas** | Zero new components |

## Native CUPS quotas: the option almost nobody documents

CUPS has shipped per-printer quota enforcement for years, and the documentation for it is essentially the source code. Two directives live in `printers.conf`, and the scheduler exposes them as printer attributes that `lpadmin` can set.

The attributes, confirmed in the CUPS scheduler source (`scheduler/printers.c`, which reads and writes `QuotaPeriod` and `PageLimit` and publishes `job-quota-period`, `job-page-limit` and `job-k-limit`):

```bash
# 500 pages per user per 7 days, and a 10 MB per-user data cap for the same window
lpadmin -p Office_LaserJet \
  -o job-quota-period=604800 \
  -o job-page-limit=500 \
  -o job-k-limit=10240
```

`job-quota-period` is in seconds; `604800` is exactly seven days. After the command, the printer's configuration carries the values directly:

```text
# /etc/cups/printers.conf (excerpt)
<Printer Office_LaserJet>
PrinterId 42
UUID urn:uuid:...
Info Front office colour laser
Location 2nd floor
MakeModel HP Color LaserJet M479
DeviceURI ipp://192.168.10.42/ipp/print
State Idle
StateTime 1763500000
ConfigTime 1763500000
Type 8433684
Accepting Yes
Shared Yes
JobSheets none none
QuotaPeriod 604800
PageLimit 500
KLimit 10240
</Printer>
```

Verify what the scheduler actually holds, rather than trusting the config file:

```bash
lpstat -l -p Office_LaserJet
lpoptions -p Office_LaserJet -l | grep -i quota
```

What this gets you: cupsd refuses jobs that would exceed the limits, per user, per printer, per rolling period. What it does not get you: any report, any money, any way to reset a single user's counter from a UI, and any per-group logic. The counters reset when the period rolls over, and the only record of consumption is the `page_log` file:

```text
# /var/log/cups/page_log — tab separated: printer user job-id date pages copies job-name
Office_LaserJet alice 1187 [19/Nov/2026:09:14:02 +0100] 12 1 invoice-draft
Office_LaserJet bob   1188 [19/Nov/2026:09:15:41 +0100] 3 2 statement
```

That log is the real accounting source for every tool in this article, including SavaPage. A small aggregation script is often all a finance team actually needs:

```bash
# Pages per user for the current month, sorted descending
awk -v m="$(date +%b)" '$4 ~ m {pages[$2]+=$5} END {for (u in pages) print pages[u], u}' \
  /var/log/cups/page_log | sort -rn | head -20
```

Two operational details matter. First, `PageLimit` is enforced by the scheduler, so a job that would exceed the cap is rejected at submission — users see "job held" or a rejection, not a partial print. Second, quotas are per printer, not global: a user with 500 pages on the colour device gets another 500 on the mono device. If you need a single pool across a fleet, CUPS alone cannot do it.

## PyKota: balance-based accounting that refuses to die

PyKota takes the opposite approach. Instead of the scheduler enforcing a page count, PyKota installs itself as a CUPS backend wrapper (`cupspykota`), and every job passes through it. It writes to its own database, charges the user's balance, and rejects the job when the balance hits zero.

It is old software. Upstream development effectively stopped over a decade ago, and the project's documentation is a period piece. But it is still in the Debian archive, which means it still installs and still works on current systems:

```bash
apt-cache policy pykota
apt-get install -y pykota postgresql
```

The backend wiring is the part that trips people up. PyKota must intercept jobs before they reach the real device backend:

```bash
# Symlink the PyKota backend so CUPS can call it
ln -s /usr/share/pykota/cupspykota /usr/lib/cups/backend/cupspykota
chmod 700 /usr/lib/cups/backend/cupspykota
systemctl restart cups
```

Then declare the printer, the price per page, and the users, using PyKota's CLI:

```bash
# Register the printer with a per-page charge of 0.05 and 0.40 for colour
pkprinters --add --charge 0.05 --maxjobsize 100 Office_LaserJet

# Create a user with a €50 balance
pkusers --add --limitby balance --balance 50 alice

# Alternatively, a hard page quota instead of money
edpykota --add --limitby quota --soft 100 --hard 150 bob

# Check what is left
repykota --users alice
```

`repykota` and `dumpykota` are the reporting surface, and `dumpykota --data all --output csv` is what most people pipe into a spreadsheet:

```bash
dumpykota --data history --start 2026-11-01 --end 2026-11-30 --output csv > november-print.csv
warnpykota --groups students --soft 80   # email warnings at 80% of quota
```

Where PyKota still earns its place: the balance model. If your requirement is "each user has a credit, each page costs money, and the job dies when the credit is gone", PyKota expresses that natively, with a database you can query and a per-user ledger you can reconcile. Native CUPS quotas cannot express money at all.

Where it hurts: no web UI, no release stations, no user self-service, Python 2-era code paths in parts of the tree, and documentation that assumes CUPS 1.3. On a modern systemd host you will fight the init scripts. Budget a day, not an hour, and test the backend path with `lp -d Office_LaserJet test.txt` while watching `/var/log/cups/error_log` at debug level.

## SavaPage: the only one that is a product

SavaPage is a Java web application that sits in front of your printers as an IPP proxy. Jobs are not printed when submitted — they are held, and released by the user at a release station, from the web portal, or by swiping a card. Around that core it adds user accounts, shared accounts, cost centres, vouchers, a Web Print upload page, and financial statements.

![SavaPage official logo](/img/screenshots/cups-official.jpg "CUPS remains the print transport underneath every accounting layer")

Architecturally, the pieces you are actually deploying are:

| Component | Role |
|---|---|
| SavaPage server | Java application, holds jobs, serves the user portal and admin console |
| PostgreSQL | users, accounts, transactions, job history |
| IPP proxy printer | the queues users print to; SavaPage forwards to the real device on release |
| Release station | browser or dedicated terminal where a user authenticates and prints |
| CUPS on the host | still the transport driver and the source of `page_log`-style device data |

Deployment is a native installer from savapage.org on Debian/Ubuntu (a PostgreSQL instance is required), followed by a browser-based setup wizard that creates the admin account and the internal database schema. Because it is an IPP proxy, the printers you expose to users are *new* queues created inside SavaPage, not your existing `printers.conf` entries — that is the conceptual jump most first-time deployments miss.

The day-to-day admin workflow is where the value shows up:

1. Create user groups and cost centres, then map each user to a budget.
2. Add the physical printers to SavaPage and let it create the proxy queues.
3. Point clients at the proxy queues (or publish them over IPP/DNS-SD).
4. Configure a release station per floor, or enable "print immediately" for users who do not need pull printing.
5. Turn on statements and let finance export the ledger instead of asking you for a spreadsheet.

What it costs you: a servlet container's worth of memory (realistically 1–2 GB for a small office), a PostgreSQL instance you now back up, and a real deployment project measured in days. What you get in return is the only one of the three that a non-technical office manager can operate without SSH.

Honest caveat on sourcing: SavaPage does not publish its application source as an official GitHub repository — there is no `savapage/savapage` project to star, and most GitHub hits are third-party packaging wrappers. Treat it as open-source-with-caveats: source is distributed by the project, but your supply-chain tooling will not find a repository to pin. If that is a hard requirement, CUPS plus PyKota is the only fully repository-backed path in this article.

## Pitfalls that break print-quota rollouts

**Quotas are per printer, not per fleet.** Three printers with `PageLimit 500` give a user 1,500 pages. If your policy is "500 pages total", CUPS cannot enforce it and PyKota can only approximate it with shared group limits.

**`page_log` is your only audit trail — rotate it deliberately.** A logrotate rule that compresses and deletes after seven days destroys your chargeback history. Ship it to a central log store before rotation touches it.

**Duplicate jobs after a backend failure.** If a PyKota-filtered job fails mid-transfer, the user may retry and be charged twice. Reconcile `dumpykota --data history` against `page_log` monthly; the discrepancy is usually duplicates, not fraud.

**IPP Everywhere clients bypass your carefully built queue.** A user who adds the printer by mDNS may reach the device directly. Disable mDNS advertisement on the device or put printers on a segment that only the print server can reach.

**Release-station sessions expire.** Set the hold time deliberately. A 24-hour hold looks convenient until a hundred stale jobs fill the spool on Monday morning.

**Do not virtualise the print server behind a NAT you do not control.** IPP is chatty, and clients that cannot reach the proxy will silently fall back to direct printing.

If you are still building the underlying print service, start with our [CUPS, IPP Everywhere and Samba print server guide](../2026-06-03-self-hosted-print-server-cups-ipp-everywhere-samba-guide/) and the [label printing walkthrough for Brother QL and ZPL devices](../2026-10-25-self-hosted-label-printing-brother-ql-niimbot-zpl/). Teams automating the documents themselves should see the [document automation comparison](../2026-05-03-docassemble-vs-docxtemplater-vs-pandoc-self-hosted-document-automation-guide/).

## FAQ

### Does CUPS support per-user print quotas natively?

Yes. CUPS exposes `job-quota-period`, `job-page-limit` and `job-k-limit` as printer attributes, settable with `lpadmin -p <printer> -o <attr>=<value>`, and persists them as `QuotaPeriod`, `PageLimit` and `KLimit` in `printers.conf`. The scheduler then refuses jobs that would exceed the limits for that user on that printer within the period.

### Is PyKota still maintained?

Barely. Upstream development stopped around 2015, but the software is still packaged in Debian and still functions as a CUPS backend on current systems. Treat it as frozen-but-working: no new features, and you own any breakage caused by CUPS or Python changes.

### Can I run SavaPage without Docker?

Yes. SavaPage ships a native installer for Debian/Ubuntu and runs as a systemd service with PostgreSQL. Docker wrappers exist but are community-maintained, not official — for production, the native installer plus a managed PostgreSQL instance is the lower-risk path.

### How do I charge different prices for colour and mono?

Native CUPS quotas cannot express money at all — they count pages and kilobytes. PyKota supports per-page charges (`pkprinters --charge`) and per-printer pricing, and SavaPage prices per printer and per colour mode inside its cost model. If money matters, CUPS quotas alone are the wrong tool.

### What is secure pull printing and do I need it?

Pull printing holds a job until the user authenticates at the device, so documents are not left in the output tray and jobs sent to the wrong printer are not wasted. It matters in offices with confidential documents or shared floors. Only SavaPage implements it directly; with CUPS or PyKota you would have to build a hold-and-release workflow yourself.

### Can I export print accounting data to a billing system?

Yes, from all three. CUPS writes `page_log` (tab-separated, one line per job), PyKota exports via `dumpykota --output csv`, and SavaPage produces CSV statements from its ledger. The integration work is mapping users and cost centres to your billing system's identifiers — plan for that step explicitly.

---

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Print Quotas on Linux in 2026: Native CUPS Limits vs PyKota vs SavaPage",
  "description": "Enforce print quotas and cost accounting on Linux: CUPS quota attributes, PyKota balance accounting and SavaPage print portal, with real commands and pitfalls.",
  "datePublished": "2026-11-19",
  "dateModified": "2026-11-19",
  "author": {
    "@type": "Organization",
    "name": "OpenSwap Guide"
  },
  "publisher": {
    "@type": "Organization",
    "name": "OpenSwap Guide",
    "logo": {
      "@type": "ImageObject",
      "url": "https://www.pistack.xyz/logo.png"
    }
  }
}
</script>

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
