@echo off
echo 🚀 UV Setup for worldenergydata
echo ================================

echo Checking uv installation...
uv --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ uv is not installed. Installing uv...
    powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
    if %errorlevel% neq 0 (
        echo ❌ Failed to install uv automatically. Please install manually.
        echo Visit: https://docs.astral.sh/uv/getting-started/installation/
        pause
        exit /b 1
    )
)

echo ✅ uv is installed

echo.
echo 📦 Syncing dependencies from pyproject.toml...
uv sync

echo.
echo 🔧 Installing development dependencies...
uv sync --extra dev

echo.
echo 🧪 Verifying installation...
uv run python --version
uv run python -c "import worldenergydata; print('✅ worldenergydata imported successfully')" 2>nul
if %errorlevel% neq 0 (
    echo ⚠️  Package import test failed, but setup is complete
)

echo.
echo ✅ Setup complete! Available commands:
echo   uv run python -m worldenergydata    # Run main application
echo   uv run pytest                       # Run tests
echo   uv run ruff check .                 # Lint code
echo   uv run black .                      # Format code
echo   uv add ^<package^>                  # Add new dependency
echo   uv sync                             # Update dependencies
echo.
echo 🎉 Development environment is ready!

pause
