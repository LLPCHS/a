@echo off
setlocal

rem ----------------------------------------
rem  مسیر فایل مبدا و پوشه مقصد را تنظیم کنید
rem ----------------------------------------
set "SOURCE=D:\P\AI\a\rm_dt.bat"
set "DEST=D:\P\AI\emojis"

rem ----------------------------------------
rem  بررسی وجود فایل مبدا
rem ----------------------------------------
if not exist "%SOURCE%" (
    echo File not found: %SOURCE%
    exit /b 1
)

rem ----------------------------------------
rem  در صورت عدم وجود پوشه مقصد، ایجاد می‌شود
rem ----------------------------------------
if not exist "%DEST%" (
    echo Not found destination folder: %DEST%
    mkdir "%DEST%"
    if errorlevel 1 (
        echo Error in create destination folder
        exit /b 1
    )
)

rem ----------------------------------------
rem  انتقال فایل (Cut & Paste)
rem ----------------------------------------
move /Y "%SOURCE%" "%DEST%\"
if errorlevel 1 (
    echo Error in transfer file
    exit /b 1
) else (
    echo File successfully transferred to: %DEST%
)

endlocal
