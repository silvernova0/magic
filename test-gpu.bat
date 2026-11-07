@echo off
echo Setting Visual Studio 2022 Build Tools environment...
set "VS2022INSTALLDIR=C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools"
set "VSINSTALLDIR=%VS2022INSTALLDIR%\"
echo.
echo Setting oneAPI environment variables...
call "C:\Program Files (x86)\Intel\oneAPI\setvars.bat"
echo.
echo Running GPU detection test...
C:\Users\fuckthisshit\openvino_env\Scripts\python scripts\test-gpu.py
pause
