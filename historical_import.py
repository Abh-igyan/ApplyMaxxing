import imaplib
import email
from email.header import decode_header
import sqlite3
import os
import json
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

load_dotenv()

EMAIL_ACCOUNT = os.getenv("EMAIL_ACCOUNT")
APP_PASSWORD = os.getenv("APP_PASSWORD")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DB_FILE = 'jobs.db'

# Define the expected JSON array structure from the LLM
class ExtractedJob(BaseModel):
    email_id: str = Field(description="The ID of the email this was extracted from")
    company_name: str = Field(description="The exact name of the company.")
    role: str = Field(description="The job title or role.")
    status: str = Field(description="Must be one of: 'Applied', 'Online Assessment (OA)', 'Interviewing', 'Offer', 'Rejected'")

class BatchJobResult(BaseModel):
    jobs: list[ExtractedJob] = Field(description="List of valid job applications found in the batch.")

def connect_to_gmail():
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(EMAIL_ACCOUNT, APP_PASSWORD)
    return mail

def is_likely_junk(subject: str, sender: str) -> bool:
    subject_lower = subject.lower()
    sender_lower = sender.lower()
    
    junk_domains = ['amazon', 'netflix', 'swiggy', 'zomato', 'flipkart', 'myntra', 
                    'hdfc', 'sbi', 'icici', 'paypal', 'uber', 'ola', 'youtube', 'github.com', 'quora']
    if any(domain in sender_lower for domain in junk_domains):
        return True
        
    junk_keywords = ['newsletter', 'digest', 'alert', 'sale', 'discount', 'exclusive offer', 
                     'verify your', 'security alert', 'login', 'otp', 'password', 
                     'hackathon', 'competition', 'weekly', 'monthly']
    if any(word in subject_lower for word in junk_keywords):
        return True
        
    job_keywords = ['application', 'apply', 'applied', 'interview', 'assessment', 
                    'hackerrank', 'codesignal', 'offer', 'update', 'status', 'next steps',
                    'thank you for', 'received', 'candidate', 'resume', 'talent', 'careers']
    
    if not any(word in subject_lower for word in job_keywords):
        return True 
        
    return False

def get_clean_text(msg):
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                try:
                    body = part.get_payload(decode=True).decode()
                    break
                except:
                    pass
    else:
        try:
            body = msg.get_payload(decode=True).decode()
        except:
            pass
    return body.replace('\n', ' ').replace('\r', ' ')[:200]

