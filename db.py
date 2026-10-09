import sqlite3
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

if __name__ == '__main__':
    init_db()

