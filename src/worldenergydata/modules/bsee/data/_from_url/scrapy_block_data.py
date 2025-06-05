# Standard library imports
from loguru import logger # noqa
import os  # noqa
from io import BytesIO  # noqa
import logging # noqa

# Third party imports
import pandas as pd  # noqa
import scrapy  # noqa
from colorama import Fore, Style
from colorama import init as colorama_init
from scrapy import FormRequest  # noqa
from scrapy.crawler import CrawlerRunner  # noqa

import warnings
warnings.filterwarnings("ignore", category=scrapy.exceptions.ScrapyDeprecationWarning)

#from scrapy.crawler import CrawlerProcess  # noqa
from scrapy.utils.response import (  # noqa useful while program is running
    open_in_browser,
)
#from twisted.internet import defer, reactor  # noqa

from assetutilities.common.utilities import is_dir_valid_func
from crochet import setup, wait_for

setup()

colorama_init()

logging.getLogger('scrapy').propagate = False
class BSEESpider(scrapy.Spider):

    name = 'well_data_by_block'
    start_urls = ['https://www.data.bsee.gov/Well/APD/Default.aspx']

    def __init__(self, input_item=None, cfg=None, data_store=None, *args, **kwargs):
        super(BSEESpider, self).__init__(*args, **kwargs)
        self.input_item = input_item
        self.cfg = cfg
        self.data_store = data_store

    def parse(self, response):
        bottom_block_num = str(self.input_item['bottom_block']['number'])
        area = str(self.input_item['bottom_block']['area'])

        first_request_data = self.cfg['data_retrieval']['block']['website']['form_data']['first_request'].copy()
        first_request_data['ASPxFormLayout1_ASPxComboBoxBBN_VI'] = bottom_block_num
        first_request_data['ASPxFormLayout1$ASPxComboBoxBBN'] = bottom_block_num
        first_request_data['ASPxFormLayout1$ASPxComboBoxBA$DDD$L'] = area

        logger.debug(f"Getting data for BLOCK {bottom_block_num} ... START")

        yield FormRequest.from_response(response, formdata=first_request_data, callback=self.step2)

    def step2(self, response):
        if response.status == 200:
            logger.success(f" {Fore.GREEN} Webpage's Data request is successful{Style.RESET_ALL}")
        else:
            logger.error(f"{Fore.RED}Data request failed to webpage {Style.RESET_ALL}. Status code: {response.status}")

        bottom_block_num = str(self.input_item['bottom_block']['number'])
        area = str(self.input_item['bottom_block']['area'])

        second_request_data = self.cfg['data_retrieval']['block']['website']['form_data']['second_request'].copy()
        second_request_data['ASPxFormLayout1_ASPxComboBoxBBN_VI'] = bottom_block_num
        second_request_data['ASPxFormLayout1$ASPxComboBoxBBN'] = bottom_block_num
        second_request_data['ASPxFormLayout1$ASPxComboBoxBA$DDD$L'] = area

        yield FormRequest.from_response(response, formdata=second_request_data, callback=self.parse_csv_data)

    def parse_csv_data(self, response):

        bottom_block_num = str(self.input_item['bottom_block']['number'])
        area = str(self.input_item['bottom_block']['area'])
        label = area + '_' + bottom_block_num
        output_path = os.path.join(self.cfg['Analysis']['result_folder'], 'Data')
        if output_path is None:
            result_folder = self.cfg['Analysis']['result_folder']
            output_path = os.path.join(result_folder, 'Data')
        analysis_root_folder = self.cfg['Analysis']['analysis_root_folder']
        is_dir_valid, output_path = is_dir_valid_func(output_path, analysis_root_folder)

        output_file = os.path.join(output_path, str(label) + '.csv')

        if response.status == 200:
            logger.debug(f"Getting data for BLOCK {bottom_block_num} ... COMPLETE")
            response_csv = pd.read_csv(BytesIO(response.body))
            
            if response_csv.empty:
                logger.warning(f"{Fore.RED}Empty dataframe for BLOCK {bottom_block_num}. Skipping CSV file.{Style.RESET_ALL}")
            else:
                with open(output_file, 'wb') as f:
                    f.write(response.body)
                    # logger.debug("\n****The Scraped data of given value ****\n")
                    # logger.debug(response_csv)
        else:
            logger.error(f"{Fore.RED}Failed to get the data for block {bottom_block_num}. Status code: {response.status} {Style.RESET_ALL}")
            self.data_store['data'] = pd.DataFrame()

class ScrapyRunnerBlock:
    def __init__(self):
        # Initialize the CrawlerRunner with specific settings
        self.runner = CrawlerRunner({
            'LOG_LEVEL': 'CRITICAL',
        })

    # Run the spider with the given configuration and input item
    @wait_for(timeout=120)  # Adjust timeout as needed
    def run_spider(self, cfg, input_item):
        data_store = {}
        deferred = self.runner.crawl(BSEESpider, input_item=input_item, cfg=cfg, data_store=data_store)
        deferred.addCallback(lambda _: data_store.get('data', pd.DataFrame()))  # Return DataFrame from data_store
        return deferred

if __name__ == "__main__":
    runner = ScrapyRunnerBlock()
    bsee_spider = BSEESpider()
     