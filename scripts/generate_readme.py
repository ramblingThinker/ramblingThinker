import json
import os
import re
import urllib.request
from datetime import datetime, timezone

USER = os.getenv('GH_USERNAME', 'ramblingThinker')
TOKEN = os.getenv('GH_TOKEN', '')
TEMPLATE = 'README.template.md'
OUTPUT = 'README.md'

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


def repo_topics(repo):
    topics = repo.get('topics') or []
    text = ' '.join([
        repo.get('name', ''),
        repo.get('description') or '',
        ' '.join(topics)
    ]).lower()
    return topics, text


def classify_repo(repo):
    topics, text = repo_topics(repo)
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


repos = gh_json(f'https://api.github.com/users/{USER}/repos?per_page=100&sort=updated')
repos = [r for r in repos if not r.get('fork')]

newest = sorted(repos, key=lambda r: parse_dt(r['created_at']), reverse=True)[:6]
updated = sorted(repos, key=lambda r: parse_dt(r['pushed_at']), reverse=True)[:8]

buckets = {'platform': [], 'security': [], 'linux': []}
for repo in repos:
    category = classify_repo(repo)
    if category in buckets and len(buckets[category]) < 5:
        buckets[category].append(repo)

with open(TEMPLATE, 'r', encoding='utf-8') as f:
    readme = f.read()

newest_md = '\n'.join(fmt_repo(r) for r in newest) if newest else '- No public repositories found.'
updates_md = '\n'.join(fmt_repo(r, include_updated=True) for r in updated) if updated else '- No recent public repo updates found.'
platform_md = '\n'.join(fmt_repo(r) for r in buckets['platform']) if buckets['platform'] else '- Add topics like `platform`, `devops`, `sre`, `observability`, or `aws` to repos to surface them here.'
security_md = '\n'.join(fmt_repo(r) for r in buckets['security']) if buckets['security'] else '- Add topics like `security`, `cybersecurity`, `ctf`, `detection`, or `hardening` to repos to surface them here.'
linux_md = '\n'.join(fmt_repo(r) for r in buckets['linux']) if buckets['linux'] else '- Add topics like `linux`, `bash`, `automation`, `shell`, or `dotfiles` to repos to surface them here.'

readme = replace_section(readme, 'newest', newest_md)
readme = replace_section(readme, 'repo_updates', updates_md)
readme = replace_section(readme, 'platform', platform_md)
readme = replace_section(readme, 'security', security_md)
readme = replace_section(readme, 'linux', linux_md)

with open(OUTPUT, 'w', encoding='utf-8') as f:
    f.write(readme)
