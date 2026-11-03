"""Read builder source as data, including code that must never execute."""

import ast
import importlib.util
from pathlib import Path
from textwrap import dedent

import pytest

# tests/unit/maintenance is three directory levels below the repository root.
SCRIPT = (
    Path(__file__).resolve().parents[3]
    / "scripts/maintenance/classify_report_inventory.py"
)


@pytest.fixture
def inventory():
    spec = importlib.util.spec_from_file_location("report_inventory_ast", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def literal_builder(tmp_path):
    path = tmp_path / "literal_builder.py"
    path.write_text(
        dedent(
            """\
            raise RuntimeError("builder source must not execute")

            def build_shared_assets():
                raise RuntimeError("shared builder must not execute")

            def build_reports():
                folder = REPORTS / "example"
                overview = folder / "index.html"
                asset = SITE_ASSETS / "chart.html"
                data = folder / "data.csv"
                rows = [("index.html", "Overview"), ("detail.html", "Detail")]
                pages = {"summary.html": "Summary", "appendix.html": "Appendix"}
                for name in ("first.html", "second.html"):
                    pass
                shutil.copy2(overview, PUBLIC / "index.html")
                shutil.copyfile(folder / "detail.html", PUBLIC / "detail.html")
                shutil.copy2(asset, PUBLIC / "chart.html")
                shutil.copyfile(data, PUBLIC / "data.csv")
                raise RuntimeError("report builder must not execute")

            def unused_helper():
                raise RuntimeError("unused helper must not execute")

            DOMAINS = {"example": build_reports}
            """
        ),
        encoding="utf-8",
    )
    return path


@pytest.fixture
def dynamic_builder(tmp_path):
    path = tmp_path / "dynamic_builder.py"
    path.write_text(
        dedent(
            """\
            raise RuntimeError("dynamic builder source must not execute")

            def dynamic_value():
                from pathlib import Path
                Path(__file__).with_suffix(".executed").write_text("executed")
                raise RuntimeError("dynamic table call must not execute")

            def build_dynamic():
                rows = [("literal.html", "Literal"), dynamic_value()]
                pages = {"dynamic.html": dynamic_value()}
                for name in ("literal.html", dynamic_value()):
                    pass
                safe = [("static.html", "Static")]
                shutil.copyfile(REPORTS / "static.html", PUBLIC / "static.html")
                raise RuntimeError("dynamic builder must not execute")

            DOMAINS = {"example": build_dynamic}
            """
        ),
        encoding="utf-8",
    )
    return path


def test_builder_helpers_parse_without_execution(inventory, literal_builder):
    original = literal_builder.read_bytes()
    for _ in ("first pass", "repeat pass"):
        functions = inventory.builder_functions(literal_builder)
        # Expectations are transcribed from literal_builder above, not inferred.
        assert set(functions) == {
            "build_shared_assets",
            "build_reports",
            "unused_helper",
        }
        assert all(isinstance(node, ast.FunctionDef) for node in functions.values())
        assert inventory.registered_builders(literal_builder) == {
            "build_reports",
            "build_shared_assets",
        }
        assert inventory.literal_tables(functions["build_reports"]) == [
            [("index.html", "Overview"), ("detail.html", "Detail")],
            {"summary.html": "Summary", "appendix.html": "Appendix"},
            ("first.html", "second.html"),
        ]
        assert inventory.direct_copy_sources(functions["build_reports"]) == [
            "reports/example/index.html",
            "reports/example/detail.html",
            "site_assets/chart.html",
        ]
        assert inventory.literal_tables(functions["unused_helper"]) == []
        assert inventory.direct_copy_sources(functions["unused_helper"]) == []
        assert literal_builder.read_bytes() == original


def test_dynamic_table_is_not_executed(inventory, dynamic_builder):
    original = dynamic_builder.read_bytes()
    marker = dynamic_builder.with_suffix(".executed")
    assert not marker.exists()
    for _ in ("first pass", "repeat pass"):
        functions = inventory.builder_functions(dynamic_builder)
        # Only the safe table is literal in dynamic_builder above.
        assert set(functions) == {"dynamic_value", "build_dynamic"}
        assert inventory.registered_builders(dynamic_builder) == {
            "build_dynamic",
            "build_shared_assets",
        }
        assert inventory.literal_tables(functions["build_dynamic"]) == [
            [("static.html", "Static")]
        ]
        assert inventory.direct_copy_sources(functions["build_dynamic"]) == [
            "reports/static.html"
        ]
        assert not marker.exists()
        assert dynamic_builder.read_bytes() == original
