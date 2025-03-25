import asyncio
import playwright.async_api as Playwright
import pypdf
from fnmatch import fnmatch
from io import BytesIO
from typing import Iterable, NotRequired, TypedDict, Unpack

from .logger import logger


class PPDFCapturerOptions(TypedDict):
    concurrency: NotRequired[int]
    recurse_enabled: NotRequired[bool]
    recurse_level: NotRequired[int]
    recurse_reject: NotRequired[Iterable[str]]
    recurse_accept: NotRequired[Iterable[str]]
    recurse_seen: NotRequired[Iterable[str]]


class PPDFCapturer:
    browser_ctx: Playwright.BrowserContext
    pdf_document: pypdf.PdfWriter
    queue: asyncio.Queue[tuple[int, str]]

    concurrency: int
    recurse_enabled: bool
    recurse_level: int
    recurse_reject: set[str]
    recurse_accept: set[str]
    recurse_seen: set[str]

    def __init__(
        self,
        browser_ctx: Playwright.BrowserContext,
        **kwargs: Unpack[PPDFCapturerOptions],
    ) -> None:
        self.browser_ctx = browser_ctx
        self.concurrency = kwargs.get('concurrency', 4)
        self.pdf_document = pypdf.PdfWriter()
        self.queue = asyncio.Queue()

        # recursion
        self.recurse_enabled = kwargs.get('recurse_enabled', False)
        self.recurse_level = kwargs.get('recurse_level', 1)
        self.recurse_accept = set(kwargs.get('recurse_accept', []))
        self.recurse_reject = set(kwargs.get('recurse_reject', []))
        self.recurse_seen = set(kwargs.get('recurse_seen', []))

    @staticmethod
    async def connect(
        ws_endpoint: str, urls: Iterable[str], **kwargs: Unpack[PPDFCapturerOptions]
    ) -> None:
        assert False

    @staticmethod
    async def launch(
        urls: Iterable[str], **kwargs: Unpack[PPDFCapturerOptions]
    ) -> pypdf.PdfWriter:
        async with Playwright.async_playwright() as playwright:
            browser = await playwright.chromium.launch(channel='chrome')
            browser_ctx = await browser.new_context()
            try:
                logger.debug('browser launched...')
                return await PPDFCapturer.execute(browser_ctx, urls, **kwargs)
            except Exception:
                raise
            finally:
                logger.debug('browser closing...')
                await browser.close()

    @staticmethod
    async def execute(
        browser_ctx: Playwright.BrowserContext,
        urls: Iterable[str],
        **kwargs: Unpack[PPDFCapturerOptions],
    ) -> pypdf.PdfWriter:
        capturer = PPDFCapturer(browser_ctx, **kwargs)
        # enqueue initial urls
        await capturer.enqueue(urls, 0)
        # wait for async queue
        await capturer.join()
        # return final merged document
        return capturer.pdf_document

    def _normalize(self, url: str) -> str:
        # TODO: optionally ignore anchor / url params
        # TODO: add trailing slash instead of removing
        if url.endswith('/'):
            url = url[:-1]
        return url

    @staticmethod
    async def _page_on_dialog(dialog: Playwright.Dialog) -> None:
        await dialog.dismiss()

    @staticmethod
    async def _page_on_download(download: Playwright.Download) -> None:
        await download.cancel()

    @staticmethod
    async def _page_capture(page: Playwright.Page, url: str) -> tuple[bytes, list[str]]:
        # create page http request
        response = await page.goto(url, wait_until='domcontentloaded', timeout=10e3)
        if not response:
            raise Exception('response was not received!')
        if not response.ok and response.status in range(100, 600):
            raise Exception(
                f'[{response.status}]: request failed! {response.status_text}'
            )
        # wait for dynamic elements
        await page.wait_for_load_state('networkidle', timeout=10e3)
        await PPDFCapturer._page_sleep(page, 150)
        # find all anchor links
        pdf_links: list[str] = await page.eval_on_selector_all(
            'a', '(links) => links.map((a) => a.href).filter((a) => !!a)'
        )
        # create page pdf bytes
        pdf_bytes = await page.pdf(print_background=True)
        return (pdf_bytes, pdf_links)

    @staticmethod
    async def _page_sleep(page: Playwright.Page, ms: int) -> None:
        await page.evaluate(
            'async (ms) => await new Promise((res, rej) => setTimeout(res, ms))', ms
        )

    async def _worker_process(self, level: int, url: str) -> None:
        logger.debug(f'({level}) task started "{url}"')
        # TODO: use asyncio task timeout
        page = await self.browser_ctx.new_page()
        page.on('dialog', self._page_on_dialog)
        page.on('download', self._page_on_download)
        try:
            pdf_bytes, pdf_links = await self._page_capture(page, url)
            self.pdf_document.append(BytesIO(pdf_bytes))
            logger.debug(f'({level}) task finished "{url}"')
        except Exception:
            raise
        finally:
            logger.debug(f'({level}) task finalized "{url}"!')
            # queue new tasks
            await self.enqueue(pdf_links, level + 1)
            # close tab
            await page.close()
            # finish queue task
            self.queue.task_done()

    async def _worker_create(self, id: int) -> None:
        logger.debug(f'created worker-{id}')
        while True:
            try:
                level, url = await self.dequeue()
                await self._worker_process(level, url)
            except asyncio.CancelledError:
                return
            except Exception as error:
                logger.error(f'worker-{id} task failed!\n{error}\n')

    async def dequeue(self) -> tuple[int, str]:
        return await self.queue.get()

    async def enqueue(self, urls: Iterable[str], level: int) -> set[str]:
        # check recursion level
        if level > self.recurse_level:
            return set()
        new_urls = set(self._normalize(url) for url in urls)
        # find unvisited urls
        unvisited = new_urls - self.recurse_seen
        self.recurse_seen.update(unvisited)
        for url in unvisited:
            accepted = (
                level == 0
                or len(self.recurse_accept) == 0
                or any(fnmatch(url, pat) for pat in self.recurse_accept)
            )
            rejected = not accepted and any(
                fnmatch(url, pat) for pat in self.recurse_reject
            )
            # print(f'accepted = {accepted}, rejected = {rejected}')
            if rejected:
                logger.debug(f'queue skipped "{url}"')
            else:
                logger.debug(f'queue added "{url}"')
                await self.queue.put((level, url))
        return unvisited

    async def join(self) -> None:
        workers = [
            asyncio.create_task(self._worker_create(i)) for i in range(self.concurrency)
        ]
        # wait for queue
        await self.queue.join()
        # close workers
        for w in workers:
            w.cancel()
        await asyncio.gather(*workers, return_exceptions=True)
