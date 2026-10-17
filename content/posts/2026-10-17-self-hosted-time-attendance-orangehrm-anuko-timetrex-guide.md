---
title: "Self-Hosted Time & Attendance in 2026: OrangeHRM vs Anuko Time Tracker vs TimeTrex"
date: "2026-10-17"
tags: ["self-hosted", "time-attendance", "hr", "orangehrm", "payroll", "workforce"]
draft: false
description: "Self-hosted time and attendance software compared in 2026: OrangeHRM, Anuko Time Tracker and TimeTrex — deployment, overtime rules, audit trails, and which projects are actually maintained."
---

Every payroll dispute starts the same way: someone claims they worked eight hours, the spreadsheet says seven and a half, and nobody can prove either number. Time and attendance software exists to make that argument impossible — a timestamped, auditable record of who was where, for how long, approved by a named supervisor.

The commercial market answers this with per-employee pricing. The self-hosted market answers it with three names that come up in every procurement thread: **OrangeHRM** (1,153 stars, last commit June 2026), **Anuko Time Tracker** (207 stars, last commit December 2023), and **TimeTrex** (community repository dormant since 2018). They are not equivalent, and two of the three are effectively frozen. This guide explains what each one actually does, how to deploy it, and where the traps are.

## Quick Verdict

**Deploy OrangeHRM** if you need attendance plus leave, timesheets, and employee records in one system that is still being maintained. It is the only one of the three with an actively developed open-source edition and an official container image.

**Use Anuko Time Tracker** if your requirement is narrow — punch in, punch out, project time, weekly approval — and you want something a single person can install on a €5 PHP host and forget about for a year.

**Avoid TimeTrex Community for new deployments.** Its payroll engine is genuinely capable, but the community repository has not seen a commit since 2018, and running a payroll system on an eight-year-old unaudited codebase is a compliance decision, not an IT decision.

## Side-by-Side Comparison

| Dimension | OrangeHRM | Anuko Time Tracker | TimeTrex Community |
|---|---|---|---|
| **Stack** | PHP + MySQL/MariaDB | PHP + MySQL/MariaDB | PHP + PostgreSQL/MySQL |
| **Attendance model** | Web punch in/out, timesheets, leave integration | Punch in/out with project and task attribution | Punch in/out, schedules, absence, job costing |
| **Payroll** | No (exports to payroll) | No (reports only) | Yes, built-in |
| **Overtime rules** | Basic, via timesheet approval | Manual, via report interpretation | Configurable premium policies |
| **Approval workflow** | Supervisor + admin, per timesheet | Supervisor approval per timesheet | Multi-level, per timesheet |
| **Audit trail** | Yes, admin-visible change log | Limited | Yes, detailed |
| **Official container** | Yes — `orangehrm/orangehrm` (249K+ pulls) | No (community images only) | No |
| **License** | GPL-2.0 (open-source edition) | GPL-2.0 | GPL-2.0 (community edition) |
| **GitHub stars** | 1,153 | 207 | 10 |
| **Last commit** | 2026-06-28 | 2023-12-28 | 2018-11-06 |
| **Best fit** | SMEs needing HR + attendance | Small teams needing simple timesheets | Existing legacy installs only |

## Decision Matrix

| Your situation | Recommended | Why |
|---|---|---|
| 20-200 employees, need leave + attendance + records | **OrangeHRM** | Only maintained project with the full HR adjacent modules |
| 3-15 people, billable hours, no HR department | **Anuko Time Tracker** | Minimal footprint, no payroll complexity, easy backup |
| Union rules with shift premiums and job costing | **TimeTrex** (with a hard look at support) | Its payroll policy engine is the most flexible of the three |
| Need biometric terminal integration | None out of the box | Budget for a middleware bridge or a commercial product |
| Must run air-gapped on one VM | **OrangeHRM** or **Anuko** | Both run fully offline with a local database |
| Regulated environment requiring vendor security patches | **OrangeHRM** | Anuko and TimeTrex cannot offer a patch cadence in 2026 |

## OrangeHRM: The Maintained Default

OrangeHRM's open-source edition is the safest starting point because it is the only one of the three where "self-hosted" does not mean "abandoned". The free edition covers employee records (PIM), leave management, timesheets, attendance punch in/out, recruitment, and performance reviews. Payroll is a paid module — for self-hosted deployments you export approved timesheets and process payroll elsewhere.

The official image is the shortest path to a working install:

