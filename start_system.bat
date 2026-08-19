@echo off
title AutoIntel System Launcher
echo ==================================================
echo 🚗 Launching AI Vehicle Service & Insurance System
echo ==================================================

echo 📦 1. Starting Local MySQL Server Daemon...
start /B "MySQL Server" "C:\Program Files\MySQL\MySQL Server 9.7\bin\mysqld.exe" --datadir="y:\AI_Vehicle_Service_Repair_Insurance_Intelligence\database\mysql_data" --port=3306 --console

echo ⏳ Waiting for database to initialize (5 seconds)...
timeout /t 5 /nobreak >nul

echo 🐍 2. Starting Flask Web Application Server...
start "Flask App Server" python app.py

echo 🌐 3. Launching Web Browser...
timeout /t 2 /nobreak >nul
start http://127.0.0.1:5000

echo ==================================================
echo ✅ AutoIntel is running successfully!
echo Close this window to keep MySQL running in background.
echo ==================================================
pause
