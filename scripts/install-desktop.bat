@echo off
REM Aura IDE - install as a desktop application (Windows).
REM Builds the Electron app and creates a desktop shortcut.
setlocal
cd /d "%~dp0.."

set APPNAME=Aura IDE
set SHORTCUT="%USERPROFILE%\Desktop\Aura IDE.lnk"

if /I "%~1"=="--skip-build" goto build_done
echo [1/3] Building Electron app (vscode-win32-x64)...
call npm run gulp vscode-win32-x64
if errorlevel 1 exit /b 1
:build_done

if not exist "..\VSCode-win32-x64" (
  echo Ready build not found in ..\VSCode-win32-x64. Run without --skip-build. >&2
  exit /b 1
)

echo [2/3] Installing to %LOCALAPPDATA%\Programs\AuraIDE ...
if exist "%LOCALAPPDATA%\Programs\AuraIDE" rmdir /s /q "%LOCALAPPDATA%\Programs\AuraIDE"
xcopy /e /i /q "..\VSCode-win32-x64" "%LOCALAPPDATA%\Programs\AuraIDE" >nul

set EXE="%LOCALAPPDATA%\Programs\AuraIDE\Code.exe"
if not exist %EXE% (
  REM binary name may differ; pick the first .exe in the folder
  for /f %%f in ('dir /b "..\VSCode-win32-x64\*.exe"') do set EXE="%LOCALAPPDATA%\Programs\AuraIDE\%%f"
)

echo [3/3] Creating desktop shortcut ...
powershell -NoProfile -Command ^
  "$ws=New-Object -ComObject WScript.Shell; $s=$ws.CreateShortcut(%SHORTCUT%); $s.TargetPath=%EXE%; $s.WorkingDirectory=%LOCALAPPDATA%\Programs\AuraIDE; $s.Description='Aura IDE (VS Code fork with Aura API and AGGG plugins)'; $s.Save()"

echo Done. Shortcut created on Desktop. Update: see docs/desktop-app.md
endlocal
