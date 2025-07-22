#!/bin/bash
# UV Script Runner - Common development tasks with UV

set -e

show_help() {
    echo "UV Script Runner for worldenergydata"
    echo "Usage: $0 <command> [args...]"
    echo ""
    echo "Available commands:"
    echo "  setup         - Setup development environment"
    echo "  test          - Run tests"
    echo "  test-verbose  - Run tests with verbose output"
    echo "  lint          - Run linting (ruff)"
    echo "  format        - Format code (black + isort)"
    echo "  check         - Run all checks (lint + format check)"
    echo "  run           - Run main application"
    echo "  shell         - Start UV shell"
    echo "  sync          - Sync dependencies"
    echo "  add <pkg>     - Add new dependency"
    echo "  clean         - Clean cache and temporary files"
    echo ""
    echo "Examples:"
    echo "  $0 setup"
    echo "  $0 test"
    echo "  $0 add requests"
    echo "  $0 run --help"
}

case "${1:-help}" in
    setup)
        echo "🚀 Setting up development environment..."
        uv sync --extra dev
        echo "✅ Setup complete!"
        ;;
    test)
        echo "🧪 Running tests..."
        uv run pytest "${@:2}"
        ;;
    test-verbose)
        echo "🧪 Running tests (verbose)..."
        uv run pytest -v --tb=short "${@:2}"
        ;;
    lint)
        echo "🔍 Running linter..."
        uv run ruff check . "${@:2}"
        ;;
    format)
        echo "🎨 Formatting code..."
        uv run black .
        uv run isort .
        echo "✅ Code formatted!"
        ;;
    check)
        echo "🔍 Running all checks..."
        uv run ruff check .
        uv run black --check .
        uv run isort --check-only .
        echo "✅ All checks passed!"
        ;;
    run)
        echo "🚀 Running application..."
        uv run python -m worldenergydata "${@:2}"
        ;;
    shell)
        echo "🐚 Starting UV shell..."
        uv shell
        ;;
    sync)
        echo "📦 Syncing dependencies..."
        uv sync "${@:2}"
        ;;
    add)
        if [ -z "$2" ]; then
            echo "❌ Error: Package name required"
            echo "Usage: $0 add <package-name>"
            exit 1
        fi
        echo "📦 Adding package: $2"
        uv add "${@:2}"
        ;;
    clean)
        echo "🧹 Cleaning cache and temporary files..."
        find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
        find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
        find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
        find . -name "*.pyc" -delete 2>/dev/null || true
        echo "✅ Cleanup complete!"
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "❌ Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac