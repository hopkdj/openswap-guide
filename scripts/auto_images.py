"""
Pi Stack Auto-Image Script v2
Only adds screenshots for software with Web UIs.
Skips CLI-only tools (Redis, etcd, etc.) to avoid wasting time.

Usage: python auto_images.py [post.md] [--dry-run]
  If post.md is provided, only process that file.
  Otherwise, processes files modified in the last 24 hours.
"""
import os
import re
import sys
import subprocess
import time
import json
from pathlib import Path

# ── Configuration ──
CONTENT_DIR = "/root/.hermes/hermes-agent/opensource_alternatives_site/content/posts"
SCREENSHOT_DIR = "/root/.hermes/hermes-agent/opensource_alternatives_site/static/img/screenshots"
DRY_RUN = "--dry-run" in sys.argv
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# ── Known software with Web UIs and their screenshot sources ──
# This is a curated map - we only try to screenshot software we know has a GUI
UI_SOFTWARE_MAP = {
    'casaos': {'repo': 'IceWhaleTech/CasaOS', 'img_pattern': 'snapshot'},
    'umbrel': {'repo': 'getumbrel/umbrel', 'img_pattern': 'umbrel'},
    'yunohost': {'repo': 'YunoHost/yunohost', 'img_pattern': 'admin'},
    'nextcloud': {'repo': 'nextcloud/server', 'img_pattern': 'screenshots'},
    'home assistant': {'repo': 'home-assistant/core', 'img_pattern': 'dashboard'},
    'jellyfin': {'repo': 'jellyfin/jellyfin', 'img_pattern': 'web'},
    'authentik': {'repo': 'goauthentik/authentik', 'img_pattern': 'screenshot'},
    'zitadel': {'repo': 'zitadel/zitadel', 'img_pattern': 'screenshot'},
    'gitea': {'repo': 'go-gitea/gitea', 'img_pattern': 'screenshot'},
    'forgejo': {'repo': 'forgejo/forgejo', 'img_pattern': 'screenshot'},
    'gitlab': {'repo': 'gitlabhq/gitlabhq', 'img_pattern': 'screenshot'},
    'n8n': {'repo': 'n8n-io/n8n', 'img_pattern': 'screenshot'},
    'vikunja': {'repo': 'go-vikunja/vikunja', 'img_pattern': 'screenshot'},
    'penpot': {'repo': 'penpot/penpot', 'img_pattern': 'screenshot'},
    'appsmith': {'repo': 'appsmithorg/appsmith', 'img_pattern': 'screenshot'},
    'budibase': {'repo': 'Budibase/budibase', 'img_pattern': 'screenshot'},
    'directus': {'repo': 'directus/directus', 'img_pattern': 'screenshot'},
    'strapi': {'repo': 'strapi/strapi', 'img_pattern': 'screenshot'},
    'grafana': {'repo': 'grafana/grafana', 'img_pattern': 'screenshot'},
    'kibana': {'repo': 'elastic/kibana', 'img_pattern': 'screenshot'},
    'portainer': {'repo': 'portainer/portainer', 'img_pattern': 'screenshot'},
    'traefik': {'repo': 'traefik/traefik', 'img_pattern': 'dashboard'},
    'haproxy': None,  # CLI only
    'nginx': None,
    'redis': None,
    'etcd': None,
    'consul': None,
    'vault': None,
    'docker': None,
    'kubernetes': None,
    'prometheus': {'repo': 'prometheus/prometheus', 'img_pattern': 'screenshot'},
    'loki': {'repo': 'grafana/loki', 'img_pattern': 'screenshot'},
    'tempo': {'repo': 'grafana/tempo', 'img_pattern': 'screenshot'},
}

def log(msg):
    print(f"[auto-images] {msg}")

def extract_title(md_content):
    m = re.search(r'title:\s*"([^"]+)"', md_content)
    return m.group(1) if m else ""

def extract_software_from_title(title):
    """Extract software names from title like 'X vs Y vs Z: Description'"""
    # Remove year/guide suffix
    title = re.sub(r'\s*(Best|Top|Complete|Ultimate|Guide|Comparison|Alternatives|20\d{2}).*$', '', title, flags=re.IGNORECASE)
    # Split by vs/and/&
    parts = re.split(r'\s+vs\s+|\s+and\s+|\s+&\s+', title, flags=re.IGNORECASE)
    # Clean up
    names = []
    for p in parts:
        p = p.strip().rstrip(':').strip()
        if 2 < len(p) < 40:
            names.append(p)
    return names

def get_github_readme_images(repo):
    """Get image URLs from a GitHub repo's README."""
    if not repo:
        return []
    
    # Try main branch first, then master
    for branch in ['main', 'master']:
        url = f"https://raw.githubusercontent.com/{repo}/{branch}/README.md"
        result = subprocess.run(['curl', '-sL', '--max-time', '8', url], capture_output=True, text=True)
        if result.returncode == 0 and result.stdout:
            # Find all image URLs
            imgs = re.findall(r'!\[.*?\]\((https?://[^\s)]+\.(?:jpg|jpeg|png|gif|webp))', result.stdout)
            # Filter out badges/logos
            filtered = []
            for img in imgs:
                if any(skip in img.lower() for skip in ['shields.io', 'badge', 'svg', 'logo', 'avatar', 'travis', 'codecov', 'coveralls', 'discord.com/api/guilds']):
                    continue
                # Check for size hints in URL
                if 'width=20' in img or 'height=20' in img or '?s=' in img:
                    continue
                filtered.append(img)
            if filtered:
                return filtered
    return []

