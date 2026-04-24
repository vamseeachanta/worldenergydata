# Standard library imports
import logging  # noqa
import os  # noqa
from io import BytesIO  # noqa

# Third party imports
import pandas as pd  # noqa
import scrapy  # noqa
from colorama import Fore, Style
from colorama import init as colorama_init

# from twisted.internet import reactor, defer
from crochet import setup, wait_for
from loguru import logger  # noqa
from scrapy import FormRequest  # noqa
from scrapy.crawler import CrawlerRunner

# from scrapy.crawler import CrawlerProcess  # noqa
from scrapy.utils.response import (  # noqa useful while program is running
    open_in_browser,
)

setup()
colorama_init()

# Disable propagation of scrapy logs
logging.getLogger("scrapy").propagate = False


class BSEEDataSpider(scrapy.Spider):

    name = "API_well_data"
    # Starting URL for the spider
    start_urls = ["https://www.data.bsee.gov/Well/APD/Default.aspx"]

    # Initialize the spider with input item and configuration
    def __init__(self, input_item=None, cfg=None, data_store=None, *args, **kwargs):
        super(BSEEDataSpider, self).__init__(*args, **kwargs)
        self.input_item = input_item
        self.cfg = cfg
        self.data_store = data_store

    # Parse the initial response
    def parse(self, response):
        api_num = str([self.input_item["api12"]])
        api_label = self.input_item["label"]

        # Prepare form data for the first request
        first_request_data = self.cfg["data_retrieval"]["well"]["website"]["form_data"][
            "first_request"
        ].copy()
        first_request_data["ASPxFormLayout1$ASPxTextBoxAPI"] = api_num

        logger.debug(f"Data for API12 {api_label} ... START")

        # Submit the form and proceed to step2
        yield FormRequest.from_response(
            response, formdata=first_request_data, callback=self.step2
        )

    # Handle the response of the first form submission
    def step2(self, response):
        if response.status == 200:
            logger.success(
                f" {Fore.GREEN} Webpage's Data request is successful{Style.RESET_ALL}"
            )
        else:
            logger.error(
                f"{Fore.RED}Data request failed to webpage{Style.RESET_ALL}. Status code: {response.status}"  # noqa: E501
            )

        # Extract API number from input item
        api_num = str(self.input_item["api12"][0])

        # Prepare form data for the second request
        second_request_data = self.cfg["data_retrieval"]["well"]["website"][
            "form_data"
        ]["second_request"].copy()
        second_request_data["ASPxFormLayout1$ASPxTextBoxAPI"] = api_num

        # Submit the form and proceed to parse CSV data
        yield FormRequest.from_response(
            response, formdata=second_request_data, callback=self.parse_csv_data
        )

    # Parse the CSV data from the response
    def parse_csv_data(self, response):

        api_label = self.input_item["label"]
        output_path = os.path.join(self.cfg["Analysis"]["result_folder"], "Data")
        output_file_name = os.path.join(output_path, api_label + ".csv")

        if response.status == 200:
            logger.debug(f"Data for API12 {api_label} ...COMPLETE")
            response_csv = pd.read_csv(BytesIO(response.body))

            if response_csv.empty:
                logger.warning(
                    f"{Fore.RED}Empty DataFrame for API {api_label}. Skipping CSV file.{Style.RESET_ALL}"  # noqa: E501
                )
            else:
                with open(output_file_name, "wb") as f:
                    f.write(response.body)
                self.data_store["data"] = response_csv  # Store DataFrame in data_store

        else:
            logger.error(
                f"{Fore.RED}Failed to get the data for API .{api_label}. Status code: {response.status} {Style.RESET_ALL}"  # noqa: E501
            )
            self.data_store["data"] = pd.DataFrame()


# Define a class to run the Scrapy spider
class ScrapyRunnerAPI:
    def __init__(self):
        self.runner = CrawlerRunner(
            {
                "LOG_LEVEL": "CRITICAL",
            }
        )

    @wait_for(timeout=180.0)
    def run_spider(self, cfg, input_item):
        data_store = {}
        deferred = self.runner.crawl(
            BSEEDataSpider, input_item=input_item, cfg=cfg, data_store=data_store
        )
        deferred.addCallback(
            lambda _: data_store.get("data", pd.DataFrame())
        )  # Return DataFrame from data_store
        return deferred


if __name__ == "__main__":
    runner = ScrapyRunnerAPI()
    spider_bsee = BSEEDataSpider()
