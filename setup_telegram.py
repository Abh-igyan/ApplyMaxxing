import os
import requests
import re
from dotenv import load_dotenv

ENV_FILE = '.env'

def update_env_variable(key, value):
    if not os.path.exists(ENV_FILE):
        with open(ENV_FILE, 'w') as f:
            f.write(f'{key}="{value}"\n')
        return

    with open(ENV_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    pattern = rf'^{key}=.*$'
    if re.search(pattern, content, flags=re.MULTILINE):
        new_content = re.sub(pattern, f'{key}="{value}"', content, flags=re.MULTILINE)
    else:
        new_content = content.rstrip() + f'\n{key}="{value}"\n'

    with open(ENV_FILE, 'w', encoding='utf-8') as f:
        f.write(new_content)

def setup_telegram():
    print("=" * 60)
    print("🤖 TELEGRAM NOTIFICATION SETUP FOR APPLYMAXXING")
    print("=" * 60)
    print("\nFollow these 2 quick steps:")
    print("1. Open Telegram, search for '@BotFather', and send '/newbot'.")
    print("2. Choose a name and username. Copy the HTTP API token provided.\n")

    token = input("👉 Enter your Telegram BOT_TOKEN: ").strip()
    if not token:
        print("❌ No token provided. Exiting.")
        return

    # Verify Bot
    print("\n🔍 Verifying Bot Token...")
    try:
        r = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
        data = r.json()
        if not data.get("ok"):
            print(f"❌ Invalid Bot Token: {data.get('description')}")
            return
        bot_name = data["result"].get("first_name", "Bot")
        bot_user = data["result"].get("username", "")
        print(f"✅ Bot Verified: {bot_name} (@{bot_user})")
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return

    # Get Chat ID
    print(f"\n👉 Now open Telegram, search for @{bot_user}, and click 'Start' (or send 'hello').")
    input("Press Enter once you have sent a message to your bot...")

    print("🔍 Fetching your Chat ID...")
    try:
        r = requests.get(f"https://api.telegram.org/bot{token}/getUpdates", timeout=10)
        data = r.json()
        updates = data.get("result", [])
        if not updates:
            print("⚠️ No messages found yet! Make sure you clicked 'Start' or messaged your bot.")
            chat_id = input("If you already know your Chat ID, enter it manually (or press Enter to cancel): ").strip()
            if not chat_id:
                return
        else:
            last_message = updates[-1]
            chat = last_message.get("message", {}).get("chat", {}) or last_message.get("my_chat_member", {}).get("chat", {})
            chat_id = str(chat.get("id"))
            first_name = chat.get("first_name", "User")
            print(f"✅ Found chat with: {first_name} (Chat ID: {chat_id})")
    except Exception as e:
        print(f"❌ Failed to fetch updates: {e}")
        return

    # Save to .env
    update_env_variable("TELEGRAM_BOT_TOKEN", token)
    update_env_variable("TELEGRAM_CHAT_ID", chat_id)
    print("💾 Saved credentials to .env file!")

    # Send test message
    test_url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": "🎉 *ApplyMaxxing Connected!*\n\nYou're all set! Whenever new applications, OAs, interview calls, or offers are detected in your email, you will receive real-time alerts right here.",
        "parse_mode": "Markdown"
    }
    try:
        requests.post(test_url, json=payload, timeout=10)
        print("\n🚀 Test notification sent successfully to your Telegram!")
        print("=" * 60)
    except Exception as e:
        print(f"Failed to send test message: {e}")

if __name__ == "__main__":
    setup_telegram()
