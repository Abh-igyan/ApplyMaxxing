import sqlite3
import requests
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# SETUP TELEGRAM NOTIFICATIONS
# 1. Message @BotFather on Telegram, send /newbot, and get your BOT_TOKEN.
# 2. Message your new bot, then go to https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates to get your CHAT_ID.
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "your_bot_token_here")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "your_chat_id_here")

DB_FILE = 'jobs.db'

def send_telegram_message(text):
    if TELEGRAM_BOT_TOKEN == "your_bot_token_here":
        print("Please set up your Telegram Bot Token in notifier.py!")
        return
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print("Notification sent successfully.")
    except Exception as e:
        print(f"Failed to send telegram message: {e}")

def check_deadlines():
    print("Checking for upcoming deadlines...")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Get jobs with status 'Saved' or similar that haven't been applied to yet
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
    check_deadlines()

