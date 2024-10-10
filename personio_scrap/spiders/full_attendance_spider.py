import scrapy
import dotenv
import os
import datetime

from scrapy.http import FormRequest, Request
from scrapy_playwright.page import PageMethod

class FullAttendanceSpiderSpider(scrapy.Spider):
    name = "full_attendance"
    allowed_domains = ["id.personio.de"]
    start_urls = []

    def __init__(self, action=None, *args, **kwargs):
        super(FullAttendanceSpiderSpider, self).__init__(*args, **kwargs)
        dotenv.load_dotenv(verbose=True, override=True)

        self.allowed_domains.append(os.getenv('BASE_URL'))
        start_url = f'https://{os.getenv("BASE_URL")}/login/index'
        self.start_urls.append(start_url)

        self.email = os.getenv('CREDS_EMAIL')
        self.password = os.getenv('CREDS_PASS')
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
                "playwright_page_methods": [
                    # wait for all components to be rendered
                    PageMethod("wait_for_timeout", 8000)
                ],
            },
            dont_filter = True
            )
        
    def redirect_attendance(self, response):
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
                        # click the button to perform the action
                        PageMethod("click", selector = f'button[aria-label="{self.aria_label[self.action]}"]',),
                        # wait for the action to be performed
                        PageMethod("wait_for_timeout", 3000),
                    ],
                    },
            )
            return
        else:
            print("[PersonioClocker] Log in successful")
            print(f"[PersonioClocker] Redirecting to attendance page")
            # get url from the attendance link a tag, aria-label="Time Tracking"
            url = f'https://{os.getenv("BASE_URL")}{response.css("a[aria-label='Time Tracking']::attr(href)").extract_first()}'
            # get today date YYYY-MM-DD
            today = datetime.date.today().isoformat()
            print(f"[PersonioClocker] Waiting for registering attendance for {today}")
            yield Request(
                url=url,
                callback=self.perform_attendance,
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_page_methods": [
                        # wait for all components to be rendered
                        PageMethod("wait_for_timeout", 8000),
                        # click the button located in <div data-test-id="day_2024-10-03"><button data-test-id="day-cell-action-button"> to perform the action
                        PageMethod("click", selector = f'div[data-test-id="today-cell"] button[data-test-id="day-cell-action-button"]',),
                        # wait for the action to be performed
                        PageMethod("wait_for_timeout", 3000),
                    ],
                },
            )
            
    async def perform_attendance(self, response):
        print(f"[PersonioClocker] Performing attendance registration")
        # data-test-id="work-entry" -> data-test-id="timerange-start" + data-test-id="timerange-end"
        # data-test-id="break-entry" -> data-test-id="timerange-start" + data-test-id="timerange-end"
        # click button data-test-id="day-entry-save"
        # get uuids from the timeranges (id attribute of input with data-test-id="timerange-start")
        work_entry_uuid = "-".join(response.css('section[data-test-id="work-entry"] input[data-test-id="timerange-start"]::attr(id)').extract_first().split('-')[2:])
        break_entry_uuid = "-".join(response.css('section[data-test-id="break-entry"] input[data-test-id="timerange-start"]::attr(id)').extract_first().split('-')[2:])

        print(f"[PersonioClocker] Entries UUIDs: {work_entry_uuid}, {break_entry_uuid}")

        page = response.meta["playwright_page"]
        await page.fill(f'input[id="start-input-{work_entry_uuid}"]', "09:00")
        await page.fill(f'input[id="end-input-{work_entry_uuid}"]', "18:00")
        await page.fill(f'input[id="start-input-{break_entry_uuid}"]', "13:00")
        await page.fill(f'input[id="end-input-{break_entry_uuid}"]', "14:00")

        await page.click('button[data-test-id="day-entry-save"]')
        print(f"[PersonioClocker] Attendance registered successfully for {datetime.date.today().isoformat()}")
        yield Request(page.url)
        




    def get_page(self, response):

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
                        # click the button to perform the action
                        PageMethod("click", selector = f'button[aria-label="{self.aria_label[self.action]}"]',),
                        # wait for the action to be performed
                        PageMethod("wait_for_timeout", 3000),
                    ],
                    },
            )
            return

        else :
            print("[PersonioClocker] Log in successful")

            print(f"[PersonioClocker] Performing action: {self.aria_label[self.action]}")
                