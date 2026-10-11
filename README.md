# ApplyMaxxing 🚀

A highly optimized, fully-automated local job application tracker that scans your emails, extracts application updates, and organizes them without exhausting your LLM API limits. Built for the modern intern grindset.

Now equipped with **True Local RAG (Retrieval-Augmented Generation)** across your applications and email history!

## Features ✨
- **Local-First & Privacy-Respecting:** All your data stays on your machine (`jobs.db`).
- **Local RAG Engine:** 
  - Semantic vector search powered by `gemini-embedding-001` (3072-dimension dense embeddings).
  - Pure Python cosine similarity retrieval (zero heavy vector database bloat).
  - Grounded answering with citations via `gemini-3.8-flash`.
- **Dual-Interface Q&A:**
  - **Streamlit Web Dashboard:** Interactive chat tab with sources and preset questions.
  - **Telegram Bot Assistant:** Ask `/ask <question>` or chat directly via Telegram on the go.
- **Multi-Layer AI Parsing:** 
  - **Layer 1:** Heuristic pre-filter drops 95% of junk emails (ads, spam, unrelated stuff) locally.
  - **Layer 2:** LLM precision extraction (Gemini 3.8 Flash) identifies OAs, Interviews, Rejections, and Offers.
- **Context Compression & Batch Inference:** Bypasses strict API rate limits (e.g., Gemini's 5 RPM / 20 RPD) by batching 50 emails per prompt. Processes 500 emails in just 10 API calls!
- **Real-Time Telegram Push Alerts:** Instant notifications whenever an OA, interview invite, or offer is discovered.

## Setup 🛠️

1. **Clone the repo:**
   ```bash
   git clone https://github.com/Abh-igyan/ApplyMaxxing.git
   cd ApplyMaxxing
   ```

2. **Create a virtual environment & install dependencies:**
   ```bash
   python -m venv venv
   .\venv\Scripts\activate  # On Windows
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables:**
   - Copy `.env.example` to `.env`.
   - Add your Gmail App Password, Gemini API Key, and Telegram Bot credentials:
   ```bash
   python setup_telegram.py
   ```

## Usage 💻

### Launch Menu (One-Click)
```bash
start.bat
```

### Or run components individually:
**1. Run the Web Dashboard with RAG Chat:**
```bash
streamlit run app.py
```

**2. Start the Telegram Bot Assistant:**
```bash
python telegram_bot.py
```
*(Send `/ask What companies sent me OAs?` or `/status` directly to your bot)*

**3. Deep Scan (Last 1 year of emails):**
```bash
python historical_import.py
```

**4. Index email bodies into RAG vector store:**
```bash
python rag_ingest.py
```
