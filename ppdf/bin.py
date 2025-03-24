from .constant.metadata import NAME, DESCRIPTION, VERSION
from .capturer import PPDFCapturer, PPDFCapturerOptions
from .logger import logger_configure

import asyncio
import argparse
import urllib.parse
import os
import time
from pathlib import Path
from typing import Optional, Sequence


class PPDFNamespace(argparse.Namespace):
    accept: list[str]
    reject: list[str]
    recurse: bool
    level: int
    jobs: int
    format: str
    urls: list[str]
    output: Path
    wait: int
    quiet: Optional[bool]
    verbose: Optional[bool]

    @staticmethod
    def url_type(arg: str) -> str:
        url = urllib.parse.urlparse(arg)
        if not url.scheme or not url.netloc:
            raise argparse.ArgumentTypeError(f'invalid url "{arg}"')
        if url.scheme not in ('http', 'https'):
            raise argparse.ArgumentTypeError(f'unsupported protocol "{url.scheme}"')
        return arg

    def as_kwargs(self) -> PPDFCapturerOptions:
        return {
            'concurrency': self.jobs,
            'recurse_enabled': self.recurse,
            'recurse_level': self.level,
            'recurse_accept': self.accept,
            'recurse_reject': self.reject,
        }


# TODO: command line completion

# setup argument parser
parser = argparse.ArgumentParser(prog=NAME, description=DESCRIPTION, usage='')
parser.add_argument('--version', action='version', version=f'{NAME} v{VERSION}')
parser.add_argument('-q', '--quiet', action='store_true')
parser.add_argument('-v', '--verbose', action='store_true')

# setup parser options
parser.add_argument(
    '-r', '--recurse', action='store_true', default=False, help='recurse through links'
)
parser.add_argument('-l', '--level', default=1, help='recursion depth limit', type=int)
parser.add_argument('-j', '--jobs', default=2, help='task concurrency limit', type=int)
parser.add_argument(
    '-o', '--output', default='out.pdf', help='output file path', type=Path
)
parser.add_argument(
    '-f', '--format', default='letter', help='paper format or dimensions'
)
parser.add_argument(
    '-w', '--wait', default=150, help='wait miliseconds after networkidle'
)

# TODO: avoid nargs='+' and implement wget like -A / -R
parser.add_argument('-A', '--accept', nargs='+', default=[], help='accept url glob')
parser.add_argument('-R', '--reject', nargs='+', default=[], help='reject url glob')

# setup parser arguments
parser.add_argument('urls', nargs='+', help='page url(s)', type=PPDFNamespace.url_type)


# entrypoint
def main(args: Optional[Sequence[str]] = None) -> int:
    time_start = time.time()
    options = parser.parse_args(args, PPDFNamespace)()
    logger = logger_configure(
        level='DEBUG' if os.getenv('DEBUG') == 'true' else 'INFO',
        quiet=options.quiet or False,
    )
    logger.info(f'starting capture for {len(options.urls)} page(s)...')
    # argument parsing
    with open(options.output, 'wb') as file:
        pdf_writer = asyncio.run(
            PPDFCapturer.launch(options.urls, **options.as_kwargs())
        )
        pdf_writer.write(file)
    logger.info(f'finished capture in {round(time.time() - time_start, 2)}s')
    return 0
