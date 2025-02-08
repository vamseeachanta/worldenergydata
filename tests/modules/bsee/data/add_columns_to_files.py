import os
import re
import csv

def convert_text_to_csv(input_folder, output_folder):
    # Create output directory if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)

    # Process each text file in the input directory
    for filename in os.listdir(input_folder):
        if filename.endswith('.txt'):
            input_path = os.path.join(input_folder, filename)
            output_path = os.path.join(output_folder, f"{os.path.splitext(filename)[0]}.csv")

            with open(input_path, 'r') as infile, open(output_path, 'w', newline='') as outfile:
                csv_writer = csv.writer(outfile)
                
                for line in infile:
                    # Extract values between quotes and clean whitespace
                    fields = re.findall(r'"\s*(.*?)\s*"', line.strip())
                    if fields:  # Only write rows with valid data
                        csv_writer.writerow(fields)

if __name__ == "__main__":
    text_folder = os.path.join('tests', 'modules', 'bsee', 'data', 'temp_delete')
    csv_folder = os.path.join('tests', 'modules', 'bsee', 'data', 'well_production_yearly')
    
    convert_text_to_csv(text_folder, csv_folder)
    print("Conversion completed successfully!")