"""Preparation preserves live inputs; all observations below are synthetic."""

import hashlib
import json
import shutil
from datetime import date
from pathlib import Path

import pytest

from worldenergydata.cost import monthly_refresh as api
from worldenergydata.cost import project_field_crosswalk as crosswalk
from worldenergydata.cost.timeseries import dataset as ds
from worldenergydata.cost.timeseries.reference_series import FRED_PAGE, REFERENCE_SERIES

ROOT = Path(__file__).resolve().parents[3]
CURATED = Path("data/modules/cost/curated")
INDEX = CURATED / "cost_component_timeseries.csv"
TODAY = date(2026, 11, 13)


def snapshot(root):
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in root.rglob("*")
        if p.is_file()
    }


def fetch(series):
    return [
        (date(y, m, 1), 100.0 + y - 1998 + m / 100)
        for y in range(1998, 2027)
        for m in range(1, 13)
        if date(y, m, 1) <= date(2026, 9, 1)
    ]


@pytest.fixture
def source(tmp_path):
    root = tmp_path / "source"
    shutil.copytree(ROOT / crosswalk.COST, root / crosswalk.COST)
    for path in (crosswalk.CATALOG, crosswalk.FIELD_IDENTITIES):
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / path, root / path)
    urls = {FRED_PAGE.format(series_id=s.series_id) for s in REFERENCE_SERIES}
    ds.write_timeseries_csv(
        [r for r in ds.read_timeseries_csv(root / INDEX) if r.source_url not in urls],
        root / INDEX,
    )
    return root


def test_prepares_five_products_without_publication(source, tmp_path):
    before, stage = snapshot(source), tmp_path / "stage"
    receipt = api.prepare(source, stage, fetch, TODAY, source_revision="example")
    assert receipt == json.loads((stage / "refresh-prepared.json").read_text())
    assert receipt["disposition"] == "PREPARED" and receipt["promoted"] is False
    assert receipt["source_revision"] == "example" and receipt["inputs"]
    assert len(receipt["products"]) == 5
    for path, digest in receipt["products"].items():
        assert hashlib.sha256((stage / path).read_bytes()).hexdigest() == digest
    assert not api.reference.check_freshness(stage / INDEX, TODAY)
    assert crosswalk.validate_repository(stage)["accounted_for"] > 0
    assert snapshot(source) == before


@pytest.mark.parametrize(
    "target",
    (
        "reference.refresh escalation.main crosswalk.validate_repository "
        "outturn_check.main reference.check_freshness"
    ).split(),
)
def test_stage_failure(source, tmp_path, monkeypatch, target):
    component, function = target.split(".")
    module = getattr(api, component)
    original, calls = getattr(module, function), []

    def fail(*args, **kwargs):
        calls.append(True)
        if len(calls) < (2 if component == "crosswalk" else 1):
            return original(*args, **kwargs)
        if function == "main":
            return 2
        if function == "check_freshness":
            return ["injected stale data"]
        raise ValueError("injected stage failure")

    monkeypatch.setattr(module, function, fail)
    before, stage = snapshot(source), tmp_path / "stage"
    with pytest.raises(ValueError, match="injected|failed"):
        api.prepare(source, stage, fetch, TODAY)
    assert snapshot(source) == before
    assert not (stage / "refresh-prepared.json").exists()


@pytest.mark.parametrize(
    "change",
    ("label crosswalk catalog identities added removed research concurrent").split(),
)
def test_changed_stage_inputs_require_review(source, tmp_path, monkeypatch, change):
    original = api.escalation.main

    def tamper(argv):
        result = original(argv)
        stage = Path(argv[argv.index("--output") + 1]).parents[4]
        path = stage / CURATED / "sanctioned_projects_2026.csv"
        if change == "label":
            label = crosswalk.read_csv(path)[1][0]["PROJECT"]
            path.write_text(path.read_text().replace(label, label + " changed"))
        elif change == "research":
            path = stage / INDEX
            rows = ds.read_timeseries_csv(path)
            row = next(r for r in rows if "fred.stlouisfed.org" not in r.source_url)
            rows[rows.index(row)] = row.model_copy(
                update={"notes": "changed provenance"}
            )
            ds.write_timeseries_csv(rows, path)
        elif change == "removed":
            path.unlink()
        elif change == "added":
            (stage / CURATED / "extra.csv").write_text("PROJECT\nExample\n")
        else:
            path = (source if change == "concurrent" else stage) / getattr(
                crosswalk, "CATALOG" if change == "concurrent" else change.upper()
            )
            path.write_bytes(path.read_bytes() + b"\n")
            if change == "concurrent":
                before.update(snapshot(source))
        return result

    monkeypatch.setattr(api.escalation, "main", tamper)
    before, stage = snapshot(source), tmp_path / "stage"
    with pytest.raises(ValueError, match="review|source changed"):
        api.prepare(source, stage, fetch, TODAY)
    assert snapshot(source) == before
    assert not (stage / "refresh-prepared.json").exists()


@pytest.mark.parametrize("kind", ["inside", "ancestor", "existing", "symlink", "input"])
def test_rejects_unsafe_destinations(source, tmp_path, kind):
    stage = source / "stage" if kind == "inside" else tmp_path / "stage"
    if kind == "ancestor":
        stage = source.parent
    elif kind == "existing":
        stage.mkdir()
    elif kind == "symlink":
        stage.symlink_to(tmp_path / "elsewhere", target_is_directory=True)
    elif kind == "input":
        path = source / INDEX
        saved = tmp_path / "held.csv"
        path.rename(saved)
        path.symlink_to(saved)
    before = snapshot(source)
    with pytest.raises((ValueError, FileExistsError)):
        api.prepare(source, stage, fetch, TODAY)
    assert snapshot(source) == before


def test_cli_requires_prepare_and_stage():
    with pytest.raises(SystemExit) as error:
        api.main([])
    assert error.value.code == 2
