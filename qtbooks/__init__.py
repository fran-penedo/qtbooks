import logging

logger = logging.getLogger("qtbooks")
logger.addHandler(logging.NullHandler())

import sys

LOGGER_DEBUG_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "debug_formatter": {
            "format": "%(levelname).1s %(module)s(%(lineno)d):%(funcName)s %(message)s"
        }
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "debug_formatter",
        }
    },
    "loggers": {
        "qtbooks": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": True,
        }
    },
}

if "nose" in sys.modules.keys() and ":" in sys.argv[-1]:
    import logging.config

    logging.config.dictConfig(LOGGER_DEBUG_CONFIG)
