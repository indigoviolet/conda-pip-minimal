from __future__ import annotations

from dataclasses import dataclass, field
import json
from more_itertools import collapse
import subprocess
from typing import List
from snoop import pp
import ast


def run_cmd(args) -> str:
    proc = subprocess.run(args, capture_output=True, check=True, encoding="utf-8")
    return proc.stdout.strip()


@dataclass
class Cmd:
    binary: str
    args: List[str] = field(default_factory=list)

    def __call__(self, *args) -> str:
        return run_cmd(self.construct_args(args))

    def construct_args(self, *args) -> List[str]:
        return list(collapse([self.binary, self.args, args]))

    def json(self, *args):
        return json.loads(self(*args))

    def literal(self, *args):
        return ast.literal_eval(self(*args))
