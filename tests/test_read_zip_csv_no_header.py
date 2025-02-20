import pandas as pd
import zipfile

def read_zip_csv_no_header(zip_filepath, csv_filename, delimiter=',', column_names=None):
    """
    Reads a delimited CSV file within a ZIP archive, handling cases without a header row.

    Args:
        zip_filepath (str): Path to the ZIP file.
        csv_filename (str): Name of the CSV file within the ZIP archive.
        delimiter (str, optional): Delimiter used in the CSV file. Defaults to ','.
        column_names (list, optional): List of column names to use. If None, default names will be assigned (0, 1, 2...).

    Returns:
        pandas.DataFrame: A DataFrame containing the data from the CSV file.
    """
    with zipfile.ZipFile(zip_filepath, 'r') as zf:
        with zf.open(csv_filename) as csvf:
            df = pd.read_csv(csvf, sep=delimiter, header=None, names=column_names)
    return df

# Example usage:
zip_file_path = 'data.zip'
csv_file_name = 'data.csv'
# Assuming the CSV has 3 columns, if you know the names, replace with: ['col1', 'col2', 'col3']
column_names = None
df = read_zip_csv_no_header(zip_file_path, csv_file_name, delimiter=',', column_names=column_names)
print(df)