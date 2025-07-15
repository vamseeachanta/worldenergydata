#!/bin/bash
# UV Python Development Environment Setup Script

# # 1. Install UV
# curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Create virtual environment
echo "Creating environment..."
uv venv

echo "Installing dependencies from requirements.txt..."
if [ -f "scripts/requirements.txt" ]; then
    uv add -r scripts/requirements.txt
else
    echo "Warning: scripts/requirements.txt not found"
fi

# 3. Sync dependencies from pyproject.toml
echo "Syncing dependencies from pyproject.toml..."
uv sync

# 5. Add development dependencies
echo "Adding development dependencies..."
uv add --dev pytest ruff mypy

# 7. Run commands in the environment (examples)
uv run python --version
uv run pytest
uv run ruff check .

# 8. Install a specific Python version (example: 3.12)
# uv python install 3.12