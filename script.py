from telethon.sync import TelegramClient
from dotenv import load_dotenv
import os
import time
import threading
import json
import MetaTrader5 as mt5
import openai
import base64
import re

# Load environment variables
load_dotenv()

TELEGRAM_API_ID = int(os.getenv("TELEGRAM_API_ID"))
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH")
TELEGRAM_PHONE = os.getenv("TELEGRAM_PHONE")
TARGET_GROUP_ID = int(os.getenv("TARGET_GROUP_ID"))

# Initialize Telegram client
client = TelegramClient('session', TELEGRAM_API_ID, TELEGRAM_API_HASH)
client.start(phone=TELEGRAM_PHONE)

print("✅ Listening for new messages... (type commands anytime)")

last_msg_id = None
command_queue = []

# Show Account Details
def accountdetails():
    print("📄 Fetching account details from MT5 servers...\n")

    try:
        with open('accounts.json', 'r') as f:
            accounts = json.load(f)
    except FileNotFoundError:
        print("❌ accounts.json file not found.")
        return
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON: {e}")
        return

    for account_name, acc in accounts.items():
        if not acc.get("ENABLE", False):
            print(f"⚠️ Skipping disabled account: {account_name}")
            continue

        login = acc.get("MT5_LOGIN")
        password = acc.get("MT5_PASSWORD")
        server = acc.get("MT5_SERVER")

        print(f"🔹 Logging into: {account_name} ({login}@{server})")

        if not mt5.initialize(login=login, password=password, server=server):
            print(f"❌ Failed to connect to {account_name}: {mt5.last_error()}")
            print("-" * 60)
            mt5.shutdown()
            continue

        account_info = mt5.account_info()
        if account_info is None:
            print(f"❌ Failed to fetch account info for {account_name}")
        else:
            print(f"✅ Connected. Account Info:")
            print(f"   Balance : {account_info.balance}")
            print(f"   Equity  : {account_info.equity}")
            print(f"   Margin  : {account_info.margin}")
        
        print("-" * 60)
        mt5.shutdown()

# Test Trade 
def testTrade(symbol="XAUUSDm", lot=0.01):
    print("🧪 Starting test trade...")

    try:
        with open('accounts.json', 'r') as f:
            accounts = json.load(f)
    except FileNotFoundError:
        print("❌ accounts.json file not found.")
        return
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON: {e}")
        return

    for account_name, acc in accounts.items():
        if not acc.get("ENABLE", False):
            print(f"⚠️ Skipping disabled account: {account_name}")
            continue

        login = acc.get("MT5_LOGIN")
        password = acc.get("MT5_PASSWORD")
        server = acc.get("MT5_SERVER")

        print(f"🔹 Logging into: {account_name} ({login}@{server})")

        if not mt5.initialize(login=login, password=password, server=server):
            print(f"❌ Failed to initialize MT5: {mt5.last_error()}")
            continue

        if not mt5.symbol_select(symbol, True):
            print(f"❌ Failed to select symbol {symbol}")
            mt5.shutdown()
            continue

        price = mt5.symbol_info_tick(symbol).ask
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot,
            "type": mt5.ORDER_TYPE_BUY,
            "price": price,
            "deviation": 10,
            "magic": 123456,
            "comment": "Test Buy Trade",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC
        }

        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"❌ Trade failed: {result.retcode} - {result.comment}")
            mt5.shutdown()
            continue

        print(f"✅ Buy Order placed successfully. Ticket: {result.order}")

        time.sleep(2)  # Short wait before closing

        position = mt5.positions_get(ticket=result.order)
        if position:
            close_price = mt5.symbol_info_tick(symbol).bid
            close_request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": lot,
                "type": mt5.ORDER_TYPE_SELL,
                "position": result.order,
                "price": close_price,
                "deviation": 10,
                "magic": 123456,
                "comment": "Test Close Trade",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC
            }

            close_result = mt5.order_send(close_request)
            if close_result.retcode == mt5.TRADE_RETCODE_DONE:
                print(f"✅ Position closed successfully. Ticket: {close_result.order}")
            else:
                print(f"❌ Failed to close position: {close_result.retcode} - {close_result.comment}")
        else:
            print("⚠️ No position found to close.")

        print("-" * 60)
        mt5.shutdown()

