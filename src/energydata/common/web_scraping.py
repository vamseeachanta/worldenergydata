from selenium import webdriver
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import pandas as pd

def extract_table_content(url, input_data):

    driver = webdriver.Chrome()

    driver.get(url)


    input_box = driver.find_element(By.XPATH, '//input[@name="ASPxFormLayout1$ASPxTextBoxAPI"]')
    submit_button = driver.find_element(By.XPATH, "(//div[@id='ASPxFormLayout1_ASPxButtonSubmitQ_CD'])[1]")

    CSV_button = driver.find_element(By.XPATH, "(//span[normalize-space()='CSV'])[1]")

    input_box.send_keys(input_data)

    # Clicking on the submit button
    submit_button.click()

    CSV_button.click()

    # In order to Wait for the page to load
    driver.implicitly_wait(250)
    driver.quit()


extract_table_content("https://www.data.bsee.gov/Well/APD/Default.aspx",608174149400)# GIVE THE INPUTS HERE

import os

# Directory where the downloaded file is located
from pathlib import Path

home_dir = Path.home()

download_directory = home_dir / 'Downloads'


download_directory = str(download_directory)

download_directory = download_directory.replace("\\","\\")

# Loop through files in the directory
for filename in os.listdir(download_directory):
    # Check if the file ends with .tmp extension
    if filename.endswith('.tmp'):
        # Rename the file to change the extension to .csv
        os.rename(os.path.join(download_directory, filename), os.path.join(download_directory, filename[:-4] + '.csv'))



def get_file_paths(directory):
    file_paths = []
    for root, _, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            file_paths.append(file_path)
    return file_paths

def filter_csv_files(file_paths):
    csv_files = [file_path for file_path in file_paths if file_path.endswith('.csv')]
    return csv_files

# Specify the directory where files are located
specified_directory = download_directory

# Get the paths of all files in the specified directory and its subdirectories
all_file_paths = get_file_paths(specified_directory)

# Filter out the CSV files from all files
csv_files = filter_csv_files(all_file_paths)

# Print the paths of CSV files
print("CSV files in the specified directory and its subdirectories:")
s=str(csv_files[0])

s=s.replace("\\","\\")
df=pd.read_csv(s)
print(df.to_string())