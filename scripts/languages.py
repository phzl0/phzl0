"""Atualiza painel circular de linguagens usando bytes da API pública do GitHub."""
import collections
import base64
import re
import urllib.error
import datetime as dt
import html
import json
import math
import os
import urllib.request
from pathlib import Path

USER = "phzl0"
TOKEN = os.getenv("GH_TOKEN", "")
HEADERS = {"Accept": "application/vnd.github+json", "User-Agent": "phzl0-language-dashboard"}
if TOKEN:
    HEADERS["Authorization"] = "Bearer " + TOKEN

def get(path):
    req = urllib.request.Request("https://api.github.com" + path, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as res:
        return json.load(res)

def collect():
    totals = collections.Counter()
    included = 0
    projects = []
    page = 1
    while True:
        repos = get(f"/users/{USER}/repos?per_page=100&page={page}&type=owner")
        if not repos:
            break
        for repo in repos:
            if repo.get("private") or repo.get("archived"):
                continue
            languages = get(f"/repos/{USER}/{repo['name']}/languages")
            if languages:
                totals.update(languages)
                included += 1
            projects.append(repo)
        page += 1
    if not totals:
        raise RuntimeError("Nenhuma linguagem encontrada; painel anterior preservado.")
    return totals, included, projects

def source_file(repo, path):
    """Lê arquivos de dependências encontrados em qualquer subpasta."""
    import urllib.parse
    name = urllib.parse.quote(repo["name"], safe="")
    quoted = urllib.parse.quote(path, safe="/")
    try:
        item = get(f"/repos/{USER}/{name}/contents/{quoted}")
        if isinstance(item, dict) and item.get("type") == "file" and item.get("encoding") == "base64":
            return base64.b64decode(item.get("content", "")).decode("utf-8", "replace")[:200000]
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise
    return ""


def detect(projects):
    """Varre toda a árvore Git da branch principal e conta presença por repositório."""
    names = ["React", "Node.js", "Spring Boot", "FastAPI", "Docker", "n8n"]
    counts = collections.Counter()
    inspected = 0
    skipped = 0
    for repo in projects:
        branch = repo.get("default_branch")
        if not branch:
            continue
        import urllib.parse
        slug = urllib.parse.quote(repo["name"], safe="")
        ref = urllib.parse.quote(branch, safe="")
        tree = get(f"/repos/{USER}/{slug}/git/trees/{ref}?recursive=1")
        if tree.get("truncated"):
            skipped += 1
            continue
        entries = [entry["path"] for entry in tree.get("tree", [])
                   if entry.get("type") == "blob"]
        inspected += 1
        candidates = []
        for path in entries:
            base = path.rsplit("/", 1)[-1].lower()
            if base in ("package.json", "pom.xml", "build.gradle", "build.gradle.kts",
                        "requirements.txt", "pyproject.toml", "pipfile",
                        "dockerfile", "compose.yaml", "compose.yml",
                        "docker-compose.yml", "docker-compose.yaml") or base.endswith(".dockerfile"):
                # Não varrer dependências empacotadas de terceiros.
                if not any(p in path.lower().split("/") for p in
                           ("node_modules", ".venv", "venv", "vendor", "dist", "build", ".git")):
                    candidates.append(path)
        found = set()
        for path in candidates:
            base = path.rsplit("/", 1)[-1].lower()
            if base == "dockerfile" or base.endswith(".dockerfile") or base in (
                "docker-compose.yml", "docker-compose.yaml", "compose.yaml", "compose.yml"):
                found.add("Docker")
                continue
            text = source_file(repo, path)
            if base == "package.json":
                if re.search(r'"react"\s*:', text):
                    found.add("React")
                if re.search(r'"(@types/node|express|fastify|koa|@nestjs/core)"\s*:', text):
                    found.add("Node.js")
                if re.search(r'"n8n"\s*:|"n8n-nodes-[^"]+"\s*:', text):
                    found.add("n8n")
            if base in ("pom.xml", "build.gradle", "build.gradle.kts") and "spring-boot" in text:
                found.add("Spring Boot")
            if base in ("requirements.txt", "pyproject.toml", "pipfile"):
                if re.search(r'(?im)(^|["\\s])fastapi(?:\\[[^]]*\\])?\\s*(?:[=<>!~"]|$)', text):
                    found.add("FastAPI")
        for name in found:
            counts[name] += 1
    return [(name, counts[name]) for name in names if counts[name]], inspected, skipped


def render(totals, included, technologies, inspected, skipped):
    total_bytes = sum(totals.values())
    ranked = totals.most_common()
    top = ranked[:7]
    if len(ranked) > 7:
        top.append(("Outras", sum(v for _, v in ranked[7:])))
    palette = ["#79b99c", "#4d8c7a", "#a5cbb9", "#598eac", "#a5a3c9", "#bfaf83", "#668976", "#526b70"]
    cx, cy, radius = 172, 170, 91
    circumference = 2 * math.pi * radius
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="780" height="445" viewBox="0 0 780 445" role="img" aria-labelledby="title desc">',
        '<title id="title">Linguagens dos repositórios públicos de phzl0</title>',
        '<desc id="desc">Percentuais calculados a partir dos bytes de linguagens identificados pelo GitHub em todos os repositórios públicos não arquivados.</desc>',
        '<rect x="1" y="1" width="778" height="443" rx="13" fill="#0d1519" stroke="#355348"/>',
        '<g font-family="Arial,Helvetica,sans-serif">',
        '<text x="28" y="35" font-size="12" letter-spacing="2" fill="#83b49f">LANGUAGE ANALYTICS</text>',
        '<text x="28" y="63" font-size="22" font-weight="bold" fill="#e5eee9">Linguagens utilizadas</text>',
        f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="none" stroke="#20342e" stroke-width="27"/>']
    offset = 0.0
    for index, (lang, value) in enumerate(top):
        length = value / total_bytes * circumference
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="none" stroke="{palette[index]}" stroke-width="27" stroke-dasharray="{length:.3f} {circumference - length:.3f}" stroke-dashoffset="{-offset:.3f}" transform="rotate(-90 {cx} {cy})"><title>{html.escape(lang)}: {value/total_bytes*100:.1f}%</title></circle>')
        offset += length
    parts += [
        f'<text x="{cx}" y="{cy - 3}" text-anchor="middle" font-size="23" font-weight="bold" fill="#e9f2ed">100%</text>',
        f'<text x="{cx}" y="{cy + 19}" text-anchor="middle" font-size="12" fill="#9bb6a8">{included} repositórios</text>',
    ]
    for i, (lang, value) in enumerate(top):
        x = 355 + (i // 4) * 209
        y = 112 + (i % 4) * 48
        parts += [
            f'<rect x="{x}" y="{y-10}" width="12" height="12" rx="3" fill="{palette[i]}"/>',
            f'<text x="{x+21}" y="{y}" font-size="12" fill="#d5e6de">{html.escape(lang)}</text>',
            f'<text x="{x+21}" y="{y+20}" font-size="15" font-weight="bold" fill="#aed7c2">{value/total_bytes*100:.1f}%</text>',
        ]
    parts += [
        '<path d="M28 291 H752" stroke="#2d473d"/>',
        '<text x="28" y="315" font-size="13" fill="#dce9e2" font-weight="bold">Frameworks e ferramentas identificados</text>',
        f'<text x="28" y="333" font-size="10" fill="#92a99e">Tecnologias identificadas em {inspected} repositórios; {skipped} árvores grandes não analisadas</text>',
    ]
    if technologies:
        for i, (name, count) in enumerate(technologies[:8]):
            col = i % 4
            row = i // 4
            x, y = 28 + col * 185, 347 + row * 37
            label = html.escape(name)
            parts.append(f'<rect x="{x}" y="{y}" width="173" height="29" rx="6" fill="#182a25" stroke="#345748"/>')
            parts.append(f'<text x="{x + 10}" y="{y + 19}" font-size="12" fill="#d6e7df">{label}</text>')
            parts.append(f'<text x="{x + 162}" y="{y + 19}" text-anchor="end" font-size="11" font-weight="bold" fill="#90c8aa">{count} proj.</text>')
    else:
        parts.append('<text x="28" y="365" font-size="12" fill="#9fb5a9">Nenhuma dependência reconhecida nos arquivos verificados</text>')
    today = dt.datetime.now(dt.timezone.utc).strftime("%d/%m/%Y")
    parts += [
        '<path d="M28 418 H752" stroke="#2d473d"/>',
        f'<text x="28" y="436" font-size="11" fill="#91a99f">Por bytes detectados pelo GitHub · Atualizado em {today} UTC</text>',
        '</g></svg>'
    ]
    return "\n".join(parts) + "\n"

def main():
    totals, included, projects = collect()
    technologies, inspected, skipped = detect(projects)
    Path("assets/language-donut.svg").write_text(render(totals, included, technologies, inspected, skipped), encoding="utf-8")

if __name__ == "__main__":
    main()