```yaml
services:
  orangehrm:
    image: orangehrm/orangehrm:latest
    container_name: orangehrm
    restart: unless-stopped
    ports:
      - "8080:80"
    environment:
      ORANGEHRM_DATABASE_HOST: mariadb
      ORANGEHRM_DATABASE_USER: orangehrm
      ORANGEHRM_DATABASE_PASSWORD: change-this-password
      ORANGEHRM_DATABASE_NAME: orangehrm
    depends_on:
      - mariadb

  mariadb:
    image: mariadb:10.11
    container_name: orangehrm-db
    restart: unless-stopped
    environment:
      MARIADB_ROOT_PASSWORD: change-this-root-password
      MARIADB_DATABASE: orangehrm
      MARIADB_USER: orangehrm
      MARIADB_PASSWORD: change-this-password
    volumes:
      - orangehrm-db:/var/lib/mysql

volumes:
  orangehrm-db:
```

Bring it up, then complete the installer at `http://server:8080`:

```bash
docker compose up -d
docker compose logs -f orangehrm
```

Two operational notes from running this in practice. First, the container writes uploads and configuration to its own filesystem — mount a volume for `/var/www/html/lib/confs` and `/var/www/html/web/uploads` if you care about surviving a container recreate. Second, the database is the only state that matters for backups; a nightly `mariadb-dump` of the `orangehrm` schema plus the uploads volume is a complete restore set.

Attendance in OrangeHRM is web-based punch in/out with a timestamp and an optional note. There is no geofencing and no biometric device support in the free edition. For a single-office SME that is fine; for a warehouse with a shared terminal, plan to run a kiosk-mode browser session and accept that a colleague can punch in for a colleague.

## Anuko Time Tracker: Small, Honest, Frozen

Anuko is the opposite design philosophy. It is a single PHP application with a small schema: users, projects, tasks, time records, expenses, and an approval flag. Installation is the classic LAMP routine — copy files, create a database, run the web installer:

```bash
git clone https://github.com/anuko/timetracker.git /var/www/timetracker
mysql -u root -p -e "CREATE DATABASE timetracker CHARACTER SET utf8mb4;"
mysql -u root -p -e "CREATE USER 'tt'@'localhost' IDENTIFIED BY 'strong-password';"
mysql -u root -p -e "GRANT ALL ON timetracker.* TO 'tt'@'localhost';"
```

Then point the web server at the directory and open `/install.php`:

```apache
<VirtualHost *:443>
    ServerName time.example.com
    DocumentRoot /var/www/timetracker
    <Directory /var/www/timetracker>
        AllowOverride All
        Require all granted
    </Directory>
    SSLEngine on
    SSLCertificateFile      /etc/letsencrypt/live/time.example.com/fullchain.pem
    SSLCertificateKeyFile   /etc/letsencrypt/live/time.example.com/privkey.pem
</VirtualHost>
```

What it does well: punch in/out with a comment, per-project and per-task attribution, weekly timesheet submission, supervisor approval, and CSV export that a bookkeeper can actually use. What it does not do: overtime premium calculation, shift scheduling, biometric integration, or granular audit logging.

The last commit was December 2023. That is not automatically disqualifying for a time tracker — the domain changes slowly and the attack surface is small — but it does mean you own security review. Put it behind a reverse proxy with authentication, keep it off the public internet, and patch PHP yourself.

## TimeTrex: Capable Engine, Dormant Repository

TimeTrex Community Edition is the only one of the three with a real payroll engine: wage groups, premium policies, overtime thresholds by jurisdiction, job costing, and accrual balances. On paper it is the most complete open-source workforce management system available.

In practice, the community repository shows **10 stars and a last commit in November 2018**. Development effort goes into the commercial cloud product. If you install the community edition today, you are running code from an era before PHP 7.3 was current — on modern PHP versions it requires patching, and there is no upstream to send those patches to.

If you inherit a TimeTrex installation, the responsible path is to document it, isolate it on its own VM with no outbound access, and plan a migration. If you are choosing fresh software, choose something with a security response process.

## The Compliance Layer Nobody Budgets For

Attendance data is employee personal data, and in several jurisdictions it is regulated more tightly than ordinary HR records.

- **Time zone and DST handling.** A punch at 01:30 on a DST transition day can be recorded twice or not at all. Store UTC timestamps and render local time at display, and check how your chosen system handles the spring-forward gap before your first payroll run.
- **Rounding rules.** Rounding to the nearest five minutes is common and lawful in many places only if it does not systematically favour the employer. Whatever policy you choose, publish it and make the raw punches visible to employees.
- **Biometric terminals.** Fingerprint clock-in is convenient and legally risky: Illinois BIPA requires written consent and a retention policy, and GDPR treats biometric data as a special category. A PIN or badge avoids the entire problem.
- **Retention.** Employment-law retention periods commonly run from two to seven years. Set a retention policy in the database, not in someone's memory, and test the export before you need it.
- **Audit integrity.** A supervisor who can silently edit a punch destroys the evidentiary value of the system. Prefer systems that keep an immutable change log; OrangeHRM logs admin changes, Anuko's logging is thin.

