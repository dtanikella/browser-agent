import atexit
from playwright.sync_api import sync_playwright, Page, Error as PlaywrightError, TimeoutError as PlaywrightTimeoutError

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
        try:
            page.goto(url, timeout=30000)
        except PlaywrightTimeoutError:
            raise RuntimeError(f"ERROR: Timeout loading {url}")
        except PlaywrightError as e:
            raise RuntimeError(f"ERROR: Navigation failed for {url} — {e.message}")
        _page_cache[url] = page
    return _page_cache[url]


def get_page_title(url: str) -> str:
    try:
        return _get_page(url).title()
    except Exception as e:
        return str(e)


def get_body(url: str) -> str:
    try:
        return _get_page(url).inner_text("body")
    except Exception as e:
        return str(e)


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
            "name": "get_body",
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
    "get_body": get_body,
}
