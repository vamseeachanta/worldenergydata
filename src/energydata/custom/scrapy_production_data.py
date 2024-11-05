import scrapy
from scrapy.utils.response import open_in_browser #noqa useful while program is running
from scrapy.crawler import CrawlerProcess #noqa
from scrapy import FormRequest #noqa

import pandas as pd #noqa
import os #noqa
from io import BytesIO #noqa
import logging #noqa
from colorama import Fore, Style
from colorama import init as colorama_init

colorama_init()

logging.getLogger('scrapy').propagate = False # to avoid displaying log outputs in terminal
class SpiderBsee(scrapy.Spider):

    name = 'Production_data'
    start_urls = ['https://www.data.bsee.gov/Production/ProductionData/Default.aspx']

    def __init__(self, input_item=None, cfg=None, *args, **kwargs):
        super(SpiderBsee, self).__init__(*args, **kwargs)
        self.input_item = input_item
        self.cfg = cfg

    def router(self, cfg):
        settings = {
            'LOG_LEVEL': 'CRITICAL',
            'REQUEST_FINGERPRINTER_IMPLEMENTATION': '2.7'  # to avoid the warning message
        }

        process = CrawlerProcess(settings=settings)

        master_settings = cfg['settings_master']
        for input_item in cfg['input']:
            input_item = {**master_settings, **input_item}
            process.crawl(SpiderBsee, input_item=input_item, cfg=cfg)

        process.start()

    def parse(self, response):
        lease_number = str(self.input_item['lease_number'])
        from_date = str(self.input_item['Duration']['from'])
        to_date = str(self.input_item['Duration']['to'])

        data = {
            'ASPxFormLayout1$ASPxTextBoxLN': lease_number,
            'ASPxFormLayout1$ASPxTextBoxDF': from_date,
            'ASPxFormLayout1$ASPxTextBoxDT': to_date,
            'ASPxFormLayout1$ASPxButtonSubmitQ': 'Submit Query'
        }
        yield FormRequest.from_response(response, formdata=data, callback=self.step2)
    
    def step2(self, response):
        if response.status == 200:
            print(f"Lease number {self.input_item['lease_number']}{Fore.GREEN} submission successful!{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}Failed to submit lease number{Style.RESET_ALL}. Status code: {response.status}")

        lease_number = self.input_item['lease_number']
        lease_number = str(lease_number)

        data = {
            'ASPxFormLayout1$ASPxTextBoxLN': lease_number,
            '__EVENTTARGET': 'ASPxFormLayout2$btnCsvExport',
            '__EVENTARGUMENT': 'Click',
        }
        yield FormRequest.from_response(response, formdata=data, callback=self.parse_csv_data)

    def parse_csv_data(self, response):

        label = self.input_item['label']
        lease_number = self.input_item['lease_number'] 
        file_path = os.path.join(r'src\energydata\tests\test_data\bsee\results\Data\by_API', f'{label}.csv')

        if response.status == 200:
            with open(file_path, 'wb') as f:
                f.write(response.body)
                response_csv = pd.read_csv(BytesIO(response.body))
                print()
                print(f"\n****The Scraped data of {lease_number} ****\n")
                print(response_csv)
        else:
            print(f"{Fore.RED}Failed to export CSV.{Style.RESET_ALL} Status code: {response.status}")