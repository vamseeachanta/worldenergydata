import scrapy
from scrapy.utils.response import open_in_browser
from scrapy.crawler import CrawlerProcess
from scrapy import FormRequest
import pandas as pd

class BSEEDataSpider(scrapy.Spider):

    name = 'API_well_data'
    start_urls = ['https://www.data.boem.gov/Well/Borehole/Default.aspx']

    def parse(self, response):
        data = {
            '__EVENTTARGET': '',
            '__EVENTARGUMENT': '',
            'ASPxFormLayout1$ASPxTextBoxAPI': '608164024500',
            'ASPxFormLayout1$ASPxButtonSubmitQ': 'Submit Query'
        }
        yield FormRequest.from_response(response,formdata=data, callback=self.step2)

    def step2(self, response):

        data = {
            '__EVENTTARGET': 'ASPxFormLayout2$btnCsvExport',
            '__EVENTARGUMENT': 'Click',
        }
        yield FormRequest.from_response(response,formdata=data, callback=self.parse_csv_data)

    def parse_csv_data(self, response): 
        pass

def run_spider():
    process = CrawlerProcess()
    process.crawl(BSEEDataSpider)
    process.start()

if __name__ == "__main__":
    run_spider()

        