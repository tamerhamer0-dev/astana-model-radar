import os import re import json import time from pathlib import Path from urllib.parse import quote
import requests
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"] CHAT_ID = os.environ["TELEGRAM_CHAT_ID"] STATE = Path("seen.json")
QUERIES = [ "ищу модель Астана", "кастинг Астана", "модель на съемку Астана", "ищу парня для съемки Астана", "мужская модель Астана", "UGC Астана", "съемка рекламы Астана", "модель Казахстан Астана", "ищу модель Астана",
    "ищем модель Астана",
    "ищем моделей Астана",
    "ищем парня для съемки Астана",
    "ищем парней для съемки Астана",
    "ищем мужчину для съемки Астана",
    "ищем мужчин для съемки Астана",
    "ищем моделей на съемку Астана",
    "ищем мужскую модель Астана",
    "ищем актера Астана",
    "ищем актёра Астана",
    "нужна модель Астана",
    "нужны модели Астана",
    "нужен парень для съемки Астана",
    "нужны парни для съемки Астана",
    "требуется модель Астана",
    "требуются модели Астана",
    "кастинг Астана",
    "модель на съемку Астана",
    "мужская модель Астана",
    "UGC Астана",
    "съемка рекламы Астана",
    "ищем лицо бренда Астана",
    "ищем героя для рекламы Астана",
]
UA = "facebookexternalhit/1.1" SCRIPT_RE = re.compile( r'<script[^>]type="application/json"[^>]>(.*?)</script>', re.S, ) RELEVANT = re.compile( r"модел|кастинг|съ[её]мк|ugc|реклам|" r"ищу парня|ищу мужчину|акт[её]р|бренд", re.I, )
def walk(node, posts, depth=0): if depth > 30: return if isinstance(node, list): for item in node: walk(item, posts, depth + 1) elif isinstance(node, dict): if ( isinstance(node.get("code"), str) and isinstance(node.get("pk"), str) and "caption" in node and ("taken_at" in node or "like_count" in node) ): posts[node["code"]] = node for value in node.values(): walk(value, posts, depth + 1)
def search(query): found = {} for view in ("recent", "default"): url = ( "https://www.threads.com/search?q=" + quote(query) + "&serp_type=" + view ) try: response = requests.get( url, headers={ "User-Agent": UA, "Accept-Language": "ru-RU,ru;q=0.9", }, timeout=25, ) response.raise_for_status() for block in SCRIPT_RE.findall(response.text): try: walk(json.loads(block), found) except (ValueError, TypeError): pass except requests.RequestException as error: print("Search error:", query, error) time.sleep(2) print(f"{query}: найдено {len(found)}") return found
def send_message(text): response = requests.post( f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={ "chat_id": CHAT_ID, "text": text, "disable_web_page_preview": True, }, timeout=20, ) response.raise_for_status()
def main(): seen = set(json.loads(STATE.read_text())) if STATE.exists() else set() candidates = {} irrelevant = set()
for query in QUERIES:
    for code, post in search(query).items():
        if code in seen:
            continue

        caption = post.get("caption") or {}
        caption_text = (
            caption.get("text", "")
            if isinstance(caption, dict) else ""
        )
        if not RELEVANT.search(caption_text):
            irrelevant.add(code)
            continue

        user = post.get("user") or {}
        username = user.get("username", "")
        link = f"https://www.threads.com/@{username}/post/{code}"

        candidates[code] = (
            "🎬 Возможный кастинг — Астана\n\n"
            + caption_text[:2500]
            + f"\n\nАвтор: @{username}\n{link}\nЗапрос: {query}"
        )

# Limit notifications per run; remaining candidates
# will be checked again on the next run.
sent = set()
for code, message in list(candidates.items())[:10]:
    send_message(message)
    sent.add(code)
    print("Sent:", code)

seen.update(irrelevant)
seen.update(sent)
STATE.write_text(json.dumps(sorted(seen)[-5000:]))
if name == "main": main()
