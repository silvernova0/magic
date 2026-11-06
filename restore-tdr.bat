@echo off
echo ============================================================
echo Intel Arc GPU - Restore TDR (Timeout Detection and Recovery)
echo ============================================================
echo.
echo This will restore Windows' default GPU timeout detection.
echo.
echo WARNING: This requires Administrator privileges
echo.
pause

echo.
echo Restoring default TDR values...
echo.

REM Restore default TDR values (3 = default level)
reg add "HKEY_LOCAL_MACHINE\System\CurrentControlSet\Control\GraphicsDrivers" /v "TdrLevel" /t REG_DWORD /d 3 /f
reg add "HKEY_LOCAL_MACHINE\System\CurrentControlSet\Control\GraphicsDrivers" /v "TdrDelay" /t REG_DWORD /d 2 /f
reg add "HKEY_LOCAL_MACHINE\System\CurrentControlSet\Control\GraphicsDrivers" /v "TdrDdiDelay" /t REG_DWORD /d 5 /f

echo.
echo ============================================================
echo TDR has been restored to default settings
echo ============================================================
echo.
echo YOU MUST RESTART YOUR COMPUTER for changes to take effect
echo ============================================================
pause
