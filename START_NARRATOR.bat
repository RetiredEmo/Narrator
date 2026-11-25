@echo off
setlocal
title Narrator - AI Influence 7.0
cd /d "%~dp0"

echo.
echo   Narrator for AI Influence 7.0
echo   -----------------------------
echo   Reads the actions aloud in the narrator's voice and the dialogue in
echo   each character's own, using the mod's own direction for every line.
echo.
echo   Remember: AI Influence's own TTS must be OFF, or every line is read twice.
echo   The Player2 app must be running.
echo.

rem --- Find Python: the "py" launcher first, then python on PATH ---
set "PY="
where py >nul 2>&1 && set "PY=py -3"
if not defined PY (
    where python >nul 2>&1 && set "PY=python"
)
if not defined PY goto nopython

rem The Microsoft Store stub answers to "python" but is not Python.
%PY% -c "import sys" >nul 2>&1 || goto nopython

%PY% -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"
if errorlevel 1 (
    echo   Your Python is too old. Install Python 3.10 or newer from
    echo   https://www.python.org/downloads/ and start this again.
    echo.
    pause
    exit /b 1
)

rem --- Install what the narrator needs, the first time only ---
%PY% -c "import requests, flask, pystray, PIL" >nul 2>&1
if errorlevel 1 (
    echo   First start: installing the parts the narrator needs ^(one time^)...
    echo.
    %PY% -m pip install --user --disable-pip-version-check -r "%~dp0requirements.txt"
    if errorlevel 1 (
        echo.
        echo   The install failed. Check your internet connection, then run
        echo   this again. To do it by hand, open a command prompt here and run:
        echo       %PY% -m pip install -r requirements.txt
        echo.
        pause
        exit /b 1
    )
    echo.
)

%PY% "%~dp0NARRATOR.py"

echo.
echo   The narrator has stopped.
pause
exit /b 0

:nopython
echo   Python was not found. Install Python 3.10 or newer from
echo   https://www.python.org/downloads/ and tick "Add python.exe to PATH"
echo   during setup, then start this again.
echo.
pause
exit /b 1
