import playwright.async_api as Playwright
import pytest
from typing import Any, cast

from ppdf.capturer import PPDFCapturer

# TODO: test recursion filtering


@pytest.mark.asyncio
async def test_enqueue_skips() -> None:
    capturer = PPDFCapturer(cast(Any, None))
    before = await capturer.enqueue(['test://a', 'test://b'], 0)
    after = await capturer.enqueue(['test://a', 'test://b', 'test://c', 'test://d'], 0)
    assert capturer.queue.qsize() == 4
    assert len(before) == 2
    assert len(after) == 2


@pytest.mark.asyncio(loop_scope='session')
async def test_page_capture(browser_page: Playwright.Page) -> None:
    pdf_bytes, pdf_urls = await PPDFCapturer._page_capture(
        browser_page, 'https://example.com'
    )
    assert 'https://www.iana.org/domains/example' in pdf_urls
    assert (
        b'/URI (https\072\057\057www\056iana\056org\057domains\057example)' in pdf_bytes
    )
