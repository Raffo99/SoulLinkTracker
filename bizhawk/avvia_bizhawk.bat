@echo off
chcp 65001 >NUL
cd /d "%~dp0"
rem ================================================================
rem  Avvia BizHawk con lo script Soul Link gia' caricato.
rem  Il percorso di BizHawk si imposta in config.lua (riga bizhawk = ...)
rem ================================================================
set "BIZHAWK="
for /f tokens^=2^ delims^=^" %%a in ('findstr /r /c:"^ *bizhawk *=" config.lua') do set "BIZHAWK=%%a"
if not defined BIZHAWK set "BIZHAWK=C:\BizHawk\EmuHawk.exe"
set "BIZHAWK=%BIZHAWK:/=\%"

if not exist "%BIZHAWK%" (
  echo Non trovo BizHawk in: %BIZHAWK%
  echo Apri config.lua con il Blocco note e correggi la riga bizhawk = "...".
  pause
  exit /b
)

rem ROM da aprire: la piu' recente del Soul Link, altrimenti l'originale
rem (lo script poi genera/carica da solo quella giusta per la run attuale)
set "ROM="
for /f "delims=" %%f in ('dir /b /o-d "..\rom_randomizzate\SoulLink_*.nds" 2^>NUL') do if not defined ROM set "ROM=%~dp0..\rom_randomizzate\%%f"
if not defined ROM set "ROM=%~dp0..\rom\Nero2.nds"

rem --url_get/--url_post attivano le richieste HTTP degli script Lua (l'indirizzo vero e' in config.lua)
start "" "%BIZHAWK%" --url_get=http://localhost/ --url_post=http://localhost/ --lua="%~dp0soullink.lua" "%ROM%"
