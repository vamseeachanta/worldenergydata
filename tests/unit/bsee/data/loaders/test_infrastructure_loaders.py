"""Offline characterization of infrastructure loaders using synthetic pickles.

Basis: platform_loader.py and pipeline_loader.py in the BSEE infrastructure
loader package, especially their concat, cache and exact-match predicates.
Fixture labels are test inputs, not measured data or engineering constants.
"""

import pickle
from pathlib import Path

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal


@pytest.fixture
def loaders(tmp_path, monkeypatch):
    """Prevent constructors from resolving any real repository or shared data."""
    from worldenergydata.bsee.data.loaders.infrastructure import (
        pipeline_loader,
        platform_loader,
    )

    for module in (platform_loader, pipeline_loader):
        monkeypatch.setattr(module, "get_module_data_safe", lambda name: tmp_path)
    return platform_loader.PlatformLoader(), pipeline_loader.PipelineLoader()


@pytest.fixture(params=["platform", "pipeline_permit", "pipeline_location"])
def reader(request, loaders):
    platform, pipeline = loaders
    return {
        "platform": (platform, "_load_data", "data", "_bin_dir"),
        "pipeline_permit": (
            pipeline,
            "_load_permit_data",
            "permit_data",
            "_permit_bin_dir",
        ),
        "pipeline_location": (
            pipeline,
            "_load_location_data",
            "location_data",
            "_location_bin_dir",
        ),
    }[request.param] + (request.param,)


def write_pickle(directory, name, value):
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / name).open("wb") as stream:
        pickle.dump(value, stream)


def config(key, directory):
    return {"parameters": {"filepath": {key: {"bin": directory.as_posix()}}}}


def test_initial_state_and_default_directories(loaders, tmp_path):
    platform, pipeline = loaders
    assert platform.data is None
    assert pipeline.permit_data is None
    assert pipeline.location_data is None
    assert Path(platform._bin_dir) == tmp_path / "bin" / "platform"
    assert Path(pipeline._permit_bin_dir) == tmp_path / "bin" / "pipeline_permit"
    assert Path(pipeline._location_bin_dir) == tmp_path / "bin" / "pipeline_location"


@pytest.mark.parametrize(
    "cfg", [None, {}, {"parameters": {}}, {"parameters": {"filepath": {}}}]
)
def test_default_path_and_partial_configuration(reader, cfg):
    loader, method, cache, directory, _ = reader
    expected = pd.DataFrame({"label": ["synthetic"]})
    write_pickle(Path(getattr(loader, directory)), "rows.bin", expected)
    actual = getattr(loader, method)(cfg)
    assert_frame_equal(actual, expected)
    assert getattr(loader, cache) is actual


def test_override_concatenates_frames_ignores_objects_and_other_suffixes(
    reader, tmp_path
):
    loader, method, cache, directory, key = reader
    custom = tmp_path / "custom"
    first = pd.DataFrame({"label": ["first", "first"]}, index=[7, 7])
    second = pd.DataFrame({"label": ["second"]}, index=[7])
    write_pickle(custom, "first.bin", first)
    write_pickle(custom, "second.bin", second)
    write_pickle(custom, "object.bin", {"label": "ignored"})
    write_pickle(custom, "ignored.txt", pd.DataFrame({"label": ["ignored"]}))
    write_pickle(Path(getattr(loader, directory)), "default.bin", second)
    actual = getattr(loader, method)(config(key, custom))
    expected = pd.concat([first, second], ignore_index=True)
    # glob order is unspecified; compare complete rows after sorting.
    assert_frame_equal(actual.sort_values("label").reset_index(drop=True), expected)
    assert actual.index.tolist() == list(range(len(expected)))
    assert getattr(loader, cache) is actual


@pytest.mark.parametrize("state", ["missing", "empty", "non_frame", "corrupt"])
def test_unusable_input_returns_none_and_can_retry(reader, tmp_path, state):
    loader, method, cache, _, key = reader
    directory = tmp_path / "unusable"
    if state != "missing":
        directory.mkdir()
    if state == "non_frame":
        write_pickle(directory, "input.bin", ["not a dataframe"])
    elif state == "corrupt":
        (directory / "input.bin").write_bytes(b"invalid pickle")
    assert getattr(loader, method)(config(key, directory)) is None
    assert getattr(loader, cache) is None
    expected = pd.DataFrame({"label": ["recovered"]})
    write_pickle(directory, "input.bin", expected)
    assert_frame_equal(getattr(loader, method)(config(key, directory)), expected)


