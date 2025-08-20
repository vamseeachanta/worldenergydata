"""
Helper module for creating comprehensive test configurations.
"""

def get_complete_test_config(tmp_path):
    """
    Create a complete test configuration with all required parameters.
    
    Args:
        tmp_path: pytest tmp_path fixture for temporary directories
    
    Returns:
        dict: Complete configuration for BSEE tests
    """
    # Create necessary directories
    test_data_dir = tmp_path / 'test_data'
    bin_dir = test_data_dir / 'bin'
    apd_dir = bin_dir / 'apd'
    results_dir = tmp_path / 'results'
    
    # Create all directories
    for dir_path in [test_data_dir, bin_dir, apd_dir, results_dir]:
        dir_path.mkdir(parents=True, exist_ok=True)
    
    return {
        'basename': 'bsee',
        'meta': {
            'project': 'test_integration',
            'run_id': 'test_001'
        },
        'Analysis': {
            'analysis_root_folder': str(tmp_path),
            'result_folder': str(results_dir)
        },
        'parameters': {
            'filepath': {
                'data': str(test_data_dir),
                'bin_dir': str(bin_dir),
                'Well_APD_Default': str(bin_dir / 'Well_APD_Default'),
                'production': {
                    'zip': str(test_data_dir / 'zip' / 'production_raw'),
                    'bin': str(bin_dir / 'production_raw')
                },
                'APD': str(apd_dir),
                'apm': {
                    'zip': str(test_data_dir / 'zip' / 'apd'),
                    'bin': str(apd_dir)
                },
                'war': {
                    'zip': str(test_data_dir / 'zip' / 'war'),
                    'bin': str(bin_dir / 'war')
                }
            },
            'max_allowed_npt': 90,
            'borehole_codes': [
                {
                    "BOREHOLE_STAT_CD": "APD",
                    "BOREHOLE_STAT_DESC": "APPLICATION FOR PERMIT TO DRILL"
                },
                {
                    "BOREHOLE_STAT_CD": "COM",
                    "BOREHOLE_STAT_DESC": "BOREHOLE COMPLETED"
                },
                {
                    "BOREHOLE_STAT_CD": "DRL",
                    "BOREHOLE_STAT_DESC": "DRILLING ACTIVE"
                },
                {
                    "BOREHOLE_STAT_CD": "PA",
                    "BOREHOLE_STAT_DESC": "PERMANENTLY ABANDONED"
                }
            ],
            'refresh_flag': False
        },
        'data': {
            'input_file': str(test_data_dir / 'test_data.csv'),
            'refresh_flag': False
        },
        'analysis': {
            'flag': False,
            'type': 'production'
        },
        'type': {
            'data': False,
            'analysis': False,
            'results': False
        },
        'default': {
            'log_level': 'DEBUG',
            'config': {
                'overwrite': {
                    'output': True
                },
                'cfg_sensitivities': False
            }
        }
    }


def get_minimal_test_config(tmp_path):
    """
    Create a minimal test configuration with only required parameters.
    
    Args:
        tmp_path: pytest tmp_path fixture for temporary directories
    
    Returns:
        dict: Minimal configuration for BSEE tests
    """
    bin_dir = tmp_path / 'test_data' / 'bin'
    bin_dir.mkdir(parents=True, exist_ok=True)
    
    return {
        'basename': 'bsee',
        'parameters': {
            'filepath': {
                'apm': {
                    'bin': str(bin_dir)
                }
            },
            'borehole_codes': [],
            'refresh_flag': False
        },
        'data': {
            'refresh_flag': False
        }
    }