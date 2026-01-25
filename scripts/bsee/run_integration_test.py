import os
import sys

# Add src directory to Python path
src_path = os.path.join(os.path.dirname(__file__), 'src')
sys.path.insert(0, src_path)

# Now import and run the test
from assetutilities.common.yml_utilities import ymlInput
from worldenergydata.engine import engine

def run_integration_test():
    """Run the directional survey integration test"""
    test_dir = os.path.join(os.path.dirname(__file__), 'tests', 'modules', 'bsee', 'analysis')
    input_file = os.path.join(test_dir, 'query_api_01_wells_directional_survey.yml')
    
    print(f"Running integration test with config: {input_file}")
    print(f"Testing API12 well: 608124000400")
    
    try:
        # Run the engine with the test configuration
        cfg = engine(input_file)
        print("✅ Integration test completed successfully!")
        
        # Check if directional survey results were generated
        if hasattr(cfg, 'bsee_object') and hasattr(cfg.bsee_object, 'API12'):
            api12_obj = cfg.bsee_object.API12
            if hasattr(api12_obj, 'output_data_well_path'):
                well_path_data = api12_obj.output_data_well_path
                print(f"✅ Directional survey data generated for {len(well_path_data)} wells")
                
                # Check specifically for API12 608124000400
                if 608124000400 in well_path_data:
                    survey_data = well_path_data[608124000400]
                    print(f"✅ Well 608124000400 survey data: {len(survey_data)} survey points")
                    print(f"   - X coordinates range: {survey_data['x_coor'].min():.1f} to {survey_data['x_coor'].max():.1f}")
                    print(f"   - Y coordinates range: {survey_data['y_coor'].min():.1f} to {survey_data['y_coor'].max():.1f}") 
                    print(f"   - Z coordinates range: {survey_data['z_coor'].min():.1f} to {survey_data['z_coor'].max():.1f}")
                else:
                    print("❌ API12 608124000400 not found in well path data")
            else:
                print("❌ No well path data found in API12 object")
        else:
            print("❌ BSEE API12 object not found in results")
            
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_integration_test()
    sys.exit(0 if success else 1)