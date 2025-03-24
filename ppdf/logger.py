from .constant.metadata import NAME

import logging
import logging.config

logger = logging.getLogger(NAME)
logger_config: 'logging.config._DictConfigArgs' = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'main': {
            'format': '[%(levelname)s]: %(message)s',
        }
    },
    'handlers': {
        'stderr': {
            'class': 'logging.StreamHandler',
            'level': logging.WARN,
            'formatter': 'main',
            'stream': 'ext://sys.stderr',
        },
        'stdout': {
            'class': 'logging.StreamHandler',
            'level': logging.DEBUG,
            'formatter': 'main',
            'stream': 'ext://sys.stdout',
        },
    },
    'loggers': {
        'root': {
            'level': logging.DEBUG,
            'handlers': ['stderr', 'stdout'],
        }
    },
}


def logger_configure(
    level: int | str,
    quiet: bool = False,
) -> logging.Logger:
    logging.config.dictConfig(logger_config)
    logger.setLevel(level or logging.DEBUG)
    logger.disabled = quiet
    return logger
