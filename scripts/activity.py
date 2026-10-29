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
    xp = sum(min(n, 10) * 10 + (20 if n else 0) for n in counts.values())
    best = run = 0
    for date in sorted(counts):
        run = run + 1 if counts[date] else 0
        best = max(best, run)
    cursor = today if counts.get(today, 0) else today - dt.timedelta(days=1)
    streak = 0
    while counts.get(cursor, 0):
        streak += 1
        cursor -= dt.timedelta(days=1)
    week_start = today - dt.timedelta(days=today.weekday())
    week = sum(n > 0 for d, n in counts.items() if d >= week_start)
    return active, xp, best, streak, week


def render(calendar, today):
    days = [d for w in calendar['weeks'] for d in w['contributionDays'] if dt.date.fromisoformat(d['date']) <= today]
    active, xp, best, streak, week = metrics(days, today)
    level, progress = xp // 1000 + 1, xp % 1000
    rank = 'Explorador' if level < 5 else 'Construtor' if level < 10 else 'Arquiteto' if level < 20 else 'Mestre de guilda'
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="960" height="480" viewBox="0 0 960 480" role="img" aria-labelledby="title desc">',
             '<title id="title">Jornada de contribuições de phzl0</title>',
             '<desc id="desc">Calendário de contribuições visíveis, XP recreativo e missão semanal. Não mede horas trabalhadas.</desc>',
             '<defs><linearGradient id="bg" x2="1" y2="1"><stop stop-color="#101f25"/><stop offset="1" stop-color="#0b1118"/></linearGradient><linearGradient id="xp"><stop stop-color="#64cbb5"/><stop offset="1" stop-color="#8aafe8"/></linearGradient></defs>',
             '<rect width="959" height="479" x=".5" y=".5" rx="22" fill="url(#bg)" stroke="#293f46"/>',
             '<g font-family="system-ui,Segoe UI,sans-serif">']

    def text(x, y, value, size=14, color='#9db2bd', weight='400'):
        parts.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-weight="{weight}">{html.escape(str(value))}</text>')

    text(30, 35, 'DEV QUEST  /  ATIVIDADE NO GITHUB', 12, '#82c7b4', '700')
    text(30, 72, f'Nível {level:02d} · {rank}', 28, '#ecf4f5', '700')
    text(30, 99, 'Uma jornada construída dia após dia.', 14)
    text(665, 41, 'XP DOS ÚLTIMOS 12 MESES', 11)
    text(665, 73, f'{xp:,} XP'.replace(',', '.'), 25, '#b4dfcd', '700')
    parts.append('<rect x="665" y="88" width="265" height="7" rx="3" fill="#25343f"/>')
    parts.append(f'<rect x="665" y="88" width="{max(0, 265 * progress / 1000)}" height="7" rx="3" fill="url(#xp)"/>')
    text(665, 114, f'{progress} / 1.000 XP para o próximo nível', 11)
    values = [(str(active), 'DIAS ATIVOS'), (str(streak), 'SEQUÊNCIA ATUAL'), (str(best), 'MELHOR SEQUÊNCIA'), (str(sum(d['contributionCount'] for d in days)), 'CONTRIBUIÇÕES')]
    for i, (value, label) in enumerate(values):
        x = 30 + i * 231
        parts.append(f'<rect x="{x}" y="138" width="213" height="70" rx="12" fill="#13222c" stroke="#263b46"/>')
        text(x + 15, 166, value, 25, '#e5eff3', '650')
        text(x + 15, 190, label, 10)
    text(30, 239, 'MAPA DE CONTRIBUIÇÕES', 11, '#bed0d8', '700')
    colors = ['#1a2b35', '#25494c', '#35776b', '#56a48c', '#96d6b4']
    months = ['', 'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
    last_month = None
    for wi, w in enumerate(calendar['weeks']):
        for d in w['contributionDays']:
            date = dt.date.fromisoformat(d['date'])
            if date > today:
                continue
            x, y = 65 + wi * 16, 273 + ((date.weekday() + 1) % 7) * 16
            n = d['contributionCount']
            index = 0 if not n else 1 if n < 3 else 2 if n < 6 else 3 if n < 10 else 4
            if date.month != last_month and (date.day <= 7 or last_month is None):
                text(x, 261, months[date.month], 10)
                last_month = date.month
            parts.append(f'<rect x="{x}" y="{y}" width="12" height="12" rx="3" fill="{colors[index]}"><title>{date}: {n} contribuições</title></rect>')
    for y, label in [(300, 'Seg'), (332, 'Qua'), (364, 'Sex')]:
        text(30, y, label, 9)
    text(65, 403, f'MISSÃO DA SEMANA  ·  {min(week, 5)}/5 dias ativos', 12, '#b4dfcd', '650')
    for i in range(5):
        parts.append(f'<rect x="{420+i*28}" y="391" width="20" height="12" rx="4" fill="{colors[4] if i < week else colors[0]}"/>')
    text(600, 402, 'Menos', 10)
    for i, color in enumerate(colors):
        parts.append(f'<rect x="{641+i*17}" y="392" width="12" height="12" rx="3" fill="{color}"/>')
    text(735, 402, 'Mais', 10)
    text(30, 438, '10 XP/contribuição (até 10/dia) + 20 XP/dia ativo · 1.000 XP/nível · janela móvel de 12 meses', 11)
    text(30, 461, f'Dados visíveis na API do GitHub · não representa horas de trabalho · atualizado em {today:%d/%m/%Y} (UTC)', 10, '#728b99')
    parts.append('</g></svg>')
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
    Path('assets/activity-quest.svg').write_text(render(calendar, dt.datetime.now(dt.timezone.utc).date()), encoding='utf-8')


if __name__ == '__main__':
    main()
