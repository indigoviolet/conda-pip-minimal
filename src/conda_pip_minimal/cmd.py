from __future__ import annotations

from dataclasses import dataclass, field
import json
from more_itertools import collapse
from typing import List
import ast
import trio

from loguru import logger


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
        return json.loads(await self(*args))

    async def literal(self, *args):
        return ast.literal_eval(await self(*args))
