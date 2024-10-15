import os

from selenium import webdriver
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import pandas as pd

class bseedata:
    
    def __init__(self):
        pass


    def router(self, cfg):

        data_df_array = self.get_data(cfg)
        
        return cfg

    def get_data(self, cfg):
        data_df_array = []
        for input_item in cfg['input']:
            url = input_item['url']
            well_api12 = input_item['well_api12']
            df = self.extract_table_content(url, well_api12)
            self.save_to_csv(df, input_item, cfg)

            data_df_array.append(df)

        return data_df_array

    def save_to_csv(self, df, input_item, cfg):
        save_csv = input_item.get('save_csv', False)
        if save_csv:
            sheetname = input_item['label']
            csv_filename = os.path.join(cfg['Analysis']['result_folder'], sheetname + '.csv')
            df.to_csv(csv_filename, index=False, header=True)


    def extract_table_content(self, url,input_data):

        driver = webdriver.Chrome()

        driver.get(url)


        input_box = driver.find_element(By.XPATH, '//input[@name="ASPxFormLayout1$ASPxTextBoxAPI"]')
        submit_button = driver.find_element(By.XPATH, "(//div[@id='ASPxFormLayout1_ASPxButtonSubmitQ_CD'])[1]")
            
        CSV_button = driver.find_element(By.XPATH, "(//span[normalize-space()='CSV'])[1]")

        input_box.send_keys(input_data)
                    
        
        submit_button.click()

        CSV_button.click()

        # wait for the page to load
        driver.implicitly_wait(250)
        driver.quit()

        # Directory where the downloaded file is located
        from pathlib import Path

        home_dir = Path.home()

        download_directory = home_dir / 'Downloads'


        download_directory = str(download_directory)

        download_directory = download_directory.replace("\\","\\")

        
        for filename in os.listdir(download_directory):
            if filename.endswith('.tmp'):
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

        specified_directory = download_directory

        all_file_paths = get_file_paths(specified_directory)

        # Filter out the CSV files from all files
        csv_files = filter_csv_files(all_file_paths)

        s=str(csv_files[0])


        s=s.replace("\\","\\")
        df=pd.read_csv(s)


        print() 
        print()
        print()
        print(f"****Details of {input_data}***** \n\n")
        print(df)
        print()
        print()

        #For deleting the file immediately after extracting
        os.remove(s)
        
        return df




    def get_cfg_with_master_data(self, cfg):
        pass
        
        return cfg