@echo off
setlocal EnableDelayedExpansion
title GastroCare AI - Download Offline Packages
mode con: cols=78 lines=40
color 0B
set "BASEDIR=%~dp0"
if "%BASEDIR:~-1%"=="\" set "BASEDIR=%BASEDIR:~0,-1%"
set "OFFLINE_DIR=%BASEDIR%\offline_packages"
set "VENV_DIR=%BASEDIR%\venv"
set "LOGS_DIR=%BASEDIR%\logs"
if not exist "%LOGS_DIR%" mkdir "%LOGS_DIR%"
if not exist "%OFFLINE_DIR%" mkdir "%OFFLINE_DIR%"
set "LOGFILE=%LOGS_DIR%\offline_%DATE:~-4,4%%DATE:~-7,2%%DATE:~-10,2%.log"
cls
echo.
echo  ================================================================
echo   GastroCare AI  -  OFFLINE PACKAGE DOWNLOADER
echo  ================================================================
echo  Run once while online. GastroCare AI then works offline forever.
echo  ================================================================
echo.
ping -n 1 -w 3000 8.8.8.8 >nul 2>&1
if %errorlevel% neq 0 (echo   [FAIL]  No internet. Connect and try again. & pause & exit /b 1)
echo   [ OK ]  Internet connected.
echo.
set "PIP="
if exist "%VENV_DIR%\Scripts\pip.exe" (set "PIP=%VENV_DIR%\Scripts\pip.exe" & echo   [ OK ]  Using venv pip.) else (pip --version >nul 2>&1 && (set "PIP=pip" & echo   [ OK ]  Using system pip.) || (echo   [FAIL]  pip not found. Run START_GastroCare_AI.bat first. & pause & exit /b 1))
echo.
%PIP% install --upgrade pip --quiet >> "%LOGFILE%" 2>&1
echo  Downloading packages (3-8 minutes)...
set /a DONE=0
for %%K in (flask flask-cors requests Pillow PyMuPDF anthropic numpy python-docx colorama psutil) do (
    set /a DONE+=1
    echo   [!DONE!/10]  Downloading: %%K
    %PIP% download %%K --dest="%OFFLINE_DIR%" --quiet >> "%LOGFILE%" 2>&1
    if !errorlevel!==0 (echo              [ OK ]) else (echo              [WARN] check log)
)
set /a WHLCOUNT=0
for %%W in ("%OFFLINE_DIR%\*.whl") do set /a WHLCOUNT+=1
echo.
echo   [ OK ]  %WHLCOUNT% packages cached.
(echo GastroCare AI Offline Cache & echo Downloaded: %DATE% %TIME% & echo Total: %WHLCOUNT% files) > "%OFFLINE_DIR%\MANIFEST.txt"
echo.
echo  ================================================================
echo   DOWNLOAD COMPLETE. GastroCare AI now works WITHOUT internet.
echo   Just run START_GastroCare_AI.bat normally.
echo  ================================================================
echo.
pause
