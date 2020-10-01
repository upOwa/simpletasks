import io
import logging
import time

import pytest

from simpletasks.helpers import addTestLogger
from simpletasks.orchestrator import Orchestrator, Tasks
from simpletasks.task import Task


@pytest.fixture(scope="function")
def configure():
    DEBUGGING_old = Task.DEBUGGING
    TESTING_old = Task.TESTING
    LOGGER_NAMESPACE_old = Task.LOGGER_NAMESPACE

    Task.DEBUGGING = False
    Task.TESTING = True
    Task.LOGGER_NAMESPACE = "simpletasks."
    logger = logging.getLogger("simpletasks")
    logger.setLevel(logging.DEBUG)

    yield Task

    Task.DEBUGGING = DEBUGGING_old
    Task.TESTING = TESTING_old
    Task.LOGGER_NAMESPACE = LOGGER_NAMESPACE_old


class NominalTask(Task):
    def do(self) -> bool:
        time.sleep(0.1)
        self.logger.info("Hello, from NominalTask, called with options={}".format(self.options))
        time.sleep(1)
        return True


class NominalTask2(Task):
    def do(self) -> bool:
        time.sleep(0.1)
        self.logger.info("Hello, from NominalTask2, called with options={}".format(self.options))
        time.sleep(0.5)
        return True


class NominalTask3(Task):
    def do(self) -> bool:
        time.sleep(0.1)
        self.logger.info("Hello, from NominalTask3, called with options={}".format(self.options))
        time.sleep(0.5)
        return True


class NominalTask4(Task):
    def do(self) -> bool:
        time.sleep(0.1)
        self.logger.info("Hello, from NominalTask4!")
        time.sleep(0.5)
        return True


class FailureTask(Task):
    def do(self) -> None:
        time.sleep(0.1)
        raise RuntimeError("error")


class Orch(Orchestrator):
    tasks: Tasks = {
        NominalTask: ([], {}),
        NominalTask2: ([], {"show_progress": True}),
        NominalTask3: ([NominalTask], {"loggernamespace": "simpletasks.Foo"}),
        FailureTask: ([NominalTask2], {}),
        NominalTask4: ([NominalTask2, NominalTask3], {}),
    }
    num_threads = 3


# BUG: an orchestrator cannot be run multiple times, figure out why
class Orch2(Orchestrator):
    tasks: Tasks = {
        NominalTask: ([], {}),
        NominalTask2: ([], {"show_progress": True}),
        NominalTask3: ([NominalTask], {"loggernamespace": "simpletasks.Foo"}),
        FailureTask: ([NominalTask2], {}),
        NominalTask4: ([NominalTask2, NominalTask3], {}),
    }
    num_threads = 3


class OrchDeadlock(Orchestrator):
    tasks: Tasks = {
        NominalTask: ([], {}),
        NominalTask2: ([], {}),
        NominalTask4: ([NominalTask3], {}),
    }
    num_threads = 3


