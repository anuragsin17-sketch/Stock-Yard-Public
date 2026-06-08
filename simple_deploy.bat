@echo off
REM Simple deployment script for Windows
REM Uses WSL to deploy to EC2

echo Checking for WSL...
wsl --list --quiet >nul 2>&1

if %errorlevel% neq 0 (
    echo ERROR: WSL not installed
    echo Please install WSL2 from Microsoft Store first
    pause
    exit /b 1
)

echo Running deployment via WSL...
wsl bash -c "cd /mnt/d/'Stock Yard' && ssh -i stock-yard-key.pem ubuntu@32.194.58.75 'cd /home/ubuntu && git pull && bash deploy_via_git.sh'"

if %errorlevel% equ 0 (
    echo.
    echo ✅ Deployment complete!
    echo.
    echo Next: Click Confirm Trade in Telegram to test
) else (
    echo.
    echo ❌ Deployment failed
)

pause
