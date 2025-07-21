# UV Package Management Guide

This guide explains how to use UV for package management, development, and deployment in the worldenergydata project.

## Table of Contents
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Development Workflow](#development-workflow)
- [Testing](#testing)
- [Building and Deployment](#building-and-deployment)
- [CI/CD Integration](#cicd-integration)
- [Troubleshooting](#troubleshooting)
- [Migration from pip/conda](#migration-from-pipconda)

## Quick Start

```bash
# Setup development environment
./scripts/uv_setup.sh         # Linux/Mac
./scripts/uv_migrate.bat       # Windows

# Install dependencies
uv sync --extra dev

# Run the application
uv run python -m worldenergydata

# Run tests
uv run pytest

# Add a new dependency
uv add requests
```

## Installation

### Install UV

**Linux/Mac:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows:**
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Alternative (using pip):**
```bash
pip install uv
```

### Setup Project Environment

**Automated Setup:**
```bash
# Linux/Mac
./scripts/uv_setup.sh

# Windows
./scripts/uv_migrate.bat
```

**Manual Setup:**
```bash
# Initialize UV project (if not done)
uv sync

# Install with development dependencies
uv sync --extra dev
```

## Development Workflow

### Common Commands

```bash
# Sync dependencies (like pip install -r requirements.txt)
uv sync

# Add new dependency
uv add pandas>=2.0.0

# Add development dependency
uv add --dev pytest

# Remove dependency
uv remove requests

# Update all dependencies
uv sync --upgrade

# Run Python scripts
uv run python script.py

# Run module
uv run python -m worldenergydata
```

### Using the Helper Script

The `scripts/uv_run.sh` script provides common development tasks:

```bash
# Setup environment
./scripts/uv_run.sh setup

# Run tests
./scripts/uv_run.sh test

# Format code
./scripts/uv_run.sh format

# Run linting
./scripts/uv_run.sh lint

# Clean cache
./scripts/uv_run.sh clean
```

### Virtual Environment Management

UV automatically manages virtual environments:

```bash
# UV creates and manages .venv automatically
uv sync

# Activate shell (optional, uv run handles this automatically)
uv shell

# Show environment info
uv info
```

## Testing

### Running Tests

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_example.py

# Run with verbose output
uv run pytest -v

# Run with coverage
uv run pytest --cov=worldenergydata

# Using helper script
./scripts/uv_run.sh test
./scripts/uv_run.sh test-verbose
```

### Test Configuration

Tests are configured in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
addopts = [
    "--strict-markers",
    "--disable-warnings",
]
```

## Building and Deployment

### Local Building

```bash
# Build package
uv build

# Test build locally
./scripts/uv_deploy.sh test-build
```

### Publishing

```bash
# Publish to TestPyPI (for testing)
export TESTPYPI_TOKEN="your-token"
./scripts/uv_deploy.sh publish-test

# Publish to PyPI (production)
export PYPI_TOKEN="your-token"
./scripts/uv_deploy.sh publish
```

### Build Configuration

Building is configured in `pyproject.toml`:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build]
packages = ["src/worldenergydata"]
```

## CI/CD Integration

### GitHub Actions

The project includes a complete CI/CD pipeline in `.github/workflows/ci.yml`:

- **Testing**: Multi-platform, multi-Python version testing
- **Linting**: Code quality checks
- **Building**: Package building
- **Publishing**: Automated publishing on tags

### Environment Variables

For CI/CD, set these secrets:

- `PYPI_TOKEN`: PyPI API token for publishing
- `TESTPYPI_TOKEN`: TestPyPI API token for testing

## Troubleshooting

### Common Issues

**UV not found after installation:**
```bash
# Add to PATH (Linux/Mac)
export PATH="$HOME/.cargo/bin:$PATH"

# Restart shell or source profile
source ~/.bashrc  # or ~/.zshrc
```

**Dependency conflicts:**
```bash
# Clear lock file and resync
rm uv.lock
uv sync
```

**Cache issues:**
```bash
# Clear UV cache
uv cache clean

# Or use helper script
./scripts/uv_run.sh clean
```

**Import errors:**
```bash
# Ensure package is installed in development mode
uv sync --extra dev

# Verify installation
uv run python -c "import worldenergydata"
```

### Performance Issues

UV is designed to be fast, but if you experience slowdowns:

```bash
# Use UV's faster resolver
uv sync --resolution=highest

# Parallel installation
uv sync --no-dev  # Install only production deps first
uv sync --extra dev  # Then add dev deps
```

## Migration from pip/conda

### From pip + requirements.txt

1. **Copy dependencies to pyproject.toml** (already done in this project)
2. **Remove requirements.txt** (keep for reference if needed)
3. **Update scripts** to use `uv run` instead of `python`

### From conda

1. **Export conda environment:**
   ```bash
   conda env export > environment.yml
   ```

2. **Convert to UV dependencies:**
   ```bash
   # Manual process - add packages to pyproject.toml
   # UV handles Python packages; system dependencies may need separate handling
   ```

3. **Test the migration:**
   ```bash
   uv sync --extra dev
   uv run pytest  # Ensure everything works
   ```

### Script Updates

**Old (pip):**
```bash
python script.py
pip install package
```

**New (uv):**
```bash
uv run python script.py
uv add package
```

## Advanced Usage

### Working with Multiple Python Versions

```bash
# Install specific Python version
uv python install 3.12

# Use specific Python version
uv run --python 3.12 python script.py

# Create environment with specific Python
uv venv --python 3.11 my-env
```

### Custom Package Sources

```toml
# In pyproject.toml
[tool.uv.sources]
my-package = { git = "https://github.com/user/repo.git" }
other-package = { path = "../local-package", editable = true }
```

### Workspace Management

For monorepo setups:

```toml
# In pyproject.toml
[tool.uv.workspace]
members = ["packages/*", "tools/*"]
```

## Integration with IDEs

### VS Code

Add to `.vscode/settings.json`:

```json
{
    "python.defaultInterpreterPath": ".venv/bin/python",
    "python.terminal.activateEnvironment": true
}
```

### PyCharm

1. Go to Settings → Project → Python Interpreter
2. Select "Add Interpreter" → "Existing environment"
3. Point to `.venv/bin/python` (or `.venv\Scripts\python.exe` on Windows)

## Best Practices

### Dependency Management

1. **Pin major versions** for stability:
   ```toml
   dependencies = [
       "pandas>=2.0.0,<3.0.0",
       "requests>=2.25.0,<3.0.0"
   ]
   ```

2. **Use extras for optional features:**
   ```toml
   [project.optional-dependencies]
   plotting = ["matplotlib>=3.7.0", "plotly>=5.17.0"]
   dev = ["pytest>=7.0.0", "black>=23.0"]
   ```

3. **Regular updates:**
   ```bash
   uv sync --upgrade  # Update all dependencies
   ```

### Development Workflow

1. **Always use `uv run`** for script execution
2. **Use helper scripts** for common tasks
3. **Keep pyproject.toml clean** and well-organized
4. **Test dependency changes** thoroughly

### Performance Tips

1. **Use UV's caching** (automatic)
2. **Parallel execution** with `uv run`
3. **Minimal extras** in production environments
4. **Lock file discipline** (commit `uv.lock`)

## Resources

- [UV Documentation](https://docs.astral.sh/uv/)
- [UV GitHub Repository](https://github.com/astral-sh/uv)
- [Python Packaging Guide](https://packaging.python.org/)
- [pyproject.toml Specification](https://peps.python.org/pep-0621/)

---

*This documentation is maintained alongside the codebase. For questions or improvements, please open an issue.*