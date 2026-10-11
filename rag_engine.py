import os
import json
import math
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
from google import genai
from google.genai import types
import db

load_dotenv()

DB_FILE = 'jobs.db'
EMBED_MODEL = 'gemini-embedding-001'
CHAT_MODEL = 'gemini-3.8-flash'

def get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_gemini_api_key_here":
        raise ValueError("GEMINI_API_KEY is not configured in .env")
    return genai.Client(api_key=api_key)

def get_embedding(text: str) -> list[float]:
    """Generates a vector embedding for the input text using Gemini."""
    client = get_gemini_client()
    # Truncate text to avoid exceeding limits
    truncated_text = text[:3000].strip()
    if not truncated_text:
        truncated_text = "Empty content"
        
    response = client.models.embed_content(
        model=EMBED_MODEL,
        contents=truncated_text
    )
    return response.embeddings[0].values

def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Calculates cosine similarity between two float vectors."""
    dot_product = sum(a * b for a, b in zip(v1, v2))
    norm_a = math.sqrt(sum(a * a for a in v1))
    norm_b = math.sqrt(sum(b * b for b in v2))
    if not norm_a or not norm_b:
        return 0.0
    return dot_product / (norm_a * norm_b)

def index_email(company: str, role: str, email_subject: str, email_body: str, received_date: str = None) -> bool:
    """Embeds and saves an email into the RAG database."""
    try:
        content_to_embed = f"Company: {company}\nRole: {role}\nSubject: {email_subject}\n\n{email_body[:1500]}"
        vector = get_embedding(content_to_embed)
        db.add_rag_email(company, role, email_subject, email_body, vector, received_date)
        return True
    except Exception as e:
        print(f"Error indexing email: {e}")
        return False

def search_similar_emails(query: str, top_k: int = 4) -> list[dict]:
    """Retrieves top_k relevant email documents for the query."""
    query_vector = get_embedding(query)
    all_emails = db.get_all_rag_emails()
    
    scored_docs = []
    for row in all_emails:
        doc_id, company, role, subject, body, embedding_json, date = row
        try:
            doc_vector = json.loads(embedding_json)
            score = cosine_similarity(query_vector, doc_vector)
            scored_docs.append({
                "id": doc_id,
                "company": company,
                "role": role,
                "subject": subject,
                "body": body,
                "date": date,
                "score": score
            })
        except Exception:
            continue
            
    scored_docs.sort(key=lambda x: x["score"], reverse=True)
    return scored_docs[:top_k]

def get_job_summary_context(query: str) -> str:
    """Finds matching metadata from the jobs table (company name or status matches)."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT company, role, status, applied_date, deadline, notes FROM jobs")
    rows = c.fetchall()
    conn.close()
    
    query_lower = query.lower()
    matched_jobs = []
    
    for r in rows:
        company, role, status, applied_date, deadline, notes = r
        if (company and company.lower() in query_lower) or (status and status.lower() in query_lower):
            matched_jobs.append(f"• {company} ({role}) | Status: {status} | Applied: {applied_date} | Notes: {notes or 'N/A'}")
            
    if matched_jobs:
        return "Relevant Jobs in Tracker:\n" + "\n".join(matched_jobs[:10])
    return ""

def ask_rag(question: str) -> dict:
    """Answers a user question grounded in retrieved email contents and job records."""
    client = get_gemini_client()
    
    # 1. Retrieve relevant emails via semantic vector search
    retrieved_emails = search_similar_emails(question, top_k=4)
    
    # 2. Retrieve job tracker metadata
    job_context = get_job_summary_context(question)
    
    # 3. Assemble prompt context
    email_contexts = []
    sources = []
    for i, doc in enumerate(retrieved_emails):
        if doc["score"] > 0.35: # Only include documents with reasonable similarity
            email_contexts.append(
                f"[Source {i+1}]\nCompany: {doc['company']}\nRole: {doc['role']}\nSubject: {doc['subject']}\nDate: {doc['date']}\nContent:\n{doc['body'][:1200]}"
            )
            sources.append({
                "company": doc["company"],
                "subject": doc["subject"],
                "date": doc["date"],
                "score": round(doc["score"], 3)
            })
            
    context_str = "\n\n---\n\n".join(email_contexts)
    if not context_str:
        context_str = "No specific email text found with high semantic similarity."
        
    full_prompt = f"""
You are the AI Assistant for ApplyMaxxing, the user's personal job application tracker.
Answer the user's question accurately using ONLY the provided application records and retrieved email communications.

If the answer cannot be found in the provided context, state that clearly and suggest what information might be missing.

USER QUESTION:
{question}

RETRIEVED EMAIL CONTEXT:
{context_str}

TRACKER DATABASE CONTEXT:
{job_context}

Provide a direct, helpful, and concise answer. Cite specific company names, dates, assessment links, or instructions if present.
"""

    try:
        response = client.models.generate_content(
            model=CHAT_MODEL,
            contents=full_prompt,
            config=types.GenerateContentConfig(
                temperature=0.2
            )
        )
        answer = response.text
    except Exception as e:
        answer = f"Error generating answer: {e}"
        
    return {
        "answer": answer,
        "sources": sources
    }

if __name__ == '__main__':
    print("Testing RAG Engine...")
    test_q = "Have I applied to Google or any trading firms?"
    res = ask_rag(test_q)
    print("Answer:\n", res["answer"])
