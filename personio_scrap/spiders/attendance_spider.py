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
    allowed_domains = ["id.personio.de"]
    start_urls = []

    def __init__(self, action=None, *args, **kwargs):
        super(AttendanceSpider, self).__init__(*args, **kwargs)
        dotenv.load_dotenv(verbose=True, override=True)

        self.allowed_domains.append(os.getenv('BASE_URL'))
        start_url = f'https://{os.getenv("BASE_URL")}/login/index'
        self.start_urls.append(start_url)

        self.email = os.getenv('CREDS_EMAIL')
        self.password = os.getenv('CREDS_PASS')

        self.non_working_days = os.getenv('NON_WORKING_DAYS').split(',')
        self.non_working_triggers = os.getenv('NON_WORKING_TRIGGERS').split(',')

        self.action = action  # 'start', 'break', 'stop_break' or 'stop'
        self.state_file = '.attendance_state.json'
        self.aria_label = {
            'start': 'Clock in',
            'break': 'Start break',
            'stop_break': 'Resume work',
            'stop': 'Clock out'
        }

    def start_requests(self):
        url = self.start_urls[0]
        print(f"[PersonioClocker] Trying to log in for {self.email}")
        yield scrapy.FormRequest(
            url=url,
            callback=self.redirect_attendance, 
            formdata={'email': self.email, 'password': self.password},
            meta={
                "playwright": True,
                "playwright_include_page": True,
                "playwright_page_methods": [
                    # wait for all components to be rendered
                    PageMethod("wait_for_timeout", 8000)
                ],
            },
            dont_filter = True
            )

    def get_page(self, response):

        page = response.meta.get("playwright_page")
        if not page:
            print("[PersonioClocker] Error: 'playwright_page' not found in response metadata.")
            return

        if "For security reasons you're required to enter the token" in response.text:
            print(f"[PersonioClocker] Personio detected a login from a new device, they sent a code to {self.email}")

            hidden_token = response.css('input[name="_token"]::attr(value)').extract_first()

            # wait user input for code
            code = input(f"[PersonioClocker] Please enter the code you received at {self.email} : ")

            url = self.start_urls[0]

            yield FormRequest(
                url=url,
                formdata={"_token": hidden_token, "token": code},
                meta={
                    "playwright": True,
                    "playwright_page_methods": [
                        # wait for all components to be rendered
                        PageMethod("wait_for_timeout", 8000),
                    ],
                    },
            )
            return

        else :
            print("[PersonioClocker] Log in successful")


                # # click the button to perform the action
                # PageMethod("click", selector = f'button[aria-label="{self.aria_label[self.action]}"]',),
                # # wait for the action to be performed
                # PageMethod("wait_for_timeout", 3000),

            print(f"[PersonioClocker] Performing action: {self.aria_label[self.action]}")
                