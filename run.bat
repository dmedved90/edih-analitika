@echo off
REM EDIH Analytics - Run Script for Windows

echo Starting EDIH Analytics Dashboard...

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install/update dependencies
echo Installing dependencies...
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

REM Check if .env exists
if not exist ".env" (
    echo Warning: .env file not found!
    if exist ".env.example" (
        echo Creating from .env.example...
        copy .env.example .env
        echo Created .env - Please edit it with your API keys
        pause
        exit /b 1
    ) else (
        echo .env.example not found. Please create .env manually.
        pause
        exit /b 1
    )
)

REM Run configuration test
echo Testing configuration...
python test_config.py
if errorlevel 1 (
    echo Configuration test failed. Please fix issues before running.
    pause
    exit /b 1
)

REM Create logs directory
if not exist "logs" mkdir logs

REM Run the application
echo Starting application on http://localhost:8501
echo Press Ctrl+C to stop
streamlit run app.py

deactivate
