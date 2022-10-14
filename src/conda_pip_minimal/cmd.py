from __future__ import annotations

import ast
from dataclasses import dataclass, field
import json
from more_itertools import collapse
import trio
from typing import List

from .logging import logger


async def run_cmd(args) -> str:
    proc = await trio.run_process(args, capture_stdout=True, check=True)  # type: ignore
    return proc.stdout.decode("utf-8").strip()


@dataclass
class Cmd:
    binary: str
    args: List[str] = field(default_factory=list)

    async def __call__(self, *args) -> str:
        result = await run_cmd(self.construct_args(args))
        logger.debug(f"Ran {self.binary=} {self.args=} {args=}")
        return result

    def construct_args(self, *args) -> List[str]:
        return list(collapse([self.binary, self.args, args]))

    async def json(self, *args):
        result = await self(*args)
        try:
            return json.loads(result)
        except:
            logger.exception(
                f"Unable to parse JSON from cmd {self.binary=} {self.args=}"
            )
            raise

    async def literal(self, *args):
        result = await self(*args)
        try:
            return ast.literal_eval(result)
        except:
            logger.exception(
                f"Unable to parse literal from cmd {self.binary=} {self.args=}"
            )
            raise
