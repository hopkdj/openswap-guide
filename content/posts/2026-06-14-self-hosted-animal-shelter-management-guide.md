---
title: "Self-Hosted Animal Shelter & Rescue Management: ASM3 vs Shelter Manager vs PetAdoption"
date: "2026-06-14"
tags: ["animal-shelter", "rescue-management", "pet-adoption", "nonprofit", "animal-welfare", "self-hosted"]
draft: false
---

Animal shelters and rescue organizations manage complex operations spanning animal intake, medical treatment tracking, foster home coordination, adoption processing, volunteer scheduling, and donor relationship management — all while operating under the constant pressure of limited kennel space and the ethical imperative to minimize euthanasia rates. Despite the mission-critical nature of this data, a surprising number of shelters still track animals on whiteboards, Excel spreadsheets, or aging desktop software installed on a single computer in the front office.

Self-hosted shelter management platforms bring shelter operations into the modern era without the recurring subscription costs of commercial alternatives like Shelterluv ($200+/month) or PetPoint (enterprise pricing). By running an open-source system on local hardware or a cloud VPS, shelters maintain full control over their animal records, medical histories, and adopter data — important considerations when working with law enforcement on animal cruelty cases or managing the privacy of foster home volunteers.

## Comparison: Animal Shelter Management Platforms

| Feature | ASM3 (Animal Shelter Manager) | Shelter Manager | PetAdoption Platform |
|---------|------------------------------|----------------|---------------------|
| **GitHub Stars** | 140 | Community | Community |
| **Primary Language** | Java/Spring Boot | PHP/Laravel | Python/Django |
| **Animal Intake** | Full intake with photos, microchip | Stray surrender, owner surrender | Adoption-focused intake |
| **Medical Records** | Vaccination tracking, treatments, weight | Basic medical notes | Vaccination records |
| **Foster Management** | Foster home database, assignments | Foster application workflow | Limited |
| **Adoption Processing** | Application review, contracts, fees | Adoption matching | Full adoption pipeline |
| **Volunteer Scheduling** | Shift management, role assignment | Basic scheduling | Volunteer coordination |
| **Reporting** | Asilomar stats, intake/disposition | Custom reports | Adoption metrics |
| **Multi-Site Support** | Yes (shelter network mode) | Single site | Multi-site |
| **Docker Support** | Self-hosting documentation available | Docker Compose | Docker Compose |
| **License** | GPLv3 | MIT | AGPLv3 |

## Self-Hosted Deployment

### ASM3 — Animal Shelter Manager

ASM3 is the most mature open-source shelter management platform, with over 15 years of development history serving shelters across the UK, Australia, and North America. It tracks the complete animal lifecycle from intake through medical care, foster placement, adoption, or other outcomes. ASM3 generates the statistical reports required by shelter accreditation bodies and humane societies, including Asilomar Accords live release rate calculations and intake/disposition summaries by species, age group, and intake type.

```yaml
# docker-compose.yml for ASM3
version: "3.8"
services:
  asm3:
    image: sheltermanager/asm3:latest
    ports:
      - "8080:8080"
    environment:
      ASM_DB_HOST: db
      ASM_DB_PORT: 5432
      ASM_DB_NAME: asm3
      ASM_DB_USER: asm3user
      ASM_DB_PASSWORD: securepassword
      ASM_ADMIN_EMAIL: admin@yourshelter.org
      ASM_SMTP_HOST: smtp.yourshelter.org
      ASM_SMTP_PORT: "587"
      ASM_SMTP_USER: notifications@yourshelter.org
      ASM_SMTP_PASSWORD: smtp_password
    depends_on:
      - db
    volumes:
      - asm_media:/app/media
      - asm_reports:/app/reports

  db:
    image: postgres:16
    environment:
      POSTGRES_USER: asm3user
      POSTGRES_PASSWORD: securepassword
      POSTGRES_DB: asm3
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
  asm_media:
  asm_reports:
```

### Shelter Manager (PHP/Laravel)

Shelter Manager provides a modern PHP-based alternative with a clean Laravel backend and responsive frontend. It focuses on the core shelter workflow — animal registration, medical note-taking, foster application processing, and adoption matching — with an emphasis on ease of deployment for shelters with limited IT resources. The Laravel ecosystem means shelters can leverage existing PHP hosting infrastructure or deploy on shared hosting alongside their public-facing adoption website.

```php
# config/shelter.php — Core configuration
return [
    'organization_name' => env('SHELTER_NAME', 'Your Animal Shelter'),
    'intake_types' => ['stray', 'owner_surrender', 'transfer', 'cruelty_seizure', 'wildlife'],
    'species' => ['dog', 'cat', 'rabbit', 'bird', 'reptile', 'small_mammal', 'livestock'],
    'adoption_fee_defaults' => [
        'dog' => 15000,    // in cents ($150)
        'cat' => 8500,     // $85
        'rabbit' => 5000,  // $50
    ],
    'vaccination_schedule' => [
        'DHPP' => ['initial' => 'intake', 'booster' => '21_days'],
        'Bordetella' => ['initial' => 'intake', 'booster' => null],
        'Rabies' => ['initial' => 'intake_if_12_weeks', 'booster' => '365_days'],
        'FVRCP' => ['initial' => 'intake', 'booster' => '21_days'],
    ],
    'foster_approval_required' => true,
    'adoption_application_review_days' => 3,
];
```

## Why Self-Host Your Shelter Management System?

