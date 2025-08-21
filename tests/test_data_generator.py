"""
Test Data Generator for BSEE Data Processing Pipelines
Creates realistic test data files to enable actual pipeline testing
This will dramatically increase code coverage by running real data processing
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import yaml
from pathlib import Path
import zipfile
import io


class BSEETestDataGenerator:
    """Generate realistic BSEE test data for comprehensive pipeline testing"""
    
    def __init__(self, output_dir="tests/test_data/bsee"):
        """Initialize test data generator"""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # API well numbers for testing
        self.test_apis = [
            "177154051100",  # Anchor field
            "177154051200",  # Julia field
            "177154051300",  # Jack field
            "177154051400",  # St. Malo field
            "608174123500",  # Test well
        ]
        
        # Lease numbers
        self.test_leases = [
            "OCS-G-35364",
            "OCS-G-35365",
            "OCS-G-35366",
            "OCS-G-32684",
            "OCS-G-32685",
        ]
        
        # Field names
        self.field_names = ["ANCHOR", "JULIA", "JACK", "ST MALO", "TEST FIELD"]
        
    def generate_production_data(self, num_months=24):
        """Generate production data CSV file"""
        print("Generating production data...")
        
        records = []
        start_date = datetime(2022, 1, 1)
        
        for api in self.test_apis:
            for month in range(num_months):
                prod_date = start_date + timedelta(days=30*month)
                
                # Generate realistic production values with decline
                initial_oil = np.random.uniform(5000, 15000)
                decline_factor = 0.95 ** month  # 5% monthly decline
                
                record = {
                    'API_WELL_NUMBER': api,
                    'PRODUCTION_DATE': prod_date.strftime('%Y-%m-%d'),
                    'PRODUCTION_DATETIME': prod_date.strftime('%Y-%m-%d %H:%M:%S'),
                    'OIL_VOLUME': int(initial_oil * decline_factor * np.random.uniform(0.9, 1.1)),
                    'GAS_VOLUME': int(initial_oil * 5 * decline_factor * np.random.uniform(0.8, 1.2)),
                    'WATER_VOLUME': int(initial_oil * 0.3 * (1.1 ** month) * np.random.uniform(0.9, 1.1)),  # Water increases
                    'LEASE_NUMBER': self.test_leases[self.test_apis.index(api)],
                    'FIELD_NAME': self.field_names[self.test_apis.index(api)],
                    'WELL_NAME': f"WELL_{api[-4:]}",
                    'COMPLETION_NAME': f"COMP_{api[-4:]}",
                    'DAYS_ON_PRODUCTION': 30,
                    'CHOKE_SIZE': np.random.uniform(20, 64),
                    'WELL_STATUS': 'ACTIVE' if decline_factor > 0.3 else 'SHUT-IN'
                }
                records.append(record)
        
        df = pd.DataFrame(records)
        
        # Save as CSV
        csv_path = self.output_dir / "production_data.csv"
        df.to_csv(csv_path, index=False)
        
        # Also save as Excel
        excel_path = self.output_dir / "production_data.xlsx"
        df.to_excel(excel_path, index=False, sheet_name='Production')
        
        print(f"Created production data: {csv_path}")
        return df
    
    def generate_well_data(self):
        """Generate well master data"""
        print("Generating well data...")
        
        well_data = []
        for i, api in enumerate(self.test_apis):
            well_data.append({
                'API_WELL_NUMBER': api,
                'WELL_NAME': f"WELL_{api[-4:]}",
                'LEASE_NUMBER': self.test_leases[i],
                'FIELD_NAME': self.field_names[i],
                'WATER_DEPTH': np.random.uniform(4000, 7000),
                'TOTAL_DEPTH': np.random.uniform(20000, 35000),
                'SPUD_DATE': (datetime(2020, 1, 1) + timedelta(days=i*60)).strftime('%Y-%m-%d'),
                'COMPLETION_DATE': (datetime(2020, 6, 1) + timedelta(days=i*60)).strftime('%Y-%m-%d'),
                'STATUS': 'ACTIVE',
                'OPERATOR': 'TEST OPERATOR',
                'LONGITUDE': -90.0 + np.random.uniform(-2, 2),
                'LATITUDE': 27.0 + np.random.uniform(-2, 2),
                'AREA': 'WALKER RIDGE',
                'BLOCK': np.random.randint(100, 999),
                'WELL_TYPE': 'OIL',
                'BOTTOM_HOLE_PRESSURE': np.random.uniform(8000, 12000),
                'BOTTOM_HOLE_TEMPERATURE': np.random.uniform(200, 300)
            })
        
        df = pd.DataFrame(well_data)
        
        # Save well data
        csv_path = self.output_dir / "well_data.csv"
        df.to_csv(csv_path, index=False)
        
        excel_path = self.output_dir / "well_data.xlsx"
        df.to_excel(excel_path, index=False, sheet_name='Wells')
        
        print(f"Created well data: {csv_path}")
        return df
    
    def generate_directional_survey(self):
        """Generate directional survey data"""
        print("Generating directional survey data...")
        
        survey_data = []
        for api in self.test_apis[:2]:  # Just for first 2 wells
            depths = range(0, 25000, 1000)
            for depth in depths:
                survey_data.append({
                    'API_WELL_NUMBER': api,
                    'MEASURED_DEPTH': depth,
                    'INCLINATION': min(depth/500, 85),  # Increase to 85 degrees max
                    'AZIMUTH': 45 + np.random.uniform(-10, 10),
                    'TVD': depth * np.cos(np.radians(min(depth/500, 85))),
                    'NORTHING': depth * np.sin(np.radians(min(depth/500, 85))) * np.cos(np.radians(45)),
                    'EASTING': depth * np.sin(np.radians(min(depth/500, 85))) * np.sin(np.radians(45)),
                    'DOGLEG_SEVERITY': np.random.uniform(0, 3),
                    'SURVEY_DATE': datetime(2020, 1, 1).strftime('%Y-%m-%d')
                })
        
        df = pd.DataFrame(survey_data)
        
        csv_path = self.output_dir / "directional_survey.csv"
        df.to_csv(csv_path, index=False)
        
        print(f"Created directional survey: {csv_path}")
        return df
    
    def generate_completion_data(self):
        """Generate completion data"""
        print("Generating completion data...")
        
        completion_data = []
        for api in self.test_apis:
            # Multiple completions per well
            for comp in range(1, np.random.randint(2, 5)):
                completion_data.append({
                    'API_WELL_NUMBER': api,
                    'COMPLETION_NAME': f"COMP_{api[-4:]}_{comp}",
                    'COMPLETION_DATE': datetime(2020, 6, 1).strftime('%Y-%m-%d'),
                    'TOP_MD': 18000 + comp * 500,
                    'BOTTOM_MD': 18500 + comp * 500,
                    'PERFORATION_TOP': 18100 + comp * 500,
                    'PERFORATION_BOTTOM': 18400 + comp * 500,
                    'COMPLETION_TYPE': 'PERFORATED',
                    'SAND_CONTROL': 'GRAVEL PACK',
                    'TUBING_SIZE': 5.5,
                    'PACKER_DEPTH': 17500 + comp * 500,
                    'STATUS': 'ACTIVE'
                })
        
        df = pd.DataFrame(completion_data)
        
        csv_path = self.output_dir / "completion_data.csv"
        df.to_csv(csv_path, index=False)
        
        print(f"Created completion data: {csv_path}")
        return df
    
    def generate_lease_data(self):
        """Generate lease data"""
        print("Generating lease data...")
        
        lease_data = []
        for i, lease in enumerate(self.test_leases):
            lease_data.append({
                'LEASE_NUMBER': lease,
                'LEASE_NAME': f"LEASE_{lease[-4:]}",
                'OPERATOR': 'TEST OPERATOR',
                'FIELD_NAME': self.field_names[i],
                'WATER_DEPTH': np.random.uniform(4000, 7000),
                'AREA': 'WALKER RIDGE',
                'BLOCK': np.random.randint(100, 999),
                'LEASE_EFFECTIVE_DATE': datetime(2015, 1, 1).strftime('%Y-%m-%d'),
                'LEASE_EXPIRATION_DATE': datetime(2030, 1, 1).strftime('%Y-%m-%d'),
                'LEASE_STATUS': 'ACTIVE',
                'ACREAGE': np.random.uniform(5000, 10000),
                'ROYALTY_RATE': 0.1875  # 18.75% standard
            })
        
        df = pd.DataFrame(lease_data)
        
        csv_path = self.output_dir / "lease_data.csv"
        df.to_csv(csv_path, index=False)
        
        print(f"Created lease data: {csv_path}")
        return df
    
    def generate_test_config(self):
        """Generate test configuration YAML files"""
        print("Generating test configurations...")
        
        # Basic BSEE config
        bsee_config = {
            'meta': {
                'library': 'worldenergydata',
                'basename': 'bsee',
                'label': 'test_run'
            },
            'basename': 'bsee',
            'default': {
                'log_level': 'INFO',
                'config': {
                    'overwrite': {
                        'output': True
                    }
                }
            },
            'data_source': {
                'production': str(self.output_dir / 'production_data.csv'),
                'wells': str(self.output_dir / 'well_data.csv'),
                'completions': str(self.output_dir / 'completion_data.csv'),
                'leases': str(self.output_dir / 'lease_data.csv')
            },
            'query': {
                'flag': True,
                'api_list': self.test_apis[:2],
                'date_range': {
                    'start': '2022-01-01',
                    'end': '2023-12-31'
                }
            },
            'Analysis': {
                'analysis_root_folder': str(self.output_dir / 'results')
            }
        }
        
        config_path = self.output_dir / "test_bsee_config.yml"
        with open(config_path, 'w') as f:
            yaml.dump(bsee_config, f, default_flow_style=False)
        
        print(f"Created config: {config_path}")
        
        # Custom analysis config
        custom_config = {
            'meta': {
                'library': 'worldenergydata',
                'basename': 'bsee_custom',
                'label': 'test_custom'
            },
            'basename': 'bsee_custom',
            'drilling_n_completion_days': {
                'flag': True
            },
            'custom_analysis': {
                'flag': False
            },
            'filepath': {
                'leases': str(self.output_dir / 'lease_data.csv'),
                'production': str(self.output_dir / 'production_data.csv')
            },
            'Analysis': {
                'analysis_root_folder': str(self.output_dir / 'results')
            }
        }
        
        custom_config_path = self.output_dir / "test_custom_config.yml"
        with open(custom_config_path, 'w') as f:
            yaml.dump(custom_config, f, default_flow_style=False)
        
        print(f"Created custom config: {custom_config_path}")
        
        return bsee_config, custom_config
    
    def create_zip_archives(self):
        """Create ZIP archives of test data for testing zip processing"""
        print("Creating ZIP archives...")
        
        # Create production data ZIP
        zip_path = self.output_dir / "production_data.zip"
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.write(self.output_dir / "production_data.csv", "production_data.csv")
            zf.write(self.output_dir / "well_data.csv", "well_data.csv")
        
        print(f"Created ZIP: {zip_path}")
        
        return zip_path
    
    def generate_all_test_data(self):
        """Generate all test data files"""
        print("\n" + "="*60)
        print("GENERATING COMPREHENSIVE TEST DATA FOR BSEE PIPELINES")
        print("="*60 + "\n")
        
        # Generate all data files
        production_df = self.generate_production_data()
        well_df = self.generate_well_data()
        survey_df = self.generate_directional_survey()
        completion_df = self.generate_completion_data()
        lease_df = self.generate_lease_data()
        
        # Generate configs
        bsee_config, custom_config = self.generate_test_config()
        
        # Create ZIP archives
        zip_path = self.create_zip_archives()
        
        # Summary
        print("\n" + "="*60)
        print("TEST DATA GENERATION COMPLETE!")
        print("="*60)
        print(f"\nGenerated files in: {self.output_dir}")
        print(f"- Production records: {len(production_df)}")
        print(f"- Well records: {len(well_df)}")
        print(f"- Survey points: {len(survey_df)}")
        print(f"- Completions: {len(completion_df)}")
        print(f"- Leases: {len(lease_df)}")
        print("\nReady for pipeline testing!")
        
        return {
            'production': production_df,
            'wells': well_df,
            'survey': survey_df,
            'completions': completion_df,
            'leases': lease_df,
            'config_path': self.output_dir / "test_bsee_config.yml",
            'custom_config_path': self.output_dir / "test_custom_config.yml",
            'zip_path': zip_path
        }


if __name__ == "__main__":
    # Generate all test data
    generator = BSEETestDataGenerator()
    test_data = generator.generate_all_test_data()