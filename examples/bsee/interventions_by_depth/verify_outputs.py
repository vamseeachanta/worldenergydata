"""Reconcile delivered aggregates and chart dimensions without network/raw files."""

import hashlib
import json
import platform
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
import yaml
from estimate_costs import estimate
from PIL import Image

ROOT = Path(__file__).resolve().parent


def verify():
    out = ROOT / "output"
    counts = pd.read_csv(out / "counts_by_year_band_group.csv")
    monthly = pd.read_csv(out / "coverage_by_month.csv")
    rates = pd.read_csv(out / "rates.csv")
    summary = json.loads((out / "summary.json").read_text())
    last = summary["last_full_year"]
    selected_months = (
        monthly.month.str[:4].astype(int).between(summary["first_full_year"], last + 1)
    )
    assert (
        counts.permits.sum() == monthly.loc[selected_months, "approved_permits"].sum()
    )
    assert (rates.standing_wells >= 0).all()
    for row in rates.itertuples():
        groups = (
            ["workover and recompletion", "production enhancement", "other well work"]
            if row.family == "well work"
            else [
                "temporary abandonment",
                "permanent abandonment",
                "abandonment unspecified",
            ]
        )
        n = counts.loc[
            counts.year.eq(row.year)
            & counts.band.eq(row.band)
            & counts.group.isin(groups),
            "permits",
        ].sum()
        assert n == row.permits
        if row.standing_wells:
            assert np.isclose(
                row.per_100_standing_wells, n / row.standing_wells * 100, atol=1e-6
            )
        else:
            assert pd.isna(row.per_100_standing_wells)
    averages = pd.read_csv(out / "full_year_averages.csv").set_index(["band", "family"])
    actual = (
        rates[rates.year.le(last)]
        .groupby(["band", "family"])
        .agg(
            mean_annual_permits=("permits", "mean"),
            mean_annual_rate=("per_100_standing_wells", "mean"),
        )
    )
    np.testing.assert_allclose(
        averages, actual.reindex(averages.index), atol=1e-6, equal_nan=True
    )
    basis = yaml.safe_load((ROOT / "cost_basis.yml").read_text(encoding="utf-8"))
    generated = estimate(basis)
    saved = pd.read_csv(out / "cost_table.csv")
    pd.testing.assert_frame_equal(saved, generated, check_dtype=False)
    for scenario in basis["scenarios"]:
        for case in ["low", "base", "high"]:
            for fact in scenario[case].values():
                assert all(
                    k in fact
                    for k in [
                        "value",
                        "unit",
                        "asset",
                        "band",
                        "citation",
                        "interpretation",
                    ]
                )
                assert all(
                    k in fact["citation"]
                    for k in [
                        "title",
                        "publisher",
                        "date",
                        "url",
                        "retrieval_date",
                        "location",
                    ]
                )
    files = sorted(
        p
        for p in out.iterdir()
        if p.suffix in [".csv", ".json", ".png", ".svg"]
        and p.name != "verification.json"
    )
    for png in out.glob("*.png"):
        with Image.open(png) as img:
            assert img.width >= 1600
    receipt = dict(
        criteria_revision=1,
        software=dict(
            python=platform.python_version(),
            pandas=pd.__version__,
            numpy=np.__version__,
            matplotlib=matplotlib.__version__,
            pyyaml=yaml.__version__,
        ),
        code_and_basis_sha256={
            p.relative_to(ROOT.parents[2])
            .as_posix(): hashlib.sha256(p.read_bytes())
            .hexdigest()
            for p in sorted(
                list(ROOT.glob("*.py"))
                + [
                    ROOT / "cost_basis.yml",
                    ROOT / "README.md",
                    ROOT / "requirements.txt",
                    ROOT.parents[2] / "tests/unit/bsee/test_interventions_by_depth.py",
                ]
            )
        },
        checks=[
            "all selected-year APM approvals partitioned",
            "rates reconcile with groups and denominator",
            "partial year excluded from averages",
            "cost table equals cited YAML arithmetic",
            "all cost inputs carry provenance",
            "PNG width at least 1600",
        ],
        files={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
    )
    (out / "verification.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps({"checks": len(receipt["checks"]), "verified_files": len(files)}))


if __name__ == "__main__":
    verify()
