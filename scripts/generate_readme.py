import json
import os
import re
import urllib.request
from datetime import datetime
from pathlib import Path

USER = os.getenv('GH_USERNAME', 'ramblingThinker')
TOKEN = os.getenv('GH_TOKEN', '')
TEMPLATE = 'README.template.md'
OUTPUT = 'README.md'
WRITEUPS_FILE = Path('content/writeups.json')
HIGHLIGHT_TOPICS = {'platform', 'devops', 'sre', 'security', 'cybersecurity', 'linux', 'observability', 'automation'}

headers = {
    'Accept': 'application/vnd.github+json',
    'User-Agent': f'{USER}-profile-readme-generator'
}
if TOKEN:
    headers['Authorization'] = f'Bearer {TOKEN}'


def gh_json(url):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode('utf-8'))


def parse_dt(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def repo_text(repo):
    topics = repo.get('topics') or []
    return ' '.join([
        repo.get('name', ''),
        repo.get('description') or '',
        ' '.join(topics)
    ]).lower()


def classify_repo(repo):
    text = repo_text(repo)
    sec_keys = ['security', 'cyber', 'soc', 'siem', 'threat', 'detection', 'forensics', 'incident', 'ctf', 'pentest', 'hardening']
    plat_keys = ['platform', 'infra', 'infrastructure', 'devops', 'sre', 'kubernetes', 'docker', 'terraform', 'observability', 'monitoring', 'grafana', 'prometheus', 'aws', 'cloud', 'cicd']
    linux_keys = ['linux', 'bash', 'shell', 'automation', 'script', 'unix', 'dotfiles', 'sysadmin']
    if any(k in text for k in sec_keys):
        return 'security'
    if any(k in text for k in plat_keys):
        return 'platform'
    if any(k in text for k in linux_keys):
        return 'linux'
    return 'other'


def fmt_repo(repo, include_updated=False):
    name = repo['name']
    url = repo['html_url']
    desc = (repo.get('description') or 'No description yet.').strip()
    stars = repo.get('stargazers_count', 0)
    lang = repo.get('language') or 'n/a'
    if include_updated:
        updated = parse_dt(repo['pushed_at']).strftime('%Y-%m-%d')
        return f'- [{name}]({url}) — {desc} _(lang: {lang}, ★ {stars}, updated: {updated})_'
    return f'- [{name}]({url}) — {desc} _(lang: {lang}, ★ {stars})_'


def replace_section(text, section, content):
    pattern = rf'<!-- START_SECTION:{section} -->.*?<!-- END_SECTION:{section} -->'
    repl = f'<!-- START_SECTION:{section} -->\n{content}\n<!-- END_SECTION:{section} -->'
    return re.sub(pattern, repl, text, flags=re.S)


def load_writeups():
    if not WRITEUPS_FILE.exists():
        return []
    try:
        data = json.loads(WRITEUPS_FILE.read_text(encoding='utf-8'))
        return data if isinstance(data, list) else []
    except Exception:
        return []


repos = gh_json(f'https://api.github.com/users/{USER}/repos?per_page=100&sort=updated')
repos = [r for r in repos if not r.get('fork')]

newest = sorted(repos, key=lambda r: parse_dt(r['created_at']), reverse=True)[:6]
updated = sorted(repos, key=lambda r: parse_dt(r['pushed_at']), reverse=True)[:8]

buckets = {'platform': [], 'security': [], 'linux': []}
for repo in repos:
    category = classify_repo(repo)
    if category in buckets and len(buckets[category]) < 5:
        buckets[category].append(repo)

highlighted = []
for repo in sorted(repos, key=lambda r: (r.get('stargazers_count', 0), parse_dt(r['pushed_at'])), reverse=True):
    topics = set(repo.get('topics') or [])
    if topics & HIGHLIGHT_TOPICS or classify_repo(repo) != 'other':
        highlighted.append(repo)
    if len(highlighted) == 4:
        break

writeups = load_writeups()[:5]
writeups_md = '\n'.join(
    f"- [{w.get('title','Untitled')}]({w.get('url','#')}) — {w.get('summary','No summary provided.')} _(topic: {w.get('topic','general')})_"
    for w in writeups
) if writeups else '- Add a `content/writeups.json` file to populate this section automatically.'

with open(TEMPLATE, 'r', encoding='utf-8') as f:
    readme = f.read()

readme = replace_section(readme, 'highlighted', '\n'.join(fmt_repo(r) for r in highlighted) if highlighted else '- Add topics to your repos to surface highlighted projects here.')
readme = replace_section(readme, 'newest', '\n'.join(fmt_repo(r) for r in newest) if newest else '- No public repositories found.')
readme = replace_section(readme, 'repo_updates', '\n'.join(fmt_repo(r, include_updated=True) for r in updated) if updated else '- No recent public repo updates found.')
readme = replace_section(readme, 'platform', '\n'.join(fmt_repo(r) for r in buckets['platform']) if buckets['platform'] else '- Add topics like `platform`, `devops`, `sre`, `observability`, or `aws` to repos to surface them here.')
readme = replace_section(readme, 'security', '\n'.join(fmt_repo(r) for r in buckets['security']) if buckets['security'] else '- Add topics like `security`, `cybersecurity`, `ctf`, `detection`, or `hardening` to repos to surface them here.')
readme = replace_section(readme, 'linux', '\n'.join(fmt_repo(r) for r in buckets['linux']) if buckets['linux'] else '- Add topics like `linux`, `bash`, `automation`, `shell`, or `dotfiles` to repos to surface them here.')
readme = replace_section(readme, 'writeups', writeups_md)

with open(OUTPUT, 'w', encoding='utf-8') as f:
    f.write(readme)
