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

        self.shift_start = os.getenv('SHIFT_START')
        self.shift_end = os.getenv('SHIFT_END')
        self.break_start = os.getenv('BREAK_START')
        self.break_end = os.getenv('BREAK_END')

        self.non_working_days = os.getenv('NON_WORKING_DAYS').split(',')
        self.non_working_triggers = os.getenv('NON_WORKING_TRIGGERS').split(',')

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


            yield scrapy.FormRequest(
                url=url,
                callback=self.redirect_attendance, 
                formdata={"_token": hidden_token, "token": code},
                meta={
                    "playwright": True,
                    "playwright_page_methods": [
                        # wait for all components to be rendered
                        PageMethod("wait_for_timeout", 8000)
                    ],
                },
                dont_filter = True
            )
            return
        else:
            print("[PersonioClocker] Log in successful")
            print(f"[PersonioClocker] Redirecting to attendance page")
            # get url from the attendance link a tag, aria-label="Time Tracking"
            url = f'https://{os.getenv("BASE_URL")}{response.css("a[aria-label='Time Tracking']::attr(href)").extract_first()}'
            # get today date YYYY-MM-DD
            today = datetime.date.today().isoformat()
            day = datetime.date.today().strftime("%A").lower()

            if day in self.non_working_days:
                print(f"[PersonioClocker] Today is {day}, it is a non-working day")
                return

            print(f"[PersonioClocker] Waiting for registering attendance for {today}")
            yield Request(
                url=url,
                callback=self.perform_attendance,
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_page_methods": [
                        PageMethod("wait_for_timeout", 8000),
                    ],
                },
            )
            
    async def perform_attendance(self, response):
        page = response.meta.get("playwright_page")
        if not page:
            print("[PersonioClocker] Error: 'playwright_page' not found in response metadata.")
            return

        try:
            # Check if today is a non-working day
            inner = await page.inner_html('div[data-test-id="today-cell"]')
            if any(trigger in inner for trigger in self.non_working_triggers):
                print(f"[PersonioClocker] Today is a non-working day (trigger detected from {self.non_working_triggers})")
                return

            # Click the action button for today
            await page.click('div[data-test-id="today-cell"] button[data-test-id="day-cell-action-button"]')
            await page.wait_for_timeout(3000)
            print("[PersonioClocker] Performing attendance registration")

            # Extract UUIDs for work and break entries
            work_entry_uuid = await self.extract_uuid(page, 'work-entry')
            break_entry_uuid = await self.extract_uuid(page, 'break-entry')

            if not work_entry_uuid or not break_entry_uuid:
                print("[PersonioClocker] Error: Unable to extract entry UUIDs.")
                return

            print(f"[PersonioClocker] Entries UUIDs: {work_entry_uuid}, {break_entry_uuid}")

            # Fill in the work and break times
            await page.fill(f'input[id="start-input-{work_entry_uuid}"]', self.shift_start)
            await page.fill(f'input[id="end-input-{work_entry_uuid}"]', self.shift_end)
            await page.fill(f'input[id="start-input-{break_entry_uuid}"]', self.break_start)
            await page.fill(f'input[id="end-input-{break_entry_uuid}"]', self.break_end)

            # Save the entries
            await page.click('button[data-test-id="day-entry-save"]')
            print(f"[PersonioClocker] Attendance registered successfully for {datetime.date.today().isoformat()}")

        except Exception as e:
            print(f"[PersonioClocker] An error occurred: {e}")
        finally:
            await page.close()
        
    def validate_time_format(self, time_str):
        try:
            datetime.datetime.strptime(time_str, '%H:%M')
            return True
        except ValueError:
            return False

    async def extract_uuid(self, page, entry_type):
        try:
            selector = f'section[data-test-id="{entry_type}"] input[data-test-id="timerange-start"]'
            element = await page.query_selector(selector)
            if element:
                element_id = await element.get_attribute('id')
                uuid_parts = element_id.split('-')[2:]
                return "-".join(uuid_parts)
            else:
                print(f"[PersonioClocker] Error: Selector '{selector}' not found.")
                return None
        except Exception as e:
            print(f"[PersonioClocker] Error extracting UUID for {entry_type}: {e}")
            return None