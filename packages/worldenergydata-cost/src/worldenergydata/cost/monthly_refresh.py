"""Prepare five validated cost products in isolation; never publish live data."""

import argparse
import hashlib
import json
import shutil
from datetime import date, datetime, timezone
from pathlib import Path

from worldenergydata.cost import escalation, outturn_check
from worldenergydata.cost import project_field_crosswalk as crosswalk
from worldenergydata.cost.timeseries import refresh as reference
from worldenergydata.cost.timeseries.reference_series import FRED_PAGE, REFERENCE_SERIES

CURATED = crosswalk.CURATED
INDEX = CURATED / "cost_component_timeseries.csv"
DERIVED = CURATED / "sanctioned_projects_2026.csv"
REPORT = Path("reports/cost/sanction_vs_outturn.csv")
REFERENCE = CURATED / reference.MANIFEST_NAME
PROJECTS = CURATED / "sanctioned_projects.csv"
YEARS = CURATED / "sanctioned_project_cost_years.csv"
TRAILS = CURATED / "cost_revision_trails.csv"
QUALIFIERS = CURATED / "cost_revision_trail_qualifiers.csv"
PRODUCTS = (INDEX, REFERENCE, DERIVED, crosswalk.MANIFEST, REPORT)


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _plain(path):
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("symlinked destinations or inputs are unsupported")


def _digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _snapshot(root):
    paths = {root / crosswalk.CATALOG, root / crosswalk.FIELD_IDENTITIES, root / REPORT}
    for folder in ("curated", "staging"):
        _plain(root / crosswalk.COST / folder)
        for path in (root / crosswalk.COST / folder).rglob("*"):
            if not path.is_dir() or path.is_symlink():
                paths.add(path)
    for path in paths:
        _plain(path)
    return {
        p.relative_to(root).as_posix(): _digest(p) if p.is_file() else None
        for p in sorted(paths)
    }


def _labels(root):
    return crosswalk.input_paths(root), crosswalk.load_cost_projects(root)


def _research(root):
    owned = {
        (FRED_PAGE.format(series_id=s.series_id), s.component.value)
        for s in REFERENCE_SERIES
    }
    return sorted(
        tuple(sorted(r.items()))
        for r in crosswalk.read_csv(root / INDEX)[1]
        if (r["SOURCE_URL"], r["COMPONENT"]) not in owned
    )


def _run(module, **paths):
    args = []
    for name, path in paths.items():
        args.extend(("--" + name.replace("_", "-"), str(path)))
    _require(module.main(args) == 0, module.__name__ + " failed")


def prepare(root, stage, fetch, accessed_date, *, source_revision=None):
    """Return a read-back PREPARED receipt; partial stages remain caller-owned."""
    root, stage = Path(root).absolute(), Path(stage).absolute()
    _plain(root)
    _plain(stage)
    root, stage = root.resolve(), stage.resolve()
    _require(
        root != stage and root not in stage.parents and stage not in root.parents,
        "source and stage must be disjoint",
    )
    _require(not stage.exists(), "stage must be a fresh directory")
    started = datetime.now(timezone.utc).isoformat()
    before = _snapshot(root)
    required = (*PRODUCTS[:4], crosswalk.CROSSWALK, YEARS, QUALIFIERS)
    _require(all((root / p).is_file() for p in required), "required input missing")
    crosswalk.validate_repository(root)
    labels, research = _labels(root), _research(root)
    stage.mkdir(parents=True)
    for relative, digest in before.items():
        if digest is not None and relative != REPORT.as_posix():
            target = stage / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / relative, target)
    expected = dict(before, **{REPORT.as_posix(): None})
    _require(_snapshot(stage) == expected, "source changed while copying")
    reference.refresh(stage / INDEX, accessed_date, fetch=fetch)
    _run(
        escalation,
        projects=stage / PROJECTS,
        indices=stage / INDEX,
        statement_years=stage / YEARS,
        output=stage / DERIVED,
    )
    changed = _snapshot(stage)
    mutable = {p.as_posix() for p in PRODUCTS[:3]}
    _require(
        changed.keys() == expected.keys()
        and all(changed[p] == expected[p] for p in expected if p not in mutable),
        "review required: input inventory or protected bytes changed",
    )
    _require(
        _labels(stage) == labels and _research(stage) == research,
        "review required: project labels or research rows changed",
    )
    (stage / crosswalk.MANIFEST).write_text(
        json.dumps(crosswalk.build_manifest(stage), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    crosswalk.validate_repository(stage)
    _run(
        outturn_check,
        trails=stage / TRAILS,
        indices=stage / INDEX,
        qualifiers=stage / QUALIFIERS,
        output=stage / REPORT,
    )
    problems = reference.check_freshness(stage / INDEX, accessed_date)
    _require(not problems, "; ".join(problems))
    for path in PRODUCTS:
        if path.suffix == ".csv":
            _require(crosswalk.read_csv(stage / path)[1], "empty prepared product")
        else:
            json.loads((stage / path).read_text(encoding="utf-8"))
    receipt = dict(
        disposition="PREPARED",
        promoted=False,
        source_revision=source_revision,
        started_utc=started,
        finished_utc=datetime.now(timezone.utc).isoformat(),
        inputs=before,
        products={p.as_posix(): _digest(stage / p) for p in PRODUCTS},
        retention="Caller-owned stage; retain for review or discard explicitly.",
    )
    _require(_snapshot(root) == before, "source changed during preparation")
    pending = stage / "refresh-prepared.pending"
    pending.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    readback = json.loads(pending.read_text(encoding="utf-8"))
    _require(readback == receipt, "receipt readback mismatch")
    for p, digest in readback["products"].items():
        _require(_digest(stage / p) == digest, "product readback mismatch")
    _require(_snapshot(root) == before, "source changed before receipt publication")
    pending.rename(stage / "refresh-prepared.json")
    return readback


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare", action="store_true", required=True)
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    try:
        prepare(args.root, args.stage, reference.fetch_fred_series, date.today())
    except (ValueError, OSError, RuntimeError) as error:
        parser.exit(2, f"preparation failed: {error}\n")
    print("PREPARED; promoted: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
