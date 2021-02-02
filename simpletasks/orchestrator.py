import abc
import copy
import logging
import queue
import threading
from typing import Any, Dict, List, Optional, Tuple, Type

from .task import Task

_TTask = Type[Task]
_Args = Dict[str, Any]
Tasks = Dict[_TTask, Tuple[List[_TTask], _Args]]


class Orchestrator(Task):
    """Task to execute multiple tasks in parallel (experimental).

    Definition:
    ```
    class MySubTask1(Task):
        ...
    class MySubTask2(Task):
        ...

    class MyTask(Orchestrator):
        tasks = {
            MySubTask1: ([], {}),
            MySubTask2: ([MySubTask1], {}),
        }
        num_threads = 3
    ```
    """

    @property
    @abc.abstractmethod
    def tasks(self) -> Tasks:
        """Map of tasks to execute.

        Keys are the types of the tasks to execute.
        Values are a tuple of 2 items:
        - List of predecessors
        - Map of options for the task (if any)

        Returns:
        - Tasks: Map of tasks.
        """
        pass  # pragma: no cover

    @property
    @abc.abstractmethod
    def num_threads(self) -> int:
        """Defines the maximum number of concurrent threads to use

        Returns:
        - int: Maximum number of concurrent threads to use
        """
        pass  # pragma: no cover

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        self._queue = {key: copy.deepcopy(value) for key, value in self.tasks.items()}
        self._args = copy.deepcopy(kwargs)
        self.fail_on_exception = self.options.get("fail_on_exception", True)

        self.exceptions: List[Tuple[_TTask, Exception]] = []
        self.q: queue.Queue[Optional[Tuple[_TTask, _Args]]] = queue.Queue()
        self.lock = threading.Lock()

    def _findNextTasks(self) -> None:
        """ Not thread-safe, must be guarded """
        if self.fail_on_exception and len(self.exceptions) > 0:
            # TODO: we could pick up all tasks not depending on the one that failed
            self.logger.debug("Failure - not picking up any new tasks")
            return

        availableTasks = list(filter(lambda x: len(self._queue[x][0]) == 0, self._queue))
        if not availableTasks:
            return

        for task in availableTasks:
            args = copy.deepcopy(self._args)
            args.update(self._queue[task][1])
            args.update({"loggernamespace": self.loggernamespace + "." + task.__name__})
            args.update(self._args)
            args.update(self._queue[task][1])
            del self._queue[task]

            self.logger.info("Adding task {} into queue".format(task.__name__))
            self.q.put((task, args))

    def _worker(self) -> None:
        while True:
            item = self.q.get()
            if item is None:
                break

            self.logger.info("Starting task {}".format(item[0].__name__))
            if self.logger.isEnabledFor(logging.DEBUG):
                self.logger.debug("Starting task {} using arguments: {}".format(item[0].__name__, item[1]))

            try:
                t = item[0](**(item[1]))
                res = t.run()
                self.logger.info("Completed task {}: {}".format(item[0].__name__, res))
            except Exception as e:
                self.logger.info("Failed task {}: {}".format(item[0].__name__, e))
                self.exceptions.append((item[0], e))

            with self.lock:
                for predecessors in self._queue.values():
                    if item[0] in predecessors[0]:
                        predecessors[0].remove(item[0])

                self._findNextTasks()
                self.logger.debug("{} tasks remaining in queue".format(self.q.qsize()))

                self.q.task_done()

    def do(self) -> None:
        threads = []

        for _ in range(self.num_threads):
            t = threading.Thread(target=self._worker)
            t.start()
            threads.append(t)

        with self.lock:
            self._findNextTasks()

        self.q.join()
        for _ in range(self.num_threads):
            self.q.put(None)
        for t in threads:
            t.join()

        if len(self._queue) > 0:
            self.logger.critical(
                "Done but some tasks remaining: {}".format(";".join([x.__name__ for x in self._queue.keys()]))
            )

        if self.exceptions:
            for task, exception in self.exceptions:
                self.logger.critical(
                    "Could not run {}: {} {}".format(task.__name__, exception.__class__.__name__, exception)
                )
            raise RuntimeError("Task failed")
