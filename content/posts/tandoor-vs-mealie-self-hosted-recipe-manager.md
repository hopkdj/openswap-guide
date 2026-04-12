---
title: "Tandoor Recipes vs Mealie: Best Self-Hosted Recipe Manager 2026"
date: 2026-04-12
tags: ["comparison", "guide", "self-hosted", "privacy", "meal-planning"]
draft: false
description: "Compare Tandoor Recipes and Mealie for self-hosted recipe management. Full Docker setup guides, feature comparison, meal planning workflows, and import strategies for 2026."
---

## Why Self-Host Your Recipe Collection?

Recipe platforms like Paprika, Yummly, and BigOven lock your culinary data behind paywalls, limit imports, and can disappear overnight — taking your curated collection with them. Self-hosting a recipe manager puts you in full control:

- **Own your recipes forever** — no subscription fees, no account suspensions, no disappearing services
- **Import from anywhere** — scrape recipes directly from any cooking website with one click
- **Meal planning on your terms** — generate shopping lists, plan weeks ahead, and scale servings without premium tiers
- **Family access** — share your collection with household members, each with their own accounts and preferences
- **Offline availability** — access recipes on your local network even when the internet is down
- **Custom categories and tags** — organize by cuisine, dietary restriction, difficulty, cooking method, or any system you invent

Whether you are a home cook building a personal collection, a family managing weekly dinners, or a meal prep enthusiast tracking macros, a self-hosted recipe manager pays for itself within weeks of the Paprika subscription you will never pay.

## Feature Comparison: Tandoor Recipes vs Mealie

Tandoor Recipes and Mealie are the two leading open-source, self-hosted recipe managers. Both scrape recipes from URLs, support meal planning, and run in Docker. But they differ significantly in philosophy and features.

| Feature | Tandoor Recipes | Mealie |
|---------|----------------|--------|
| **License** | MIT | MIT |
| **Language Stack** | Python/Django + Vue.js | Python/FastAPI + Vue.js |
| **Database** | PostgreSQL or SQLite | PostgreSQL or SQLite |
| **Recipe Import** | URL import, JSON, Paprika, ChowNow, Nextcloud Cook | URL import, JSON, Paprika, Pepper, Tandoor |
| **URL Scrape Success** | Excellent (Django-based parser) | Excellent (recipe-scrapers library) |
| **Image Import** | ✅ Downloads and stores images | ✅ Downloads and stores images |
| **Meal Planning** | ✅ Calendar view with drag-and-drop | ✅ Calendar view with drag-and-drop |
| **Shopping Lists** | ✅ Auto-generated from meal plan | ✅ Auto-generated from meal plan |
| **Servings Scaling** | ✅ Dynamic ingredient scaling | ✅ Dynamic ingredient scaling |
| **Nutritional Info** | ✅ Per-recipe breakdown | ✅ Per-recipe breakdown |
| **Barcode Scanning** | ❌ No | ✅ Yes (mobile web) |
| **Cook Mode** | ✅ Step-by-step full-screen | ✅ Step-by-step full-screen |
| **Multi-language** | 20+ languages | 25+ languages |
| **API** | ✅ Full REST API | ✅ Full REST API |
| **Bookmarks/Collections** | ✅ Custom books with filters | ✅ Categories, tags, and tools |
| **User Roles** | Admin, User, Guest | Admin, User, Read-only |
| **Food/Unit Management** | ✅ Centralized with aliases | ✅ Centralized with aliases |
| **Automations** | ✅ Custom automation rules | ❌ Limited |
| **iOS/Android Apps** | ❌ Progressive Web App only | ❌ Progressive Web App only |
| **Recipe Printing** | ✅ Clean print view | ✅ Clean print view |
| **Comments/Ratings** | ✅ Per recipe | ✅ Per recipe |
| **Fuzzy Search** | ✅ PostgreSQL full-text | ✅ Full-text via SQLAlchemy |
| **Docker Image Size** | ~400 MB | ~250 MB |
| **GitHub Stars** | 3,000+ | 6,000+ |
| **Latest Release Cadence** | Monthly | Bi-weekly |

