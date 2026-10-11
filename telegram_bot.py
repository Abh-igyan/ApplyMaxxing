import os
import sys
import time
import requests
import sqlite3
from dotenv import load_dotenv
import rag_engine
import notifier

# Ensure Windows terminal doesn't crash on UTF-8 strings
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
DB_FILE = 'jobs.db'

def get_updates(offset=None):
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    params = {"timeout": 20}
    if offset:
        params["offset"] = offset
    try:
        r = requests.get(url, params=params, timeout=25)
        if r.status_code == 200:
            return r.json().get("result", [])
    except Exception as e:
        print(f"Error fetching updates: {e}")
    return []

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        r = requests.post(url, json=payload, timeout=15)
        if r.status_code == 400 and "can't parse entities" in r.text:
            payload.pop("parse_mode", None)
            requests.post(url, json=payload, timeout=15)
    except Exception as e:
        print(f"Error sending message: {e}")

def get_stats():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM jobs")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM jobs WHERE status = 'Applied'")
    applied = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM jobs WHERE status LIKE '%Assessment%' OR status LIKE '%OA%'")
    oas = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM jobs WHERE status LIKE '%Interview%'")
    interviews = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM jobs WHERE status = 'Offer'")
    offers = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM jobs WHERE status = 'Rejected'")
    rejected = c.fetchone()[0]
    conn.close()
    
    return (
        f"📊 *ApplyMaxxing Stats:*\n\n"
        f"• *Total Tracked:* {total}\n"
        f"• *Applied:* {applied}\n"
        f"• *Online Assessments (OA):* {oas}\n"
        f"• *Interviewing:* {interviews}\n"
        f"• *Offers:* {offers}\n"
        f"• *Rejected:* {rejected}\n"
    )

def handle_message(chat_id, text):
    text = text.strip()
    if text.startswith("/start") or text.startswith("/help"):
        msg = (
            "🤖 *ApplyMaxxing AI Bot (RAG Enabled)*\n\n"
            "You can ask me questions about your applications, emails, OAs, and rejections directly here!\n\n"
            "*Available commands:*\n"
            "• `/ask <question>` — Semantic Q&A with your applications\n"
            "• `/status` — Quick breakdown of your job tracker\n"
            "• Or just send any natural question (e.g. _'Which firms sent me OAs?'_)"
        )
        send_message(chat_id, msg)
        return

    if text.startswith("/status"):
        send_message(chat_id, get_stats())
        return

    question = text
    if text.startswith("/ask"):
        question = text.replace("/ask", "", 1).strip()

    if not question:
        send_message(chat_id, "Please provide a question, e.g.: `/ask Did I apply to Google?`")
        return

    send_message(chat_id, "🔍 *Searching your applications & emails...*")
    try:
        result = rag_engine.ask_rag(question)
        answer = result["answer"]
        sources = result.get("sources", [])
        
        reply = answer
        if sources:
            reply += "\n\n📚 *Sources:*\n"
            for s in sources:
                reply += f"• *{s['company']}* ({s['date']}) — _{s['subject']}_\n"
                
        send_message(chat_id, reply)
    except Exception as e:
        send_message(chat_id, f"❌ Error querying RAG engine: {e}")

def run_bot():
    if not TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not found in .env!")
        return

    print("🤖 ApplyMaxxing Telegram RAG Bot is running in polling mode...")
    print("Press Ctrl+C to stop.")
    
    offset = None
    while True:
        try:
            updates = get_updates(offset)
            for u in updates:
                offset = u["update_id"] + 1
                msg = u.get("message")
                if not msg:
                    continue
                chat_id = str(msg.get("chat", {}).get("id"))
                text = msg.get("text")
                if text:
                    print(f"📩 Received message from {chat_id}: '{text}'")
                    handle_message(chat_id, text)
            time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping bot.")
            break
        except Exception as e:
            print(f"Error in polling loop: {e}")
            time.sleep(3)

if __name__ == "__main__":
    run_bot()
