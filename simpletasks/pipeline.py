import abc
from typing import List, Type

from .task import Task


class Pipeline(Task):
    """Task to execute multiple tasks one after each other.

    Definition:
    ```
    class MySubTask1(Task):
        ...
    class MySubTask2(Task):
        ...

    class MyTask(Pipeline):
        tasks = [MySubTask1, MySubTask2]
    ```
    """

    @property
    @abc.abstractmethod
    def tasks(self) -> List[Type[Task]]:
        pass  # pragma: no cover

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.args = kwargs
        self.fail_on_exception = self.options.get("fail_on_exception", True)

    def do(self) -> None:
        exceptions = []
        for t in self.tasks:
            args = self.args.copy()
            args.update({"loggernamespace": self.loggernamespace + "." + t.__name__})
            if self.fail_on_exception:
                t(**args).run()
            else:
                try:
                    t(**args).run()
                except Exception as e:
                    exceptions.append((t, e))

        if exceptions:
            for task, exception in exceptions:
                self.logger.critical(
                    "Could not run {}: {} {}".format(task.__name__, exception.__class__.__name__, exception)
                )
            raise RuntimeError("Task failed")
