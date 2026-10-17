import os
import requests

token = os.environ["TELEGRAM_BOT_TOKEN"]
chat_id = os.environ["TELEGRAM_CHAT_ID"]

url = f"https://api.telegram.org/bot{token}/sendMessage"

response = requests.post(
    url,
    data={
        "chat_id": chat_id,
        "text": "✅ Astana Model Radar подключён! Тестовое сообщение получено."
    },
    timeout=20
)

print(response.status_code)
print(response.text)
response.raise_for_status()
