import scrapy
from scrapy.utils.response import open_in_browser # useful while program is running
from scrapy.crawler import CrawlerProcess
from scrapy import FormRequest
import pandas as pd

class BSEEDataSpider(scrapy.Spider):

    name = 'API_well_data'
    start_urls = ['https://www.data.bsee.gov/Well/APD/Default.aspx']

    def parse(self, response):
        data = {
            'ASPxFormLayout1$ASPxTextBoxAPI': '608164024500',
            'ASPxFormLayout1$ASPxButtonSubmitQ': 'Submit Query'
        }
        yield FormRequest.from_response(response,formdata=data, callback=self.step2)

    def step2(self, response):

        data = {
            'ASPxFormLayout1$ASPxTextBoxAPI': '608164024500',
            '__EVENTTARGET': 'ASPxFormLayout2$btnCsvExport',
            '__EVENTARGUMENT': 'Click'
        }
        yield FormRequest.from_response(response,formdata=data, callback=self.parse_csv_data)

    def parse_csv_data(self, response): 
        with open('downloaded_data.csv', 'wb') as f:
            f.write(response.body)

def run_spider():
    process = CrawlerProcess()
    process.crawl(BSEEDataSpider)
    process.start()

if __name__ == "__main__":
    run_spider()

        