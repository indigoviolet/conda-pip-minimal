from __future__ import annotations

# Adapted from https://gist.github.com/arthur-tacca/32c9b5fa81294850cabc890f4a898a4e

from collections.abc import Generator, Iterable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
import trio
from typing import Any, Awaitable, Callable, Optional

ArgType = Any
ResultType = Any
AsyncFnType = Callable[..., Awaitable[ResultType]]


class TaskNotDoneException(Exception):
    pass


class TaskFailedException(Exception):
    pass


@dataclass
class ResultCapture(Awaitable[Any]):
    nursery: trio.Nursery
    f: AsyncFnType
    args: Iterable[ArgType]

    _done_event: trio.Event = field(init=False, default_factory=trio.Event)
    _result: Any = field(init=False)
    _exception: Optional[BaseException] = field(init=False, default=None)

    def __post_init__(self):
        self.nursery.start_soon(self._run)

    async def _run(self):
        try:
            self._result = await self.f(*self.args)
        except BaseException as e:
            self._exception = e
            raise
        finally:
            self._done_event.set()

    @property
    def result(self):
        if not self._done_event.is_set():
            raise TaskNotDoneException(self)
        if self._exception is not None:
            raise TaskFailedException(self) from self._exception

        return self._result

    def __await__(self) -> Generator[Any, None, Any]:
        yield from self._done_event.wait().__await__()
        return self.result


@dataclass
class ResultCaptureNursery:
    nursery: trio.Nursery

    def start_soon(self, f: AsyncFnType, *args: ArgType):
        return ResultCapture(self.nursery, f, args)


@asynccontextmanager
async def open_capturing_nursery():
    async with trio.open_nursery() as N:
        yield ResultCaptureNursery(N)
