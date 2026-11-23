import os

import requests
from bs4 import BeautifulSoup

from worldenergydata.common.logging import get_logger

logger = get_logger(__name__)


class GetWellProdDataFromWebsite:

    def __init__(self):
        pass

    def router(self, cfg):

        self.get_well_prod_data(cfg)
        return cfg

    def get_well_prod_data(self, cfg):

        url = "https://www.data.bsee.gov/Main/OGOR-A.aspx"

        save_dir = cfg["settings"]["out_dir"]
        os.makedirs(save_dir, exist_ok=True)

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"  # noqa: E501
        }

        # Fetch the page content
        response = requests.get(url, headers=headers, timeout=120)
        soup = BeautifulSoup(response.content, "html.parser")

        links = soup.find_all("a", string="Delimit")

        if not links:
            logger.info("No 'Delimit' links found.")
            exit()

        def download_file(file_url, save_path):
            response = requests.get(file_url, headers=headers, timeout=120)
            with open(save_path, "wb") as file:
                file.write(response.content)
            logger.info(f"Downloaded: {save_path}")

        base_url = "https://www.data.bsee.gov"
        for link in links:
            file_url = base_url + link["href"]
            file_name = os.path.join(save_dir, link["href"].split("/")[-1])
            download_file(file_url, file_name)

        logger.info("All files downloaded.")
