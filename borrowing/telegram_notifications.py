import os
import requests
from dotenv import load_dotenv


load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
API_URL = "https://api.telegram.org/bot"


def send_message(message):
    url = f"{API_URL}{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}

    response = requests.post(url, data=data)

    if response.status_code != 200:
        raise Exception(f"Error sending message: {response.text}")
