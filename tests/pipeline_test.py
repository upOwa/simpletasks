import datetime
import logging

import pytest

from simpletasks.helpers import addTestLogger
from simpletasks.pipeline import Pipeline
from simpletasks.task import Task


@pytest.fixture(scope="function")
def configure():
    DEBUGGING_old = Task.DEBUGGING
    TESTING_old = Task.TESTING
    LOGGER_NAMESPACE_old = Task.LOGGER_NAMESPACE

    Task.DEBUGGING = False
    Task.TESTING = False
    Task.LOGGER_NAMESPACE = "simpletasks."
    logger = logging.getLogger("simpletasks")
    logger.setLevel(logging.INFO)

    yield Task

    Task.DEBUGGING = DEBUGGING_old
    Task.TESTING = TESTING_old
    Task.LOGGER_NAMESPACE = LOGGER_NAMESPACE_old


class NominalTask(Task):
    def do(self) -> bool:
        self.logger.info("Hello, from NominalTask!")
        self.logger.info("Called with options={}".format(self.options))
        return True


class NominalTask2(Task):
    def do(self) -> bool:
        self.logger.info("Hello, from NominalTask2!")
        self.logger.info("Called with options={}".format(self.options))
        return True


class FailureTask(Task):
    def do(self) -> None:
        raise RuntimeError("error")


class NominalPipeline(Pipeline):
    tasks = [NominalTask, NominalTask2]


class FailurePipeline(Pipeline):
    tasks = [NominalTask, FailureTask, NominalTask2]


def test_pipeline(configure) -> None:
    o = NominalPipeline()
    logger = addTestLogger(o)

    o.run()
    assert (
        logger.getvalue()
        == """simpletasks.NominalPipeline.NominalTask - INFO - Hello, from NominalTask!
simpletasks.NominalPipeline.NominalTask - INFO - Called with options={'loggernamespace': 'simpletasks.NominalPipeline.NominalTask'}
simpletasks.NominalPipeline.NominalTask2 - INFO - Hello, from NominalTask2!
simpletasks.NominalPipeline.NominalTask2 - INFO - Called with options={'loggernamespace': 'simpletasks.NominalPipeline.NominalTask2'}
"""
    )


def test_failure(configure) -> None:
    o = FailurePipeline()
    logger = addTestLogger(o)

    with pytest.raises(RuntimeError) as e:
        o.run()
    assert str(e.value) == "error"

    output = logger.getvalue()
    assert output.startswith(
        """simpletasks.FailurePipeline.NominalTask - INFO - Hello, from NominalTask!
simpletasks.FailurePipeline.NominalTask - INFO - Called with options={'loggernamespace': 'simpletasks.FailurePipeline.NominalTask'}
simpletasks.FailurePipeline.FailureTask - CRITICAL - Got exception: RuntimeError error
Traceback (most recent call last):
"""
    )
    assert output.endswith(
        """RuntimeError: error
"""
    )


def test_failure_catched(configure) -> None:
    o = FailurePipeline(fail_on_exception=False)
    logger = addTestLogger(o)

    with pytest.raises(RuntimeError) as e:
        o.run()
    assert str(e.value) == "Task failed"

    output = logger.getvalue()
    assert output.startswith(
        """simpletasks.FailurePipeline.NominalTask - INFO - Hello, from NominalTask!
simpletasks.FailurePipeline.NominalTask - INFO - Called with options={'fail_on_exception': False, 'loggernamespace': 'simpletasks.FailurePipeline.NominalTask'}
simpletasks.FailurePipeline.FailureTask - CRITICAL - Got exception: RuntimeError error
Traceback (most recent call last):
"""
    )
    assert (
        """RuntimeError: error
simpletasks.FailurePipeline.NominalTask2 - INFO - Hello, from NominalTask2!
simpletasks.FailurePipeline.NominalTask2 - INFO - Called with options={'fail_on_exception': False, 'loggernamespace': 'simpletasks.FailurePipeline.NominalTask2'}
simpletasks.FailurePipeline - CRITICAL - Could not run FailureTask: RuntimeError error
simpletasks.FailurePipeline - CRITICAL - Got exception: RuntimeError Task failed
"""
        in output
    )
    assert output.endswith(
        """RuntimeError: Task failed
"""
    )


def test_options(configure) -> None:
    logging.getLogger("myspace").setLevel(logging.INFO)

    o = NominalPipeline(
        loggernamespace="myspace",
        showprogress=False,
        dryrun=True,
        quick=True,
        force=True,
        verbose=True,
        timestamp="2020-01-01",
        date=datetime.date(2020, 1, 1),
    )
    assert o.loggernamespace == "myspace"
    assert not o.showprogress
    assert o.dryrun
    assert o.force
    assert o.verbose
    assert o.timestamp == "2020-01-01"
    assert o.date == datetime.date(2020, 1, 1)

    logger = addTestLogger(o)

    o.run()
    assert (
        logger.getvalue()
        == """myspace.NominalTask - INFO - Hello, from NominalTask!
myspace.NominalTask - INFO - Called with options={'loggernamespace': 'myspace.NominalTask', 'showprogress': False, 'dryrun': True, 'quick': True, 'force': True, 'verbose': True, 'timestamp': '2020-01-01', 'date': datetime.date(2020, 1, 1)}
myspace.NominalTask2 - INFO - Hello, from NominalTask2!
myspace.NominalTask2 - INFO - Called with options={'loggernamespace': 'myspace.NominalTask2', 'showprogress': False, 'dryrun': True, 'quick': True, 'force': True, 'verbose': True, 'timestamp': '2020-01-01', 'date': datetime.date(2020, 1, 1)}
"""
    )
