@echo off
echo Starting JobTracker AI...

echo.
echo Please choose an option:
echo 1. Start the JobTrack AI Web Dashboard (Streamlit)
echo 2. Check for upcoming deadlines (Telegram Notification)
echo 3. Scan recent emails for interview/rejection updates
echo 4. Deep Scan: Import all jobs from the past 1 year (Batch LLM)
echo.

set /p choice=Enter your choice (1-4): 

if "%choice%"=="1" (
    echo Starting Streamlit app...
    call venv\Scripts\activate
    streamlit run app.py
) else if "%choice%"=="2" (
    echo Checking deadlines...
    call venv\Scripts\activate
    python notifier.py
    pause
) else if "%choice%"=="3" (
    echo Scanning emails...
    call venv\Scripts\activate
    python email_scanner.py
    pause
) else if "%choice%"=="4" (
    echo Launching Historical Import...
    call venv\Scripts\activate
    python historical_import.py
    pause
) else (
    echo Invalid choice.
    pause
)

