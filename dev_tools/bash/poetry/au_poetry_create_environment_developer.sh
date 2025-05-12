#!/bin/bash
# File: poetry_dev.sh
# Usage: ./poetry_dev.sh
# Description: Prompt to install local libraries and resolve Python version if needed

set -e

# Find the top-level directory of the git repo
TOPLEVEL=$(git rev-parse --show-toplevel 2>/dev/null || echo ".")
if [ "$TOPLEVEL" = "." ]; then
    echo "[ERROR] Not in a git repository. Please run this script from within your project."
    exit 1
fi

cd "$TOPLEVEL"
read -p "Enter the local library name (e.g., assetutilities): " LOCAL_LIB_NAME
read -p "Enter the local library path (relative, e.g., ../assetutilities): " LOCAL_LIB_PATH
PYPROJECT="$TOPLEVEL/pyproject.toml"

if [ ! -d "$LOCAL_LIB_PATH" ]; then
    echo "[ERROR] Local library path '$LOCAL_LIB_PATH' does not exist."
    exit 1
fi

if [ -f "$PYPROJECT" ]; then
    echo "[INFO] Found pyproject.toml in the repo. Validating..."
else
    echo "[INFO] No pyproject.toml found. Initializing poetry project..."
    poetry init
fi

# Check if dependency already exists
if grep -q "$LOCAL_LIB_NAME" "$PYPROJECT"; then
    echo "[INFO] '$LOCAL_LIB_NAME' already declared in pyproject.toml. Skipping add."
else
    echo "[INFO] Adding local library '$LOCAL_LIB_NAME' to $PYPROJECT..."

    if grep -q "\[tool.poetry.dependencies\]" "$PYPROJECT"; then
        # Append to existing dependencies block
        sed -i "/\[tool.poetry.dependencies\]/a $LOCAL_LIB_NAME = { path = \"$LOCAL_LIB_PATH\", develop = true }" "$PYPROJECT"
    else
        # Create new dependencies block
        echo -e "\n[tool.poetry.dependencies]\n$LOCAL_LIB_NAME = { path = \"$LOCAL_LIB_PATH\", develop = true }" >> "$PYPROJECT"
    fi
fi

# Run poetry lock first to sync lock file with updated pyproject.toml
echo "[INFO] Locking updated dependencies..."
poetry lock

if ! poetry install; then
    echo "[ERROR] poetry install failed with exit code $?. Please check the error message above."
    echo "[INFO] ensure you have the correct Python version installed and all dependencies are available in pyproject.toml."
    exit 1
else
    echo "[INFO] poetry install completed successfully."
fi