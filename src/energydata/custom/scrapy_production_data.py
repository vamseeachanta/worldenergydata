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

        master_settings = cfg['settings']
        for input_item in cfg['input']:
            input_item = {**master_settings, **input_item}
            process.crawl(SpiderBsee, input_item=input_item, cfg=cfg)

        process.start()

    def parse(self, response):
        
        first_request_data = self.cfg['form_data']['first_request']

        yield FormRequest.from_response(response, formdata=first_request_data, callback=self.step2)
    
    def step2(self, response):
        if response.status == 200:
            print(f"{Fore.GREEN} submitted given form data successfully!{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}Failed to submit the form data{Style.RESET_ALL}. Status code: {response.status}")

        second_request_data = self.cfg['form_data']['second_request']

        yield FormRequest.from_response(response, formdata=second_request_data, callback=self.parse_csv_data)

    def parse_csv_data(self, response):

        label = self.input_item['label'] 
        output_path = self.input_item['output_dir']
        file_path = os.path.join(output_path, f"{label}.csv")

        if response.status == 200:
            with open(file_path, 'wb') as f:
                f.write(response.body)
                response_csv = pd.read_csv(BytesIO(response.body))
                print()
                print("\n****The Scraped data of given parameter ****\n")
                print(response_csv)
        else:
            print(f"{Fore.RED}Failed to export CSV file.{Style.RESET_ALL} Status code: {response.status}")