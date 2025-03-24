import playwright.async_api as Playwright
import pytest_asyncio
from typing import AsyncGenerator


@pytest_asyncio.fixture(autouse=True, scope='session')
async def browser() -> AsyncGenerator[Playwright.Browser, None]:
    async with Playwright.async_playwright() as playwright:
        browser = await playwright.chromium.launch(channel='chrome')
        yield browser
        await browser.close()


@pytest_asyncio.fixture(autouse=True, scope='session')
async def browser_ctx(
    browser: Playwright.Browser,
) -> AsyncGenerator[Playwright.BrowserContext, None]:
    browser_ctx = await browser.new_context()
    yield browser_ctx
    await browser_ctx.close()


@pytest_asyncio.fixture(autouse=False, scope='function')
async def browser_page(
    browser_ctx: Playwright.BrowserContext,
) -> AsyncGenerator[Playwright.Page, None]:
    browser_page = await browser_ctx.new_page()
    yield browser_page
    await browser_page.close()
