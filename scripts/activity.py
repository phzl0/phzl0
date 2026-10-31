"""Render a public contribution calendar; no private credentials or dependencies."""
import datetime as dt
import html
import json
import os
from pathlib import Path
import urllib.request


def metrics(days, today):
    counts = {dt.date.fromisoformat(d['date']): d['contributionCount'] for d in days}
    active = sum(n > 0 for n in counts.values())
    best = run = 0
    for date in sorted(counts):
        run = run + 1 if counts[date] else 0
        best = max(best, run)
    cursor = today if counts.get(today, 0) else today - dt.timedelta(days=1)
    streak = 0
    while counts.get(cursor, 0):
        streak += 1
        cursor -= dt.timedelta(days=1)
    return active, best, streak


def render(calendar, today):
    days = [d for w in calendar['weeks'] for d in w['contributionDays']
            if dt.date.fromisoformat(d['date']) <= today]
    active, best, streak = metrics(days, today)
    recent = days[-84:]
    weekly = [sum(d['contributionCount'] for d in recent[i:i + 7])
              for i in range(0, 84, 7)]
    weekly = ([0] * max(0, 12 - len(weekly)) + weekly)[-12:]
    peak = max(1, *weekly)
    total = sum(d['contributionCount'] for d in days)
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="760" height="290" viewBox="0 0 760 290" role="img" aria-labelledby="t d">',
        '<title id="t">Dashboard de contribuições de phzl0</title>',
        '<desc id="d">Contribuições públicas visíveis no GitHub; atualização diária.</desc>',
        '<rect x="1" y="1" width="758" height="288" rx="14" fill="#0d1518" stroke="#365349"/>',
        '<g font-family="Arial,Helvetica,sans-serif">',
        '<text x="29" y="31" font-size="12" fill="#87b69f" letter-spacing="2">GITHUB / CONTRIBUTIONS</text>',
        '<text x="29" y="57" font-size="21" font-weight="bold" fill="#e2ece7">Dashboard de contribuições</text>',
    ]
    stats = [('CONTRIBUIÇÕES', total), ('DIAS ATIVOS', active),
             ('SEQUÊNCIA ATUAL', streak), ('MELHOR SEQUÊNCIA', best)]
    for i, (label, value) in enumerate(stats):
        x = 29 + i * 181
        parts.append(f'<rect x="{x}" y="73" width="170" height="66" rx="8" fill="#162421" stroke="#29473b"/>')
        parts.append(f'<text x="{x + 14}" y="102" font-size="23" font-weight="bold" fill="#e4f0e9">{value}</text>')
        parts.append(f'<text x="{x + 14}" y="123" font-size="10" fill="#91b29f">{label}</text>')
    parts.append('<text x="29" y="166" font-size="12" fill="#b5d1c2">Contribuições por semana · últimas 12 semanas</text>')
    for i, number in enumerate(weekly):
        height = max(5 if number else 2, round(number / peak * 70))
        color = '#579c7a' if number else '#263b37'
        parts.append(f'<rect x="{44 + i * 47}" y="{228 - height}" width="24" height="{height}" rx="4" fill="{color}"><title>Semana {i + 1}: {number} contribuições</title></rect>')
    parts += [
        '<path d="M29 230H731" stroke="#385249"/>',
        f'<text x="29" y="263" font-size="11" fill="#819a90">Atualizado em {today:%d/%m/%Y} · dados públicos visíveis</text>',
        '<text x="728" y="263" font-size="11" text-anchor="end" fill="#819a90">GitHub Actions</text>',
        '</g></svg>',
    ]
    return '\n'.join(parts) + '\n'


def main():
    query = 'query($login:String!){user(login:$login){contributionsCollection{contributionCalendar{weeks{contributionDays{date contributionCount}}}}}}'
    request = urllib.request.Request('https://api.github.com/graphql', data=json.dumps({'query': query, 'variables': {'login': 'phzl0'}}).encode(), headers={'Authorization': 'Bearer ' + os.environ['GH_TOKEN'], 'Content-Type': 'application/json', 'User-Agent': 'phzl0-activity-panel'})
    with urllib.request.urlopen(request, timeout=45) as response:
        data = json.load(response)
    if data.get('errors') or not data.get('data', {}).get('user'):
        raise RuntimeError('Não foi possível consultar o calendário; painel anterior preservado.')
    calendar = data['data']['user']['contributionsCollection']['contributionCalendar']
    if not calendar['weeks']:
        raise RuntimeError('Calendário vazio; painel anterior preservado.')
    Path('assets/contributions-dashboard.svg').write_text(render(calendar, dt.datetime.now(dt.timezone.utc).date()), encoding='utf-8')


if __name__ == '__main__':
    main()