def find_best_screenshot(software_name):
    """Find the best screenshot for a software."""
    key = software_name.lower()
    
    # Check our map first
    if key in UI_SOFTWARE_MAP:
        repo_info = UI_SOFTWARE_MAP[key]
        if repo_info is None:
            return None  # Known CLI-only tool
        repo = repo_info.get('repo')
        if repo:
            imgs = get_github_readme_images(repo)
            if imgs:
                return imgs[0]
    
    # Try to auto-discover from GitHub API
    search_term = key.replace(' ', '+')
    api_url = f"https://api.github.com/search/repositories?q={search_term}+in:name&sort=stars&order=desc&per_page=3"
    result = subprocess.run(['curl', '-sL', '--max-time', '8', api_url], capture_output=True, text=True)
    
    if result.returncode == 0 and result.stdout:
        try:
            data = json.loads(result.stdout)
            for item in data.get('items', [])[:3]:
                # Skip forks
                if item.get('fork'):
                    continue
                repo = item['full_name']
                # Check if it's actually about this software
                desc = (item.get('description') or '').lower()
                if key in desc or key in item['name'].lower():
                    imgs = get_github_readme_images(repo)
                    if imgs:
                        return imgs[0]
        except:
            pass
    
    return None

def download_image(url, output_path):
    """Download image, return True on success."""
    if not url:
        return False
    try:
        result = subprocess.run(
            ['wget', '-O', output_path, '--max-time', '15', '-q', url],
            capture_output=True, text=True
        )
        if result.returncode == 0 and os.path.exists(output_path):
            size = os.path.getsize(output_path)
            if size > 5000:  # At least 5KB
                return True
            else:
                os.remove(output_path)
    except:
        pass
    return False

def process_post(md_path):
    """Process a single markdown file."""
    log(f"Processing: {md_path.name}")
    
    with open(md_path, 'r') as f:
        content = f.read()
    
    # Skip if already has cover image
    if 'cover:' in content and 'img/screenshots/' in content:
        log("  Already has cover + screenshots, skipping")
        return
    
    title = extract_title(content)
    if not title:
        return
    
    software_names = extract_software_from_title(title)
    if not software_names:
        return
    
    log(f"  Title: {title}")
    log(f"  Found software: {software_names}")
    
    images_found = []
    for name in software_names:
        key = name.lower()
        
        # Skip known CLI tools
        if key in UI_SOFTWARE_MAP and UI_SOFTWARE_MAP[key] is None:
            log(f"  Skipping {name} (CLI-only)")
            continue
        
        # Skip if already in content
        if f'/img/screenshots/{key}' in content:
            continue
        
        screenshot_url = find_best_screenshot(name)
        if screenshot_url:
            filename = f"{re.sub(r'[^a-z0-9]', '-', key).strip('-')}-dashboard.jpg"
            output_path = os.path.join(SCREENSHOT_DIR, filename)
            
            if DRY_RUN:
                log(f"  [DRY RUN] Would download {name} -> {filename}")
                images_found.append({'name': name, 'filename': filename})
            elif download_image(screenshot_url, output_path):
                log(f"  Downloaded {name} -> {filename}")
                images_found.append({'name': name, 'filename': filename})
            else:
                log(f"  Failed to download {name}")
        else:
            log(f"  No screenshot for {name}")
    
    if images_found:
        # Add cover and hero image
        cover_filename = images_found[0]['filename']
        
        # Insert cover in frontmatter
        if 'cover:' not in content:
            content = re.sub(
                r'(description:\s*"[^"]*")',
                rf'\1\ncover: "/img/screenshots/{cover_filename}"',
                content, count=1
            )
        
        # Insert hero image after frontmatter
        hero_markdown = f'\n![{images_found[0]["name"]} Dashboard](/img/screenshots/{cover_filename} "{images_found[0]["name"]} interface")\n'
        parts = content.split('---', 2)
        if len(parts) >= 3 and '![' not in parts[2][:300]:
            content = parts[0] + '---' + parts[1] + '---' + hero_markdown + parts[2]
        
        # Insert images before each software section
        for img in images_found[1:]:
            pattern = rf'(##\s+.*{re.escape(img["name"])}.*\n)'
            match = re.search(pattern, content, re.IGNORECASE)
            if match and img['filename'] not in content:
                img_md = f'\n![{img["name"]} Dashboard](/img/screenshots/{img["filename"]} "{img["name"]} interface")\n'
                content = content[:match.end()] + img_md + content[match.end():]
        
        if not DRY_RUN:
            with open(md_path, 'w') as f:
                f.write(content)
            log(f"  Updated with {len(images_found)} image(s)")
        else:
            log(f"  [DRY RUN] Would insert {len(images_found)} image(s)")

def main():
    log("Pi Stack Auto-Image Pipeline v2")
    
    if len(sys.argv) > 1 and sys.argv[1].endswith('.md'):
        # Process specific file
        posts = [Path(sys.argv[1])]
    else:
        # Process recent files (last 24h)
        posts = []
        content_path = Path(CONTENT_DIR)
        now = time.time()
        for f in content_path.glob("*.md"):
            if (now - f.stat().st_mtime) <= 86400:
                posts.append(f)
    
    if not posts:
        log("No posts to process")
        return
    
    log(f"Found {len(posts)} post(s) to check\n")
    
    for post in sorted(posts):
        try:
            process_post(post)
        except Exception as e:
            log(f"Error processing {post.name}: {e}")
    
    log(f"\nDone!")

if __name__ == "__main__":
    main()
