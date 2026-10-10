import sqlite3
import requests
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
DB_FILE = 'jobs.db'

def is_telegram_configured():
    invalid = ["your_bot_token_here", "your_telegram_bot_token", "", None]
    return TELEGRAM_BOT_TOKEN not in invalid and TELEGRAM_CHAT_ID not in invalid

def send_telegram_message(text):
    if not is_telegram_configured():
        return False
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        print("📱 Telegram notification sent.")
        return True
    except Exception as e:
        print(f"Failed to send telegram notification: {e}")
        return False

def notify_new_application(company, role, status, applied_date=""):
    emoji = "🎯"
    if "Offer" in status:
        emoji = "🏆"
    elif "Interview" in status:
        emoji = "💼"
    elif "OA" in status or "Assessment" in status:
        emoji = "⚡"
    elif "Rejected" in status:
        emoji = "🛑"

    message = (
        f"{emoji} *Job Tracker Alert: New Application*\n\n"
        f"🏢 *Company:* {company}\n"
        f"💼 *Role:* {role}\n"
        f"📌 *Status:* `{status}`\n"
    )
    if applied_date:
        message += f"📅 *Date:* {applied_date}\n"
    
    send_telegram_message(message)

def notify_status_update(company, role, old_status, new_status):
    emoji = "🔄"
    if "Offer" in new_status:
        emoji = "🎉🏆"
    elif "Interview" in new_status:
        emoji = "🚀💼"
    elif "OA" in new_status or "Assessment" in new_status:
        emoji = "⚡"
    elif "Rejected" in new_status:
        emoji = "📉"

    message = (
        f"{emoji} *Job Application Status Update!*\n\n"
        f"🏢 *Company:* {company}\n"
        f"💼 *Role:* {role}\n"
        f"📊 *Status:* `{old_status}` ➔ *{new_status}*\n"
    )
    send_telegram_message(message)

def check_deadlines():
    print("Checking for upcoming deadlines...")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT company, role, deadline, job_link FROM jobs WHERE status LIKE '%Saved%'")
    saved_jobs = c.fetchall()
    conn.close()
    
    today = datetime.now().date()
    messages = []
    
    for job in saved_jobs:
        company, role, deadline_str, link = job
        if not deadline_str:
            continue
            
        try:
            deadline_date = datetime.strptime(deadline_str, "%Y-%m-%d").date()
            days_left = (deadline_date - today).days
            
            if 0 <= days_left <= 3:
                messages.append(f"🚨 *Deadline Approaching*\n*{company}* - {role}\nDeadline in *{days_left} days* ({deadline_date}).\n[Apply Here]({link})")
        except ValueError:
            continue
            
    if messages:
        final_message = "\n\n".join(messages)
        send_telegram_message(final_message)
    else:
        print("No urgent deadlines in the next 3 days.")

if __name__ == "__main__":
    if is_telegram_configured():
        print("Testing Telegram connection...")
        success = send_telegram_message("🚀 *ApplyMaxxing* connected! You will now receive instant application & status updates here.")
        if success:
            print("✅ Test message delivered!")
    else:
        print("⚠️ Telegram is not configured in .env yet.")
