# Standard library imports
import os
import requests
from bs4 import BeautifulSoup
from io import BytesIO
import pandas as pd
from colorama import Fore, Style
from colorama import init as colorama_init

colorama_init()

class BSEEDataScrapper:
    
    def __init__(self):
        pass

    def router(self, cfg):

        self.input_data(cfg)
        return cfg
    
    def input_data(self, cfg):

        for input_item in cfg['input']:
            self.get_data(cfg, input_item)

    def get_data(self, cfg, input_item):

        url = input_item['url']
        API_number = input_item['well_api12']

        session = requests.Session()  

        response = session.get(url) # GET request to the form page
        soup = BeautifulSoup(response.content, 'html.parser') 

        viewstate = soup.find('input', {'name': '__VIEWSTATE'})['value']
        eventvalidation = soup.find('input', {'name': '__EVENTVALIDATION'})['value']
        viewstate_generator = soup.find('input', {'name': '__VIEWSTATEGENERATOR'})['value']

        # POST request Payload for submitting the API number
        api_submit_payload = {
            '__EVENTTARGET': '',
            '__EVENTARGUMENT': '',
            '__VIEWSTATE': viewstate,
            '__VIEWSTATEGENERATOR': viewstate_generator,
            '__EVENTVALIDATION': eventvalidation,
            'ASPxFormLayout1$ASPxTextBoxAPI': API_number,  # The API number
            'ASPxFormLayout1$ASPxButtonSubmitQ': 'Submit Query',  # The submit button
        }

        # Submit the API form
        response = session.post(url, data=api_submit_payload)
        soup = BeautifulSoup(response.content, 'html.parser')

        if response.status_code == 200:
            print(f"API {API_number}{Fore.GREEN} submission successful!{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}Failed to submit API {API_number}{Style.RESET_ALL}. Status code: {response.status_code}")

        # For CSV export, extract required hidden fields
        viewstate = soup.find('input', {'name': '__VIEWSTATE'})['value']
        eventvalidation = soup.find('input', {'name': '__EVENTVALIDATION'})['value']
        viewstate_generator = soup.find('input', {'name': '__VIEWSTATEGENERATOR'})['value']

        csv_export_payload = {
            '__EVENTTARGET': 'ASPxFormLayout2$btnCsvExport',  # Targeting the CSV button
            '__EVENTARGUMENT': 'Click',
            '__VIEWSTATE': viewstate,
            '__VIEWSTATEGENERATOR': viewstate_generator,
            '__EVENTVALIDATION': eventvalidation
        }

        csv_response = session.post(url, data=csv_export_payload)

        label = input_item['label']
        csv_path = os.path.join(r'src\energydata\tests\test_data\bsee\results\Data', f'{label}.csv')

        if csv_response.status_code == 200:
            with open(csv_path, 'wb') as f:
                f.write(csv_response.content)
                df = pd.read_csv(BytesIO(csv_response.content))
                print()
                print(f"****The Scraped data of {API_number} ****\n\n")
                print(df)
        else:
            print(f"{Fore.RED}Failed to export CSV.{Style.RESET_ALL} Status code: {csv_response.status_code}")

    