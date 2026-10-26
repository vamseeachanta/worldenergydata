"""Offline local grouping contracts; all identities come from synthetic rows below.

API and lease sentinels are arbitrary test identities, not measured data. Expected
API lists use the literal rows in first-seen order, excluding blanks. The loader
file is loaded in isolation so binary-source and path helpers can be stubbed
without importing their dependencies or leaking stubs into other test modules.
"""

import csv
import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, call

import pandas as pd
import pytest


@pytest.fixture
def local_loader(monkeypatch, tmp_path):
    source = SimpleNamespace(router=Mock())
    binary_module = ModuleType("worldenergydata.bsee.data.sources.bin.lease_data")
    binary_module.LeaseData = Mock(return_value=source)
    utilities = ModuleType("assetutilities.common.utilities")
    utilities.is_dir_valid_func = Mock(return_value=(True, str(tmp_path)))
    monkeypatch.setitem(sys.modules, binary_module.__name__, binary_module)
    monkeypatch.setitem(sys.modules, utilities.__name__, utilities)

    # tests/unit/bsee/data is four directories below the repository root.
    root = Path(__file__).resolve().parents[4]
    path = root / (
        "packages/worldenergydata-bsee/src/worldenergydata/bsee/"
        "data/loaders/lease/local_files.py"
    )
    spec = importlib.util.spec_from_file_location("local_lease_groups_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    reads = Mock(wraps=pd.read_csv)
    monkeypatch.setattr(module.pd, "read_csv", reads)
    return SimpleNamespace(
        loader=module.DataFromLocalFiles(),
        source=source,
        resolver=utilities.is_dir_valid_func,
        reads=reads,
        directory=tmp_path,
    )


def configuration(local_loader, row_groups):
    """Write tiny CSVs using the existing lease_<number-list>.csv convention."""
    groups = []
    for rows in row_groups:
        leases = list(dict.fromkeys(row["BOTM_LEASE_NUM"] for row in rows))
        groups.append({"bottom_lease": {"number": leases}})
        path = local_loader.directory / f"lease_{leases}.csv"
        with path.open("w", newline="") as stream:
            writer = csv.DictWriter(
                stream, fieldnames=["BOTM_LEASE_NUM", "API_WELL_NUMBER"]
            )
            writer.writeheader()
            writer.writerows(rows)
    return {
        "basename": "lease",
        "lease": {"data": {"groups": groups}},
        "Analysis": {
            "result_folder": str(local_loader.directory),
            "analysis_root_folder": str(local_loader.directory),
        },
    }


def assert_groups(local_loader, cfg, grouped, row_groups):
    """Compare tables and metadata to the input, including order and read count."""
    metadata = cfg["lease"]["data"]["groups"]
    assert len(grouped) == len(row_groups)
    assert len(metadata) == len(row_groups)
    for nested, group, rows in zip(grouped, metadata, row_groups):
        (table_group,) = nested
        assert {
            key: value for key, value in table_group.items() if key != "lease_df"
        } == group
        expected_leases = list(dict.fromkeys(row["BOTM_LEASE_NUM"] for row in rows))
        expected_apis = list(
            dict.fromkeys(
                row["API_WELL_NUMBER"]
                for row in rows
                if row["API_WELL_NUMBER"] is not None
            )
        )
        assert group["bottom_lease"]["number"] == expected_leases
        assert group["api12"] == expected_apis
        pd.testing.assert_frame_equal(
            table_group["lease_df"],
            pd.DataFrame(rows, columns=["BOTM_LEASE_NUM", "API_WELL_NUMBER"]),
        )
    assert local_loader.reads.call_args_list == [
        call(group["file_name"], low_memory=False) for group in metadata
    ]
    assert local_loader.source.router.call_args_list == [
        call(
            cfg,
            {
                "bottom_lease": {
                    "number": list(dict.fromkeys(row["BOTM_LEASE_NUM"] for row in rows))
                }
            },
        )
        for rows in row_groups
    ]
    assert local_loader.resolver.call_args_list == [
        call(str(local_loader.directory / "Data"), str(local_loader.directory))
        for rows in row_groups
    ]


def test_all_local_lease_groups_are_retained(local_loader):
    rows = [
        [{"BOTM_LEASE_NUM": "lease_alpha", "API_WELL_NUMBER": 111111111111}],
        [{"BOTM_LEASE_NUM": "lease_beta", "API_WELL_NUMBER": 222222222222}],
    ]
    cfg = configuration(local_loader, rows)

    returned_cfg, grouped = local_loader.loader.router(cfg)

    assert returned_cfg is cfg
    assert_groups(local_loader, returned_cfg, grouped, rows)


def test_empty_local_lease_groups(local_loader):
    cfg = configuration(local_loader, [])

    returned_cfg, grouped = local_loader.loader.router(cfg)

    assert returned_cfg is cfg
    assert_groups(local_loader, returned_cfg, grouped, [])


def test_single_local_lease_group(local_loader):
    rows = [[{"BOTM_LEASE_NUM": "lease_alpha", "API_WELL_NUMBER": 111111111111}]]
    cfg = configuration(local_loader, rows)

    returned_cfg, grouped = local_loader.loader.router(cfg)

    assert_groups(local_loader, returned_cfg, grouped, rows)


def test_multi_lease_group_reads_table_once(local_loader):
    rows = [
        [
            {"BOTM_LEASE_NUM": "lease_alpha", "API_WELL_NUMBER": 111111111111},
            {"BOTM_LEASE_NUM": "lease_beta", "API_WELL_NUMBER": 222222222222},
        ]
    ]
    cfg = configuration(local_loader, rows)

    returned_cfg, grouped = local_loader.loader.router(cfg)

    assert_groups(local_loader, returned_cfg, grouped, rows)


def test_missing_local_group_file_raises(local_loader):
    rows = [[{"BOTM_LEASE_NUM": "lease_alpha", "API_WELL_NUMBER": 111111111111}]]
    cfg = configuration(local_loader, rows)
    missing_directory = local_loader.directory / "missing"
    local_loader.resolver.return_value = (True, str(missing_directory))

    with pytest.raises(FileNotFoundError) as error:
        local_loader.loader.router(cfg)

    missing_path = missing_directory / "lease_['lease_alpha'].csv"
    assert error.value.filename == str(missing_path)
    assert local_loader.reads.call_args_list == [
        call(str(missing_path), low_memory=False)
    ]
    assert cfg["lease"]["data"]["groups"] == [
        {"bottom_lease": {"number": ["lease_alpha"]}}
    ]


def test_api_metadata_uses_unique_nonblank_input_rows(local_loader):
    rows = [
        [
            {"BOTM_LEASE_NUM": "lease_alpha", "API_WELL_NUMBER": 222222222222},
            {"BOTM_LEASE_NUM": "lease_alpha", "API_WELL_NUMBER": None},
            {"BOTM_LEASE_NUM": "lease_alpha", "API_WELL_NUMBER": 111111111111},
            {"BOTM_LEASE_NUM": "lease_alpha", "API_WELL_NUMBER": 222222222222},
        ]
    ]
    cfg = configuration(local_loader, rows)

    returned_cfg, grouped = local_loader.loader.router(cfg)

    assert_groups(local_loader, returned_cfg, grouped, rows)


def test_configuration_only_loader_preserves_return_contract(local_loader):
    rows = [
        [{"BOTM_LEASE_NUM": "lease_alpha", "API_WELL_NUMBER": 111111111111}],
        [{"BOTM_LEASE_NUM": "lease_beta", "API_WELL_NUMBER": 222222222222}],
    ]
    cfg = configuration(local_loader, rows)

    returned_cfg = local_loader.loader.get_lease_data_from_local_files(cfg)

    assert returned_cfg is cfg
    metadata = returned_cfg["lease"]["data"]["groups"]
    assert [group["api12"] for group in metadata] == [
        [row["API_WELL_NUMBER"] for row in group_rows] for group_rows in rows
    ]
    assert all("lease_df" not in group for group in metadata)
    assert local_loader.reads.call_args_list == [
        call(group["file_name"], low_memory=False) for group in metadata
    ]
