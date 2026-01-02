@echo off
REM Batch script to create Windows Task Scheduler task for Webex CDR Downloader
REM This must be run as Administrator

echo ============================================================
echo Webex CDR Downloader - Task Scheduler Setup
echo ============================================================
echo.

REM Get the current directory
set SCRIPT_DIR=%~dp0
set PYTHON_EXE=C:\Python313\python.exe
set SCRIPT_PATH=%SCRIPT_DIR%webex_cdr_downloader.py
set TASK_NAME=Webex CDR Downloader

REM Check if running as administrator
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: This script must be run as Administrator!
    echo.
    echo Right-click this file and select "Run as administrator"
    echo.
    pause
    exit /b 1
)

echo Creating scheduled task...
echo.
echo Task Configuration:
echo   Name:      %TASK_NAME%
echo   Python:    %PYTHON_EXE%
echo   Script:    %SCRIPT_PATH%
echo   Schedule:  Every 15 minutes
echo   Run as:    %USERNAME%
echo.

REM Delete existing task if it exists
schtasks /query /tn "%TASK_NAME%" >nul 2>&1
if %errorLevel% equ 0 (
    echo Task already exists. Deleting old task...
    schtasks /delete /tn "%TASK_NAME%" /f >nul
)

REM Create the scheduled task
schtasks /create ^
    /tn "%TASK_NAME%" ^
    /tr "\"%PYTHON_EXE%\" \"%SCRIPT_PATH%\"" ^
    /sc minute ^
    /mo 15 ^
    /ru "%USERDOMAIN%\%USERNAME%" ^
    /rl HIGHEST ^
    /f

if %errorLevel% equ 0 (
    echo.
    echo ============================================================
    echo SUCCESS! Task created successfully!
    echo ============================================================
    echo.
    echo Task Details:
    echo   Name:               %TASK_NAME%
    echo   Schedule:           Every 15 minutes
    echo   Run when logged off: YES
    echo.
    echo Management Commands:
    echo   View task:          schtasks /query /tn "%TASK_NAME%" /v /fo list
    echo   Run task now:       schtasks /run /tn "%TASK_NAME%"
    echo   Disable task:       schtasks /change /tn "%TASK_NAME%" /disable
    echo   Enable task:        schtasks /change /tn "%TASK_NAME%" /enable
    echo   Delete task:        schtasks /delete /tn "%TASK_NAME%" /f
    echo.
    echo View in GUI:
    echo   1. Press Win+R and type: taskschd.msc
    echo   2. Look for '%TASK_NAME%' in Task Scheduler Library
    echo.

    REM Ask to run the task now
    set /p RUNNOW="Run the task now to test? (Y/N): "
    if /i "%RUNNOW%"=="Y" (
        echo.
        echo Running task now...
        schtasks /run /tn "%TASK_NAME%"
        echo Task started! Check logs with: python webex_cdr_downloader.py --stats
    )
) else (
    echo.
    echo ============================================================
    echo ERROR: Failed to create scheduled task!
    echo ============================================================
    echo.
    echo Please check:
    echo   1. You are running as Administrator
    echo   2. Python is installed at: %PYTHON_EXE%
    echo   3. Script exists at: %SCRIPT_PATH%
)

echo.
pause
