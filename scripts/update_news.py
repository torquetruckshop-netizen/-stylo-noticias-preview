import hashlib
import html
import json
import re
import urllib.parse
from datetime import datetime, timezone, timedelta
from pathlib import Path

import feedparser

QUERIES = [
    ("Argentina", 'transporte cargas camiones Argentina when:30d'),
    ("Camiones", 'camiones pesados Argentina OR Brasil OR Chile OR Uruguay OR Paraguay when:30d'),
    ("Remolques", 'remolques semirremolques Argentina OR Brasil OR Uruguay when:45d'),
    ("Logística", 'logística transporte cargas Argentina Sudamérica when:30d'),
    ("Economía", 'transporte cargas combustible tarifas crédito tasas Argentina when:30d'),
    ("Rutas y normativa", 'rutas transporte cargas normativa Argentina bitrenes pesos dimensiones when:45d'),
    ("Región", 'transporte cargas Sudamérica fronteras puertos corredores Mercosur when:30d'),
]

BLOCKED_TERMS = ['europa','europeo','alemania','francia','reino unido','españa','italia']
BLOCKED_SOURCES = ['www1.ru']
REGIONAL_TERMS = ['argentina','brasil','chile','uruguay','paraguay','bolivia','perú','peru','colombia','sudamérica','sudamerica','mercosur','latinoamérica','latinoamerica']
TRUSTED_SOURCE_TERMS = ['argentina.gob.ar','boletín oficial','boletin oficial','fadeeac','arlog','infobae','transportemundial']
MAX_AGE_DAYS = 60
OUT = Path(__file__).resolve().parents[1] / 'data' / 'news.json'


def clean(text):
    text = html.unescape(text or '')
    text = re.sub(r'<[^>]+>', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def normalize(text):
    text = clean(text).lower()
    text = re.sub(r'[^a-záéíóúüñ0-9 ]+', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def clean_title(title, source):
    title, source = clean(title), clean(source)
    suffix = f' - {source}' if source else ''
    if suffix and title.lower().endswith(suffix.lower()):
        title = title[:-len(suffix)].strip()
    return title


def article_id(title, source):
    return hashlib.sha1(f'{normalize(title)}|{normalize(source)}'.encode('utf-8')).hexdigest()[:14]


def published_datetime(entry):
    parsed = entry.get('published_parsed') or entry.get('updated_parsed')
    if not parsed:
        return None
    try:
        return datetime(*parsed[:6], tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def is_relevant(title, summary, source):
    haystack = f'{title} {summary}'.lower()
    source_l = source.lower()
    if any(term in source_l for term in BLOCKED_SOURCES):
        return False
    if any(term in haystack for term in BLOCKED_TERMS) and not any(term in haystack for term in REGIONAL_TERMS):
        return False
    return any(term in haystack for term in REGIONAL_TERMS) or 'transporte' in haystack or 'camion' in haystack or 'logística' in haystack or 'logistica' in haystack


def score(title, summary, source, published_at):
    haystack = f'{title} {summary}'.lower()
    source_l = source.lower()
    points = 0
    if 'argentina' in haystack: points += 20
    if any(term in haystack for term in REGIONAL_TERMS): points += 10
    if any(term in source_l for term in TRUSTED_SOURCE_TERMS): points += 15
    if any(term in haystack for term in ['camión','camion','cargas','transportista','semirremolque','ruta','bitren']): points += 8
    if published_at:
        age_hours = max(0, (datetime.now(timezone.utc) - published_at).total_seconds() / 3600)
        points += max(0, 80 - min(age_hours / 8, 80))
    return round(points, 2)


def useful_summary(title, summary, category):
    summary = clean(summary)
    if not summary or normalize(summary) == normalize(title):
        return f'Información reciente de {category.lower()} seleccionada por el radar regional de Stylo Camión.'
    return summary[:260]


def rss(query):
    q = urllib.parse.quote(query)
    return f'https://news.google.com/rss/search?q={q}&hl=es-419&gl=AR&ceid=AR:es-419'


def main():
    items, seen = [], set()
    cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)
    for category, query in QUERIES:
        feed = feedparser.parse(rss(query))
        for entry in feed.entries[:20]:
            source = clean((entry.get('source') or {}).get('title', 'Fuente externa'))
            title = clean_title(entry.get('title', ''), source)
            summary = clean(entry.get('summary', ''))
            link = entry.get('link', '')
            published = published_datetime(entry)
            key = normalize(title)
            if not title or not link or not key or key in seen: continue
            if published and published < cutoff: continue
            if not is_relevant(title, summary, source): continue
            seen.add(key)
            items.append({
                'id': article_id(title, source),
                'title': title,
                'summary': useful_summary(title, summary, category),
                'category': category,
                'source': source,
                'url': link,
                'published_at': published.isoformat() if published else None,
                '_score': score(title, summary, source, published),
            })
    items.sort(key=lambda x: (x['_score'], x.get('published_at') or ''), reverse=True)
    for item in items: item.pop('_score', None)
    payload = {'updated_at': datetime.now(timezone.utc).isoformat(), 'items': items[:60]}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Noticias guardadas: {len(payload["items"])}')


if __name__ == '__main__':
    main()
