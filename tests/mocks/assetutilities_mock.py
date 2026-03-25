"""
Mock implementation of assetutilities to allow tests to run.
This provides minimal implementations of assetutilities components used by worldenergydata.
"""

class WorkingWithYAML:
    """Mock YAML utilities"""
    def __init__(self):
        pass
    
    def read_yaml(self, filepath):
        return {}
    
    def write_yaml(self, data, filepath):
        pass

class ZipFilestoDf:
    """Mock ZIP to DataFrame converter"""
    def __init__(self):
        pass
    
    def convert(self, zip_path):
        import pandas as pd
        return pd.DataFrame()

class Transform:
    """Mock data transformer"""
    def __init__(self):
        pass
    
    def transform(self, data):
        return data

class SaveData:
    """Mock data saver"""
    def __init__(self):
        pass
    
    def save(self, data, path):
        pass

class VisualizationTemplatesPlotly:
    """Mock Plotly visualization templates"""
    def __init__(self):
        pass
    
    def plot(self, data):
        pass

def is_dir_valid_func(path):
    """Mock directory validation"""
    import os
    return os.path.isdir(path)

class Engine:
    """Mock assetutilities engine"""
    def __init__(self):
        pass
    
    def process(self, cfg):
        return cfg

# Create module structure
class MockModule:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

# Build mock module structure with all needed components
common = MockModule(
    yml_utilities=MockModule(WorkingWithYAML=WorkingWithYAML),
    utilities=MockModule(is_dir_valid_func=is_dir_valid_func),
    data=MockModule(Transform=Transform, SaveData=SaveData),
    visualization=MockModule(
        visualization_templates_plotly=MockModule(
            VisualizationTemplatesPlotly=VisualizationTemplatesPlotly
        )
    )
)

# The modules directory that's missing in the real package
modules = MockModule(
    zip_utilities=MockModule(
        zip_files_to_dataframe=MockModule(ZipFilestoDf=ZipFilestoDf)
    )
)

engine = Engine()