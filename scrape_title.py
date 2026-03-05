from playwright.sync_api import sync_playwright

URL = "https://example.com" 

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(URL)
    print(page.title())
    browser.close()
