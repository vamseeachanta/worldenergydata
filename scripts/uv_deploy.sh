#!/bin/bash
# UV Package Deployment Script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

show_help() {
    echo "UV Deployment Script for worldenergydata"
    echo "Usage: $0 <command>"
    echo ""
    echo "Commands:"
    echo "  build         - Build the package"
    echo "  test-build    - Build and test the package locally"
    echo "  publish-test  - Publish to TestPyPI"
    echo "  publish       - Publish to PyPI (production)"
    echo "  clean         - Clean build artifacts"
    echo ""
    echo "Environment variables:"
    echo "  PYPI_TOKEN    - PyPI API token for publishing"
    echo "  TESTPYPI_TOKEN - TestPyPI API token for testing"
}

clean_build() {
    echo "🧹 Cleaning build artifacts..."
    rm -rf "$PROJECT_DIR/dist/"
    rm -rf "$PROJECT_DIR/build/"
    rm -rf "$PROJECT_DIR"/*.egg-info/
    echo "✅ Clean complete!"
}

build_package() {
    echo "📦 Building package..."
    cd "$PROJECT_DIR"
    
    # Ensure dependencies are up to date
    uv sync --extra build
    
    # Build the package
    uv build
    
    echo "✅ Build complete!"
    echo "📄 Build artifacts:"
    ls -la dist/
}

test_build() {
    echo "🧪 Testing build locally..."
    
    # Clean and build
    clean_build
    build_package
    
    # Test installation in temporary environment
    echo "🔍 Testing package installation..."
    TEMP_DIR=$(mktemp -d)
    cd "$TEMP_DIR"
    
    # Test wheel installation
    uv venv test-env
    source test-env/bin/activate || source test-env/Scripts/activate
    
    pip install "$PROJECT_DIR"/dist/*.whl
    
    # Test import
    python -c "import worldenergydata; print('✅ Package imported successfully')"
    
    # Cleanup
    deactivate
    cd "$PROJECT_DIR"
    rm -rf "$TEMP_DIR"
    
    echo "✅ Local build test passed!"
}

publish_test() {
    if [ -z "$TESTPYPI_TOKEN" ]; then
        echo "❌ Error: TESTPYPI_TOKEN environment variable not set"
        echo "Get a token from: https://test.pypi.org/manage/account/token/"
        exit 1
    fi
    
    echo "🚀 Publishing to TestPyPI..."
    
    # Build package
    clean_build
    build_package
    
    # Upload to TestPyPI
    uv run twine upload --repository testpypi dist/* \
        --username __token__ \
        --password "$TESTPYPI_TOKEN"
    
    echo "✅ Published to TestPyPI!"
    echo "🔗 View at: https://test.pypi.org/project/worldenergydata/"
}

publish_production() {
    if [ -z "$PYPI_TOKEN" ]; then
        echo "❌ Error: PYPI_TOKEN environment variable not set"
        echo "Get a token from: https://pypi.org/manage/account/token/"
        exit 1
    fi
    
    echo "⚠️  WARNING: This will publish to PRODUCTION PyPI!"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Cancelled"
        exit 1
    fi
    
    echo "🚀 Publishing to PyPI..."
    
    # Build package
    clean_build
    build_package
    
    # Upload to PyPI
    uv run twine upload dist/* \
        --username __token__ \
        --password "$PYPI_TOKEN"
    
    echo "✅ Published to PyPI!"
    echo "🔗 View at: https://pypi.org/project/worldenergydata/"
}

case "${1:-help}" in
    build)
        build_package
        ;;
    test-build)
        test_build
        ;;
    publish-test)
        publish_test
        ;;
    publish)
        publish_production
        ;;
    clean)
        clean_build
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