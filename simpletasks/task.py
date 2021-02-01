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
    """Class to do stuffs.

    Definition:
    ```
    class MyTask(Task):
        def do(self) -> int:
            self.logger.info("That's where I do stuff!")
            return 42
    ```

    Usage: either via `Cli` decorator to define a Click command, or called via Python code:
    ```
    res = MyTask(dryrun=False, showprogress=True).run()
    ```
    """

    DEBUGGING = False  # Set to True while debugging (prevents catching exceptions)
    TESTING = False  # Set to True while automated testing (can force dryrun in some tasks)
    LOGGER_NAMESPACE = ""

    def __init__(self, **kwargs) -> None:
        """Initializes a task.

        Accepted kwargs:
        - loggernamespace (str): namespace for the logger object, defaults to `Task.LOGGER_NAMESPACE` + name of the class
        - progress (bool): show progress or not (via tqdm) - see CliParams.progress()
        - dryrun (bool) - see CliParams.dryrun()
        - quick (bool) - see CliParams.quick()
        - includearchives (bool) - see CliParams.include_archives()
        - force (bool) - see CliParams.force()
        - verbose (bool) - see CliParams.verbose()
        - date (datetime.date) - see CliParams.date()
        - timestamp (str) - timestamp in YYYY-MM-DD format, deprecated, use `date` instead
        """
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
        self.includearchives = self.options.get("includearchives", False)
        self.force = self.options.get("force", False)
        self.verbose = self.options.get("verbose", False)

        # TODO: remove this
        self.timestamp = self.options.get("timestamp", None) or datetime.datetime.now().strftime("%Y-%m-%d")
        self.date = self.options.get("date", None) or datetime.date.today()

    def progress(self, iterable: Iterable[X], total: int = None, desc: str = None) -> Iterable[X]:
        """Shows progress over an iterable `iterable` if progress option is used and if tqdm is available.
        Otherwise has no effect.

        Usage:
        ```
        for x in self.progress(myiterable):
            do_stuff_with(x)
        ```

        Args:
        - iterable (Iterable[X]): iterable to iterate over
        - total (int, optional): Total number of iterations - tqdm tries to estimate it if the iterable has a length. Defaults to None.
        - desc (str, optional): Description for the progress bar. Defaults to None.

        Returns:
        - Iterable[X]: Iterable to iterator over
        """
        if self.showprogress and _has_tqdm:
            return tqdm(iterable, total=total, desc=desc)
        else:
            return iterable

    def execute(self, func: Callable[..., X], stubbedValue: X = None) -> Optional[X]:
        """Executes the callback `func` if not in dryrun mode and returns the value.
        If in dryrun mode, function is not called and `stubbedValue` is returned.

        Usage:
        ```
        self.execute(lambda: db.session.commit())
        ```

        Args:
        - func (Callable[..., X]): Function to call
        - stubbedValue (X, optional): Value to return in dryrun mode. Defaults to None.

        Returns:
        - Optional[X]: Returned value from the callback
        """

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
        """Executes the callback `func` if not in dryrun mode and returns the value.
        If the call fails with any Exception, retries several times with exponential backoff.
        If the call still fails after `maxretries`, the last exception is re-raised.

        If in dryrun mode, function is not called and `stubbedValue` is returned.

        Args:
        - func (Callable[..., X]): Function to call
        - maxretries (int, optional): Maximum number of times to retry. Defaults to 5.
        - initialdelay (float, optional): Initial delay to wait between retries (in seconds). Delay is multiplied by half between each retry. Defaults to 30.
        - stubbedValue (X, optional): Value to return in dryrun mode. Defaults to None.

        Raises:
        - e: Last exception raised if maximum retries is reached

        Returns:
        - Optional[X]: Returned value from the callback
        """
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
        """Method to implement and does the work.

        Returns:
        - Any: Any value to return
        """
        raise NotImplementedError  # pragma: no cover

    def run(self) -> Any:
        """Executes the task.

        If an exception is raised during execution, its stack will be printed in the logger and the exception
        will be re-raised.

        Raises:
        - e: Any exception raised by `do()`

        Returns:
        - Any: Any value returned by `do()`
        """
        if Task.DEBUGGING:
            return self.do()
        else:
            try:
                return self.do()
            except Exception as e:
                self.logger.critical("Got exception: {} {}".format(e.__class__.__name__, e), exc_info=e)
                raise e
