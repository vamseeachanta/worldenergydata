# ABOUTME: Custom exceptions for the vessel hull models module
# ABOUTME: Defines errors for geometry parsing, acquisition, and validation

"""
Custom Exceptions for Vessel Hull Models Module
"""


class VesselHullModelsError(Exception):
    """Base exception for vessel hull models module"""

    pass


class OBJParseError(VesselHullModelsError):
    """Error parsing OBJ file format"""

    pass


class OBJValidationError(VesselHullModelsError):
    """OBJ file validation failed"""

    pass


class MeshOperationError(VesselHullModelsError):
    """Error during mesh manipulation"""

    pass


class AcquisitionError(VesselHullModelsError):
    """Error acquiring model from repository"""

    pass


class APIClientError(AcquisitionError):
    """Error communicating with 3D model repository API"""

    pass


class RateLimitError(APIClientError):
    """API rate limit exceeded"""

    pass


class ModelNotFoundError(AcquisitionError):
    """Requested model not found in repository"""

    pass


class ParametricGenerationError(VesselHullModelsError):
    """Error generating parametric hull model"""

    pass


class DimensionValidationError(VesselHullModelsError):
    """Hull dimensions do not match expected specifications"""

    def __init__(self, message: str, expected: dict, actual: dict):
        super().__init__(message)
        self.expected = expected
        self.actual = actual


class FormatConversionError(VesselHullModelsError):
    """Error converting between mesh formats"""

    pass


class VisualizationError(VesselHullModelsError):
    """Error rendering 3D visualization"""

    pass
