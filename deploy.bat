@echo off
REM Deploy Angel API to EC2

echo Finding SSH key...
set "keyPath=%USERPROFILE%\.ssh\stock-yard-key.pem"

if not exist "%keyPath%" (
    echo SSH key not found at: %keyPath%
    echo Looking for alternative paths...
    for %%F in (
        "%USERPROFILE%\.ssh\id_rsa"
        "%USERPROFILE%\.ssh\aws.pem"
        "C:\Users\%USERNAME%\.ssh\stock-yard-key.pem"
    ) do (
        if exist "%%F" (
            set "keyPath=%%F"
            echo Found key at: %%F
            goto found_key
        )
    )
    echo ERROR: SSH key not found!
    exit /b 1
)

:found_key
echo Using SSH key: %keyPath%

REM Fix SSH key permissions
echo Fixing SSH key permissions...
icacls "%keyPath%" /inheritance:r
icacls "%keyPath%" /grant:r "%USERNAME%:F"

echo Testing SSH connection...
ssh -i "%keyPath%" -o StrictHostKeyChecking=no -o ConnectTimeout=5 ubuntu@32.194.58.75 "echo SSH OK"

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: SSH connection failed
    exit /b 1
)

echo.
echo Deploying to EC2...
ssh -i "%keyPath%" -o StrictHostKeyChecking=no ubuntu@32.194.58.75 ^
    "sudo systemctl stop angel-api; sleep 1; sudo systemctl restart angel-api; sleep 2; sudo systemctl status angel-api; echo ''; sudo journalctl -u angel-api -n 15 --no-pager"

echo.
echo Deployment complete!
echo Testing health endpoint...
timeout /t 2 /nobreak

curl http://32.194.58.75:5000/health

echo.
echo Next: Run: python test_order_placement.py
