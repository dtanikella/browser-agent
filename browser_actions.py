import atexit
from playwright.sync_api import sync_playwright, Page

_playwright = None
_browser = None
_page_cache: dict[str, Page] = {}


def _ensure_browser():
    global _playwright, _browser
    if _playwright is None:
        _playwright = sync_playwright().start()
        _browser = _playwright.chromium.launch()
        atexit.register(_cleanup)


def _cleanup():
    global _playwright, _browser
    if _browser:
        _browser.close()
    if _playwright:
        _playwright.stop()


def _get_page(url: str) -> Page:
    _ensure_browser()
    if url not in _page_cache:
        page = _browser.new_page()
        page.goto(url)
        _page_cache[url] = page
    return _page_cache[url]


def get_page_title(url: str) -> str:
    return _get_page(url).title()


def get_page_text(url: str) -> str:
    return _get_page(url).inner_text("body")


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_page_title",
            "description": "Get the title of a web page.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The URL to fetch the title from."}
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_page_text",
            "description": "Get the visible body text of a web page.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The URL to fetch the text from."}
                },
                "required": ["url"],
            },
        },
    },
]

TOOL_MAP = {
    "get_page_title": get_page_title,
    "get_page_text": get_page_text,
}
