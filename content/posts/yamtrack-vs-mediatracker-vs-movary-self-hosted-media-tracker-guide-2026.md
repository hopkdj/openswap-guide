---
title: "Yamtrack vs MediaTracker vs Movary: Best Self-Hosted Media Tracker 2026"
date: 2026-04-19
tags: ["comparison", "guide", "self-hosted", "media", "privacy"]
draft: false
description: "Compare Yamtrack, MediaTracker, and Movary — the top three self-hosted alternatives to Letterboxd and Trakt for tracking movies, TV shows, books, and games."
---

If you track what you watch, read, or play online, chances are you rely on a centralized service like Letterboxd, Trakt, or Goodreads. These platforms are convenient — but they also hold your entire consumption history, viewing habits, and personal ratings on servers you don't control. Accounts get banned, APIs get rate-limited, and services shut down without warning.

Self-hosted media trackers give you the same functionality with full ownership of your data. In this guide, we compare the three leading open-source options: **Yamtrack**, **MediaTracker**, and **Movary**. Each offers a web-based interface for cataloging and rating your media, but they differ significantly in scope, architecture, and target audience.

## Why Self-Host a Media Tracker

There are several compelling reasons to move away from centralized tracking platforms:

- **Data ownership**: Your watch history, ratings, and reviews stay on your own server. No third party can delete, monetize, or restrict access to your data.
- **No account bans**: Centralized platforms can suspend accounts arbitrarily. Self-hosted tools are under your control.
- **Unlimited API access**: Trakt and TMDB impose rate limits on third-party apps. A self-hosted tracker using your own API key avoids shared quotas.
- **Offline access**: Your media library and history remain available even when external services experience outages.
- **Privacy**: No behavioral tracking, no targeted advertising, no data harvesting from your viewing patterns.
- **Integration with self-hosted media servers**: Tools like [jellyfin](https://jellyfin.org/), Plex, and Emby can sync playback status directly to your tracker.

For readers managing their own media infrastructure — perhaps running a [Jellyfin vs Plex vs Emby media server](../jellyfin-vs-plex-vs-emby/) or a [video transcoding pipeline with Tdarr](../tdarr-vs-unmanic-vs-handbrake-self-hosted-video-transcoding-guide-2026/) — a self-hosted media tracker completes the ecosystem.

## Yamtrack: The Full-Featured All-Rounder

[Yamtrack](https://github.com/FuzzyGrim/Yamtrack) is a Django-based media tracker built with Python and backed by PostgreSQL or SQLite. With over 2,500 GitHub stars and active development as of April 2026, it is the most popular option in this comparison.

Yamtrack covers the widest range of media types: movies, TV shows, anime, video games, books, and manga. It pulls metadata from TMDB (The Movie Database), IGDB (Internet Game Database), and other sources to provide rich details including posters, descriptions, and episode lists.

### Key Features

- **Multi-media support**: Movies, TV shows, anime, games, books, and manga in a single interface
- **TMDB and IGDB integration**: Automatic metadata fetching with poster [redis](https://redis.io/)nd descriptions
- **Redis caching**: Built-in Redis layer for fast page loads and reduced API calls
- **PostgreSQL or SQLite**: Choose a lightweight SQLite setup for single users or PostgreSQL for multi-user deployments
- **User accounts**: Multi-user support with per-user watch histories
- **Import/Export**: Import data from Trakt, Letterboxd, and Goodreads via CSV
- **Responsive UI**: Clean Tailwind CSS interface that works on[docker](https://www.docker.com/)op and mobile

### Docker Compose Setup

Yamtrack provides two compose configurations. The default uses SQLite for simplicity:

```yaml
services:
  yamtrack:
    container_name: yamtrack
    image: ghcr.io/fuzzygrim/yamtrack
    restart: unless-stopped
    depends_on:
      - redis
    environment:
      - TZ=Europe/Berlin
      - SECRET=your-secret-key-here
      - REDIS_URL=redis://redis:6379
    volumes:
      - ./db:/yamtrack/db
    ports:
      - "8000:8000"

  redis:
    container_name: yamtrack-redis
    image: redis:8-alpine
    restart: unless-stopped
    volumes:
      - redis_data:/data

volumes:
  redis_data:
```

For production deployments with multiple users, the PostgreSQL variant (`docker-compose.postgres.yml`) replaces SQLite with a dedicated database container for better concurrency and reliability.

Start the stack with:

```bash
docker compose up -d
```

Then access the web UI at `http://your-server:8000`. The first user created automatically becomes the admin.

## MediaTracker: Games, Books, and Audiobooks Included

[MediaTracker](https://github.com/bonukai/MediaTracker) is a TypeScript application that covers movies, TV shows, video games, books, and audiobooks. It has around 900 GitHub stars, though development has slowed since early 2025.

What sets MediaTracker apart is its audiobook support — none of the other trackers in this comparison handle audiobooks natively. It also provides a REST API, making it easy to integrate with custom scripts or other self-hosted services.

### Key Features

- **Audiobook tracking**: The only tracker in this comparison with native audiobook support
- **REST API**: Full programmatic access for integrations and custom dashboards
- **Progress tracking**: Track episode-by-episode progress for TV shows and chapter progress for books
- **User ratings and reviews**: Per-item ratings with optional written reviews
- **Simple deployment**: Single container with bundled SQLite storage
- **Docker volume persistence**: All data stored in a mapped volume for easy backups

### Docker Compose Setup

MediaTracker uses a straightforward single-container setup with SQLite:

```yaml
services:
  mediatracker:
    container_name: MediaTracker
    image: bonukai/mediatracker
    restart: unless-stopped
    ports:
      - "7481:7481"
    volumes:
      - ./data:/storage
      - assets_volume:/assets

volumes:
  assets_volume:
```

Start with:

```bash
docker compose up -d
```

Access the interface at `http://your-server:7481`. The storage volume at `/storage` contains the SQLite database and should be backed up regularly.

## Movary: The Movie Specialist

[Movary](https://github.com/leepeuker/movary) takes a focused approach: it tracks movies and nothing else. Written in PHP, it currently holds around 700 GitHub stars with very active development — version 0.71.1 was released in April 2026.

Movary is ideal if you primarily care about film tracking and want the closest open-source alternative to Letterboxd. Its feature set is deliberately narrow but deep within that niche.

### Key Features

- **Letterboxd import**: Direct CSV import from Letterboxd exports for easy migration
- **TMDB integration**: Automatic movie metadata, posters, and cast information with optional image caching
- **Jellyfin, Plex, and Emby sync**: Automatically mark movies as watched based on playback in your media server
- **Watchlist and diary**: Maintain a watchlist and a chronological diary of viewed films
- **User statistics**: Viewing statistics including total movies watched, average rating, and genre breakdowns
- **Lightweight PHP stack**: Runs on a standard LAMP-style stack without Redis or external dependencies
- **Active development**: Frequent releases with new features and bug fixes

### Docker Compose Setup

Movary ships with a development-oriented compose file, but for production use you can run it directly from the GitHub Container Registry image:

```yaml
services:
  movary:
    container_name: movary
    image: ghcr.io/leepeuker/movary:latest
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      - TMDB_API_KEY=your-tmdb-api-key
      - TMDB_ENABLE_IMAGE_CACHING=1
    volumes:
      - ./data:/var/www/html/data
```

If you need MySQL instead of the built-in SQLite, Movary provides a separate `docker-compose.mysql.yml` file in the repository.

Start the container:

```bash
docker compose up -d
```

Navigate to `http://your-server:8080` and configure your TMDB API key through the settings panel. You can get a free API key from [themoviedb.org](https://www.themoviedb.org/settings/api).

## Feature Comparison

| Feature | Yamtrack | MediaTracker | Movary |
|---------|----------|--------------|--------|
| **Movies** | Yes | Yes | Yes |
| **TV Shows** | Yes | Yes | No |
| **Anime** | Yes | No | No |
| **Video Games** | Yes | Yes | No |
| **Books** | Yes | Yes | No |
| **Manga** | Yes | No | No |
| **Audiobooks** | No | Yes | No |
| **TMDB Integration** | Yes | Yes | Yes |
| **Letterboxd Import** | Yes (CSV) | No | Yes (CSV) |
| **Trakt Import** | Yes | No | No |
| **Plex/Jellyfin Sync** | No | No | Yes |
| **Multi-User** | Yes | Yes | Yes |
| **REST API** | Limited | Yes | No |
| **Database** | PostgreSQL / SQLite | SQLite | SQLite / MySQL |
| **Redis Caching** | Yes | No | No |
| **Language** | Python (Django) | TypeScript | PHP |
| **GitHub Stars** | ~2,500 | ~900 | ~700 |
| **Last Update** | April 2026 | Feb 2025 | April 2026 |

## Which Tracker Should You Choose?

**Choose Yamtrack if** you want the most comprehensive tracker covering the widest range of media types. Its Django architecture with Redis caching delivers good performance, and the multi-database support lets you scale from a personal SQLite setup to a multi-user PostgreSQL deployment. It is the best general-purpose option.

**Choose MediaTracker if** audiobook tracking is important to you, or if you need a REST API to integrate with other tools. The TypeScript stack is clean and the single-container deployment is simple. However, the slower development pace since early 2025 may be a concern for long-term maintainability.

**Choose Movary if** you primarily track movies and want the closest experience to Letterboxd in a self-hosted package. Its Jellyfin/Plex/Emby sync is unique among these three tools, automatically updating your diary when you watch something on your media server. If you run a [self-hosted NAS with TrueNAS or OpenMediaVault](../self-hosted-nas-solutions-openmediavault-truenas-rockstor-guide/) as your media storage, Movary's media server integration makes it a natural fit.

## Migration: Importing Your Existing Data

All three tools support some form of data migration:

### From Letterboxd

1. Go to your Letterboxd account settings and request a data export
2. Download the CSV file containing your diary, ratings, and reviews
3. In Yamtrack: go to Settings → Import → Letterboxd CSV
4. In Movary: go to Settings → Import → Letterboxd CSV

### From Trakt

1. Export your Trakt data via the Trakt export feature or use a tool like `trakt-export`
2. In Yamtrack: go to Settings → Import → Trakt CSV

### From Goodreads

1. Export your Goodreads library as CSV from account settings
2. In Yamtrack: go to Settings → Import → Goodreads CSV
3. In MediaTracker: manually add books or use the REST API to batch import

## FAQ

### Do I need a TMDB API key to use these trackers?

Yes, all three tools rely on The Movie Database (TMDB) for movie and TV show metadata. The API key is free — sign up at [themoviedb.org](https://www.themoviedb.org/settings/api) and paste your key into the tracker's settings. Yamtrack also uses the IGDB API for game metadata, which requires a separate Twitch developer account.

### Can multiple people use the same instance?

Yes. Yamtrack, MediaTracker, and Movary all support multi-user accounts. Each user has their own watch history, ratings, and watchlist. Yamtrack with PostgreSQL is best suited for larger households or group deployments.

### How do I back up my tracker data?

For SQLite-based setups (all three tools support it), simply back up the database file in your Docker volume mount. For Yamtrack with PostgreSQL, use `pg_dump` to create logical backups. Movary with MySQL can use `mysqldump`. Automate backups with a cron job that copies the volume to a separate location.

### Can these trackers replace Letterboxd or Trakt entirely?

For personal use, yes. You lose the social features (friend feeds, public lists, community discussions) but gain complete data ownership and privacy. Yamtrack and Movary both support importing your existing Letterboxd and Trakt data, so the transition is straightforward.

### Which tracker has the best mobile experience?

All three provide responsive web interfaces that work on mobile browsers. None of them currently offer dedicated native mobile apps, but the web UIs are usable on phones and tablets. Yamtrack's Tailwind CSS interface is the most polished of the three on smaller screens.

### Do these trackers work offline?

Once your metadata is fetched from TMDB, it is cached locally. You can browse your collection and add new entries offline. However, fetching new metadata (searching for a movie you haven't logged yet) requires an internet connection to query the TMDB API.

### Is there a way to automatically mark movies as watched?

Movary is the only one of the three with automatic sync to Jellyfin, Plex, and Emby. When you watch a movie on your media server, Movary automatically logs it in your diary. Yamtrack and MediaTracker require manual entry or CSV import.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Yamtrack vs MediaTracker vs Movary: Best Self-Hosted Media Tracker 2026",
  "description": "Compare Yamtrack, MediaTracker, and Movary — the top three self-hosted alternatives to Letterboxd and Trakt for tracking movies, TV shows, books, and games.",
  "datePublished": "2026-04-19",
  "dateModified": "2026-04-19",
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
