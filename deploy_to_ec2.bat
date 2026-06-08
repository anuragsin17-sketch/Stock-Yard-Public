@echo off
REM Deploy Angel API to EC2

echo.
echo ========================================
echo Angel One API - EC2 Deployment
echo ========================================
echo.

setlocal enabledelayedexpansion

REM Check if key file exists
if not exist "stock-yard-key.pem" (
    echo ERROR: stock-yard-key.pem not found
    echo Please make sure you're in the correct directory
    exit /b 1
)

REM Check if angel-api.service exists
if not exist "angel-api.service" (
    echo ERROR: angel-api.service not found
    echo Please create it first
    exit /b 1
)

REM Check if angel_order_handler.py exists
if not exist "angel_order_handler.py" (
    echo ERROR: angel_order_handler.py not found
    exit /b 1
)

echo Step 1: Pull latest code from GitHub
echo.
echo Run this on EC2:
echo   cd /home/ubuntu ^&^& git pull origin main
echo.

echo Step 2: Copy service file
echo.
echo Run this on EC2:
echo   sudo cp /home/ubuntu/angel-api.service /etc/systemd/system/
echo   sudo chmod 644 /etc/systemd/system/angel-api.service
echo.

echo Step 3: Reload and start service
echo.
echo Run this on EC2:
echo   sudo systemctl daemon-reload
echo   sudo systemctl enable angel-api
echo   sudo systemctl start angel-api
echo   sleep 2
echo   sudo systemctl status angel-api
echo.

echo Step 4: Test health endpoint
echo.
echo Run this on EC2:
echo   curl http://localhost:5000/health
echo.

echo Step 5: Test from your PC
echo.
echo Run this on YOUR PC:
echo   curl http://32.194.58.75:5000/health
echo.

echo ========================================
echo.
echo SSH into EC2:
echo   ssh -i stock-yard-key.pem ubuntu@32.194.58.75
echo.
echo Then copy-paste the commands above one by one.
echo.

pause