def test_cached_frame_prevents_further_io_even_with_new_configuration(
    reader, tmp_path, monkeypatch
):
    loader, method, cache, directory, key = reader
    expected = pd.DataFrame({"label": ["cached"]})
    write_pickle(Path(getattr(loader, directory)), "input.bin", expected)
    actual = getattr(loader, method)()

    def unexpected_io(*args, **kwargs):
        pytest.fail("cached load attempted filesystem discovery")

    monkeypatch.setattr(Path, "glob", unexpected_io)
    assert getattr(loader, method)(config(key, tmp_path / "other")) is actual
    assert getattr(loader, cache) is actual
    assert_frame_equal(actual, expected)


def test_empty_dataframe_is_cached(reader):
    loader, method, cache, directory, _ = reader
    expected = pd.DataFrame({"label": pd.Series(dtype="str")})
    write_pickle(Path(getattr(loader, directory)), "empty.bin", expected)
    actual = getattr(loader, method)()
    assert_frame_equal(actual, expected)
    assert getattr(loader, cache) is actual
    assert getattr(loader, method)() is actual


def test_failed_read_does_not_publish_partial_cache(reader, monkeypatch):
    loader, method, cache, directory, _ = reader
    directory = Path(getattr(loader, directory))
    write_pickle(directory, "valid.bin", pd.DataFrame({"label": ["valid"]}))
    (directory / "corrupt.bin").write_bytes(b"invalid pickle")
    monkeypatch.setattr(
        Path, "glob", lambda *args: [directory / "valid.bin", directory / "corrupt.bin"]
    )
    assert getattr(loader, method)() is None
    assert getattr(loader, cache) is None


QUERIES = [
    ("platform", "get_platforms_by_area_block", ("EI", 330), ["match"]),
    ("platform", "get_platforms_by_complex", (330,), ["match", "other_area"]),
    ("platform", "get_infrastructure_by_lease", (330,), ["match", "other_block"]),
    ("pipeline_permit", "get_pipelines_by_status", ("ACT",), ["match", "other_area"]),
    (
        "pipeline_permit",
        "get_infrastructure_by_lease",
        (330,),
        ["match", "other_block"],
    ),
]


def query_frame():
    # Synthetic inputs; field names and equality rules come from the loaders.
    # EI/330 and ACT labels also occur in the existing platform/pipeline model tests.
    return pd.DataFrame(
        {
            "label": ["match", "other_area", "other_block"],
            "AREA_CODE": ["EI", "other", "EI"],
            "BLOCK_NUMBER": ["330", "330", "other"],
            "COMPLEX_ID_NUM": ["330", "330", "other"],
            "LEASE_NUMBER": ["330", "other", "330"],
            "STATUS_CODE": ["ACT", "ACT", "other"],
        }
    )


@pytest.mark.parametrize("key,method,args,labels", QUERIES)
@pytest.mark.parametrize("mode", ["match", "no_match", "no_data", "empty"])
def test_public_queries(loaders, tmp_path, key, method, args, labels, mode):
    loader = loaders[0] if key == "platform" else loaders[1]
    frame = query_frame()
    directory = tmp_path / "query"
    if mode != "no_data":
        write_pickle(
            directory, "input.bin", frame.iloc[:0] if mode == "empty" else frame
        )
    if mode == "no_match":
        args = tuple("absent" for _ in args)
    actual = getattr(loader, method)(*args, cfg=config(key, directory))
    if mode == "match":
        assert_frame_equal(actual, frame[frame["label"].isin(labels)])
        cache = loader.data if key == "platform" else loader.permit_data
        assert_frame_equal(cache, frame)
    else:
        assert actual is None


def test_pipeline_caches_are_independent(loaders, tmp_path):
    _, loader = loaders
    permits = pd.DataFrame({"STATUS_CODE": ["ACT"]})
    locations = pd.DataFrame({"label": ["location"]})
    write_pickle(Path(loader._permit_bin_dir), "permit.bin", permits)
    write_pickle(Path(loader._location_bin_dir), "location.bin", locations)
    actual_permits = loader._load_permit_data()
    assert loader.location_data is None
    actual_locations = loader._load_location_data()
    assert_frame_equal(actual_permits, permits)
    assert_frame_equal(actual_locations, locations)
    assert loader.permit_data is actual_permits
    assert loader.location_data is actual_locations
    assert loader._load_permit_data() is actual_permits
