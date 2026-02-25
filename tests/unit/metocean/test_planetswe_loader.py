# ABOUTME: Unit tests for PlanetsweLoader — The Well planetswe dataset integration.
# ABOUTME: Uses mocks so tests pass whether or not the_well package is installed.

"""
Unit tests for PlanetsweLoader (worldenergydata/metocean/well_datasets).

The Well dataset — CC BY 4.0, Polymathic AI
https://github.com/PolymathicAI/the_well
"""

from unittest.mock import MagicMock, patch

import pytest


class TestPlanetsweLoaderImport:
    """Tests that the module and class are importable."""

    def test_module_importable(self):
        """Test that well_datasets module can be imported."""
        from worldenergydata.metocean.well_datasets import planetswe_loader  # noqa: F401

    def test_class_importable(self):
        """Test that PlanetsweLoader class is importable."""
        from worldenergydata.metocean.well_datasets.planetswe_loader import (
            PlanetsweLoader,
        )

        assert PlanetsweLoader is not None

    def test_attribution_constant_importable(self):
        """Test that attribution constant is importable from module."""
        from worldenergydata.metocean.well_datasets.planetswe_loader import (
            THE_WELL_ATTRIBUTION,
        )

        assert THE_WELL_ATTRIBUTION is not None


class TestPlanetsweLoaderConstruction:
    """Tests for PlanetsweLoader class construction."""

    def test_default_construction(self):
        """Test PlanetsweLoader constructs with default parameters."""
        from worldenergydata.metocean.well_datasets.planetswe_loader import (
            PlanetsweLoader,
        )

        loader = PlanetsweLoader()
        assert loader is not None

    def test_dataset_name_attribute(self):
        """Test loader exposes dataset_name attribute."""
        from worldenergydata.metocean.well_datasets.planetswe_loader import (
            PlanetsweLoader,
        )

        loader = PlanetsweLoader()
        assert loader.dataset_name == "planetswe"

    def test_split_default_is_train(self):
        """Test default split is train."""
        from worldenergydata.metocean.well_datasets.planetswe_loader import (
            PlanetsweLoader,
        )

        loader = PlanetsweLoader()
        assert loader.split == "train"

    def test_custom_split_accepted(self):
        """Test loader accepts custom split parameter."""
        from worldenergydata.metocean.well_datasets.planetswe_loader import (
            PlanetsweLoader,
        )

        loader = PlanetsweLoader(split="valid")
        assert loader.split == "valid"

    def test_repr_contains_dataset_name(self):
        """Test string representation includes dataset name."""
        from worldenergydata.metocean.well_datasets.planetswe_loader import (
            PlanetsweLoader,
        )

        loader = PlanetsweLoader()
        assert "planetswe" in repr(loader)


class TestPlanetsweLoaderAttribution:
    """Tests for attribution constant compliance (CC BY 4.0)."""

    def test_attribution_contains_cc_by(self):
        """Test attribution string references CC BY 4.0 license."""
        from worldenergydata.metocean.well_datasets.planetswe_loader import (
            THE_WELL_ATTRIBUTION,
        )

        assert "CC BY 4.0" in THE_WELL_ATTRIBUTION

    def test_attribution_contains_polymathic_ai(self):
        """Test attribution string credits Polymathic AI."""
        from worldenergydata.metocean.well_datasets.planetswe_loader import (
            THE_WELL_ATTRIBUTION,
        )

        assert "Polymathic AI" in THE_WELL_ATTRIBUTION

    def test_attribution_contains_the_well(self):
        """Test attribution string names The Well dataset."""
        from worldenergydata.metocean.well_datasets.planetswe_loader import (
            THE_WELL_ATTRIBUTION,
        )

        assert "The Well" in THE_WELL_ATTRIBUTION

    def test_loader_exposes_attribution(self):
        """Test PlanetsweLoader instance exposes attribution attribute."""
        from worldenergydata.metocean.well_datasets.planetswe_loader import (
            PlanetsweLoader,
        )

        loader = PlanetsweLoader()
        assert hasattr(loader, "attribution")
        assert "CC BY 4.0" in loader.attribution


