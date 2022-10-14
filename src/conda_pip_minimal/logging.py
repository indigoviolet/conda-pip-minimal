from __future__ import annotations

from loguru import logger
import sys
from typing import Any, Dict

# https://github.com/Delgan/loguru/blob/0f89a58d3279d31915224f329e90255e9c7f5449/loguru/_defaults.py#L31
# https://github.com/Delgan/loguru/issues/592
no_traceback_debug_format = (
    lambda _: "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>\n"
)
no_traceback_format = lambda _: "<level>{message}</level>\n"


def configure_logger(debug: int = 0):
    logger.remove()
    args: Dict[str, Any] = dict(
        level=("WARNING" if debug == 0 else "DEBUG"),
        diagnose=(debug > 1),
        backtrace=(debug > 1),
        catch=True,
    )
    if debug < 2:
        # cannot pass format=None for debug > 1
        args["format"] = no_traceback_debug_format if debug > 0 else no_traceback_format

    logger.configure(handlers=[dict(sink=sys.stderr, **args)])


configure_logger(0)