## Migration and Coexistence Notes

- **Attendance is not time tracking.** Project timers (Kimai, ActivityWatch) answer "what did we spend time on"; attendance answers "was this person at work". Most organisations need both, and merging them into one tool usually produces a system that does neither well.
- **Export before you migrate.** Every one of these systems can emit CSV. Pull two years of raw punches, verify totals against payroll, and only then cut over.
- **Never migrate mid-pay-period.** Cut over at the start of a pay period, run both systems in parallel for one cycle, and reconcile the totals before decommissioning the old one.
- **Kiosk mode needs a device policy.** A shared tablet at the entrance will be used to browse the internet unless you lock it down. Use a dedicated browser profile in kiosk mode with no address bar and no other apps.
- **Backups are the whole system.** Attendance records are legally required evidence. A nightly database dump to off-host storage plus a monthly restore test is the minimum, not an optional extra.

## Related Reading

If you are still deciding whether you need attendance or project-level time tracking, our [Kimai vs Traggo vs TimeTagger comparison](../2026-06-08-self-hosted-time-tracking-kimai-traggo-timetagger/) covers the timer-based tools. For the broader HR platform question, the [OrangeHRM vs IceHrm vs Sentrifugo HRIS guide](../2026-04-21-orangehrm-vs-icehrm-vs-sentrifugo-self-hosted-hrms-guide-2026/) goes deeper on employee records and recruitment. And for passive activity tracking as a complement, see [ActivityWatch vs Kimai vs Ever Gauzy](../2026-05-01-activitywatch-vs-kimai-vs-ever-gauzy-self-hosted-time-tracking/).

## FAQ

### What is the difference between time tracking and time and attendance?

Time tracking records effort against projects or clients, usually started and stopped by the worker. Time and attendance records presence: when someone started work, when they stopped, and whether that matches their schedule. Attendance data feeds payroll and legal compliance; time tracking feeds billing and profitability analysis.

### Is OrangeHRM really free for self-hosting?

The open-source edition is GPL-2.0 and free to self-host, including the attendance and timesheet modules. Payroll and some advanced modules are commercial. The official container image is published by OrangeHRM and has been pulled more than 249,000 times, which is a reasonable signal that the self-hosted path is supported rather than an afterthought.

### Can I use a fingerprint scanner with these systems?

Not natively. None of the three open-source editions ships a device driver for biometric terminals. The common approach is a small middleware service that reads the terminal's protocol (ZKTeco devices, for example, are readable through the open-source `pyzk` library) and posts punches into the application's database or API. That bridge is custom software you will have to maintain, and it brings the biometric-privacy obligations described above.

### How do I handle employees who work across midnight?

Record punches as absolute timestamps and compute shifts against a schedule that knows the shift start date, not the calendar date of the punch. Systems that group records by calendar day will split a night shift into two entries and often mis-apply overtime. Test this explicitly before go-live, because it is the single most common attendance bug.

### Do I need a separate database server?

For teams under roughly 100 people, MariaDB on the same host as the application is fine. Beyond that, separate the database onto its own volume and schedule dumps independently. The database is the only irreplaceable component — the application container can be rebuilt from an image in minutes.

### What should I do if I already run TimeTrex Community?

Keep it running, but treat it as frozen. Isolate it on a dedicated VM without outbound internet access, take weekly database dumps, and document the payroll rules it implements. Then evaluate OrangeHRM for attendance and a separate payroll provider, and migrate at a pay-period boundary rather than mid-cycle.

## The Bottom Line

In 2026, self-hosted time and attendance has one actively maintained general-purpose option and two narrow ones. **OrangeHRM** is the default because it is maintained, containerised, and broad enough to replace the spreadsheet. **Anuko** is a perfectly good small tool if you accept that you are the maintainer now. **TimeTrex Community** is a migration project, not a deployment target.

Pick the smallest system that satisfies your legal obligations, then spend the saved budget on backups and an audit policy. The software was never the hard part.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Time & Attendance in 2026: OrangeHRM vs Anuko Time Tracker vs TimeTrex",
  "description": "Self-hosted time and attendance software compared in 2026: OrangeHRM, Anuko Time Tracker and TimeTrex — deployment, overtime rules, audit trails, and which projects are actually maintained.",
  "datePublished": "2026-10-17",
  "dateModified": "2026-10-17",
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
