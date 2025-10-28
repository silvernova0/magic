@echo off
echo ============================================================
echo Commander AI Model Training - MANUAL LOOP (XPU Compatible)
echo ============================================================
echo.
echo Setting Visual Studio 2022 Build Tools environment...
set "VS2022INSTALLDIR=C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools"
set "VSINSTALLDIR=%VS2022INSTALLDIR%\"
echo.
echo Setting oneAPI environment variables...
call "C:\Program Files (x86)\Intel\oneAPI\setvars.bat" >nul 2>&1
echo ✓ Environment configured
echo.
echo Memory Management:
echo - Manual PyTorch training loop (no Trainer class)
echo - Direct XPU device control
echo - Checkpoints every 100 steps
echo - Aggressive garbage collection enabled
echo.
echo Starting training...
echo Expected time: 12-18 hours on Intel Arc B50 Pro
echo The script will save checkpoints every 100 steps
echo You can safely interrupt with Ctrl+C and resume later
echo.
echo TIP: Run monitor-memory.bat in another window to watch RAM usage
echo.
echo ============================================================
echo.
C:\Users\fuckthisshit\openvino_env\Scripts\python scripts\train-commander-model-manual.py
echo.
echo ============================================================
echo Training session ended
echo ============================================================
pause
