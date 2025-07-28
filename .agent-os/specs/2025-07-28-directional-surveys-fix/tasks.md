# Spec Tasks

These are the tasks to be completed for the spec detailed in @.agent-os/specs/2025-07-28-directional-surveys-fix/spec.md

> Created: 2025-07-28
> Status: Ready for Implementation

## Tasks

- [x] 1. Fix prepare_well_paths method data structure references
  - [x] 1.1 Write unit tests for prepare_well_paths method
  - [x] 1.2 Correct well_data parameter handling to match expected dictionary structure
  - [x] 1.3 Fix self.output_data_well_df references to use self.output_data_api12_df
  - [x] 1.4 Ensure proper initialization of output_data_well_path dictionary
  - [x] 1.5 Verify all tests pass for prepare_well_paths method

- [x] 2. Fix process_survey_xyz coordinate calculation method
  - [x] 2.1 Write unit tests for process_survey_xyz mathematical calculations
  - [x] 2.2 Verify survey DataFrame processing logic matches legacy implementation
  - [x] 2.3 Test XYZ coordinate calculation algorithms are working correctly
  - [x] 2.4 Ensure proper handling of survey data edge cases (duplicates, zeros)
  - [x] 2.5 Verify all tests pass for process_survey_xyz method

- [x] 3. Fix add_relative_WH_positions wellhead adjustment method
  - [x] 3.1 Write unit tests for wellhead position calculations
  - [x] 3.2 Correct API12 DataFrame filtering to use proper data structure
  - [x] 3.3 Fix coordinate adjustment calculations using SURF_x_rel and SURF_y_rel
  - [x] 3.4 Test proper survey_xyz_wh_adjusted DataFrame creation
  - [x] 3.5 Verify all tests pass for add_relative_WH_positions method

- [ ] 4. Fix plot_field_wells visualization method
  - [ ] 4.1 Write unit tests for plotting functionality 
  - [ ] 4.2 Correct attribute references for accessing well path data
  - [ ] 4.3 Fix matplotlib 3D plotting integration with proper data access
  - [ ] 4.4 Ensure file saving functionality works with proper paths
  - [ ] 4.5 Verify all tests pass for plot_field_wells method

- [ ] 5. Integration testing and validation
  - [ ] 5.1 Run existing integration test query_api_01_wells_directional_survey_test.py
  - [ ] 5.2 Verify test passes with API12 well 608124000400 processing
  - [ ] 5.3 Test complete end-to-end directional surveys workflow
  - [ ] 5.4 Validate output data structures match expected format
  - [ ] 5.5 Verify all integration tests pass successfully