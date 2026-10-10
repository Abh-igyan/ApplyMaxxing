import os
import urllib.request
import urllib.parse
import json
import re

ENV_FILE = '.env'

def make_request(url, data=None):
    try:
        req = urllib.request.Request(
            url,
            data=data,
            headers={'User-Agent': 'ApplyMaxxing/1.0', 'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        return {"ok": False, "description": str(e)}

def update_env_variable(key, value):
    if not os.path.exists(ENV_FILE):
        with open(ENV_FILE, 'w', encoding='utf-8') as f:
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
    res = make_request(f"https://api.telegram.org/bot{token}/getMe")
    if not res.get("ok"):
        print(f"❌ Invalid Bot Token: {res.get('description')}")
        return

    bot_name = res["result"].get("first_name", "Bot")
    bot_user = res["result"].get("username", "")
    print(f"✅ Bot Verified: {bot_name} (@{bot_user})")

    # Get Chat ID
    print(f"\n👉 Open Telegram, search for @{bot_user}, and click 'Start' (or send 'hello').")
    input("Press Enter once you have sent a message to your bot...")

    print("🔍 Fetching your Chat ID...")
    res = make_request(f"https://api.telegram.org/bot{token}/getUpdates")
    updates = res.get("result", [])
    
    if not updates:
        print("⚠️ No messages detected from your bot yet.")
        chat_id = input("If you already know your Chat ID, enter it manually (or press Enter to cancel): ").strip()
        if not chat_id:
            return
    else:
        last_message = updates[-1]
        chat = last_message.get("message", {}).get("chat", {}) or last_message.get("my_chat_member", {}).get("chat", {})
        chat_id = str(chat.get("id"))
        first_name = chat.get("first_name", "User")
        print(f"✅ Found chat with: {first_name} (Chat ID: {chat_id})")

    # Save to .env
    update_env_variable("TELEGRAM_BOT_TOKEN", token)
    update_env_variable("TELEGRAM_CHAT_ID", chat_id)
    print("💾 Saved credentials to .env file!")

    # Send test message
    test_url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({
        "chat_id": chat_id,
        "text": "🎉 *ApplyMaxxing Connected!*\n\nYou're all set! Whenever new applications, OAs, interview calls, or offers are detected in your email, you will receive real-time alerts right here.",
        "parse_mode": "Markdown"
    }).encode('utf-8')

    test_res = make_request(test_url, data=payload)
    if test_res.get("ok"):
        print("\n🚀 Test notification sent successfully to your Telegram!")
        print("=" * 60)
    else:
        print(f"\n⚠️ Failed to send test notification: {test_res.get('description')}")

if __name__ == "__main__":
    setup_telegram()
