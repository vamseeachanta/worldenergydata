"""Reference-reader regressions using synthetic records, never raw archives.

Positions follow docs/data/legacy/data/bsee_yearly_production_data.yml,
first df_columns sequence (repository edition at baseline). All volumes below
are supplied synthetic inputs; expected sums are independent arithmetic.
"""

import importlib.util
import sys
import zipfile
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[4]
REFERENCE = ROOT / "docs/modules/bsee/analysis/production/FDAS_V30"


def load_reference(name):
    sys.path.insert(0, str(REFERENCE))
    try:
        spec = importlib.util.spec_from_file_location(name, REFERENCE / f"{name}.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(REFERENCE))


@pytest.fixture
def matrix():
    return load_reference("build_multi_year_lease_matrix1")


@pytest.fixture
def chrono():
    return load_reference("ogora_to_chronological")


def row(api="101", code="O", oil=10, water=3):
    """Nine required fields: eight preceding API, then API at index eight."""
    return ["G1", "completion-a", "202501", "2", code, oil, "20", water, api]


def write_zip(path, members):
    with zipfile.ZipFile(path, "w") as archive:
        for name, rows in members.items():
            archive.writestr(name, "\n".join(",".join(map(str, r)) for r in rows))


def test_b1_uses_api_after_eight_fields(matrix):
    result = matrix.parse_headerless_ogora(pd.DataFrame([row()]))
    assert result["API_WELL_NUMBER"].tolist() == ["101"]


def test_b1_eight_columns_cannot_supply_api(matrix):
    with pytest.raises(ValueError, match="API"):
        matrix.parse_headerless_ogora(pd.DataFrame([row()[:8]]))


def test_b1_package_has_named_identity():
    from worldenergydata.fdas.data.production import ProductionProcessor

    data = pd.DataFrame(
        {
            "API_WELL_NUMBER": ["101"],
            "WELL_COMPLETION_ID": ["other"],
            "PROD_DATE": ["2025-01-01"],
            "OIL_VOLUME": [10],
        }
    )
    assert ProductionProcessor(data).aggregate_monthly()[
        "API_WELL_NUMBER"
    ].tolist() == ["101"]


def test_b2_all_members_and_exact_duplicates(chrono, tmp_path):
    """Member A contributes 10, B contributes 20; repeated A counts once: 30."""
    path = tmp_path / "ogora2025delimit.zip"
    write_zip(
        path,
        {
            "first.txt": [row()],
            "second.csv": [row(), row(api="102", oil=20)],
            "readme.md": [],
        },
    )
    result = chrono.read_ogor_zip(str(path))
    assert len(result) == 2
    assert pd.to_numeric(result["OIL_PROD"]).sum() == 30


def test_b2_extraction_does_not_overwrite_equal_basenames(matrix, tmp_path):
    a, b = tmp_path / "a.zip", tmp_path / "b.zip"
    write_zip(a, {"data.txt": [row()]})
    write_zip(b, {"data.txt": [row(api="102")]})
    ctx, files = matrix.extract_ogora_zips_to_temp([a, b])
    assert len(set(files)) == 2
    assert {Path(f).read_text().split(",")[-1] for f in files} == {"101", "102"}
    assert Path(ctx.name).exists()


def test_b3_matrix_oil_filter_and_b8_documented_water(matrix):
    """Oil=10+0; documented column 7 water=3+7, not gas/condensate."""
    result = matrix.parse_headerless_ogora(
        pd.DataFrame([row(), row(code="G", oil=90, water=7)])
    )
    assert result["OIL_BBL"].sum() == 10
    assert result["WATER_BBL"].sum() == 10


def test_b12_matrix_rejects_war_fanout(matrix, tmp_path):
    prod = matrix.parse_headerless_ogora(pd.DataFrame([row()]))
    war = pd.DataFrame(
        {
            "API_WELL_NUMBER": ["101", "101"],
            "LEASE_NAME": ["A", "B"],
            "SURF_LEASE_NUM": ["1", "2"],
            "WELL_NAME": ["w", "w"],
            "LEASE_KEY": ["A", "B"],
        }
    )
    with pytest.raises(pd.errors.MergeError):
        matrix.build_workbook(prod, war, pd.DataFrame(), tmp_path / "matrix.xlsx")


def build_fixture(chrono, tmp_path, rows, wti=True, leases=None):
    path = tmp_path / "ogora2025delimit.zip"
    write_zip(path, {"one.txt": rows})
    lease_path = tmp_path / "leases.csv"
    (
        leases
        if leases is not None
        else pd.DataFrame(
            {
                "LEASE_NUM": ["G1"],
                "LEASE_NAME": ["A"],
                "DEV_NAME": ["development-a"],
                "DEV_SYSTEM": ["test"],
            }
        )
    ).to_csv(lease_path, index=False)
    price = tmp_path / "wti.csv"
    pd.DataFrame({"MONTH": ["2025-01-01"], "WTI_USD": [5]}).to_csv(price, index=False)
    out = tmp_path / "chrono.xlsx"
    chrono.build_chrono(
        str(tmp_path),
        str(lease_path),
        "ogora*.zip",
        None,
        str(price) if wti else None,
        str(out),
    )
    return pd.read_excel(out, sheet_name="chronological")


def test_b3_b9_chrono_product_filter_and_water(chrono, tmp_path):
    """Oil=10, water=3+7=10; revenue=10*5=50, with no gas oil added."""
    result = build_fixture(chrono, tmp_path, [row(), row(code="G", oil=90, water=7)])
    assert result["MONTHLY_OIL_VOLUME"].sum() == 10
    assert result["MONTHLY_WATER_VOLUME"].sum() == 10
    assert result["MONTHLY_REVENUE_USD"].sum() == 50


def test_b9_absent_water_is_not_zero(chrono, tmp_path):
    data = row()
    data[7] = ""
    result = build_fixture(chrono, tmp_path, [data])
    assert result["MONTHLY_WATER_VOLUME"].isna().all()
    assert result["WATER_STATUS"].tolist() == ["NOT_EVALUATED"]


def test_b10_omitted_price_is_not_zero(chrono, tmp_path):
    result = build_fixture(chrono, tmp_path, [row()], wti=False)
    assert result["WTI_USD"].isna().all()
    assert result["MONTHLY_REVENUE_USD"].isna().all()


def test_b12_same_name_fallback_does_not_multiply_rows(chrono, tmp_path):
    """Two leases sharing a name and identical mapping still yield one row."""
    leases = pd.DataFrame({"LEASE_NUM": ["G1", "G2"], "LEASE_NAME": ["A", "A"]})
    result = build_fixture(chrono, tmp_path, [row()], leases=leases)
    assert len(result) == 1
    assert result["MONTHLY_OIL_VOLUME"].sum() == 10


def test_b9_partial_water_is_not_a_complete_total(chrono, tmp_path):
    a, b = row(), row(code="G")
    b[7] = ""
    result = build_fixture(chrono, tmp_path, [a, b])
    assert result["MONTHLY_WATER_VOLUME"].isna().all()
    assert result["WATER_STATUS"].tolist() == ["NOT_EVALUATED"]


def test_b12_matrix_preserves_well_pairs(matrix, tmp_path):
    """Two APIs paired with two names produce two rows, never four pairs."""
    prod = matrix.parse_headerless_ogora(pd.DataFrame([row(), row(api="102")]))
    war = pd.DataFrame(
        {
            "API_WELL_NUMBER": ["101", "102"],
            "LEASE_NAME": ["A", "A"],
            "SURF_LEASE_NUM": ["1", "1"],
            "WELL_NAME": ["w1", "w2"],
            "LEASE_KEY": ["A", "A"],
        }
    )
    out = tmp_path / "pairs.xlsx"
    matrix.build_workbook(prod, war, pd.DataFrame(), out)
    assert len(pd.read_excel(out, sheet_name="A")) == 2


def test_b12_conflicting_lease_keys_raise(chrono, tmp_path):
    leases = pd.DataFrame({"LEASE_NUM": ["G1", "G1"], "LEASE_NAME": ["A", "B"]})
    with pytest.raises(pd.errors.MergeError):
        build_fixture(chrono, tmp_path, [row()], leases=leases)


def test_b1_documented_lease_fallback(matrix):
    assert matrix.parse_headerless_ogora(pd.DataFrame([row()]))[
        "LEASE_FALLBACK"
    ].tolist() == ["G1"]


def test_b1_raw_reader_to_war_join(matrix, tmp_path):
    """A synthetic API joins lease A even when the completion identifier differs."""
    raw = tmp_path / "ogora.txt"
    raw.write_text(",".join(map(str, row())))
    war = tmp_path / "war.txt"
    war.write_text("API_WELL_NUMBER,SURF_LEASE_NUM,LEASE_NAME,WELL_NAME\n101,G1,A,w1\n")
    prod = matrix.load_ogora_production(str(raw))
    out = tmp_path / "joined.xlsx"
    matrix.build_workbook(prod, matrix.load_war_main(str(war)), pd.DataFrame(), out)
    result = pd.read_excel(out, sheet_name="A__bbl")
    assert result["API_WELL_NUMBER"].tolist() == [101]
    assert result["2025-01"].tolist() == [10]
