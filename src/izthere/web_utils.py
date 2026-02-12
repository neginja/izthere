from typing import Any

import httpx
from playwright.async_api import TimeoutError as PWTimeoutError
from playwright.async_api import async_playwright

from izthere.logger import get_logger

logger = get_logger()


async def fetch_json(
    url: str, timeout: int = 10, headers: dict[str, str] | None = None
) -> dict[str, Any]:
    async with httpx.AsyncClient(headers=headers, timeout=timeout) as client:
        resp: httpx.Response = await client.get(url)
        _ = resp.raise_for_status()
        return resp.json()


async def fetch_html_no_js(
    url: str, timeout: int = 10, headers: dict[str, str] | None = None
) -> str:
    async with httpx.AsyncClient(headers=headers, timeout=timeout) as client:
        resp: httpx.Response = await client.get(url)
        _ = resp.raise_for_status()
        return resp.text


async def fetch_html(
    url: str, timeout: int = 10, headers: dict[str, str] | None = None
) -> str:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)

        context_kwargs = {}
        if headers:
            context_kwargs["extra_http_headers"] = headers

        context = await browser.new_context(**context_kwargs)
        page = await context.new_page()

        try:
            _ = await page.goto(url, timeout=timeout * 1000, wait_until="networkidle")
        except PWTimeoutError:
            logger.warning(f"Playwright navigation timed out after {timeout}")
        except Exception:
            raise

        html = await page.content()
        await context.close()
        await browser.close()
        return html