@pytest.mark.slow
def test_orchestrator(configure) -> None:
    o = Orch(show_progress=False, dryrun=True, verbose=True)
    task_logger = addTestLogger(o)

    foo_logger = io.StringIO()
    ch = logging.StreamHandler(foo_logger)
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(logging.Formatter("%(name)s - %(levelname)s - %(message)s"))
    logging.getLogger("simpletasks.Foo").addHandler(ch)

    with pytest.raises(RuntimeError) as e:
        o.run()
    assert str(e.value) == "Task failed"

    assert o._events == [
        ("added", "NominalTask", ""),
        ("added", "NominalTask2", ""),
        (
            "started",
            "NominalTask",
            "{'show_progress': False, 'dryrun': True, 'verbose': True, 'loggernamespace': 'simpletasks.Orch.NominalTask'}",
        ),
        (
            "started",
            "NominalTask2",
            "{'show_progress': True, 'dryrun': True, 'verbose': True, 'loggernamespace': 'simpletasks.Orch.NominalTask2'}",
        ),
        ("completed", "NominalTask2", "True"),
        ("added", "FailureTask", ""),
        (
            "started",
            "FailureTask",
            "{'show_progress': False, 'dryrun': True, 'verbose': True, 'loggernamespace': 'simpletasks.Orch.FailureTask'}",
        ),
        ("failed", "FailureTask", "error"),
        ("completed", "NominalTask", "True"),
        ("done", "", ""),
    ]

    output = task_logger.getvalue()
    assert (
        """simpletasks.Orch - INFO - Starting task NominalTask
simpletasks.Orch - DEBUG - Using arguments: {'show_progress': False, 'dryrun': True, 'verbose': True, 'loggernamespace': 'simpletasks.Orch.NominalTask'}
"""
        in output
    )
    assert (
        """simpletasks.Orch - INFO - Starting task NominalTask2
simpletasks.Orch - DEBUG - Using arguments: {'show_progress': True, 'dryrun': True, 'verbose': True, 'loggernamespace': 'simpletasks.Orch.NominalTask2'}
"""
        in output
    )
    assert (
        """simpletasks.Orch - INFO - Starting task FailureTask
simpletasks.Orch - DEBUG - Using arguments: {'show_progress': False, 'dryrun': True, 'verbose': True, 'loggernamespace': 'simpletasks.Orch.FailureTask'}
"""
        in output
    )
    assert """simpletasks.Orch - INFO - Starting task NominalTask3""" not in output
    assert """simpletasks.Orch - INFO - Starting task NominalTask4""" not in output

    assert (
        "simpletasks.Orch.NominalTask - INFO - Hello, from NominalTask, called with options={'show_progress': False, 'dryrun': True, 'verbose': True, 'loggernamespace': 'simpletasks.Orch.NominalTask'}"
        in output
    )
    assert (
        "simpletasks.Orch.NominalTask2 - INFO - Hello, from NominalTask2, called with options={'show_progress': True, 'dryrun': True, 'verbose': True, 'loggernamespace': 'simpletasks.Orch.NominalTask2'}"
        in output
    )
    assert "simpletasks.Orch.NominalTask4 - INFO - Hello, from NominalTask4!" not in output

    assert "simpletasks.Orch - INFO - Completed task NominalTask2: True" in output
    assert "simpletasks.Orch - INFO - Completed task NominalTask: True" in output
    assert "simpletasks.Orch - INFO - Completed task NominalTask3: True" not in output
    assert "simpletasks.Orch - INFO - Completed task NominalTask4: True" not in output

    assert (
        """simpletasks.Orch.FailureTask - CRITICAL - Got exception: RuntimeError error
Traceback (most recent call last):
"""
        in output
    )
    assert "simpletasks.Orch - CRITICAL - Could not run FailureTask: RuntimeError error" in output

    assert foo_logger.getvalue() == ""


