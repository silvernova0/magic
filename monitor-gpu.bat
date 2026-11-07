@echo off
echo ============================================================
echo GPU Memory Monitor (Intel Arc)
echo ============================================================
echo.
echo Monitoring Intel Arc GPU usage...
echo This shows GPU activity and approximate memory usage
echo.
echo Close window to stop monitoring
echo.
:loop
cls
echo ============================================================
echo GPU MONITOR - %date% %time%
echo ============================================================
echo.

REM Check if xpu-smi exists (Intel GPU monitoring tool)
where xpu-smi >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Using xpu-smi for detailed GPU info:
    echo.
    xpu-smi dump -d 0 -m 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18
) else (
    echo xpu-smi not found in PATH
    echo.
    echo Checking GPU processes via Task Manager:
    echo.
    powershell -Command "Get-Process | Where-Object {$_.ProcessName -like '*python*'} | Select-Object ProcessName, @{Name='GPU';Expression={$_.GPU}}, @{Name='GPU Memory (MB)';Expression={[math]::Round($_.PrivateMemorySize64 / 1MB, 2)}} | Format-Table -AutoSize"
)

echo.
echo ============================================================
echo Refreshing in 5 seconds... (Press Ctrl+C to stop)
timeout /t 5 /nobreak >nul
goto loop
