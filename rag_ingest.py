import sqlite3
import imaplib
import email
from email.header import decode_header
import os
import sys
import time
import sys
from datetime import datetime
from dotenv import load_dotenv
import db
import rag_engine

# Ensure Windows terminal doesn't crash on UTF-8 strings
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

load_dotenv()

EMAIL_ACCOUNT = os.getenv("EMAIL_ACCOUNT")
APP_PASSWORD = os.getenv("APP_PASSWORD")
DB_FILE = 'jobs.db'

def index_existing_jobs_metadata():
    """Indexes all 119 existing jobs in jobs.db into the RAG vector store."""
    print("[RAG Ingest] Generating semantic embeddings for existing tracker jobs...")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, company, role, status, applied_date, job_link, notes FROM jobs")
    jobs = c.fetchall()
    conn.close()
    
    indexed_count = 0
    total = len(jobs)
    
    for i, job in enumerate(jobs):
        job_id, company, role, status, applied_date, link, notes = job
        subject = f"Application Status: {status} at {company}"
        
        # Check if already indexed
        if db.rag_email_exists(company, subject):
            continue
            
        content = (
            f"Company: {company}\n"
            f"Role: {role}\n"
            f"Application Status: {status}\n"
            f"Date Applied: {applied_date}\n"
            f"Job Post Link: {link or 'Not specified'}\n"
            f"Application Notes: {notes or 'No additional notes'}"
        )
        
        print(f"[{i+1}/{total}] Indexing {company} ({role})...")
        success = rag_engine.index_email(
            company=company,
            role=role,
            email_subject=subject,
            email_body=content,
            received_date=applied_date or datetime.now().strftime("%Y-%m-%d")
        )
        if success:
            indexed_count += 1
            
        # Respect Gemini free tier RPM
        time.sleep(1)

    print(f"[RAG] Successfully indexed {indexed_count} existing jobs into RAG knowledge store!")

def index_recent_emails_from_gmail(max_emails=50):
    """Scans recent job emails from Gmail inbox and indexes their full bodies."""
    if not EMAIL_ACCOUNT or not APP_PASSWORD:
        print("[RAG] Email credentials not found in .env, skipping live Gmail sync.")
        return

    print("\n📥 Fetching recent emails from Gmail to index full text bodies...")
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL_ACCOUNT, APP_PASSWORD)
        mail.select("inbox")
    except Exception as e:
        print(f"❌ Failed to connect to Gmail: {e}")
        return

    status_code, messages = mail.search(None, 'ALL')
    if status_code != 'OK' or not messages[0]:
        print("No emails found.")
        mail.logout()
        return

    email_ids = messages[0].split()
    recent_ids = email_ids[-max_emails:]
    
    job_keywords = ['application', 'interview', 'assessment', 'hackerrank', 'codesignal', 'offer', 'status', 'candidate']
    new_emails_indexed = 0
    
    for eid in reversed(recent_ids):
        try:
            res, msg_data = mail.fetch(eid, '(RFC822)')
            for part in msg_data:
                if isinstance(part, tuple):
                    msg = email.message_from_bytes(part[1])
                    
                    subj_header = decode_header(msg.get("Subject", ""))[0]
                    subject = subj_header[0]
                    if isinstance(subject, bytes):
                        encoding = subj_header[1] or "utf-8"
                        subject = subject.decode(encoding, errors="ignore")
                    subject = str(subject)
                    
                    sender = str(msg.get("From", ""))
                    date_str = str(msg.get("Date", ""))
                    
                    # Quick filter
                    if not any(k in subject.lower() for k in job_keywords):
                        continue
                        
                    # Extract body
                    body = ""
                    if msg.is_multipart():
                        for p in msg.walk():
                            if p.get_content_type() == "text/plain":
                                try:
                                    body = p.get_payload(decode=True).decode(errors="ignore")
                                    break
                                except:
                                    pass
                    else:
                        try:
                            body = msg.get_payload(decode=True).decode(errors="ignore")
                        except:
                            pass
                            
                    clean_body = body.replace("\r", " ").replace("\n", " ").strip()
                    if not clean_body:
                        continue
                        
                    company_guess = sender.split("@")[-1].split(".")[0].capitalize()
                    
                    if not db.rag_email_exists(company_guess, subject):
                        print(f"[RAG] Indexing email: '{subject[:60]}' from {sender[:30]}...")
                        rag_engine.index_email(
                            company=company_guess,
                            role="Software Engineer Intern",
                            email_subject=subject,
                            email_body=clean_body[:3000],
                            received_date=datetime.now().strftime("%Y-%m-%d")
                        )
                        new_emails_indexed += 1
                        time.sleep(1)
        except Exception as e:
            continue
            
    mail.logout()
    print(f"[RAG] Indexed {new_emails_indexed} rich email threads into RAG.")

if __name__ == "__main__":
    db.init_db()
    index_existing_jobs_metadata()
    index_recent_emails_from_gmail(max_emails=60)
