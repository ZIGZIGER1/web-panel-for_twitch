@echo off
cd /d "%~dp0"
if exist "%SystemRoot%\System32\wscript.exe" (
  "%SystemRoot%\System32\wscript.exe" //nologo "%~dp0launch_mopsyan_silent.vbs"
) else (
  py mopsyan_sysan.py
)