### Which One Should You Choose?

**Pick Tandoor Recipes if:** you want advanced automation rules, centralized food/unit management with aliases, custom recipe books with dynamic filters, or you are already running a PostgreSQL instance and want deeper integration.

**Pick Mealie if:** you want a lighter footprint, barcode scanning on mobile, a larger community, faster release cycles, or a simpler setup that works well out of the box with minimal configuration.

Both projects are actively maintained, MIT-licensed, and suitable for production use. The remainder of this guide covers Docker deployment for both, so you can test each one before committing.

## Deploying Tandoor Recipes with Docker Compose

### Prerequisites

- Docker and Docker Compose installed
- 512 MB RAM minimum (1 GB recommended)
- A domain name (optional, for reverse proxy access)

### Step 1: Create the Project Directory

```bash
mkdir -p ~/tandoor/{staticfiles,media,nginx}
cd ~/tandoor
```

### Step 2: Write the Docker Compose File

Create `docker-compose.yml`:

```yaml
services:
  db:
    image: postgres:16-alpine
    container_name: tandoor-db
    restart: unless-stopped
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_USER: tandoor
      POSTGRES_PASSWORD: ${DB_PASSWORD:-SuperSecretPassword123}
      POSTGRES_DB: tandoor
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U tandoor"]
      interval: 10s
      timeout: 5s
      retries: 5

  web:
    image: ghcr.io/tandoorrecipes/recipes:latest
    container_name: tandoor-web
    restart: unless-stopped
    volumes:
      - staticfiles:/opt/recipes/staticfiles
      - mediafiles:/opt/recipes/mediafiles
    environment:
      SECRET_KEY: ${SECRET_KEY:-YourRandomSecretKeyHere32chars!}
      DB_ENGINE: django.db.backends.postgresql
      POSTGRES_HOST: db
      POSTGRES_PORT: 5432
      POSTGRES_USER: tandoor
      POSTGRES_PASSWORD: ${DB_PASSWORD:-SuperSecretPassword123}
      POSTGRES_DB: tandoor
      ALLOWED_HOSTS: "*"
    depends_on:
      db:
        condition: service_healthy

  nginx:
    image: nginx:alpine
    container_name: tandoor-nginx
    restart: unless-stopped
    ports:
      - "8080:80"
    volumes:
      - ./nginx/default.conf:/etc/nginx/conf.d/default.conf:ro
      - staticfiles:/static
      - mediafiles:/media
    depends_on:
      - web

volumes:
  postgres_data:
  staticfiles:
  mediafiles:
```

### Step 3: Configure Nginx

Create `nginx/default.conf`:

```nginx
server {
    listen 80;
    server_name _;
    client_max_body_size 10M;

    location / {
        proxy_pass http://web:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /static/;
        expires 30d;
    }

    location /media/ {
        alias /media/;
        expires 7d;
    }
}
```

### Step 4: Generate Secrets and Launch

```bash
# Generate a random secret key
export SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")
export DB_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# Save to .env for future restarts
echo "SECRET_KEY=$SECRET_KEY" > .env
echo "DB_PASSWORD=$DB_PASSWORD" >> .env

# Start the stack
docker compose up -d
```

### Step 5: Initial Setup

Open `http://your-server-ip:8080` in your browser. The first visit prompts you to create an admin account. After logging in:

1. Go to **Settings** → **Search** to configure full-text search (PostgreSQL only)
2. Go to **Settings** → **Import/Export** to set up recipe imports
3. Create your first recipe by pasting a URL from any cooking website into the import field

### Reverse Proxy with HTTPS (Optional)

For external access, put Tandoor behind a reverse proxy. If you are already running Caddy:

```caddy
recipes.yourdomain.com {
    reverse_proxy localhost:8080
    encode gzip
}
```

Caddy automatically provisions and renews TLS certificates via Let's Encrypt.

## Deploying Mealie with Docker Compose

### Prerequisites

- Docker and Docker Compose installed
- 256 MB RAM minimum (512 MB recommended)
- A domain name (optional, for reverse proxy access)

