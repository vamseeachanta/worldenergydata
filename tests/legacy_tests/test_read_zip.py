import zipfile

def test_read_zip_file():
    zip_path = r"data\bsee\APIRawData.zip"
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_file:
            # List files the Zip 
            file_names = [f for f in zip_file.namelist() if not f.endswith('/')]
            print("Files in the Zip archive:", file_names)
            
            for file_name in file_names:
                if not file_name.endswith('/'):
                    with zip_file.open(file_name) as file:
                        data = file.read()
                        print(f"Content of {file_name}:\n{data[:1000]}")

    except FileNotFoundError:
        print("Error: Zip file path not found.")

test_read_zip_file()
