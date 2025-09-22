@echo off
rem ----------------------------------------
rem     حذف فایل
rem ----------------------------------------
del /F /Q "C:\Program Files\ITM\data.db"
if errorlevel 1 (
  echo error for delete file
  pause
  exit /b 1
)

rem ----------------------------------------
rem     ریستارت کردن ویندوز
rem ----------------------------------------
shutdown /r /t 0 /f