### Step 1: Create the Project Directory

```bash
mkdir -p ~/mealie/data
cd ~/mealie
```

### Step 2: Write the Docker Compose File

Create `docker-compose.yml`:

```yaml
services:
  mealie:
    image: ghcr.io/mealie-recipes/mealie:latest
    container_name: mealie
    restart: unless-stopped
    ports:
      - "9925:9000"
    volumes:
      - ./data:/app/data
    environment:
      # Security
      SECRET_KEY: ${SECRET_KEY:-YourRandomSecretKeyHere32chars!}
      # Database (SQLite default — switch to PostgreSQL for production)
      DB_ENGINE: sqlite
      # SMTP for password resets and notifications
      SMTP_HOST: ""
      SMTP_PORT: 587
      SMTP_FROM_NAME: "Mealie"
      SMTP_AUTH_STRATEGY: "TLS"
      SMTP_FROM_EMAIL: ""
      SMTP_USER: ""
      SMTP_PASSWORD: ""
      # Base URL for email links and notifications
      BASE_URL: "http://localhost:9925"
      # Token settings
      TOKEN_TIME: 48
      # Allow recipe imports from any URL
      RECIPE_PUBLIC: true
    healthcheck:
      test: ["CMD", "wget", "--spider", "http://localhost:9000/api/debug/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Step 3: Generate Secrets and Launch

```bash
# Generate a random secret key
export SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")
echo "SECRET_KEY=$SECRET_KEY" > .env

# Start the stack
docker compose up -d

# Watch the logs for startup confirmation
docker compose logs -f
```

### Step 4: Initial Setup

Navigate to `http://your-server-ip:9925`. On first launch:

1. Create your admin account when prompted
2. Go to **Settings** → **Data Management** to import existing recipes
3. Go to **Settings** → **Email** to configure SMTP for password resets
4. Create a household and invite family members

### Production Deployment with PostgreSQL

For larger recipe collections (500+ recipes), PostgreSQL is recommended over SQLite:

```yaml
services:
  db:
    image: postgres:16-alpine
    container_name: mealie-db
    restart: unless-stopped
    volumes:
      - pg_data:/var/lib/postgresql/data
    environment:
      POSTGRES_USER: mealie
      POSTGRES_PASSWORD: ${DB_PASSWORD:-MealieDbPassword123}
      POSTGRES_DB: mealie
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U mealie"]
      interval: 10s
      timeout: 5s
      retries: 5

  mealie:
    image: ghcr.io/mealie-recipes/mealie:latest
    container_name: mealie
    restart: unless-stopped
    ports:
      - "9925:9000"
    volumes:
      - ./data:/app/data
    environment:
      SECRET_KEY: ${SECRET_KEY:-YourRandomSecretKeyHere32chars!}
      DB_ENGINE: postgres
      POSTGRES_USER: mealie
      POSTGRES_PASSWORD: ${DB_PASSWORD:-MealieDbPassword123}
      POSTGRES_DB: mealie
      POSTGRES_SERVER: db
      POSTGRES_PORT: 5432
      BASE_URL: "http://localhost:9925"
    depends_on:
      db:
        condition: service_healthy

volumes:
  pg_data:
```

## Importing Your Existing Recipe Collection

Both platforms support importing from other services. Here is how to migrate your recipes.

### Import from URLs (Both Platforms)

The most common workflow is importing individual recipes from websites:

```
Paste URL → Platform scrapes recipe schema → Review and edit → Save
```

Both Tandoor and Mealie use the `recipe-scrapers` Python library under the hood, which supports **300+ websites** including:

- AllRecipes, BBC Good Food, Bon Appetit, Budget Bytes
- Epicurious, Food Network, Serious Eats
- King Arthur Baking, NYT Cooking (public recipes)
- Minimalist Baker, Smitten Kitchen, The Woks of Life
- And hundreds more

### Batch Import from Paprika

Both platforms support Paprika export files:

