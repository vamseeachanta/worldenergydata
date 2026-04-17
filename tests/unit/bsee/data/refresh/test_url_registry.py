"""Tests for BSEE URL registry."""

from worldenergydata.bsee.data.refresh.url_registry import (
    BSEE_BASE_URL,
    DatasetSpec,
    get_all_specs,
    get_ogor_a_specs,
    get_regular_specs,
    get_specs_for_dir,
)


class TestDatasetSpec:
    def test_frozen(self):
        spec = DatasetSpec(
            bin_dir="test",
            zip_url="http://example.com/test.zip",
            expected_bins=["test.bin"],
        )
        assert spec.bin_dir == "test"

    def test_defaults(self):
        spec = DatasetSpec(
            bin_dir="test",
            zip_url="http://example.com/test.zip",
            expected_bins=["test.bin"],
        )
        assert spec.timeout_s == 600
        assert spec.is_ogor_a is False

    def test_custom_timeout(self):
        spec = DatasetSpec(
            bin_dir="test",
            zip_url="http://example.com",
            expected_bins=["a.bin"],
            timeout_s=1200,
        )
        assert spec.timeout_s == 1200


class TestGetRegularSpecs:
    def test_non_empty(self):
        specs = get_regular_specs()
        assert len(specs) > 20

    def test_all_have_bin_dir(self):
        for spec in get_regular_specs():
            assert spec.bin_dir
            assert isinstance(spec.bin_dir, str)

    def test_all_have_zip_url(self):
        for spec in get_regular_specs():
            assert spec.zip_url.startswith(BSEE_BASE_URL)

    def test_all_have_expected_bins(self):
        for spec in get_regular_specs():
            assert len(spec.expected_bins) >= 1
            for b in spec.expected_bins:
                assert b.endswith(".bin")

    def test_none_are_ogor_a(self):
        for spec in get_regular_specs():
            assert spec.is_ogor_a is False

    def test_known_spec_exists(self):
        specs = get_regular_specs()
        names = {s.bin_dir for s in specs}
        assert "apiraw" in names
        assert "production_raw" in names
        assert "platstruc" in names


class TestGetOgorASpecs:
    def test_non_empty(self):
        specs = get_ogor_a_specs()
        assert len(specs) >= 30  # 1996-2024 + current

    def test_all_are_ogor_a(self):
        for spec in get_ogor_a_specs():
            assert spec.is_ogor_a is True

    def test_all_same_bin_dir(self):
        for spec in get_ogor_a_specs():
            assert spec.bin_dir == "historical_production_yearly"

    def test_years_covered(self):
        specs = get_ogor_a_specs()
        urls = [s.zip_url for s in specs]
        # Check some years
        assert any("ogora2000" in u for u in urls)
        assert any("ogora2020" in u for u in urls)
        # Current (non-year-specific)
        assert any("ogoradelimit.zip" in u for u in urls)


class TestGetAllSpecs:
    def test_includes_both(self):
        all_specs = get_all_specs()
        regular = get_regular_specs()
        ogor_a = get_ogor_a_specs()
        assert len(all_specs) == len(regular) + len(ogor_a)

    def test_total_expected_bins(self):
        total_bins = sum(len(s.expected_bins) for s in get_all_specs())
        assert total_bins > 100


class TestGetSpecsForDir:
    def test_apiraw(self):
        specs = get_specs_for_dir("apiraw")
        assert len(specs) == 1
        assert specs[0].bin_dir == "apiraw"

    def test_historical_production_yearly(self):
        specs = get_specs_for_dir("historical_production_yearly")
        assert len(specs) >= 30

    def test_nonexistent_dir(self):
        specs = get_specs_for_dir("nonexistent")
        assert specs == []


class TestBSEEBaseURL:
    def test_url_format(self):
        assert BSEE_BASE_URL.startswith("https://")
        assert "bsee.gov" in BSEE_BASE_URL
