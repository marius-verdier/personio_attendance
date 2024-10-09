import scrapy
import scrapy
from scrapy.http import FormRequest, Response
from playwright.async_api import Page
from scrapy_playwright.page import PageMethod
from scrapy.utils.response import open_in_browser
from datetime import datetime
import os
import dotenv

class AttendanceSpider(scrapy.Spider):
    name = "attendance_spider"
    allowed_domains = ["dev-partner-marius.personio.de", "id.personio.de"]
    start_urls = ["https://dev-partner-marius.personio.de/login/index"]

    def __init__(self, action=None, *args, **kwargs):
        super(AttendanceSpider, self).__init__(*args, **kwargs)
        dotenv.load_dotenv()
        self.email = os.getenv('CREDS_EMAIL')
        self.password = os.getenv('CREDS_PASS')
        self.action = action  # 'start' or 'stop'
        self.state_file = '.attendance_state.json'

    def start_requests(self):
        url = self.start_urls[0]
        yield scrapy.FormRequest(
            url=url, 
            callback=self.get_page, 
            formdata={'email': self.email, 'password': self.password},
            meta={
                "playwright": True,
                "playwright_page_methods": [
                    PageMethod("wait_for_timeout", 3000),        
                ],
            },
            dont_filter = True
            )

    def get_page(self, response):

        if "For security reasons you're required to enter the token" in response.text:
            print("Token required")

            hidden_token = response.css('input[name="_token"]::attr(value)').extract_first()
            print("Hidden token : ", hidden_token)

            # wait user input for code
            code = input("Enter the code: ")

            yield FormRequest(
                url="https://dev-partner-marius.personio.de/login/token-auth",
                formdata={"_token": hidden_token, "token": code},
                meta={
                    "playwright": True,
                    "playwright_page_methods": [
                        PageMethod("wait_for_timeout", 7000),        
                    ],
                    },
            )
            return

        else :
            print("Logged in")
            print("Fetching attendance page")

            

            print(response.text)
    
    def parse(self, response):
        print("Parsing attendance page")
        print(response.text)
        open_in_browser(response)