1. In Paprika, export your recipes: **File** → **Export Recipes**
2. This creates a `.paprikarecipes` file (actually a ZIP archive)
3. In Tandoor: **Settings** → **Import/Export** → **Paprika** → upload the file
4. In Mealie: **Settings** → **Data Management** → **Import** → **Paprika** → upload

### Import from Nextcloud Cook

If you currently use the Nextcloud Cook app:

1. Export recipes from Nextcloud Cook (JSON format)
2. In Tandoor: use the **Nextcloud Cook** import option
3. In Mealie: use the generic **JSON** import option

### Import from Plain JSON/CSV

Both platforms accept structured JSON files. The expected format:

```json
{
  "name": "Classic Tomato Soup",
  "description": "A simple, comforting tomato soup",
  "recipeYield": 4,
  "prepTime": "PT10M",
  "cookTime": "PT30M",
  "recipeIngredient": [
    "2 lbs ripe tomatoes, chopped",
    "1 large onion, diced",
    "3 cloves garlic, minced",
    "2 cups vegetable broth",
    "1/2 cup heavy cream",
    "Salt and pepper to taste"
  ],
  "recipeInstructions": [
    {
      "@type": "HowToStep",
      "text": "Sauté onion and garlic in olive oil until softened."
    },
    {
      "@type": "HowToStep",
      "text": "Add tomatoes and broth. Simmer for 25 minutes."
    },
    {
      "@type": "HowToStep",
      "text": "Blend until smooth, stir in cream, and season."
    }
  ]
}
```

## Meal Planning and Shopping List Workflows

A recipe manager becomes truly powerful when you use it to plan meals and generate shopping lists automatically.

### Tandoor Recipes: Weekly Meal Planning

1. Navigate to **Plan** → **Month View** or **Calendar View**
2. Drag recipes from your library onto specific days
3. Set entry types: Breakfast, Lunch, Dinner, Snack
4. Click **Shopping** to auto-generate a consolidated shopping list
5. The system merges duplicate ingredients across all planned meals and scales quantities based on servings

Tandoor's automation feature lets you create rules like:

```
IF recipe is added to meal plan
AND recipe category is "Breakfast"
THEN add all ingredients to shopping list with tag "AM groceries"
```

### Mealie: Group Shopping Lists

Mealie takes a different approach with household-level organization:

1. Create a household for your family or roommates
2. Each member adds recipes to the shared meal plan
3. Navigate to **Shopping Lists** to see the merged ingredient list
4. Check off items as you shop — the list syncs across all household members in real time
5. Create multiple lists for different stores or trips (e.g., "Costco run" vs "Weekly groceries")

Mealie's shopping list supports categories, so ingredients are grouped by aisle:

```
🥩 Protein
  - Chicken breast — 2 lbs
  - Ground beef — 1 lb

🥬 Produce
  - Tomatoes — 6 medium
  - Onion — 2 large
  - Garlic — 1 head

🧀 Dairy
  - Heavy cream — 1/2 cup
  - Parmesan — 4 oz
```

## Backup and Disaster Recovery

Your recipe collection is valuable — back it up regularly.

### Tandoor Recipes Backup

```bash
#!/bin/bash
# backup-tandoor.sh
BACKUP_DIR="$HOME/backups/tandoor"
mkdir -p "$BACKUP_DIR"
DATE=$(date +%Y%m%d_%H%M%S)

# Export recipes via API
curl -s http://localhost:8080/api/export/all \
  -H "Authorization: Token YOUR_API_TOKEN" \
  -o "$BACKUP_DIR/tandoor_backup_$DATE.zip"

# Backup PostgreSQL database
docker exec tandoor-db pg_dump -U tandoor tandoor | gzip > "$BACKUP_DIR/tandoor_db_$DATE.sql.gz"

# Keep only last 30 days of backups
find "$BACKUP_DIR" -name "*.zip" -mtime +30 -delete
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +30 -delete

echo "Backup complete: $BACKUP_DIR"
```

Add this to cron for daily backups:

```bash
# Daily backup at 3 AM
0 3 * * * /home/user/backup-tandoor.sh >> /home/user/backups/tandoor/cron.log 2>&1
```

### Mealie Backup

