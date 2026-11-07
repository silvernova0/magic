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
echo Environment configured
echo.

echo Training options (toggle if needed)...
REM Set to 0 to disable; 1 to enable
set "USE_IPEX=1"                REM Enable Intel IPEX optimize on XPU
set "GRADIENT_CHECKPOINTING=1"  REM Enable gradient checkpointing (lower memory, slower)
REM Hugging Face datasets cache directory (for on-disk tokenization cache)
set "HF_DATASETS_CACHE=%CD%\data\.hf_cache"
echo   USE_IPEX=%USE_IPEX%  GRADIENT_CHECKPOINTING=%GRADIENT_CHECKPOINTING%
echo   HF_DATASETS_CACHE=%HF_DATASETS_CACHE%
echo.

REM Optional: run data preparation with inventory/recent context before training
REM Toggle RUN_PREP to 1 and set file paths as needed
set "RUN_PREP=0"
set "INVENTORY_FILE=data\training\inventory.json"
set "RECENT_FILE=data\training\recent_decks.jsonl"
if "%RUN_PREP%"=="1" (
  echo Preparing training data with inventory/recent context...
  C:\Users\fuckthisshit\openvino_env\Scripts\python -u scripts\prepare-training-data.py --inventory "%INVENTORY_FILE%" --recent "%RECENT_FILE%"
  echo.
)

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
C:\Users\fuckthisshit\openvino_env\Scripts\python -u scripts\train-commander-model-manual.py
echo.

echo ============================================================
echo Training session ended
echo ============================================================
pause

