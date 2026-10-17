
import os
import re
import requests
from urllib.parse import quote

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

QUERIES = [
    '"ищем модель" Астана',
    '"ищем моделей" Астана',
    '"модель для съемки" Астана',
    '"ищем парня для съемки" Астана',
    '"мужская модель" Астана',
    '"ищем актера" Астана',
    '"UGC" Астана модель',
]

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    response = requests.post(
        url,
        json={"chat_id": CHAT_ID, "text": text, "disable_web_page_preview": True},
        timeout=20,
    )
    response.raise_for_status()

def main():
    results = []
    for query in QUERIES:
        url = "https://www.threads.com/search?q=" + quote(query)
        try:
            response = requests.get(
                url,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=20,
            )
            response.raise_for_status()
            html = response.text
            if "threads" not in html.lower():
                continue
            results.append(f"Запрос: {query}\nСтраница Threads доступна: {url}")
        except requests.RequestException as error:
            results.append(f"Не удалось выполнить запрос «{query}»: {error}")

    message = "🔎 Проверка поиска кастингов в Threads\n\n" + "\n\n".join(results)
    send_telegram(message)

if __name__ == "__main__":
    main()
