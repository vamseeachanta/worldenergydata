# Standard library imports
import os
import requests
from bs4 import BeautifulSoup

import pandas as pd


class BSEEDataScrapper:
    
    def __init__(self):
        pass

    def router(self, cfg):

        self.get_data(cfg)
        return cfg

    def get_data(self, cfg):
        
        # Step 1: Start with a GET request to the form page
        url = cfg['input'][0]['url']
        API_number = cfg['input'][0]['well_api12']
        session = requests.Session()  

        response = session.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract dynamic form fields from the initial GET request
        viewstate = soup.find('input', {'name': '__VIEWSTATE'})['value']
        eventvalidation = soup.find('input', {'name': '__EVENTVALIDATION'})['value']
        viewstate_generator = soup.find('input', {'name': '__VIEWSTATEGENERATOR'})['value']

        # Step 2: Construct the POST request payload for submitting the API number
        api_submit_payload = {
            '__EVENTTARGET': '',
            '__EVENTARGUMENT': '',
            '__VIEWSTATE': viewstate,
            '__VIEWSTATEGENERATOR': viewstate_generator,
            '__EVENTVALIDATION': eventvalidation,
            'ASPxFormLayout1$ASPxTextBoxAPI': API_number,  # The API number
            'ASPxFormLayout1$ASPxButtonSubmitQ': 'Submit Query',  # The submit button
        }

        # Step 3: Submit the API form
        response = session.post(url, data=api_submit_payload)
        soup = BeautifulSoup(response.content, 'html.parser')

        # Check if the API submission was successful
        if response.status_code == 200:
            print("API number submitted successfully.")
        else:
            print(f"Failed to submit API number. Status code: {response.status_code}")

        # Step 4: After form submission, extract the updated dynamic fields (if they exist)
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

        # Step 6: Submit the CSV export request
        csv_response = session.post(url, data=csv_export_payload)

        csv_path = os.path.join(r'src\energydata\tests\test_data\bsee\results', 'output.csv')

        # Step 7: Check and save the CSV response
        if csv_response.status_code == 200:
            with open(csv_path, 'wb') as f:
                f.write(csv_response.content)
                print("CSV file downloaded successfully!")
        else:
            print(f"Failed to export CSV. Status code: {csv_response.status_code}")

    