Mealie stores everything in the `/app/data` volume, making backups straightforward:

```bash
#!/bin/bash
# backup-mealie.sh
BACKUP_DIR="$HOME/backups/mealie"
mkdir -p "$BACKUP_DIR"
DATE=$(date +%Y%m%d_%H%M%S)

# Stop the container briefly for a consistent snapshot
docker compose -f ~/mealie/docker-compose.yml stop mealie

# Create the archive
tar czf "$BACKUP_DIR/mealie_backup_$DATE.tar.gz" -C ~/mealie data

# Restart
docker compose -f ~/mealie/docker-compose.yml start mealie

# Keep only last 30 days
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +30 -delete

echo "Mealie backup complete: $BACKUP_DIR"
```

For Mealie with PostgreSQL, also dump the database as shown in the Tandoor example above.

### Automated Backup with Restic

For encrypted, deduplicated backups to any storage backend:

```bash
# Initialize a restic repository on a remote server
restic -r sftp:backup-server:/restic/mealie init

# Create a backup
restic -r sftp:backup-server:/restic/mealie backup ~/mealie/data

# Automate with cron
0 2 * * * restic -r sftp:backup-server:/restic/mealie backup ~/mealie/data \
  --password-file /home/user/.restic-password >> /var/log/restic-mealie.log 2>&1
```

## Advanced Configurations

### Running Both Side-by-Side for Evaluation

Nothing stops you from running both services simultaneously to compare them:

```yaml
# docker-compose.yml — combined evaluation stack
services:
  tandoor-db:
    image: postgres:16-alpine
    environment:
      POSTGRES_PASSWORD: tandoor_pass
      POSTGRES_DB: tandoor

  tandoor-web:
    image: ghcr.io/tandoorrecipes/recipes:latest
    ports: ["8080:8080"]
    depends_on: [tandoor-db]

  mealie:
    image: ghcr.io/mealie-recipes/mealie:latest
    ports: ["9925:9000"]
    volumes:
      - ./mealie-data:/app/data
```

Import the same 20–30 recipes into each platform, build a week of meal plans, and see which workflow feels more natural. Once you decide, stop and remove the other container.

### Integrating with Home Assistant

If you run Home Assistant, both platforms can integrate with your smart kitchen:

**Mealie** offers an official Home Assistant integration via its REST API. Add to `configuration.yaml`:

```yaml
rest:
  - authentication: bearer_token
    scan_interval: 3600
    resource: "http://mealie:9000/api/recipes"
    headers:
      Authorization: "Bearer YOUR_MEALIE_API_TOKEN"
    sensor:
      - name: "Tonight's Dinner"
        value_template: "{{ value_json.meal_plan.today.dinner.entry.name }}"
```

**Tandoor** can be queried via its REST API in automations to announce today's meal plan on smart speakers or display it on kitchen tablets.

### Reverse Proxy with Traefik

If you already run Traefik as your reverse proxy, here is a labeled configuration for Mealie:

```yaml
services:
  mealie:
    image: ghcr.io/mealie-recipes/mealie:latest
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.mealie.rule=Host(`recipes.example.com`)"
      - "traefik.http.routers.mealie.tls=true"
      - "traefik.http.routers.mealie.tls.certresolver=letsencrypt"
      - "traefik.http.services.mealie.loadbalancer.server.port=9000"
    environment:
      BASE_URL: "https://recipes.example.com"
```

## Conclusion

Self-hosting your recipe collection is one of the most practical homelab projects you can undertake. It saves money, protects your data, and creates a genuinely useful daily tool for everyone in your household.

**Tandoor Recipes** shines with its automation engine, centralized food management, and custom recipe books. It is the more powerful platform if you are willing to invest time in configuration.

**Mealie** delivers a polished, opinionated experience that works beautifully from the first launch. Its barcode scanning, lighter resource footprint, and faster development cycle make it the easier recommendation for most households.

Deploy both, import a few dozen recipes, plan a week of meals on each, and you will quickly know which one fits your kitchen workflow. Either choice means your grandmother's lasagna recipe will outlive every cloud service that ever charged a monthly fee.
