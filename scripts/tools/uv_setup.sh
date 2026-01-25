#!/bin/bash
# UV Python Development Environment Setup Script for worldenergydata

set -e  # Exit on any error

echo "🚀 Setting up worldenergydata development environment with UV..."
echo "================================================================"

# 1. Check if UV is installed
if ! command -v uv &> /dev/null; then
    echo "❌ UV is not installed. Installing UV..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Source the shell configuration to make uv available
    export PATH="$HOME/.cargo/bin:$PATH"
fi

echo "✅ UV version: $(uv --version)"

# 2. Sync dependencies from pyproject.toml (creates venv automatically)
echo "📦 Syncing dependencies from pyproject.toml..."
uv sync

# 3. Install development dependencies 
echo "🔧 Installing development dependencies..."
uv sync --extra dev

# 4. Verify installation
echo "🧪 Verifying installation..."
uv run python --version
uv run python -c "import worldenergydata; print('✅ worldenergydata package imported successfully')"

# 5. Run quick tests to verify everything works
echo "🔍 Running quick verification..."
if [ -f "tests/" ]; then
    echo "Running basic tests..."
    uv run pytest tests/ -x -v --tb=short || echo "⚠️ Some tests failed, but setup is complete"
fi

# 6. Show available commands
echo "✅ Setup complete! Available commands:"
echo "  uv run python -m worldenergydata      # Run main application"
echo "  uv run pytest                         # Run tests"  
echo "  uv run ruff check .                   # Lint code"
echo "  uv run black .                        # Format code"
echo "  uv add <package>                      # Add new dependency"
echo "  uv sync                               # Update dependencies"
echo ""
echo "🎉 Development environment is ready!"