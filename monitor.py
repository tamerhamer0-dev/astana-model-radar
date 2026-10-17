
import os
import re
import json
import time
import html
import requests
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import quote

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

# Сколько часов может быть публикации, чтобы её отправить
MAX_AGE_HOURS = 24

# Сколько объявлений максимум отправлять за один запуск
MAX_SEND_PER_RUN = 15

SEEN_FILE = Path("seen.json")

QUERIES = [
    '"ищу модель" Астана',
    '"ищем модель" Астана',
    '"ищу моделей" Астана',
    '"ищем моделей" Астана',
    '"ищу парня" съемка',
    '"ищем парня" съемка',
    '"ищу мужчину" съемка',
    '"ищем мужчину" съемка',
    '"нужна модель" Астана',
    '"нужен парень" съемка',
    '"требуется модель" Астана',
    '"кастинг моделей" Астана',
    '"модель для съемки" Астана',
    '"модель для рекламы" Астана',
    '"мужская модель" Астана',
    '"ищу актера" Астана',
    '"ищем актера" Астана',
    '"ищу актёра" Астана',
    '"ищем актёра" Астана',
    '"ищем героя" съемка Астана',
    '"парень для рекламы" Астана',
    '"мужчина для рекламы" Астана',
    '"модель на проект" Астана',
    '"срочно нужна модель" Астана',
    '"срочно ищем" модель Астана',
    '"приглашаем моделей" Астана',
    '"UGC" модель Астана',
    '"контент съемка" модель Астана',
    '"ищу модель" Казахстан',
    '"ищем модель" Казахстан',
    '"ищу парня для съемки"',
    '"ищем парня для съемки"',
    '"ищу моделей для съемки"',
    '"ищем моделей для съемки"',
]

INTENT = re.compile(
    r"\b(ищу|ищем|ищется|нужен|нужна|нужно|нужны|"
    r"требуется|требуются|кастинг|кастинги|"
    r"приглашаем|набираем|срочно|ищется|ищутся)\b",
    re.IGNORECASE,
)

ROLE = re.compile(
    r"(модел|парня|парень|мужчин|акт[её]р|съ[её]мк|"
    r"реклам|ugc|контент|ролик|клип|бренд|"
    r"амбассадор|tfp|фотосесс|для видео)",
    re.IGNORECASE,
)

HEADERS = {
    "User-Agent": (
        "facebookexternalhit/1.1 "
        "(+http://www.facebook.com/externalhit_uatext.php)"
    ),
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
}


def load_seen():
    try:
        return set(json.loads(SEEN_FILE.read_text(encoding="utf-8")))
    except (FileNotFoundError, json.JSONDecodeError, TypeError):
        return set()


def save_seen(seen):
    # Ограничиваем размер истории
    SEEN_FILE.write_text(
        json.dumps(sorted(seen)[-10000:], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    response = requests.post(
        url,
        json={
            "chat_id": CHAT_ID,
            "text": message,
            "disable_web_page_preview": True,
        },
        timeout=25,
    )
    response.raise_for_status()


def caption_text(value):
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        text = value.get("text")
        if isinstance(text, str):
            return text
    return ""


def post_timestamp(post):
    value = post.get("taken_at")
    if value is None:
        value = post.get("taken_at_timestamp")
    try:
        value = float(value)
        if value > 10_000_000_000:
            value /= 1000
        return value
    except (TypeError, ValueError):
        return None


def walk_posts(value, found):
    if isinstance(value, dict):
        code = value.get("code")
        post_id = value.get("pk") or value.get("id")
        caption = caption_text(value.get("caption"))
        timestamp = post_timestamp(value)

        if (
            isinstance(code, str)
            and isinstance(post_id, (str, int))
            and caption
            and timestamp is not None
        ):
            user = value.get("user") or value.get("owner") or {}
            username = user.get("username") if isinstance(user, dict) else None

            if username:
                url = f"https://www.threads.com/@{username}/post/{code}"
            else:
                url = f"https://www.threads.com/t/{code}"

            found[str(post_id)] = {
                "id": str(post_id),
                "text": caption,
                "timestamp": timestamp,
                "url": url,
                "username": username or "неизвестен",
            }

        for child in value.values():
            walk_posts(child, found)

    elif isinstance(value, list):
        for child in value:
            walk_posts(child, found)


def fetch_posts(query):
    url = (
        "https://www.threads.com/search?q="
        + quote(query)
        + "&serp_type=recent"
    )

    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()

    found = {}
    scripts = re.findall(
        r"<script\b[^>]*>(.*?)</script\s*>",
        response.text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    for script in scripts:
        if not script.strip():
            continue
        try:
            data = json.loads(html.unescape(script))
        except (json.JSONDecodeError, TypeError):
            continue
        walk_posts(data, found)

    return list(found.values())


def is_relevant(text):
    return bool(INTENT.search(text) and ROLE.search(text))


def main():
    seen = load_seen()
    now = datetime.now(timezone.utc).timestamp()
    cutoff = now - MAX_AGE_HOURS * 3600
    posts = {}

    for query in QUERIES:
        try:
            for post in fetch_posts(query):
                posts[post["id"]] = post
            print(f"Search completed: {query}")
        except requests.RequestException as error:
            print(f"Search failed for {query}: {error}")
        time.sleep(2)

    fresh = []
    for post in posts.values():
        if post["id"] in seen:
            continue
        if post["timestamp"] < cutoff or post["timestamp"] > now + 300:
            continue
        if not is_relevant(post["text"]):
            continue
        fresh.append(post)

    fresh.sort(key=lambda post: post["timestamp"], reverse=True)

    sent = 0
    for post in fresh[:MAX_SEND_PER_RUN]:
        published = datetime.fromtimestamp(
            post["timestamp"], timezone.utc
        ).strftime("%d.%m.%Y %H:%M UTC")

        message = (
            "🎬 НОВЫЙ ВОЗМОЖНЫЙ КАСТИНГ\n\n"
            f"{post['text'][:2500]}\n\n"
            f"Автор: @{post['username']}\n"
            f"Опубликовано: {published}\n"
            f"Ссылка: {post['url']}"
        )

        try:
            send_telegram(message)
            seen.add(post["id"])
            sent += 1
            time.sleep(1)
        except requests.RequestException as error:
            print(f"Telegram send failed: {error}")

    save_seen(seen)
    print(
        f"Posts extracted: {len(posts)}; "
        f"new matching posts: {len(fresh)}; sent: {sent}"
    )

    if not posts:
        print(
            "No posts extracted. Threads may have changed its page format "
            "or limited the request."
        )


if __name__ == "__main__":
    main()
