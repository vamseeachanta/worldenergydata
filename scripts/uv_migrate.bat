@echo off
echo 🚀 uv Migration Helper for worldenergydata
echo ==================================================

echo Checking uv installation...
uv --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ uv is not installed. Please install it first:
    echo    pip install uv
    exit /b 1
)

echo ✅ uv is installed

echo.
echo 1. Adding dependencies from requirements.txt...
uv add -r scripts/requirements.txt

echo.
echo 2. Adding dev dependencies...
uv add --dev "black>=23.0" "bumpver>=2023.1129" "isort>=5.0.0" "pytest>=7.0.0"

echo.
echo 3. Syncing environment...
uv sync

echo.
echo ✅ Migration complete!
echo.
echo Next steps:
echo - Run 'uv sync' to install dependencies
echo - Run 'uv run python -m worldenergydata' to run your project
echo - Run 'uv add ^<package^>' to add new dependencies
echo - Run 'uv remove ^<package^>' to remove dependencies

pause