def run_historical_import():
    mail = connect_to_gmail()
    print("🚀 Connected to Gmail. Fetching emails from the past 1 year...")
    mail.select("inbox")
    
    # Calculate date 1 year ago
    one_year_ago = (datetime.now() - timedelta(days=365)).strftime("%d-%b-%Y")
    status_code, messages = mail.search(None, f'(SINCE "{one_year_ago}")')
    email_ids = messages[0].split()
    
    print(f"📥 Found {len(email_ids)} total emails in the last year.")
    print("🧹 Running Layer 1 Heuristic Filter (compressing context)...")
    
    compressed_emails = []
    
    print(f"📥 Found {len(email_ids)} total emails in the last year.")
    print("🧹 Running Layer 1 Heuristic Filter (Bulk fetching headers, this will be FAST!)...")
    
    passed_filter_meta = []
    
    # BULK FETCH HEADERS in chunks of 1000 to prevent IMAP line-length limits
    chunk_size = 1000
    for i in range(0, len(email_ids), chunk_size):
        chunk = email_ids[i:i+chunk_size]
        ids_str = b",".join(chunk)
        
        res, msg_data = mail.fetch(ids_str, '(BODY.PEEK[HEADER.FIELDS (SUBJECT FROM DATE)])')
        
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                # Extract the email ID from the response (e.g., b'1234 (BODY...')
                try:
                    raw_header = response_part[0].decode('ascii', errors='ignore')
                    eid = raw_header.split(' ')[0]
                except:
                    continue

                msg = email.message_from_bytes(response_part[1])
                
                subject = ""
                if msg["Subject"]:
                    subj_header = decode_header(msg["Subject"])[0]
                    subject = subj_header[0]
                    if isinstance(subject, bytes):
                        encoding = subj_header[1] if subj_header[1] else "utf-8"
                        try:
                            subject = subject.decode(encoding, errors="ignore")
                        except:
                            subject = str(subject)
                            
                sender = str(msg.get("From", ""))
                date_str = str(msg.get("Date", ""))
                
                if subject and not is_likely_junk(subject, sender):
                    passed_filter_meta.append({
                        "id": eid,
                        "subject": subject,
                        "sender": sender,
                        "date": date_str
                    })
                    
    print(f"🎯 Filtered down to {len(passed_filter_meta)} potential job emails.")
    
    if not passed_filter_meta:
        print("No job emails found.")
        return

    print("📥 Fetching body snippets for the filtered emails...")
    compressed_emails = []
    
    # Reverse so we process newest first
    passed_filter_meta.reverse()
    
    # Now we only do sequential network calls for the TINY fraction of emails that passed the filter
    for meta in passed_filter_meta:
        res_body, body_data = mail.fetch(meta["id"].encode('ascii'), '(RFC822)')
        snippet = ""
        for response_part in body_data:
            if isinstance(response_part, tuple):
                full_msg = email.message_from_bytes(response_part[1])
                snippet = get_clean_text(full_msg)
        
        compressed_emails.append({
            "id": meta["id"],
            "date": meta["date"],
            "subject": meta["subject"],
            "sender": meta["sender"],
            "snippet": snippet
        })

    print(f"🎯 Filtered down to {len(compressed_emails)} potential job emails.")
    
    if not compressed_emails:
        print("No job emails found.")
        return

    # LAYER 2: Batch LLM Processing
    print("\n🧠 Sending batches to LLM to save API quota...")
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # We will send 50 emails per LLM request. 
    # 50 emails * ~40 words = ~2,000 words per request. Well within token limits!
    BATCH_SIZE = 50 
    total_added = 0
    
    for i in range(0, len(compressed_emails), BATCH_SIZE):
        batch = compressed_emails[i:i + BATCH_SIZE]
        print(f"⏳ Processing batch {i//BATCH_SIZE + 1} (Emails {i} to {i+len(batch)})...")
        
        prompt = f"""
        You are an expert HR and recruitment AI assistant. I am giving you a JSON array of {len(batch)} emails.
        Many of these might be educational courses, newsletters, or false positives.
        
        Analyze them and return ONLY the legitimate job applications. Extract the company name, role, and current status.
        
        Emails JSON:
        {json.dumps(batch, indent=2)}
        """
        
        MAX_RETRIES = 3
        retry_count = 0
        success = False
        
        while retry_count < MAX_RETRIES and not success:
            try:
                # Respect 5 RPM limit on every call/retry
                if i > 0 or retry_count > 0:
                    print("⏳ Sleeping for 15 seconds to respect rate limits...")
                    time.sleep(15)
                    
                response = client.models.generate_content(
                    model='gemini-3.8-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=BatchJobResult,
                        temperature=0.0
                    ),
                )
                
                valid_jobs = response.parsed.jobs
                print(f"✨ Found {len(valid_jobs)} valid jobs in this batch!")
                
                for job in valid_jobs:
                    # Find the original email date
                    original_email = next((e for e in batch if e["id"] == job.email_id), None)
                    applied_date = datetime.now().strftime("%Y-%m-%d")
                    if original_email:
                        try:
                            parsed_date = email.utils.parsedate_to_datetime(original_email["date"])
                            if parsed_date:
                                applied_date = parsed_date.strftime("%Y-%m-%d")
                        except:
                            pass
                    
                    # Check if exists
                    c.execute("SELECT id FROM jobs WHERE company LIKE ?", (f"%{job.company_name}%",))
                    if not c.fetchone():
                        c.execute('''
                            INSERT INTO jobs (company, role, platform, status, applied_date, job_link, notes)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (job.company_name, job.role, "Historical Import", job.status, applied_date, "", "Imported via Batch LLM"))
                        total_added += 1
                
                conn.commit()
                success = True
                
            except Exception as e:
                error_msg = str(e)
                if "503" in error_msg or "UNAVAILABLE" in error_msg:
                    retry_count += 1
                    print(f"⚠️ Google API is busy (503). Retrying {retry_count}/{MAX_RETRIES} in 15 seconds...")
                else:
                    print(f"❌ Batch LLM Error: {e}")
                    break # Break on non-503 errors (like 429 quota exhausted)
            
    conn.close()
    mail.logout()
    print(f"\n🎉 Historical import complete! Successfully extracted {total_added} jobs from the past year.")

if __name__ == "__main__":
    run_historical_import()

