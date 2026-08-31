import hashlib
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

import feedparser

QUERIES = [
    ("Ruta, salud y seguridad", "(camioneros OR transportistas) (salud OR sedentarismo OR estrés OR sobrepeso) Argentina when:90d"),
    ("Ruta, salud y seguridad", "(fatiga OR descanso OR alimentación) (camioneros OR conducción) Argentina when:90d"),
    ("Ruta, salud y seguridad", "(accidente camión OR paradores camioneros) Argentina when:45d"),
    ("Camiones y mercado", "(camiones patentamientos OR camiones ventas) Argentina ACARA when:60d"),
    ("Camiones y mercado", "(camiones chinos OR lanzamiento camiones) Argentina when:90d"),
    ("Camiones y mercado", "(crédito camiones OR financiación camiones) Argentina when:120d"),
    ("Logística y puertos", "(puertos OR terminales portuarias) Argentina cargas when:60d"),
    ("Logística y puertos", "(logística última milla OR Vaca Muerta transporte) Argentina when:60d"),
    ("Técnica y equipos", "(neumáticos camiones OR repuestos camiones) Argentina when:90d"),
    ("Técnica y equipos", "(remolques OR semirremolques OR tecnología transporte) Argentina when:90d"),
    ("Economía y costos", "(FADEEAC OR índice costos transporte) Argentina when:90d"),
    ("Economía y costos", "(combustible OR tarifas OR tasas) transporte cargas Argentina when:60d"),
    ("Región", "(transporte cargas OR logística) (Chile OR Brasil OR Uruguay OR Paraguay OR Bolivia OR Perú) when:45d"),
    ("Región", "(fronteras OR corredores OR puertos) Mercosur transporte when:45d"),
]
CATEGORIES = list(dict.fromkeys(category for category, _query in QUERIES))

BLOCKED_TERMS = ["europa", "europeo", "alemania", "francia", "reino unido", "españa", "italia"]
BLOCKED_SOURCES = ["www1.ru"]
REGIONAL_TERMS = [
    "argentina", "brasil", "chile", "uruguay", "paraguay", "bolivia", "perú", "peru",
    "colombia", "sudamérica", "sudamerica", "mercosur", "latinoamérica", "latinoamerica",
]
TRUSTED_SOURCE_TERMS = [
    "argentina.gob.ar", "boletín oficial", "boletin oficial", "fadeeac", "arlog",
    "infobae", "transportemundial", "supertruck", "diario río negro", "diario rio negro",
    "who.int", "msal.gob.ar", "vialidad nacional", "acara",
]
LEGACY_CATEGORY_MAP = {
    "Argentina": "Región",
    "Camiones": "Camiones y mercado",
    "Remolques": "Técnica y equipos",
    "Logística": "Logística y puertos",
    "Economía": "Economía y costos",
    "Rutas y normativa": "Ruta, salud y seguridad",
    "Región": "Región",
}
MAX_AGE_DAYS = 45
MAX_ITEMS_PER_CATEGORY = 14
MIN_SUCCESSFUL_QUERIES = 4
MIN_NEW_ITEMS = 8
MAX_ITEMS = 80
FETCH_RETRIES = 3
FETCH_TIMEOUT_SECONDS = 20
OUT = Path(__file__).resolve().parents[1] / "data" / "news.json"


