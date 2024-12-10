import os

def search_target_columns(directories, target_columns):
    
    summary = []

    for input_directory in directories:
        print(f"Processing directory: {input_directory}")
        for filename in os.listdir(input_directory):
            if filename.endswith('_columns.csv'):
                file_path = os.path.join(input_directory, filename)

                try:
                    with open(file_path, 'r') as f:
                        file_columns = {line.strip() for line in f.readlines()}

                    found = file_columns.intersection(target_columns)
                    missing = target_columns - file_columns

                    summary.append({
                        'file': filename,
                        'directory': input_directory,
                        'found': list(found),
                        'missing': list(missing),
                    })
                except Exception as e:
                    print(f"Error processing file {filename} in {input_directory}: {e}")

    txt_file_path = r'tests\modules\bsee'
    summary_file = os.path.join(txt_file_path, 'find_column_results.txt')
    with open(summary_file, 'w') as f:
        for entry in summary:
            f.write(f"Directory: {entry['directory']}\n")
            f.write(f"File: {entry['file']}\n")
            f.write(f"  Found Columns: {', '.join(entry['found'])}\n")
            f.write(f"  Missing Columns: {', '.join(entry['missing'])}\n")
            f.write("\n")
    
    print(f"Search summary saved to {summary_file}")

directories = [
    r'tests\modules\bsee\results\Data\by_API',
    r'tests\modules\bsee\results\Data\by_zip'
]

target_columns = {
    "API12", "Company Name", "Field Name", "Well Name", "Sidetrack and Bypass",
    "Spud Date", "Total Depth Date", "Well Purpose", "Water Depth", 
    "Total Measured Depth", "Total Vertical Depth", "Sidetrack KOP",
    "Surface Latitude", "Surface Longitude", "Bottom Latitude", "Bottom Longitude",
    "Wellbore Status", "Wellbore Status Date", "Completion Stub Code", "Casing Cut Code"
}

search_target_columns(directories, target_columns)
