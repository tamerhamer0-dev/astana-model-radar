
import os
import requests

def main():
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    response = requests.post(
        url,
        json={
            "chat_id": chat_id,
            "text": "Бро, бот успешно запустился!"
        },
        timeout=20,
    )
    response.raise_for_status()
    print("Telegram message sent successfully")

if __name__ == "__main__":
    main()
