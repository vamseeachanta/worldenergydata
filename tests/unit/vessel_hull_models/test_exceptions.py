"""Tests for Vessel Hull Models module exception hierarchy."""

from worldenergydata.vessel_hull_models.exceptions import (
    AcquisitionError,
    APIClientError,
    DimensionValidationError,
    FormatConversionError,
    MeshOperationError,
    ModelNotFoundError,
    OBJParseError,
    OBJValidationError,
    ParametricGenerationError,
    RateLimitError,
    VesselHullModelsError,
    VisualizationError,
)


class TestVesselHullModelsError:
    def test_basic(self):
        err = VesselHullModelsError("test")
        assert isinstance(err, Exception)
        assert "test" in str(err)


class TestOBJErrors:
    def test_parse_error(self):
        err = OBJParseError("bad format")
        assert isinstance(err, VesselHullModelsError)

    def test_validation_error(self):
        err = OBJValidationError("invalid mesh")
        assert isinstance(err, VesselHullModelsError)


class TestMeshOperationError:
    def test_basic(self):
        err = MeshOperationError("operation failed")
        assert isinstance(err, VesselHullModelsError)


class TestAcquisitionErrors:
    def test_acquisition_error(self):
        err = AcquisitionError("fetch failed")
        assert isinstance(err, VesselHullModelsError)

    def test_api_client_error(self):
        err = APIClientError("API failed")
        assert isinstance(err, AcquisitionError)

    def test_rate_limit_error(self):
        err = RateLimitError("too many requests")
        assert isinstance(err, APIClientError)

    def test_model_not_found(self):
        err = ModelNotFoundError("model XYZ not found")
        assert isinstance(err, AcquisitionError)


class TestParametricGenerationError:
    def test_basic(self):
        err = ParametricGenerationError("generation failed")
        assert isinstance(err, VesselHullModelsError)


class TestDimensionValidationError:
    def test_with_dimensions(self):
        expected = {"length": 100, "beam": 20}
        actual = {"length": 95, "beam": 18}
        err = DimensionValidationError("mismatch", expected, actual)
        assert err.expected == expected
        assert err.actual == actual
        assert isinstance(err, VesselHullModelsError)


class TestFormatConversionError:
    def test_basic(self):
        err = FormatConversionError("conversion failed")
        assert isinstance(err, VesselHullModelsError)


class TestVisualizationError:
    def test_basic(self):
        err = VisualizationError("render failed")
        assert isinstance(err, VesselHullModelsError)


class TestInheritanceChain:
    def test_all_inherit_from_base(self):
        classes = [
            OBJParseError,
            OBJValidationError,
            MeshOperationError,
            AcquisitionError,
            ParametricGenerationError,
            DimensionValidationError,
            FormatConversionError,
            VisualizationError,
        ]
        for cls in classes:
            assert issubclass(cls, VesselHullModelsError)

    def test_api_chain(self):
        assert issubclass(APIClientError, AcquisitionError)
        assert issubclass(RateLimitError, APIClientError)
        assert issubclass(ModelNotFoundError, AcquisitionError)
