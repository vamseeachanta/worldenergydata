import os

def search_target_columns_partial_match(directories, target_columns):
    """
    Search for target columns in '_all_columns.csv' files across multiple directories using partial matches.
    """
    summary = []
    
    # Generate searchable terms from target columns
    search_terms = {term.strip("[]") for col in target_columns for term in col.split()}
    
    # Loop through each directory
    for input_directory in directories:
        print(f"Processing directory: {input_directory}")
        for filename in os.listdir(input_directory):
            if filename.endswith('_all_columns.csv'):
                file_path = os.path.join(input_directory, filename)

                try:
                    # Read the column names from the file
                    with open(file_path, 'r') as f:
                        file_columns = {line.strip() for line in f.readlines()}
                    
                    # Find partial matches
                    matched_terms = set()
                    for col in file_columns:
                        for term in search_terms:
                            if term in col:
                                matched_terms.add(term)

                    # Save results
                    summary.append({
                        'file': filename,
                        'directory': input_directory,
                        'matched': list(matched_terms),
                        'unmatched': list(search_terms - matched_terms),
                    })
                except Exception as e:
                    print(f"Error processing file {filename} in {input_directory}: {e}")

    txt_file_path = r'tests\modules\analysis'
    summary_file = os.path.join(txt_file_path, 'column_results.txt')
    with open(summary_file, 'w') as f:
        for entry in summary:
            f.write(f"Directory: {entry['directory']}\n")
            f.write(f"File: {entry['file']}\n")
            f.write(f"  Matched Terms: {', '.join(entry['matched'])}\n")
            f.write(f"  Unmatched Terms: {', '.join(entry['unmatched'])}\n")
            f.write("\n")
    
    print(f"Partial match search summary saved to {summary_file}")

# Define the directories to process
directories = [
    r'tests\modules\data\results\Data\by_API',
    r'tests\modules\data\results\Data\by_zip'
]

# Define the target columns
target_columns = {
    "API12", "Company Name", "Field Name", "Well Name", "Sidetrack and Bypass",
    "Spud Date", "Total Depth Date", "Well Purpose", "Water Depth", 
    "Total Measured Depth", "Total Vertical Depth", "Sidetrack KOP",
    "Surface Latitude", "Surface Longitude", "Bottom Latitude", "Bottom Longitude",
    "Wellbore Status", "Wellbore Status Date", "Completion Stub Code", "Casing Cut Code"
}

# Call the function
search_target_columns_partial_match(directories, target_columns)
