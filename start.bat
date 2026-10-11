@echo off
echo ==============================================
echo       ApplyMaxxing - AI Job Tracker
echo ==============================================

echo.
echo Please choose an option:
echo 1. Start Web Dashboard with RAG Chat (Streamlit)
echo 2. Start Telegram AI Assistant Bot (RAG in Telegram)
echo 3. Scan recent emails for new jobs and status updates
echo 4. Deep Scan: Historical Import (Past 1 year)
echo 5. Sync/Index email bodies into RAG vector store
echo 6. Check deadlines (Telegram Notification)
echo.

set /p choice=Enter your choice (1-6): 

if "%choice%"=="1" (
    echo Starting Streamlit app...
    call venv\Scripts\activate
    streamlit run app.py
) else if "%choice%"=="2" (
    echo Starting Telegram RAG Assistant Bot...
    call venv\Scripts\activate
    python telegram_bot.py
    pause
) else if "%choice%"=="3" (
    echo Scanning recent emails...
    call venv\Scripts\activate
    python email_scanner.py
    pause
) else if "%choice%"=="4" (
    echo Launching Historical Import...
    call venv\Scripts\activate
    python historical_import.py
    pause
) else if "%choice%"=="5" (
    echo Indexing emails for RAG...
    call venv\Scripts\activate
    python rag_ingest.py
    pause
) else if "%choice%"=="6" (
    echo Checking deadlines...
    call venv\Scripts\activate
    python notifier.py
    pause
) else (
    echo Invalid choice.
    pause
)
