import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
_auth_raw = os.getenv("AUTHORIZED_USER_IDS", "")
AUTHORIZED_USERS = [
    int(uid.strip())
    for uid in _auth_raw.split(",")
    if uid.strip().isdigit()
]
DEFAULT_CHAT_ID = os.getenv("DEFAULT_CHAT_ID", "")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
