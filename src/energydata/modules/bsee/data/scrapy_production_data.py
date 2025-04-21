import scrapy
from scrapy.utils.response import open_in_browser  # noqa useful while program is running
from scrapy.crawler import CrawlerRunner  # noqa
from twisted.internet import reactor, defer  # noqa
from scrapy import FormRequest  # noqa

import pandas as pd  # noqa
import os  # noqa
from io import BytesIO  # noqa
import logging  # noqa
from colorama import Fore, Style
from colorama import init as colorama_init

from crochet import setup, wait_for

colorama_init()

# Initialize Crochet
setup()

logging.getLogger('scrapy').propagate = False  # to avoid displaying log outputs in terminal


class SpiderBsee(scrapy.Spider):
    name = 'Production_data'
    start_urls = ['https://www.data.bsee.gov/Production/ProductionData/Default.aspx']
    custom_settings = {
            "REQUEST_FINGERPRINTER_IMPLEMENTATION": "2.7"
        }

    def __init__(self, input_item=None, cfg=None, data_store=None,*args, **kwargs):
        super(SpiderBsee, self).__init__(*args, **kwargs)
        self.input_item = input_item
        self.cfg = cfg
        self.data_store = data_store

    def parse(self, response):

        lease_num = str(self.input_item['lease_number'])
        start = str(self.input_item['Duration']['from'])
        end = str(self.input_item['Duration']['to'])

        first_request_data = self.cfg['data_retrieval']['production']['website']['form_data']['first_request']
        first_request_data['ASPxFormLayout1$ASPxTextBoxLN'] = lease_num
        first_request_data['ASPxFormLayout1$ASPxTextBoxDF'] = start
        first_request_data['ASPxFormLayout1$ASPxTextBoxDT'] = end

        yield FormRequest.from_response(response, formdata=first_request_data, callback=self.step2)

    def step2(self, response):
        if response.status == 200:
            print(f"{Fore.GREEN} submitted given form data successfully!{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}Failed to submit the form data{Style.RESET_ALL}. Status code: {response.status}")

        lease_num = str(self.input_item['lease_number'])
        start = str(self.input_item['Duration']['from'])
        end = str(self.input_item['Duration']['to'])

        second_request_data = self.cfg['data_retrieval']['production']['website']['form_data']['second_request']
        second_request_data['ASPxFormLayout1$ASPxTextBoxLN'] = lease_num
        second_request_data['ASPxFormLayout1$ASPxTextBoxDF'] = start
        second_request_data['ASPxFormLayout1$ASPxTextBoxDT'] = end

        yield FormRequest.from_response(response, formdata=second_request_data, callback=self.parse_csv_data)

    def parse_csv_data(self, response):
        lease_num = self.input_item['lease_number']
        label = self.input_item['label']
        output_path = output_path = os.path.join(self.cfg['Analysis']['result_folder'], 'Data')
        output_file = os.path.join(output_path, str(label) + '.csv')

        if response.status == 200:
            response_csv = pd.read_csv(BytesIO(response.body))
            
            if response_csv.empty:
                print(f"{Fore.RED}Empty DataFrame for lease {lease_num}. Skipping CSV file.{Style.RESET_ALL}")
            else:
                with open(output_file, 'wb') as f:
                    f.write(response.body)
                    logging.debug("\n****The Scraped data of given value ****\n")
                    logging.debug(response_csv)
                    logging.info(f"Getting data for LEASE {lease_num} ... COMPLETE")

                self.data_store['data'] = response_csv  # Store DataFrame in data_store
                
        else:
            print(f"{Fore.RED}Failed to export CSV file.{Style.RESET_ALL} Status code: {response.status}")
            self.data_store['data'] = pd.DataFrame()

# Class to run the Scrapy spider
class ScrapyRunnerProduction:
    def __init__(self):
        self.runner = CrawlerRunner({
            'LOG_LEVEL': 'CRITICAL',
            'REQUEST_FINGERPRINTER_IMPLEMENTATION': '2.7'
        })

    @wait_for(timeout=60.0) 
    def run_spider(self, cfg, input_item):
        data_store = {}
        deferred = self.runner.crawl(SpiderBsee, input_item=input_item, cfg=cfg, data_store=data_store)
        deferred.addCallback(lambda _: data_store.get('data', pd.DataFrame()))  # Return DataFrame from data_store
        return deferred

if __name__ == "__main__":
    runner = ScrapyRunnerProduction()
    spider_bsee = SpiderBsee()

    