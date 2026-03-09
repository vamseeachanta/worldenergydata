import importlib
import pytest

try:
    AU_VERSION = importlib.metadata.version("assetutilities")
except Exception:
    import assetutilities
    AU_VERSION = assetutilities.__version__


@pytest.mark.contracts
def test_engine_importable():
    from assetutilities.engine import engine
    assert engine is not None

@pytest.mark.contracts
def test_FileManagement_importable():
    from assetutilities.common.file_management import FileManagement
    assert callable(FileManagement)

@pytest.mark.contracts
def test_WorkingWithYAML_importable():
    from assetutilities.common.yml_utilities import WorkingWithYAML
    assert callable(WorkingWithYAML)
