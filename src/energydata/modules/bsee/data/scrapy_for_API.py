# Standard library imports
import logging  # noqa
import os  # noqa
from io import BytesIO  # noqa

# Third party imports
import pandas as pd  # noqa
import scrapy  # noqa
from colorama import Fore, Style
from colorama import init as colorama_init
from scrapy import FormRequest  # noqa
from scrapy.crawler import CrawlerRunner
#from twisted.internet import reactor, defer
from crochet import setup, wait_for
#from scrapy.crawler import CrawlerProcess  # noqa
from scrapy.utils.response import (  # noqa useful while program is running
    open_in_browser,
)

setup()

# Initialize colorama for colored terminal output
colorama_init()

# Disable propagation of scrapy logs
logging.getLogger('scrapy').propagate = False

# Define a Scrapy Spider class 
class BSEEDataSpider(scrapy.Spider):

    name = 'API_well_data'
    # Starting URL for the spider
    start_urls = ['https://www.data.bsee.gov/Well/APD/Default.aspx']

    # Initialize the spider with input item and configuration
    def __init__(self, input_item=None, cfg=None, *args, **kwargs):
        super(BSEEDataSpider, self).__init__(*args, **kwargs)
        self.input_item = input_item
        self.cfg = cfg

    # Parse the initial response
    def parse(self, response):
        # Extract API number from input item
        api_num = str(self.input_item['well_api12'])

        # Prepare form data for the first request
        first_request_data = self.cfg['form_data']['first_request'].copy()
        first_request_data['ASPxFormLayout1$ASPxTextBoxAPI'] = api_num

        # Submit the form and proceed to step2
        yield FormRequest.from_response(response, formdata=first_request_data, callback=self.step2)

    # Handle the response of the first form submission
    def step2(self, response):
        if response.status == 200:
            print(f" {Fore.GREEN} submitted given form data successfully!{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}Failed to submit the form data {Style.RESET_ALL}. Status code: {response.status}")

        # Extract API number from input item
        api_num = str(self.input_item['well_api12'])

        # Prepare form data for the second request
        second_request_data = self.cfg['form_data']['second_request'].copy()
        second_request_data['ASPxFormLayout1$ASPxTextBoxAPI'] = api_num

        # Submit the form and proceed to parse CSV data
        yield FormRequest.from_response(response, formdata=second_request_data, callback=self.parse_csv_data)

    # Parse the CSV data from the response
    def parse_csv_data(self, response):
        # Extract label and output directory from input item
        label = self.input_item['label']
        output_path = self.input_item['output_dir']
        file_path = os.path.join(output_path, f"{label}.csv")

        if response.status == 200:
            # Write the response body to a CSV file
            with open(file_path, 'wb') as f:
                f.write(response.body)
                response_csv = pd.read_csv(BytesIO(response.body))
                print()
                print("\n****The Scraped data of given value ****\n")
                print(response_csv)
        else:
            print(f"{Fore.RED}Failed to export CSV file.{Style.RESET_ALL} Status code: {response.status}")

# Define a class to run the Scrapy spider
class ScrapyRunnerAPI:
    def __init__(self):
        self.runner = CrawlerRunner({
            'LOG_LEVEL': 'CRITICAL',
            'REQUEST_FINGERPRINTER_IMPLEMENTATION': '2.7'
        })

    @wait_for(timeout=60.0) 
    def run_spider(self, cfg, input_item):
        deferred = self.runner.crawl(BSEEDataSpider, input_item=input_item, cfg=cfg)
        return deferred

if __name__ == "__main__":
    runner = ScrapyRunnerAPI()
    spider_bsee = BSEEDataSpider()