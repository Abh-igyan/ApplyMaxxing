import imaplib
import email
from email.header import decode_header
import sqlite3
import os
import time
from datetime import datetime
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
import notifier

load_dotenv()

EMAIL_ACCOUNT = os.getenv("EMAIL_ACCOUNT")
APP_PASSWORD = os.getenv("APP_PASSWORD")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DB_FILE = 'jobs.db'

# Define the expected JSON structure from the LLM
class JobEmailData(BaseModel):
    is_job_related: bool = Field(description="True ONLY if this email is a legitimate job application confirmation, interview invite, online assessment, or rejection. False for promotional emails, newsletters, or educational course enrollments.")
    company_name: str | None = Field(description="The exact name of the company.")
    role: str | None = Field(description="The job title or role.")
    status: str | None = Field(description="Must be one of: 'Applied', 'Online Assessment (OA)', 'Interviewing', 'Offer', 'Rejected'")
    confidence: int = Field(description="Confidence score from 0 to 100")

def connect_to_gmail():
    if not EMAIL_ACCOUNT or not APP_PASSWORD:
        print("Please configure EMAIL_ACCOUNT and APP_PASSWORD in your .env file.")
        return None
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL_ACCOUNT, APP_PASSWORD)
        return mail
    except Exception as e:
        print(f"Failed to connect to Gmail: {e}")
        return None

def is_likely_junk(subject: str, sender: str) -> bool:
    """
    LAYER 1: Fast Heuristic Pre-filter.
    Drops 95% of emails instantly without calling the LLM to save quota.
    """
    subject_lower = subject.lower()
    sender_lower = sender.lower()
    
    # 1. Skip obvious junk senders (banks, ecommerce, social media)
    junk_domains = ['amazon', 'netflix', 'swiggy', 'zomato', 'flipkart', 'myntra', 
                    'hdfc', 'sbi', 'icici', 'paypal', 'uber', 'ola', 'youtube', 'github.com', 'quora']
    if any(domain in sender_lower for domain in junk_domains):
        return True
        
    # 2. Skip obvious non-job subjects
    junk_keywords = ['newsletter', 'digest', 'alert', 'sale', 'discount', 'exclusive offer', 
                     'verify your', 'security alert', 'login', 'otp', 'password', 
                     'hackathon', 'competition', 'weekly', 'monthly']
    if any(word in subject_lower for word in junk_keywords):
        return True
        
    # 3. Require at least one "maybe job-related" keyword in the subject
    job_keywords = ['application', 'apply', 'applied', 'interview', 'assessment', 
                    'hackerrank', 'codesignal', 'offer', 'update', 'status', 'next steps',
                    'thank you for', 'received', 'candidate', 'resume', 'talent', 'careers']
    
    if not any(word in subject_lower for word in job_keywords):
        return True # Doesn't look like a job email, skip it.
        
    return False