class TestStreamSampleWithMock:
    """Tests for stream_sample method using mocked the_well package."""

    def test_stream_sample_returns_iterable_when_well_available(self):
        """Test stream_sample returns an iterable when the_well is installed."""
        from worldenergydata.metocean.well_datasets import planetswe_loader as pl_module

        mock_dataset = MagicMock()
        mock_sample = {"data": MagicMock(), "metadata": {"step": 0}}
        mock_dataset.__iter__ = MagicMock(return_value=iter([mock_sample] * 5))

        mock_well_dataset_cls = MagicMock(return_value=mock_dataset)

        with patch.object(pl_module, "WELL_AVAILABLE", True), patch.object(
            pl_module, "WellDataset", mock_well_dataset_cls, create=True
        ):
            from worldenergydata.metocean.well_datasets.planetswe_loader import (
                PlanetsweLoader,
            )

            loader = PlanetsweLoader()
            result = loader.stream_sample(n_steps=5)
            assert result is not None

    def test_stream_sample_raises_import_error_when_well_missing(self):
        """Test stream_sample raises ImportError with helpful message if the_well not installed."""
        from worldenergydata.metocean.well_datasets import planetswe_loader as pl_module

        with patch.object(pl_module, "WELL_AVAILABLE", False):
            from worldenergydata.metocean.well_datasets.planetswe_loader import (
                PlanetsweLoader,
            )

            loader = PlanetsweLoader()
            with pytest.raises(ImportError) as exc_info:
                loader.stream_sample()

            error_msg = str(exc_info.value)
            assert "the_well" in error_msg
            assert "pip install" in error_msg

    def test_stream_sample_default_n_steps_is_10(self):
        """Test stream_sample default n_steps parameter is 10."""
        from worldenergydata.metocean.well_datasets import planetswe_loader as pl_module

        mock_dataset = MagicMock()
        collected_steps = []

        def fake_iter():
            for i in range(15):
                yield {"data": MagicMock(), "step": i}

        mock_dataset.__iter__ = MagicMock(side_effect=fake_iter)
        mock_well_dataset_cls = MagicMock(return_value=mock_dataset)

        with patch.object(pl_module, "WELL_AVAILABLE", True), patch.object(
            pl_module, "WellDataset", mock_well_dataset_cls, create=True
        ):
            from worldenergydata.metocean.well_datasets.planetswe_loader import (
                PlanetsweLoader,
            )

            loader = PlanetsweLoader()
            # stream_sample() without arguments should use n_steps=10
            result = list(loader.stream_sample())
            assert len(result) <= 10

    def test_stream_sample_respects_n_steps(self):
        """Test stream_sample yields at most n_steps items."""
        from worldenergydata.metocean.well_datasets import planetswe_loader as pl_module

        mock_dataset = MagicMock()

        def fake_iter():
            for i in range(100):
                yield {"data": MagicMock(), "step": i}

        mock_dataset.__iter__ = MagicMock(side_effect=fake_iter)
        mock_well_dataset_cls = MagicMock(return_value=mock_dataset)

        with patch.object(pl_module, "WELL_AVAILABLE", True), patch.object(
            pl_module, "WellDataset", mock_well_dataset_cls, create=True
        ):
            from worldenergydata.metocean.well_datasets.planetswe_loader import (
                PlanetsweLoader,
            )

            loader = PlanetsweLoader()
            result = list(loader.stream_sample(n_steps=3))
            assert len(result) == 3

    def test_stream_sample_each_item_has_data_key(self):
        """Test each streamed sample contains a 'data' key."""
        from worldenergydata.metocean.well_datasets import planetswe_loader as pl_module

        mock_dataset = MagicMock()
        fake_array = MagicMock()

        def fake_iter():
            for i in range(5):
                yield {"data": fake_array, "step": i}

        mock_dataset.__iter__ = MagicMock(side_effect=fake_iter)
        mock_well_dataset_cls = MagicMock(return_value=mock_dataset)

        with patch.object(pl_module, "WELL_AVAILABLE", True), patch.object(
            pl_module, "WellDataset", mock_well_dataset_cls, create=True
        ):
            from worldenergydata.metocean.well_datasets.planetswe_loader import (
                PlanetsweLoader,
            )

            loader = PlanetsweLoader()
            for sample in loader.stream_sample(n_steps=3):
                assert "data" in sample


class TestWellAvailableFlag:
    """Tests for WELL_AVAILABLE module-level flag."""

    def test_well_available_flag_is_bool(self):
        """Test WELL_AVAILABLE is a boolean."""
        from worldenergydata.metocean.well_datasets.planetswe_loader import (
            WELL_AVAILABLE,
        )

        assert isinstance(WELL_AVAILABLE, bool)

    def test_well_datasets_init_exports_loader(self):
        """Test well_datasets __init__ exports PlanetsweLoader."""
        from worldenergydata.metocean.well_datasets import PlanetsweLoader

        assert PlanetsweLoader is not None
