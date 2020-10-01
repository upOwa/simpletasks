import abc
import datetime
import logging
import time
from typing import Any, Callable, Iterable, Optional, TypeVar

try:
    from tqdm import tqdm

    _has_tqdm = True
except ImportError:
    _has_tqdm = False

X = TypeVar("X")


class Task(metaclass=abc.ABCMeta):
    DEBUGGING = False  # Set to True while debugging (prevents catching exceptions)
    TESTING = False  # Set to True while automated testing (can force dryrun in some tasks)
    LOGGER_NAMESPACE = ""

    def __init__(self, **kwargs) -> None:
        self.options = kwargs
        self.loggernamespace = self.options.get(
            "loggernamespace", Task.LOGGER_NAMESPACE + self.__class__.__name__
        )
        self.logger = logging.getLogger(self.loggernamespace)
        if self.options.get("progress", None) is not None:
            self.showprogress = self.options.get("progress")
        else:
            # Legacy
            self.showprogress = self.options.get("showprogress", True)
        self.dryrun = self.options.get("dryrun", False)
        self.quick = self.options.get("quick", False)
        self.force = self.options.get("force", False)
        self.verbose = self.options.get("verbose", False)

        # TODO: remove this
        self.timestamp = self.options.get("timestamp", None) or datetime.datetime.now().strftime("%Y-%m-%d")
        self.date = self.options.get("date", None) or datetime.date.today()

    def progress(self, iterable: Iterable[X], total: int = None, desc: str = None) -> Iterable[X]:
        if self.showprogress and _has_tqdm:
            return tqdm(iterable, total=total, desc=desc)
        else:
            return iterable

    def execute(self, func: Callable[..., X], stubbedValue: X = None) -> Optional[X]:
        if self.dryrun:
            self.logger.info("Stubbed")
            return stubbedValue
        else:
            return func()

    def executeOrRetry(
        self,
        func: Callable[..., X],
        maxretries: int = 5,
        initialdelay: float = 30,
        stubbedValue: X = None,
    ) -> Optional[X]:
        failures = 0
        delay = initialdelay
        while True:
            try:
                return self.execute(func, stubbedValue)
            except Exception as e:
                failures += 1
                if failures > maxretries:
                    self.logger.warning("Too many failures, abandonning")
                    raise e

                # Retry
                self.logger.warning(
                    "Failed {} times ({}), retrying in {:.0f} seconds...".format(failures, e, delay)
                )
                time.sleep(delay)
                delay *= 1.5

    @abc.abstractmethod
    def do(self) -> Any:
        raise NotImplementedError  # pragma: no cover

    def run(self) -> Any:
        if Task.DEBUGGING:
            return self.do()
        else:
            try:
                return self.do()
            except Exception as e:
                self.logger.critical("Got exception: {} {}".format(e.__class__.__name__, e), exc_info=e)
                raise e