Animal shelter data carries unique sensitivity. Cruelty case records may be subject to ongoing criminal investigations and cannot be stored on third-party servers where law enforcement access is uncertain. Foster home addresses, volunteer contact information, and adopter background check results all require strict access controls. A self-hosted deployment ensures this data remains under the shelter's direct control, with audit logs showing exactly who accessed which records and when — capabilities that are essential for organizational accreditation through bodies like the Association of Shelter Veterinarians.

The financial case is equally compelling for nonprofit shelters. Commercial shelter software like Shelterluv charges monthly fees per active animal record, meaning costs scale directly with intake volume. A self-hosted ASM3 installation on a $20/month VPS handles unlimited animal records, unlimited users, and unlimited shelter locations — a fixed cost model that nonprofit boards and grant reviewers appreciate. For shelters that also manage donor relationships, our [nonprofit CRM guide](../2026-06-04-self-hosted-nonprofit-crm-association-civicrm-tendenci-guide/) covers tools that integrate well with shelter management workflows.

Offline resilience matters when shelters operate in disaster-prone regions. During hurricanes, wildfires, or flooding events, shelters often become emergency animal evacuation centers operating around the clock — exactly when cloud-dependent software is most likely to be inaccessible due to internet outages. A self-hosted system running on local hardware with battery backup keeps animal tracking operational when it's most critically needed. For shelters accepting monetary donations during emergencies, our [donation platform comparison](../2026-05-01-opencollective-vs-liberapay-vs-giveth-self-hosted-donation-platforms/) covers options for self-hosted fundraising.
## Medical Protocol Management and Population Health

Shelter medicine operates under fundamentally different protocols than private veterinary practice. In a shelter environment, every animal entering the facility must be assumed to carry infectious disease until proven otherwise — a population-health approach that requires systematic intake screening, isolation protocols, and herd immunity management across a constantly changing animal population with unknown vaccination histories.

ASM3's medical module implements these protocols through configurable intake workflows that automatically schedule vaccinations, deworming, and disease testing based on species, estimated age, and intake condition. When a litter of kittens arrives, the system schedules the standard shelter kitten protocol: FVRCP vaccination at intake with boosters at 3-week intervals, deworming at 2-week intervals starting at 2 weeks of age, FeLV/FIV testing at 8 weeks, and spay/neuter scheduling when weight targets are met. For dogs, the system manages the DHPP series, Bordetella for kennel cough prevention in the shelter environment, and rabies vaccination scheduling based on age and local legal requirements.

Disease outbreak tracking is built into the shelter management workflow. When multiple animals in the same housing area develop respiratory symptoms, ASM3's reporting can identify the index case, trace animal movements between housing areas, and generate the quarantine zone documentation that shelter veterinarians need to contain the outbreak. This population-level disease surveillance is particularly important for shelters participating in regional animal transfer programs, where animals moving between shelters can introduce pathogens to naive populations. The medical module's reporting also generates the monthly shelter statistics — intake numbers, live release rates, length of stay averages — that form the basis of shelter performance metrics and accreditation reviews.

## FAQ

### Can ASM3 handle wildlife rehabilitation records?
ASM3 is primarily designed for domestic animal shelters, but it can be configured for wildlife intake by customizing species lists and intake types. Wildlife rehabilitators with specialized needs (permit tracking, release site coordinates, species-specific feeding protocols) may need to supplement ASM3 with a customized medical records module. The configurable reporting engine can generate the disposition summaries required by state wildlife agencies.

### How do self-hosted shelter systems handle microchip registration?
Microchip data is stored as part of the animal record in ASM3 and other shelter platforms, but microchip registration with national databases (like HomeAgain, AKC Reunite, or Found Animals Registry) typically requires separate API integration or manual batch upload. Most shelters use a hybrid workflow: register the microchip with the national database at intake using the manufacturer's portal, then record the microchip number and registry in the shelter management system for quick lookup during reclaim or transfer.

### What hardware is needed for a shelter management server?
A refurbished business desktop (Intel i5, 8GB RAM, 256GB SSD) running Ubuntu Server is more than sufficient for a single-site shelter. Add an uninterruptible power supply (UPS) for the 2-3 hours of runtime needed during common power outages. For shelters in areas with unreliable internet, pair the local server with an LTE failover router so staff can access animal records from mobile devices during off-site adoption events or disaster response deployments.

### How does foster home coordination work in self-hosted systems?
ASM3 includes a foster home database that tracks foster availability (species preferences, space capacity, whether they can take nursing litters or medical cases), current assignments, and foster application status. When an animal needs foster placement, staff can search for available foster homes matching the animal's species, size, and medical needs. Automated email notifications alert foster volunteers when new animals matching their preferences enter the system.

### Are there adoption website integration options?
Yes. ASM3 can publish adoptable animal listings via RSS/XML feeds that can be consumed by a public-facing adoption website or integrated with adoption listing aggregators like Petfinder and Adopt-a-Pet.com. Shelter Manager includes a basic public animal browser that can be embedded in an existing WordPress or static site. For shelters running their own adoption website, the system's REST API enables custom integration with any frontend framework.

---

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Animal Shelter & Rescue Management: ASM3 vs Shelter Manager vs PetAdoption",
  "description": "Compare open-source self-hosted animal shelter management platforms including ASM3 (Animal Shelter Manager), Shelter Manager, and PetAdoption for intake tracking, medical records, foster coordination, and adoption processing.",
  "datePublished": "2026-06-14",
  "dateModified": "2026-06-14",
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
