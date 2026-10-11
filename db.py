import sqlite3
import json
from datetime import datetime

DB_FILE = 'jobs.db'

def get_connection():
    return sqlite3.connect(DB_FILE)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL,
            role TEXT NOT NULL,
            platform TEXT,
            status TEXT DEFAULT 'Saved', 
            deadline DATE,
            applied_date DATE,
            job_link TEXT,
            notes TEXT
        )
    ''')
    
    # RAG vector storage table
    c.execute('''
        CREATE TABLE IF NOT EXISTS rag_emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL,
            role TEXT,
            email_subject TEXT,
            email_body TEXT,
            embedding TEXT,  -- JSON list of float values
            received_date DATE
        )
    ''')
    conn.commit()
    conn.close()

def add_job(company, role, platform, status, deadline, applied_date, job_link, notes):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO jobs (company, role, platform, status, deadline, applied_date, job_link, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (company, role, platform, status, deadline, applied_date, job_link, notes))
    conn.commit()
    conn.close()

def get_all_jobs():
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM jobs ORDER BY deadline ASC')
    jobs = c.fetchall()
    conn.close()
    return jobs

def update_job_status(job_id, new_status):
    conn = get_connection()
    c = conn.cursor()
    c.execute('UPDATE jobs SET status = ? WHERE id = ?', (new_status, job_id))
    conn.commit()
    conn.close()

def delete_job(job_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('DELETE FROM jobs WHERE id = ?', (job_id,))
    conn.commit()
    conn.close()

def add_rag_email(company, role, email_subject, email_body, embedding, received_date=None):
    conn = get_connection()
    c = conn.cursor()
    if received_date is None:
        received_date = datetime.now().strftime("%Y-%m-%d")
        
    embedding_json = json.dumps(embedding) if isinstance(embedding, list) else embedding
    c.execute('''
        INSERT INTO rag_emails (company, role, email_subject, email_body, embedding, received_date)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (company, role, email_subject, email_body, embedding_json, received_date))
    conn.commit()
    conn.close()

def rag_email_exists(company, email_subject):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT id FROM rag_emails WHERE company = ? AND email_subject = ?', (company, email_subject))
    row = c.fetchone()
    conn.close()
    return row is not None

def get_all_rag_emails():
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT id, company, role, email_subject, email_body, embedding, received_date FROM rag_emails')
    rows = c.fetchall()
    conn.close()
    return rows

if __name__ == '__main__':
    init_db()
