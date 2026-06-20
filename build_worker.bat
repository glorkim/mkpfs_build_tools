@echo off
chcp 65001 >nul
echo --------------------------------------------------
echo  mkpfs-worker.exe build (standalone GPL-3.0 CLI)
echo --------------------------------------------------
echo.

if not exist "%~dp0mkpfs_worker_launcher.py" (
    echo  [ERROR] mkpfs_worker_launcher.py not found.
    exit /b 1
)

pip install pyinstaller mkpfs >nul 2>&1

echo  cleaning previous build...
if exist "%~dp0build" rmdir /s /q "%~dp0build"
if exist "%~dp0dist\mkpfs-worker.exe" del /f /q "%~dp0dist\mkpfs-worker.exe"

echo  building...
echo.

python -m PyInstaller --clean --noconfirm "%~dp0mkpfs-worker.spec"

if not exist "%~dp0dist\mkpfs-worker.exe" (
    echo.
    echo  [FAILED]
    exit /b 1
)

echo.
echo  [DONE] dist\mkpfs-worker.exe
echo.
echo  Deploy: place mkpfs-worker.exe next to the closed-source exe,
echo          or set MKPFS_WORKER_PATH to its full path.
echo.