@pytest.mark.slow
def test_orchestrator_error_catched(configure) -> None:
    o = Orch2(show_progress=False, dryrun=True, verbose=True, fail_on_exception=False)
    task_logger = addTestLogger(o)

    foo_logger = io.StringIO()
    ch = logging.StreamHandler(foo_logger)
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(logging.Formatter("%(name)s - %(levelname)s - %(message)s"))
    logging.getLogger("simpletasks.Foo").addHandler(ch)

    with pytest.raises(RuntimeError) as e:
        o.run()
    assert str(e.value) == "Task failed"

    assert o._events == [
        ("added", "NominalTask", ""),
        ("added", "NominalTask2", ""),
        (
            "started",
            "NominalTask",
            "{'show_progress': False, 'dryrun': True, 'verbose': True, 'fail_on_exception': False, 'loggernamespace': 'simpletasks.Orch2.NominalTask'}",
        ),
        (
            "started",
            "NominalTask2",
            "{'show_progress': True, 'dryrun': True, 'verbose': True, 'fail_on_exception': False, 'loggernamespace': 'simpletasks.Orch2.NominalTask2'}",
        ),
        ("completed", "NominalTask2", "True"),
        ("added", "FailureTask", ""),
        (
            "started",
            "FailureTask",
            "{'show_progress': False, 'dryrun': True, 'verbose': True, 'fail_on_exception': False, 'loggernamespace': 'simpletasks.Orch2.FailureTask'}",
        ),
        ("failed", "FailureTask", "error"),
        ("completed", "NominalTask", "True"),
        ("added", "NominalTask3", ""),
        (
            "started",
            "NominalTask3",
            "{'show_progress': False, 'dryrun': True, 'verbose': True, 'fail_on_exception': False, 'loggernamespace': 'simpletasks.Foo'}",
        ),
        ("completed", "NominalTask3", "True"),
        ("added", "NominalTask4", ""),
        (
            "started",
            "NominalTask4",
            "{'show_progress': False, 'dryrun': True, 'verbose': True, 'fail_on_exception': False, 'loggernamespace': 'simpletasks.Orch2.NominalTask4'}",
        ),
        ("completed", "NominalTask4", "True"),
        ("done", "", ""),
    ]

    output = task_logger.getvalue()
    assert (
        """simpletasks.Orch2 - INFO - Starting task NominalTask
simpletasks.Orch2 - DEBUG - Using arguments: {'show_progress': False, 'dryrun': True, 'verbose': True, 'fail_on_exception': False, 'loggernamespace': 'simpletasks.Orch2.NominalTask'}
"""
        in output
    )
    assert (
        """simpletasks.Orch2 - INFO - Starting task NominalTask2
simpletasks.Orch2 - DEBUG - Using arguments: {'show_progress': True, 'dryrun': True, 'verbose': True, 'fail_on_exception': False, 'loggernamespace': 'simpletasks.Orch2.NominalTask2'}
"""
        in output
    )
    assert (
        """simpletasks.Orch2 - INFO - Starting task FailureTask
simpletasks.Orch2 - DEBUG - Using arguments: {'show_progress': False, 'dryrun': True, 'verbose': True, 'fail_on_exception': False, 'loggernamespace': 'simpletasks.Orch2.FailureTask'}
"""
        in output
    )
    assert (
        """simpletasks.Orch2 - INFO - Starting task NominalTask3
simpletasks.Orch2 - DEBUG - Using arguments: {'show_progress': False, 'dryrun': True, 'verbose': True, 'fail_on_exception': False, 'loggernamespace': 'simpletasks.Foo'}
"""
        in output
    )
    assert (
        """simpletasks.Orch2 - INFO - Starting task NominalTask4
simpletasks.Orch2 - DEBUG - Using arguments: {'show_progress': False, 'dryrun': True, 'verbose': True, 'fail_on_exception': False, 'loggernamespace': 'simpletasks.Orch2.NominalTask4'}
"""
        in output
    )

    assert (
        "simpletasks.Orch2.NominalTask - INFO - Hello, from NominalTask, called with options={'show_progress': False, 'dryrun': True, 'verbose': True, 'fail_on_exception': False, 'loggernamespace': 'simpletasks.Orch2.NominalTask'}"
        in output
    )
    assert (
        "simpletasks.Orch2.NominalTask2 - INFO - Hello, from NominalTask2, called with options={'show_progress': True, 'dryrun': True, 'verbose': True, 'fail_on_exception': False, 'loggernamespace': 'simpletasks.Orch2.NominalTask2'}"
        in output
    )
    assert "simpletasks.Orch2.NominalTask4 - INFO - Hello, from NominalTask4!" in output

    assert "simpletasks.Orch2 - INFO - Completed task NominalTask2: True" in output
    assert "simpletasks.Orch2 - INFO - Completed task NominalTask: True" in output
    assert "simpletasks.Orch2 - INFO - Completed task NominalTask3: True" in output
    assert "simpletasks.Orch2 - INFO - Completed task NominalTask4: True" in output

    assert (
        """simpletasks.Orch2.FailureTask - CRITICAL - Got exception: RuntimeError error
Traceback (most recent call last):
"""
        in output
    )
    assert "simpletasks.Orch2 - CRITICAL - Could not run FailureTask: RuntimeError error" in output

    assert (
        foo_logger.getvalue()
        == """simpletasks.Foo - INFO - Hello, from NominalTask3, called with options={'show_progress': False, 'dryrun': True, 'verbose': True, 'fail_on_exception': False, 'loggernamespace': 'simpletasks.Foo'}
"""
    )


@pytest.mark.slow
def test_orchestrator_deadlock(configure) -> None:
    o = OrchDeadlock()
    task_logger = addTestLogger(o)

    o.run()

    assert o._events == [
        ("added", "NominalTask", ""),
        ("added", "NominalTask2", ""),
        (
            "started",
            "NominalTask",
            "{'loggernamespace': 'simpletasks.OrchDeadlock.NominalTask'}",
        ),
        (
            "started",
            "NominalTask2",
            "{'loggernamespace': 'simpletasks.OrchDeadlock.NominalTask2'}",
        ),
        ("completed", "NominalTask2", "True"),
        ("completed", "NominalTask", "True"),
        ("done", "", ""),
    ]

    output = task_logger.getvalue()
    assert (
        """simpletasks.OrchDeadlock - INFO - Starting task NominalTask
simpletasks.OrchDeadlock - DEBUG - Using arguments: {'loggernamespace': 'simpletasks.OrchDeadlock.NominalTask'}
"""
        in output
    )
    assert (
        """simpletasks.OrchDeadlock - INFO - Starting task NominalTask2
simpletasks.OrchDeadlock - DEBUG - Using arguments: {'loggernamespace': 'simpletasks.OrchDeadlock.NominalTask2'}
"""
        in output
    )
    assert (
        """simpletasks.OrchDeadlock - CRITICAL - Done but some tasks remaining: NominalTask4
"""
        in output
    )
