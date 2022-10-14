from __future__ import annotations

from loguru import logger
import sys


def configure_logger(debug: int = 0):
    logger.remove()
    # https://github.com/Delgan/loguru/blob/0f89a58d3279d31915224f329e90255e9c7f5449/loguru/_defaults.py#L31
    # https://github.com/Delgan/loguru/issues/592
    no_traceback_debug_format = (
        lambda _: "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>\n"
    )
    no_traceback_format = lambda _: "<level>{message}</level>\n"
    default_args = dict(
        level="WARNING", diagnose=False, backtrace=False, format=no_traceback_format
    )
    debug_args = dict(
        level="DEBUG",
        diagnose=(debug > 1),
        backtrace=(debug > 1),
        format=(None if debug > 1 else no_traceback_debug_format),
    )
    logger.configure(
        handlers=[dict(sink=sys.stderr, **(debug_args if debug > 0 else default_args))]
    )


configure_logger(False)
