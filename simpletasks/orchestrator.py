import abc
import queue
import threading
from typing import Any, Dict, List, Optional, Tuple, Type

from .task import Task

_TTask = Type[Task]
_Args = Dict[str, Any]
Tasks = Dict[_TTask, Tuple[List[_TTask], _Args]]


class Orchestrator(Task):
    """Orchestrates multiple tasks"""

    @property
    @abc.abstractmethod
    def tasks(self) -> Tasks:
        pass  # pragma: no cover

    @property
    @abc.abstractmethod
    def num_threads(self) -> int:
        pass  # pragma: no cover

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        self._queue = {key: value for key, value in self.tasks.items()}
        self._args = kwargs
        if Task.TESTING:
            self._events: List[Tuple[str, str, str]] = []
        self.fail_on_exception = self.options.get("fail_on_exception", True)

    def _findNextTasks(self) -> None:
        if self.fail_on_exception and len(self.exceptions) > 0:
            # TODO: we could pick up all tasks not depending on the one that failed
            self.logger.debug("Failure - not picking up any new tasks")
            return

        availableTasks = list(filter(lambda x: len(self._queue[x][0]) == 0, self._queue))
        if not availableTasks:
            return

        for task in availableTasks:
            args = self._args.copy()
            args.update(self._queue[task][1])
            args.update({"loggernamespace": self.loggernamespace + "." + task.__name__})
            args.update(self._args)
            args.update(self._queue[task][1])
            del self._queue[task]

            if Task.TESTING:
                self._events.append(("added", task.__name__, ""))
            self.logger.info("Adding task {} into queue".format(task.__name__))
            self.q.put((task, args))

    def _worker(self) -> None:
        while True:
            item = self.q.get()
            if item is None:
                break

            with self.lock:
                if Task.TESTING:
                    self._events.append(("started", item[0].__name__, str(item[1])))
                self.logger.info("Starting task {}".format(item[0].__name__))
                self.logger.debug("Using arguments: {}".format(item[1]))

            try:
                t = item[0](**(item[1]))
                res = t.run()
                if Task.TESTING:
                    self._events.append(("completed", item[0].__name__, str(res)))
                self.logger.info("Completed task {}: {}".format(item[0].__name__, res))
            except Exception as e:
                self.logger.info("Failed task {}: {}".format(item[0].__name__, e))
                with self.lock:
                    if Task.TESTING:
                        self._events.append(("failed", item[0].__name__, str(e)))
                    self.exceptions.append((item[0], e))

            with self.lock:
                for predecessors in self._queue.values():
                    if item[0] in predecessors[0]:
                        predecessors[0].remove(item[0])

                self._findNextTasks()
                self.logger.debug("{} tasks remaining in queue".format(self.q.qsize()))

                self.q.task_done()

    def do(self) -> None:
        self.exceptions: List[Tuple[_TTask, Exception]] = []
        threads = []
        self.q: queue.Queue[Optional[Tuple[_TTask, _Args]]] = queue.Queue()
        self.lock = threading.Lock()

        for _i in range(self.num_threads):
            t = threading.Thread(target=self._worker)
            t.start()
            threads.append(t)

        with self.lock:
            self._findNextTasks()

        self.q.join()
        for _i in range(self.num_threads):
            self.q.put(None)
        for t in threads:
            t.join()

        if len(self._queue) > 0:
            self.logger.critical(
                "Done but some tasks remaining: {}".format(";".join([x.__name__ for x in self._queue.keys()]))
            )

        if Task.TESTING:
            self._events.append(("done", "", ""))

        if self.exceptions:
            for task, exception in self.exceptions:
                self.logger.critical(
                    "Could not run {}: {} {}".format(task.__name__, exception.__class__.__name__, exception)
                )
            raise RuntimeError("Task failed")
