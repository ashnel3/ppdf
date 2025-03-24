from importlib.metadata import metadata, PackageMetadata
import os
from typing import Final

# os & environment
DEBUG: Final[bool] = os.getenv('DEBUG') == 'true'

# package metadata
METADATA: Final[PackageMetadata] = metadata('ppdf')
DESCRIPTION: Final[str] = METADATA.get('summary', '')
NAME: Final[str] = METADATA.get('name', 'ppdf')
VERSION: Final[str] = METADATA.get('version', '0.0.0')
