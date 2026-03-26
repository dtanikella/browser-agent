import atexit
import base64
from typing import Optional
from playwright.sync_api import sync_playwright, Page, Error as PlaywrightError, TimeoutError as PlaywrightTimeoutError

_playwright = None
_browser = None
_page: Optional[Page] = None


def _ensure_browser():
    global _playwright, _browser, _page
    if _playwright is None:
        _playwright = sync_playwright().start()
        _browser = _playwright.chromium.launch()
        atexit.register(_cleanup)
    if _page is None:
        _page = _browser.new_page()


def _cleanup():
    global _playwright, _browser
    if _browser:
        _browser.close()
    if _playwright:
        _playwright.stop()


def navigate(url: str) -> str:
    _ensure_browser()
    try:
        _page.goto(url, timeout=30000, wait_until="domcontentloaded")
        return f"Navigated to {url}"
    except PlaywrightTimeoutError:
        return f"ERROR: Timeout navigating to {url}"
    except PlaywrightError as e:
        return f"ERROR: Navigation failed for {url} — {e.message}"


def go_back() -> str:
    _ensure_browser()
    try:
        response = _page.go_back(wait_until="domcontentloaded")
        if response is None:
            return "ERROR: No previous page in history."
        return f"Went back to: {_page.url}"
    except Exception as e:
        return f"ERROR: {e}"


def get_page_content() -> str:
    _ensure_browser()
    try:
        return _page.inner_text("body")
    except Exception as e:
        return f"ERROR: {e}"


def get_page_html() -> str:
    _ensure_browser()
    try:
        # Return a simplified snapshot: just the outer HTML, truncated for context
        html = _page.content()
        # Truncate to avoid overwhelming the model
        if len(html) > 20000:
            html = html[:20000] + "\n... [truncated]"
        return html
    except Exception as e:
        return f"ERROR: {e}"


def extract_links(selector: str = "") -> str:
    try:
        _ensure_browser()
        links = _page.evaluate("""
            (selector) => {
                const containers = selector
                    ? Array.from(document.querySelectorAll(selector))
                    : [document.body];
                const seen = new Set();
                const results = [];
                for (const el of containers) {
                    for (const a of el.querySelectorAll('a[href]')) {
                        const href = a.href;
                        const text = a.textContent.trim().replace(/\\s+/g, ' ');
                        const key = href + '|' + text;
                        if (!seen.has(key)) {
                            seen.add(key);
                            results.push({ text, href });
                        }
                    }
                }
                return results;
            }
        """, selector)
        if not links:
            return "No links found."
        lines = [f"{i+1}. [{l['text'] or '(no text)'}] -> {l['href']}" for i, l in enumerate(links)]
        return f"Found {len(links)} link(s):\n" + "\n".join(lines)
    except Exception as e:
        return f"ERROR: extract_links failed: {e}"


def click(selector: str) -> str:
    _ensure_browser()
    try:
        _page.click(selector, timeout=10000)
        return f"Clicked {selector}"
    except PlaywrightTimeoutError:
        return f"ERROR: Timeout waiting to click {selector}"
    except PlaywrightError as e:
        return f"ERROR: Click failed for {selector} — {e.message}"


def type_text(selector: str, text: str) -> str:
    _ensure_browser()
    try:
        _page.click(selector, timeout=10000)
        _page.fill(selector, text)
        return f"Typed '{text}' into {selector}"
    except PlaywrightTimeoutError:
        return f"ERROR: Timeout waiting for {selector}"
    except PlaywrightError as e:
        return f"ERROR: type_text failed for {selector} — {e.message}"


def press_key(key: str) -> str:
    _ensure_browser()
    try:
        _page.keyboard.press(key)
        return f"Pressed {key}"
    except PlaywrightError as e:
        return f"ERROR: press_key failed — {e.message}"


def wait_for_selector(selector: str, timeout_ms: int = 10000) -> str:
    _ensure_browser()
    try:
        _page.wait_for_selector(selector, timeout=timeout_ms)
        return f"Selector {selector} is visible"
    except PlaywrightTimeoutError:
        return f"ERROR: Timeout waiting for selector {selector}"
    except PlaywrightError as e:
        return f"ERROR: wait_for_selector failed — {e.message}"


def get_current_url() -> str:
    _ensure_browser()
    return _page.url


def take_screenshot() -> str:
    _ensure_browser()
    try:
        data = _page.screenshot(type="png")
        return base64.b64encode(data).decode("utf-8")
    except PlaywrightError as e:
        return f"ERROR: Screenshot failed — {e.message}"


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "navigate",
            "description": "Navigate the browser to a URL and wait for the page to load.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The URL to navigate to."}
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "go_back",
            "description": "Navigate back to the previous page in browser history. Use this when the current page is a dead end and you need to return to where you came from.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_page_content",
            "description": "Get the full visible text content of the current page.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_page_html",
            "description": "Get a simplified HTML snapshot of the current page (useful for understanding structure and CSS selectors).",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "extract_links",
            "description": (
                "Extract all links from the page or from elements matching an optional CSS selector. "
                "Returns a numbered list of {text, href} pairs. "
                "Use a selector like '#nav', '.sidebar', or 'main' to scope the results."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {
                        "type": "string",
                        "description": "Optional CSS selector to scope link extraction (e.g. '#nav', '.menu', 'main'). Omit or leave empty for all page links."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "click",
            "description": "Click an element on the current page by CSS selector.",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector of the element to click."}
                },
                "required": ["selector"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "type_text",
            "description": "Focus an input field and type text into it.",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector of the input field."},
                    "text": {"type": "string", "description": "Text to type into the field."},
                },
                "required": ["selector", "text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "press_key",
            "description": "Press a keyboard key (e.g. Enter, Tab, Escape, ArrowDown).",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "The key to press (Playwright key name)."}
                },
                "required": ["key"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "wait_for_selector",
            "description": "Wait until a CSS selector appears on the page.",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector to wait for."},
                    "timeout_ms": {"type": "integer", "description": "Timeout in milliseconds (default 10000)."},
                },
                "required": ["selector"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_url",
            "description": "Return the current page URL.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "take_screenshot",
            "description": "Capture the current page as a base64-encoded PNG screenshot.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]

TOOL_MAP = {
    "navigate": navigate,
    "go_back": go_back,
    "get_page_content": get_page_content,
    "get_page_html": get_page_html,
    "extract_links": extract_links,
    "click": click,
    "type_text": type_text,
    "press_key": press_key,
    "wait_for_selector": wait_for_selector,
    "get_current_url": get_current_url,
    "take_screenshot": take_screenshot,
}