def clean(text):
    text = html.unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize(text):
    text = clean(text).lower()
    text = re.sub(r"[^a-záéíóúüñ0-9 ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def clean_title(title, source):
    title, source = clean(title), clean(source)
    suffix = f" - {source}" if source else ""
    if suffix and title.lower().endswith(suffix.lower()):
        title = title[:-len(suffix)].strip()
    return title


def article_id(title, source):
    return hashlib.sha1(f"{normalize(title)}|{normalize(source)}".encode("utf-8")).hexdigest()[:14]


def published_datetime(entry):
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if not parsed:
        return None
    try:
        return datetime(*parsed[:6], tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def is_relevant(title, summary, source):
    haystack = f"{title} {summary}".lower()
    source_l = source.lower()
    if any(term in source_l for term in BLOCKED_SOURCES):
        return False
    if any(term in haystack for term in BLOCKED_TERMS) and not any(term in haystack for term in REGIONAL_TERMS):
        return False
    return (
        any(term in haystack for term in REGIONAL_TERMS)
        or "transporte" in haystack
        or "camion" in haystack
        or "camión" in haystack
        or "logística" in haystack
        or "logistica" in haystack
    )


def score(title, summary, source, published_at):
    haystack = f"{title} {summary}".lower()
    source_l = source.lower()
    points = 0
    if "argentina" in haystack:
        points += 20
    if any(term in haystack for term in REGIONAL_TERMS):
        points += 10
    if any(term in source_l for term in TRUSTED_SOURCE_TERMS):
        points += 15
    if any(term in haystack for term in ["camión", "camion", "cargas", "transportista", "semirremolque", "ruta", "bitren"]):
        points += 8
    if published_at:
        age_hours = max(0, (datetime.now(timezone.utc) - published_at).total_seconds() / 3600)
        points += max(0, 48 - min(age_hours / 6, 48))
    return round(points, 2)


def useful_summary(title, summary, category):
    summary = clean(summary)
    if not summary or normalize(summary) == normalize(title):
        return f"Información reciente de {category.lower()} seleccionada por el radar regional de Stylo Camión."
    return summary[:260]


def rss(query):
    q = urllib.parse.quote(query)
    return f"https://news.google.com/rss/search?q={q}&hl=es-419&gl=AR&ceid=AR:es-419"


def fetch_entries(query):
    last_error = None
    for attempt in range(1, FETCH_RETRIES + 1):
        try:
            request = urllib.request.Request(
                rss(query),
                headers={
                    "User-Agent": "StyloCamionNewsBot/1.0 (+https://noticias.stylocamion.com)",
                    "Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.8",
                },
            )
            with urllib.request.urlopen(request, timeout=FETCH_TIMEOUT_SECONDS) as response:
                payload = response.read()
            feed = feedparser.parse(payload)
            entries = list(feed.entries)
            if not entries:
                raise RuntimeError("fuente sin resultados")
            return entries
        except Exception as exc:
            last_error = exc
            if attempt < FETCH_RETRIES:
                time.sleep(attempt * 2)
    raise RuntimeError(str(last_error) if last_error else "error desconocido")


def valid_item(item):
    required = ("id", "title", "summary", "category", "source", "url", "published_at")
    return (
        isinstance(item, dict)
        and all(isinstance(item.get(key), str) and item.get(key) for key in required)
        and item["url"].startswith("https://")
        and parse_iso(item["published_at"]) is not None
    )


def parse_iso(value):
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def load_previous_items(cutoff):
    if not OUT.exists():
        return []
    try:
        payload = json.loads(OUT.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    accepted = []
    for item in payload.get("items", []):
        if not valid_item(item):
            continue
        published = parse_iso(item["published_at"])
        if published and published >= cutoff:
            accepted.append(item)
    return accepted


def headline_signature(title):
    stopwords = {
        "para", "como", "este", "esta", "desde", "sobre", "entre", "tras", "hacia",
        "todos", "todas", "nuevo", "nueva", "nuevos", "nuevas", "argentina",
        "camion", "camiones", "transporte", "cargas",
    }
    return {word for word in normalize(title).split() if len(word) > 3 and word not in stopwords}


def near_duplicate(title, accepted_titles):
    words = headline_signature(title)
    if len(words) < 3:
        return False
    for existing in accepted_titles:
        shared = len(words & existing)
        smaller = min(len(words), len(existing))
        if smaller >= 3 and shared >= 3 and shared / smaller >= 0.6:
            return True
    return False


def main():
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=MAX_AGE_DAYS)
    new_items = []
    successful_queries = 0
    failed_queries = []

    for category, query in QUERIES:
        try:
            entries = fetch_entries(query)
            successful_queries += 1
        except RuntimeError as exc:
            failed_queries.append({"category": category, "error": str(exc)[:180]})
            continue

        for entry in entries[:25]:
            source = clean((entry.get("source") or {}).get("title", "Fuente externa"))
            title = clean_title(entry.get("title", ""), source)
            summary = clean(entry.get("summary", ""))
            link = clean(entry.get("link", ""))
            published = published_datetime(entry)
            if not title or not link.startswith("https://") or not published:
                continue
            if published < cutoff or not is_relevant(title, summary, source):
                continue
            new_items.append({
                "id": article_id(title, source),
                "title": title,
                "summary": useful_summary(title, summary, category),
                "category": category,
                "source": source,
                "url": link,
                "published_at": published.isoformat(),
                "_score": score(title, summary, source, published),
            })

    if successful_queries < MIN_SUCCESSFUL_QUERIES or len(new_items) < MIN_NEW_ITEMS:
        print(
            f"Actualización rechazada: {successful_queries}/{len(QUERIES)} fuentes correctas, "
            f"{len(new_items)} noticias nuevas. Se conserva la última edición válida.",
            file=sys.stderr,
        )
        sys.exit(1)

    previous_items = load_previous_items(cutoff)
    for item in previous_items:
        item["category"] = LEGACY_CATEGORY_MAP.get(item["category"], item["category"])
    candidates = new_items + [{**item, "_score": 0} for item in previous_items]
    candidates.sort(
        key=lambda item: (
            parse_iso(item["published_at"]) or datetime.min.replace(tzinfo=timezone.utc),
            item.get("_score", 0),
        ),
        reverse=True,
    )

    accepted_by_category = {category: [] for category in CATEGORIES}
    accepted_ids = set()
    accepted_titles = []
    for item in candidates:
        bucket = accepted_by_category.get(item["category"])
        if bucket is None or len(bucket) >= MAX_ITEMS_PER_CATEGORY:
            continue
        if item["id"] in accepted_ids or near_duplicate(item["title"], accepted_titles):
            continue
        accepted_ids.add(item["id"])
        accepted_titles.append(headline_signature(item["title"]))
        item.pop("_score", None)
        bucket.append(item)

    accepted = []
    while any(accepted_by_category.values()) and len(accepted) < MAX_ITEMS:
        for category in CATEGORIES:
            if accepted_by_category[category]:
                accepted.append(accepted_by_category[category].pop(0))
            if len(accepted) >= MAX_ITEMS:
                break

    if len(accepted) < MIN_NEW_ITEMS:
        print("Actualización rechazada: el resultado validado es insuficiente.", file=sys.stderr)
        sys.exit(1)

    payload = {
        "updated_at": now.isoformat(),
        "items": accepted,
        "health": {
            "status": "ok",
            "successful_queries": successful_queries,
            "total_queries": len(QUERIES),
            "failed_queries": failed_queries,
            "new_candidates": len(new_items),
            "published_items": len(accepted),
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUT.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(OUT)
    print(
        f"Noticias guardadas: {len(accepted)} · fuentes correctas: "
        f"{successful_queries}/{len(QUERIES)}"
    )


if __name__ == "__main__":
    main()