# Status
def status():
    print("📊 Fetching account status...\n")

    try:
        with open('accounts.json', 'r') as f:
            accounts = json.load(f)
    except FileNotFoundError:
        print("❌ accounts.json file not found.")
        return
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON: {e}")
        return

    for account_name, acc in accounts.items():
        if not acc.get("ENABLE", False):
            print(f"⚠️ Skipping disabled account: {account_name}")
            continue

        login = acc.get("MT5_LOGIN")
        password = acc.get("MT5_PASSWORD")
        server = acc.get("MT5_SERVER")

        print(f"🔹 Logging into: {account_name} ({login}@{server})")

        if not mt5.initialize(login=login, password=password, server=server):
            print(f"❌ MT5 init failed: {mt5.last_error()}")
            continue

        account_info = mt5.account_info()
        if not account_info:
            print(f"❌ Failed to get account info: {mt5.last_error()}")
            mt5.shutdown()
            continue

        # ✅ Account Summary
        print("🧾 Account Summary:")
        print(f"   Balance      : {account_info.balance}")
        print(f"   Equity       : {account_info.equity}")
        print(f"   PnL          : {account_info.profit}")
        print(f"   Margin       : {account_info.margin}")
        print(f"   Free Margin  : {account_info.margin_free}")

        positions = mt5.positions_get()
        if positions is None:
            print("❌ Could not fetch open trades.")
        elif len(positions) == 0:
            print("📭 No open trades.\n" + "-"*50)
        else:
            print(f"   Total Trades : {len(positions)}\n")

            print("📄 Trades:")
            for idx, pos in enumerate(positions, 1):
                order_type = "Buy" if pos.type == mt5.ORDER_TYPE_BUY else "Sell"
                print(f"Trade {idx}: {pos.symbol} ({order_type})")
                print(f"   Entry Price : {pos.price_open}")
                print(f"   Volume      : {pos.volume}")
                print(f"   Running PnL : {pos.profit}\n")

        print("-" * 60)
        mt5.shutdown()


# Command listener in background
def listen_for_input():
    while True:
        cmd = input(">> ").strip()
        command_queue.append(cmd)

# Start input thread
threading.Thread(target=listen_for_input, daemon=True).start()

# OpenAI API Function
def send_image_to_openai(image_path):
    print(f"📤 Sending {image_path} to OpenAI...")

    with open(image_path, "rb") as f:
        encoded_image = base64.b64encode(f.read()).decode("utf-8")

    try:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are a trading assistant. Extract trade data as JSON."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{encoded_image}"
                            }
                        },
                        {
                            "type": "text",
                            "text": (
                                "Strict Mode only Extract the trade signal. Return JSON only No extra text: "
                                "{\"symbol\":\"XAUUSD\",\"action\":\"buy\",\"entry\":2345.67,\"sl\":2300,\"tp\":2400,\"ID\":#334234342}"
                            )
                        }
                    ]
                }
            ],
            max_tokens=500
        )
        content = response.choices[0].message.content
        print("✅ OpenAI Response:")
        cleaned = re.sub(r"```(?:json)?", "", content).strip("` \n")
        print(cleaned)
        openai_response = json.loads(cleaned)
        tradeplace(openai_response)
    except Exception as e:
        print("❌ OpenAI error:", e)

import MetaTrader5 as mt5

# Example `openai_response`
openai_response = {
    "symbol": "BTCUSD",
    "action": "buy",
    "entry": 108814.32,
    "sl": 108096.44,
    "tp": 109741.50,
    "ID": "#2157894451"
}

# Dummy functions for now
def updatetrade(position, openai_response):
    print(f"Updating trade {position.ticket} with new data: {openai_response}")

def newtrade(openai_response):
    print(f"Placing new trade with data: {openai_response}")

def tradeplace(openai_response):
    target_id = openai_response.get("ID")
    if not target_id:
        print("No ID in response.")
        return

    # Initialize MT5 connection
    if not mt5.initialize():
        print("MT5 initialization failed")
        return

    # Get all open positions
    positions = mt5.positions_get()

    found = False

    if positions:
        for pos in positions:
            if pos.comment == target_id:
                # ID matches, update the trade
                updatetrade(pos, openai_response)
                found = True
                break

    if not found:
        # No existing trade with this ID, open new trade
        newtrade(openai_response)

    mt5.shutdown()

# Call it
tradeplace(openai_response)




# Main polling loop
try:
    while True:
        # Poll Telegram for new messages
        messages = client.get_messages(TARGET_GROUP_ID, limit=1)
        if messages:
            msg = messages[0]
            if msg.id != last_msg_id:
                print(f"🆕 {msg.date} - {msg.sender_id}: {msg.text}")
                last_msg_id = msg.id
                if msg.photo:
                    file_path = client.download_media(msg, file=f"photo_{msg.id}.jpg")
                    # print(f"✅ Photo saved: {file_path}")
                    send_image_to_openai(file_path)

        # Handle user commands
        while command_queue:
            cmd = command_queue.pop(0)
            if cmd == "test":
                print("✅ You ran the 'test' command.")
            elif cmd == "account-details":
                accountdetails()
            elif cmd == "test-trade":
                testTrade()
            elif cmd == "status":
                status()
            elif cmd == "exit":
                print("👋 Exiting...")
                raise KeyboardInterrupt
            else:
                print(f"⚠️ Unknown command: {cmd}")

        time.sleep(2)

except KeyboardInterrupt:
    print("🛑 Script stopped by user.")
finally:
    client.disconnect()
