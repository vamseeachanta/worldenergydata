"""Static consumer checks for the first incrementally typed common modules."""

import os
import runpy
import subprocess
import sys
from collections import UserDict
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
COMMON = REPO_ROOT / "packages/worldenergydata-core/src/worldenergydata/common"


def run_mypy(source: Path, cache_dir: Path) -> subprocess.CompletedProcess[str]:
    """Check a consumer and the selected implementations, using repository rules."""
    env = os.environ.copy()
    env["MYPYPATH"] = os.pathsep.join((str(REPO_ROOT / "src"), str(COMMON.parents[1])))
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "mypy",
            "--config-file",
            str(REPO_ROOT / "pyproject.toml"),
            "--explicit-package-bases",
            "--follow-imports=silent",
            "--ignore-missing-imports",
            "--show-error-codes",
            "--cache-dir",
            str(cache_dir),
            str(COMMON / "exceptions.py"),
            str(COMMON / "logging.py"),
            str(COMMON / "types.py"),
            str(source),
        ],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_typed_consumer_accepts_mutable_mapping(tmp_path: Path) -> None:
    """The logging base-class contract accepts MutableMapping, including UserDict.

    Source: Python 3.10 logging reference, LoggerAdapter.process; expected result
    is successful checking of the base-compatible call and nested error context.
    """
    consumer = tmp_path / "valid_consumer.py"
    consumer.write_text(
        "from collections import UserDict\n"
        "from collections.abc import MutableMapping\n"
        "from typing import Any\n"
        "from worldenergydata.common.exceptions import WorldEnergyDataError\n"
        "from worldenergydata.common.logging import get_logger\n"
        "from worldenergydata.common.types import DataResult, PaginatedResult\n"
        "kwargs: MutableMapping[str, Any] = UserDict()\n"
        "message: object = object()\n"
        "get_logger('example').process(message, kwargs)\n"
        "payload: dict[str, Any] = WorldEnergyDataError(\n"
        "    'missing', context={'fields': ['date']}\n"
        ").to_dict()\n"
        "result = DataResult([], metadata=payload)\n"
        "pages = PaginatedResult([], len([]), len([]), len([]), False, False)\n"
        "count: int = result.record_count\n"
        "page_count: int = pages.total_pages\n",
        encoding="utf-8",
    )
    checked = run_mypy(consumer, tmp_path / "mypy-cache")
    assert checked.returncode == 0, checked.stdout + checked.stderr


def test_documented_example() -> None:
    """Three synthetic rows split into two plus one require two pages.

    Independent calculation: north and south fill the first page, west fills
    another; record_count = 2 and total_pages = 2. The error's nested fields
    remain intact, and call context replaces the adapter's source key while
    retaining its task key (Python 3.10 logging reference, LoggerAdapter).
    """
    example = runpy.run_path(str(REPO_ROOT / "examples/typed_common.py"))
    rows = [{"region": "north"}, {"region": "south"}, {"region": "west"}]
    # Inputs and expected counts are derived in the independent calculation above.
    assert example["summarize"](rows, page_size=2) == {
        "record_count": 2,
        "total_pages": 2,
        "error": {
            "error": "WorldEnergyDataError",
            "code": "WED_ERROR",
            "message": "Missing date",
            "context": {"fields": ["date"]},
        },
        "context": {"source": "call", "task": "sample"},
    }


def test_adapter_preserves_mapping_and_message() -> None:
    """Preserve the caller's mapping and arbitrary message object when merging.

    Python 3.10 logging reference, LoggerAdapter.process: pass the message and
    keyword arguments onward. An object and a UserDict exercise that contract.
    """
    from worldenergydata.common.logging import get_logger

    message = object()
    kwargs = UserDict({"extra": {"source": "call"}})
    msg, processed = get_logger("example", context={"task": "sample"}).process(
        message, kwargs
    )
    assert msg is message
    assert processed is kwargs
    assert kwargs["extra"] == {"task": "sample", "source": "call"}


def test_type_aliases_without_pandas(monkeypatch: pytest.MonkeyPatch) -> None:
    """The existing optional-pandas contract must still allow record containers.

    Importing the standalone types module with pandas unavailable should retain
    its Any fallback and accept an empty record list, with no records or errors.
    """
    monkeypatch.setitem(sys.modules, "pandas", None)
    spec = spec_from_file_location("common_types_without_pandas", COMMON / "types.py")
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.DataFrame is Any
    assert module.Series is Any
    result = module.DataResult([])
    assert result.data == []
    assert not result.has_errors


@pytest.mark.parametrize(
    "statement",
    [
        "WorldEnergyDataError(message=[])",
        "get_logger(name=[])",
        "DataResult(data=[], success='yes')",
    ],
)
def test_typed_consumer_rejects_invalid_arguments(
    tmp_path: Path, statement: str
) -> None:
    """Each call violates a declared argument type, so mypy must reject it.

    Source: repository signatures for message/name (str) and success (bool);
    no expected value is computed by the implementations under test.
    """
    consumer = tmp_path / "invalid_consumer.py"
    consumer.write_text(
        "from worldenergydata.common.exceptions import WorldEnergyDataError\n"
        "from worldenergydata.common.logging import get_logger\n"
        "from worldenergydata.common.types import DataResult\n" + statement + "\n",
        encoding="utf-8",
    )
    checked = run_mypy(consumer, tmp_path / "mypy-cache")
    assert checked.returncode != 0
    errors = [line for line in checked.stdout.splitlines() if ": error:" in line]
    assert errors, checked.stdout + checked.stderr
    assert all(
        "invalid_consumer.py:" in line and "[arg-type]" in line for line in errors
    )
