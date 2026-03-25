# assetutilities API Contracts — worldenergydata

## Policy

- **stable**: No breaking changes without an assetutilities major version bump.
- **provisional**: Best-effort stability; consumers should guard with `try/except ImportError`.

## Installation Note

assetutilities is installed in this repo via git URL (see `pyproject.toml`).
The installed version may differ from the local submodule HEAD.
Always verify `importlib.metadata.version("assetutilities")` in test output to confirm
which version is under test. When the git-URL ref is updated, re-run contract tests
before merging.

## Contracted Symbols

| Module path | Symbol | Stability | Notes |
|---|---|---|---|
| `assetutilities.common.data` | `SaveData` | stable | Core persistence class; must remain callable |
| `assetutilities.common.data` | `ReadData` | stable | Core read class; must remain callable |
| `assetutilities.common.data` | `AttributeDict` | stable | Dict subclass with attribute access; `d.key` and `d["key"]` both required |
| `assetutilities.common.data` | `Transform` | stable | Data transformation class; must remain callable |
| `assetutilities.engine` | `engine` | stable | Top-level engine object; must not be None after import |
| `assetutilities.common.file_management` | `FileManagement` | stable | File utility class; must remain callable |
| `assetutilities.common.yml_utilities` | `WorkingWithYAML` | stable | YAML read/write facade; must remain callable |

## Running Contracts

```bash
cd worldenergydata
PYTHONPATH="src:../assetutilities/src" uv run python -m pytest tests/contracts/ -v --tb=short -m contracts
```

## Violation Reporting

When a contract test fails, the failure output is prefixed:

```
[CONTRACT VIOLATION] symbol=<test_name> au_version=<version>
```

This identifies the broken symbol and the assetutilities version that introduced the regression.
File a bug against assetutilities and add an entry to `specs/wrk/` before upgrading.
