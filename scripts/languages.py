"""Atualiza painel circular de linguagens usando bytes da API pública do GitHub."""
import collections
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
        page += 1
    if not totals:
        raise RuntimeError("Nenhuma linguagem encontrada; painel anterior preservado.")
    return totals, included

def render(totals, included):
    total_bytes = sum(totals.values())
    ranked = totals.most_common()
    top = ranked[:7]
    if len(ranked) > 7:
        top.append(("Outras", sum(v for _, v in ranked[7:])))
    palette = ["#79b99c", "#4d8c7a", "#a5cbb9", "#598eac", "#a5a3c9", "#bfaf83", "#668976", "#526b70"]
    cx, cy, radius = 172, 170, 91
    circumference = 2 * math.pi * radius
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="780" height="350" viewBox="0 0 780 350" role="img" aria-labelledby="title desc">',
        '<title id="title">Linguagens dos repositórios públicos de phzl0</title>',
        '<desc id="desc">Percentuais calculados a partir dos bytes de linguagens identificados pelo GitHub em todos os repositórios públicos não arquivados.</desc>',
        '<rect x="1" y="1" width="778" height="348" rx="13" fill="#0d1519" stroke="#355348"/>',
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
            f'<text x="{x+21}" y="{y}" font-size="14" fill="#d5e6de">{html.escape(lang)}</text>',
            f'<text x="{x+21}" y="{y+20}" font-size="18" font-weight="bold" fill="#aed7c2">{value/total_bytes*100:.1f}%</text>',
        ]
    today = dt.datetime.now(dt.timezone.utc).strftime("%d/%m/%Y")
    parts += [
        '<path d="M28 301 H752" stroke="#2d473d"/>',
        f'<text x="28" y="323" font-size="11" fill="#91a99f">Por bytes detectados pelo GitHub · Atualizado em {today} UTC</text>',
        '</g></svg>'
    ]
    return "\n".join(parts) + "\n"

def main():
    totals, included = collect()
    Path("assets/language-donut.svg").write_text(render(totals, included), encoding="utf-8")

if __name__ == "__main__":
    main()
