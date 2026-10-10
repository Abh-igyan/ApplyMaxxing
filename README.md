# ApplyMaxxing 🚀

A highly optimized, fully-automated local job application tracker that scans your emails, extracts application updates, and organizes them without exhausting your LLM API limits. Built for the modern intern grindset.

## Features ✨
- **Local-First & Privacy-Respecting:** All your data stays on your machine (`jobs.db`).
- **Multi-Layer AI Parsing:** 
  - **Layer 1:** Heuristic pre-filter drops 95% of junk emails (ads, spam, unrelated stuff) locally.
  - **Layer 2:** LLM precision extraction (Gemini 3.8 Flash) identifies OAs, Interviews, Rejections, and Offers.
- **Context Compression & Batch Inference:** Bypasses strict API rate limits (e.g., Gemini's 5 RPM / 20 RPD) by batching 50 emails per prompt. Processes 500 emails in just 10 API calls!
- **Historical Deep Scan:** Pull your last 1 year of application history instantly.

## Setup 🛠️

1. **Clone the repo:**
   ```bash
   git clone https://github.com/Abh-igyan/ApplyMaxxing.git
   cd ApplyMaxxing
   ```

2. **Create a virtual environment & install dependencies:**
   ```bash
   python -m venv venv
   source venv/Scripts/activate  # On Windows
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables:**
   - Copy `.env.example` to `.env`.
   - Add your IMAP credentials (use an App Password for Gmail) and Gemini API Key.
   ```bash
   cp .env.example .env
   ```

## Usage 💻

**1. Historical Import (Fetch last 1 year of data):**
```bash
python historical_import.py
```

**2. Run the Dashboard:**
```bash
streamlit run app.py
```

## Why ApplyMaxxing?
Standard sequential LLM email parsers crash or exhaust free-tier API quotas instantly. ApplyMaxxing uses a smart local filter combined with batch-prompting to give you a full application knowledge graph with minimal token usage and API calls. Stop getting ghosted in the dark—track your aura.

