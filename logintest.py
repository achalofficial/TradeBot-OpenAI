import MetaTrader5 as mt5
import json

# Load accounts from JSON file
with open("accounts.json", "r") as f:
    accounts = json.load(f)

# Loop through each account in the dictionary
for name, account in accounts.items():
    if not account.get("ENABLE", False):
        continue  # Skip if ENABLE is false

    login = account["MT5_LOGIN"]
    password = account["MT5_PASSWORD"]
    server = account["MT5_SERVER"]

    if not mt5.initialize():
        print(f"❌ Failed to initialize MT5 for {name}: {mt5.last_error()}")
        continue

    authorized = mt5.login(login, password=password, server=server)
    if authorized:
        account_info = mt5.account_info()
        if account_info is not None:
            print(f"✅ {name} | Login: {login} | Balance: {account_info.balance}")
        else:
            print(f"❌ Failed to get account info for {name}: {mt5.last_error()}")
    else:
        print(f"❌ Login failed for {name}: {mt5.last_error()}")

    mt5.shutdown()
