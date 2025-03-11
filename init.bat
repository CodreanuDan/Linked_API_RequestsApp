@echo off
echo ==============================
echo INFO: Running init.bat...
echo ==============================

REM:: Clean pip cache
echo INFO: Cleaning pip cache...
pip cache purge

REM:: Get current dir path
set current_dir=%~dp0

REM:: Display dir path
echo Directory path: %current_dir%

REM:: Go to the directory where env_data.env is located
cd /d "%current_dir%api"

REM:: Check if env_data.env file exists
if not exist "env_data.env" (
    echo ERROR: No env_data.env file in the specified directory!
    pause
    exit /b
)

REM:: Check if PEXELS_API_KEY exists in env_data.env
findstr /R "^PEXELS_API_KEY=" env_data.env >nul
if %errorLevel% neq 0 (
    echo ERROR: PEXELS_API_KEY not found in env_data.env!
    pause
    exit /b
) else (
    echo INFO: PEXELS_API_KEY found!
)

REM:: Check if GEMINI_API_KEY exists in env_data.env
findstr /R "^GEMINI_API_KEY=" env_data.env >nul
if %errorLevel% neq 0 (
    echo ERROR: GEMINI_API_KEY not found in env_data.env!
    pause
    exit /b
) else (
    echo INFO: GEMINI_API_KEY found!
)

REM:: Check if OPENAI_API_KEY exists in env_data.env
findstr /R "^OPENAI_API_KEY=" env_data.env >nul
if %errorLevel% neq 0 (
    echo ERROR: OPENAI_API_KEY not found in env_data.env!
    pause
    exit /b
) else (
    echo INFO: OPENAI_API_KEY found!
)

echo ==============================
echo INFO: Finished...
exit /b