def analyze_email_with_llm(subject: str, sender: str, snippet: str):
    """
    LAYER 2: Precision Extraction.
    Only passes pre-filtered emails to Gemini for high-accuracy parsing.
    """
    if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
        print("❌ GEMINI_API_KEY is missing! Please add it to your .env file.")
        return None

    client = genai.Client(api_key=GEMINI_API_KEY)
    
    prompt = f"""
    You are an expert HR and recruitment AI assistant. Analyze this email metadata to determine if it is related to a job application.
    Be extremely careful to ignore:
    - Promotional marketing emails
    - Educational courses or math tests for student enrollment (e.g., 'Options 201 Course', 'Interview Kickstart course')
    
    Email Subject: {subject}
    Sender: {sender}
    Body Snippet: {snippet}
    
    Extract the company name, role, and the current status of the application.
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-3.8-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=JobEmailData,
                temperature=0.0
            ),
        )
        return response.parsed
    except Exception as e:
        print(f"LLM Error: {e}")
        return None

def get_email_body_snippet(msg):
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
    body = body.replace('\n', ' ').replace('\r', '')
    return body[:500] if body else "No text body available."

def scan_emails_for_updates():
    mail = connect_to_gmail()
    if not mail:
        return
        
    print("🚀 Connected to Gmail. Launching Multi-Layer Auto-Discovery Engine...")
    mail.select("inbox")
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT company, status FROM jobs")
    existing_jobs = {row[0].lower(): row[1] for row in c.fetchall()}
    
    # Fetch only recent emails to save quota (e.g. last 30 instead of 50)
    status_code, messages = mail.search(None, 'ALL')
    email_ids = messages[0].split()
    latest_email_ids = email_ids[-30:] 
    
    new_jobs_added = 0
    updates_made = 0
    llm_calls_made = 0
    MAX_LLM_CALLS = 5 # Strict limit to protect your 20 RPD quota
    
    for eid in latest_email_ids:
        if llm_calls_made >= MAX_LLM_CALLS:
            print(f"\n⚠️ Reached maximum LLM calls ({MAX_LLM_CALLS}) for this run to protect your daily quota.")
            break

        res, msg_data = mail.fetch(eid, '(RFC822)')
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                
                subj_header = decode_header(msg["Subject"])[0]
                subject = subj_header[0]
                if isinstance(subject, bytes):
                    encoding = subj_header[1] if subj_header[1] else "utf-8"
                    try:
                        subject = subject.decode(encoding, errors="ignore")
                    except:
                        subject = str(subject)
                        
                sender = str(msg.get("From"))
                date_str = msg.get("Date")
                
                # LAYER 1: Pre-filter to avoid hitting API Quota limits
                if not subject or is_likely_junk(subject, sender):
                    continue

                snippet = get_email_body_snippet(msg)
                print(f"\n🧠 [Layer 2] LLM Analyzing: '{subject}'...")
                
                # Sleep for 13 seconds to respect the 5 Requests-Per-Minute limit
                time.sleep(13) 
                
                llm_calls_made += 1
                llm_result = analyze_email_with_llm(subject, sender, snippet)
                
                if llm_result and llm_result.is_job_related and llm_result.company_name and llm_result.confidence > 70:
                    company = llm_result.company_name
                    role = llm_result.role or "Software Engineer Intern"
                    new_status = llm_result.status
                    comp_key = company.lower()
                    
                    if comp_key not in existing_jobs:
                        print(f"✨ [LLM DISCOVERY] Found New Job: {company} | Role: {role} | Status: {new_status}")
                        
                        applied_date = datetime.now().strftime("%Y-%m-%d")
                        try:
                            parsed_date = email.utils.parsedate_to_datetime(date_str)
                            if parsed_date:
                                applied_date = parsed_date.strftime("%Y-%m-%d")
                        except:
                            pass
                            
                        c.execute('''
                            INSERT INTO jobs (company, role, platform, status, applied_date, job_link, notes)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (company, role, "LLM Auto-Discovery", new_status, applied_date, "", f"Discovered from email: {subject}"))
                        conn.commit()
                        existing_jobs[comp_key] = new_status
                        new_jobs_added += 1
                        notifier.notify_new_application(company, role, new_status, applied_date)
                        
                    else:
                        current_status = existing_jobs[comp_key]
                        if new_status and new_status != "Applied" and new_status != current_status:
                            print(f"🔄 [LLM UPDATE] {company} moved to '{new_status}' (was '{current_status}')")
                            c.execute("UPDATE jobs SET status = ? WHERE company LIKE ?", (new_status, f"%{company}%"))
                            conn.commit()
                            existing_jobs[comp_key] = new_status
                            updates_made += 1
                            notifier.notify_status_update(company, role, current_status, new_status)
                elif llm_result:
                    print(f"   -> Ignored (LLM decided it's not a job application)")

    conn.close()
    mail.logout()
    print(f"\n✅ LLM Scan complete! Added {new_jobs_added} new jobs and made {updates_made} status updates.")

if __name__ == "__main__":
    scan_emails_for_updates()
