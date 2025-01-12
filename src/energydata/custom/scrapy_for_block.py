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
from scrapy.crawler import CrawlerRunner # noqa
from twisted.internet import reactor, defer # noqa
#from scrapy.crawler import CrawlerProcess  # noqa
from scrapy.utils.response import (  # noqa useful while program is running
    open_in_browser,
)

colorama_init()

logging.getLogger('scrapy').propagate = False
class BSEESpider(scrapy.Spider):

    name = 'API_well_data'
    start_urls = ['https://www.data.bsee.gov/Well/APD/Default.aspx']

    def __init__(self, input_item=None, cfg=None, *args, **kwargs):
        super(BSEESpider, self).__init__(*args, **kwargs)
        self.input_item = input_item
        self.cfg = cfg

    def parse(self, response):

        bottom_block_num = str(self.input_item['bottom_block'])

        first_request_data = self.cfg['form_data']['first_request'].copy()
        first_request_data['ASPxFormLayout1_ASPxComboBoxBBN_VI'] = bottom_block_num
        first_request_data['ASPxFormLayout1$ASPxComboBoxBBN'] = bottom_block_num

        yield FormRequest.from_response(response, formdata=first_request_data, callback=self.step2)

    def step2(self, response):
        if response.status == 200:
            print(f" {Fore.GREEN} submitted given form data successfully!{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}Failed to submit the form data {Style.RESET_ALL}. Status code: {response.status}")

        bottom_block_num = str(self.input_item['bottom_block'])

        second_request_data = self.cfg['form_data']['second_request'].copy()
        second_request_data['ASPxFormLayout1_ASPxComboBoxBBN_VI'] = bottom_block_num
        second_request_data['ASPxFormLayout1$ASPxComboBoxBBN'] = bottom_block_num

        yield FormRequest.from_response(response, formdata=second_request_data, callback=self.parse_csv_data)

    def parse_csv_data(self, response):

        label = self.input_item['label']
        output_path = self.input_item['output_dir']
        file_path = os.path.join(output_path, f"{label}.csv")

        if response.status == 200:
            with open(file_path, 'wb') as f:
                f.write(response.body)
                response_csv = pd.read_csv(BytesIO(response.body)) # For displaying data
                print()
                print("\n****The Scraped data of given value ****\n")
                print(response_csv)
        else:
            print(f"{Fore.RED}Failed to export CSV file.{Style.RESET_ALL} Status code: {response.status}")

def run_spider(cfg, input_items):
    runner = CrawlerRunner({
        'LOG_LEVEL': 'CRITICAL',
        'REQUEST_FINGERPRINTER_IMPLEMENTATION': '2.7'
    })

    @defer.inlineCallbacks
    def crawl():
        for input_item in input_items:
            yield runner.crawl(BSEESpider, input_item=input_item, cfg=cfg)
        reactor.stop()

    crawl()
    reactor.run()