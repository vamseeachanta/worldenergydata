# Development

> Resources for contributors and developers working on WorldEnergyData
> Last Updated: 2025-07-24

## Overview

WorldEnergyData is built using modern Python development practices with AI-assisted development workflows. This section provides comprehensive guidance for contributors, developers, and maintainers working on the project.

## Development Environment

### Modern Python Tooling

WorldEnergyData uses cutting-edge Python tools for optimal developer experience:

- **[UV Package Manager](uv_usage.md)** - Fast, reliable Python package management
- **Python 3.9+** - Modern Python features and performance
- **pyproject.toml** - Standardized project configuration
- **pytest** - Comprehensive testing framework

### Development Workflow

```bash

# Set up development environment

uv venv
uv activate
uv install --dev

# Run tests

pytest

# Code quality checks

black .
isort .
ruff check .
mypy .
```

## Project Structure

### Core Architecture

```
worldenergydata/
├── src/                    # Source code

│   ├── bsee/              # BSEE data module

│   ├── analysis/          # Analysis functions

│   ├── economic/          # Economic evaluation

│   └── visualization/     # Plotting and charts

├── tests/                 # Test suite

├── docs/                  # Documentation

├── data/                  # Data files and configurations

└── scripts/               # Utility scripts

```

### Module Organization

- **Data Sources**: Separate modules for each data provider (BSEE, SODIR, wind, etc.)
- **Analysis**: Reusable analysis functions and methodologies
- **Economic**: Economic evaluation and financial modeling
- **Visualization**: Plotting and visualization utilities
- **Utils**: Common utilities and helper functions

## Contributing Guidelines

### Getting Started

1. **Fork the Repository** - Create your own fork on GitHub
2. **Set Up Environment** - Use UV to install dependencies
3. **Create Feature Branch** - Work on focused, atomic changes
4. **Write Tests** - Ensure comprehensive test coverage
5. **Submit Pull Request** - Follow the PR template and guidelines

### Code Standards

- **Code Style**: Black formatting, isort for imports
- **Linting**: Ruff for fast, comprehensive linting
- **Type Hints**: mypy for static type checking
- **Documentation**: Comprehensive docstrings and comments
- **Testing**: pytest with high coverage requirements

### Development Best Practices

- **Test-Driven Development**: Write tests before implementation
- **Single Responsibility**: Each function/class has one clear purpose
- **Documentation**: Keep docs updated with code changes
- **Performance**: Profile and optimize critical paths
- **Security**: Never commit API keys or sensitive data

## Testing Framework

### Test Organization

```
tests/
├── unit/                  # Unit tests for individual functions

├── integration/           # Integration tests for workflows

├── data/                  # Test data and fixtures

└── conftest.py           # Pytest configuration

```

### Testing Standards

- **Coverage**: Minimum 90% test coverage
- **Test Types**: Unit, integration, and end-to-end tests
- **Data Fixtures**: Reusable test data and mocks
- **Performance Tests**: Benchmarking critical functions
- **Quality Tests**: Data validation and accuracy tests

### Running Tests

```bash

# Run all tests

pytest

# Run with coverage

pytest --cov=worldenergydata --cov-report=html

# Run specific test categories

pytest tests/unit/
pytest tests/integration/

# Run performance benchmarks

pytest --benchmark-only
```

## AI-Assisted Development

### Agent OS Integration

WorldEnergyData uses Agent OS for structured, AI-assisted development:

- **Spec-Driven Development**: Detailed specifications before implementation
- **Task Breakdown**: Systematic task planning and execution
- **Quality Assurance**: AI-assisted code review and testing
- **Documentation**: Automated documentation generation and updates

### Development Workflow with AI

1. **Spec Creation**: Use Agent OS to create detailed feature specifications
2. **Task Planning**: Break down complex features into manageable tasks
3. **Implementation**: AI-assisted coding with human oversight
4. **Testing**: Automated test generation and validation
5. **Documentation**: Keep documentation synchronized with code changes

## Documentation Standards

### Documentation Types

- **API Documentation**: Comprehensive function and class documentation
- **User Guides**: Step-by-step instructions for end users
- **Developer Guides**: Technical implementation details
- **Examples**: Practical usage examples and tutorials

### Documentation Tools

- **Markdown**: Standard format for all documentation
- **Docstrings**: NumPy/Google style docstrings in code
- **Type Hints**: Complete type annotations for API clarity
- **Cross-References**: Extensive linking between related content

## Release Management

### Version Management

- **Semantic Versioning**: Major.Minor.Patch version scheme
- **bumpver**: Automated version bumping and tagging
- **Changelog**: Detailed change documentation
- **Release Notes**: User-focused release communications

### Release Process

1. **Feature Freeze**: Complete all planned features
2. **Testing**: Comprehensive test suite validation
3. **Documentation**: Update all relevant documentation
4. **Version Bump**: Update version numbers and tags
5. **Package Build**: Create distribution packages
6. **Publication**: Release to PyPI and GitHub

## Performance and Optimization

### Performance Monitoring

- **Profiling**: Regular performance profiling of critical functions
- **Benchmarking**: Automated performance regression testing
- **Memory Usage**: Monitor memory consumption and leaks
- **Scalability**: Test with large datasets and complex workflows

### Optimization Strategies

- **Pandas Optimization**: Efficient DataFrame operations
- **NumPy Integration**: Leverage NumPy for numerical computations
- **Caching**: Strategic caching of expensive operations
- **Parallel Processing**: Multi-threading and multiprocessing where appropriate

## Community and Support

### Communication Channels

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: Community questions and discussions
- **Pull Requests**: Code contributions and reviews
- **Documentation**: Comprehensive guides and examples

### Getting Help

- **Issue Templates**: Structured bug reports and feature requests
- **Contributing Guide**: Step-by-step contribution instructions
- **Code of Conduct**: Community standards and expectations
- **Security Policy**: Responsible disclosure of security issues

---

*Ready to contribute? Start with [UV Usage](uv_usage.md) to set up your development environment.*