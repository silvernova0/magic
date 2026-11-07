@echo off
echo ============================================================
echo Intel Arc GPU - Disable TDR (Timeout Detection and Recovery)
echo ============================================================
echo.
echo This will disable Windows' GPU timeout detection to prevent
echo the driver from crashing during long ML training operations.
echo.
echo WARNING: This requires Administrator privileges
echo.
pause

echo.
echo Creating registry backup...
reg export "HKEY_LOCAL_MACHINE\System\CurrentControlSet\Control\GraphicsDrivers" "%USERPROFILE%\Desktop\GraphicsDrivers_backup.reg"

echo.
echo Setting TDR timeout values...
echo.

REM Disable TDR completely (0 = disabled)
reg add "HKEY_LOCAL_MACHINE\System\CurrentControlSet\Control\GraphicsDrivers" /v "TdrLevel" /t REG_DWORD /d 0 /f
reg add "HKEY_LOCAL_MACHINE\System\CurrentControlSet\Control\GraphicsDrivers" /v "TdrDelay" /t REG_DWORD /d 60 /f
reg add "HKEY_LOCAL_MACHINE\System\CurrentControlSet\Control\GraphicsDrivers" /v "TdrDdiDelay" /t REG_DWORD /d 60 /f

echo.
echo ============================================================
echo TDR has been disabled
echo ============================================================
echo.
echo A backup was saved to: %USERPROFILE%\Desktop\GraphicsDrivers_backup.reg
echo.
echo YOU MUST RESTART YOUR COMPUTER for changes to take effect
echo.
echo To re-enable TDR later, run: restore-tdr.bat
echo ============================================================
pause
