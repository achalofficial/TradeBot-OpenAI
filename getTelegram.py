from telethon.sync import TelegramClient
from dotenv import load_dotenv
import os

load_dotenv()

TELEGRAM_API_ID = int(os.getenv("TELEGRAM_API_ID"))
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH")
TELEGRAM_PHONE = os.getenv("TELEGRAM_PHONE")

client = TelegramClient('session', TELEGRAM_API_ID, TELEGRAM_API_HASH)
client.start(phone=TELEGRAM_PHONE)

print("📋 Listing your Telegram chats...\n")
print(client)

for dialog in client.iter_dialogs():
    entity = dialog.entity
    print(entity)
    name = entity.title if hasattr(entity, 'title') else entity.first_name
    username = getattr(entity, 'username', None)
    chat_id = entity.id

    chat_type = type(entity).__name__

    print(f"🔹 Name: {name}")
    print(f"   ID: {chat_id}")
    print(f"   Username: {username}")
    print(f"   Type: {chat_type}")
    print("-" * 40)

client.disconnect()
