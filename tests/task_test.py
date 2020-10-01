import datetime
import logging

import pytest

from simpletasks.helpers import addTestLogger
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
        assert self.execute(lambda: "foo") == "foo"
        assert self.executeOrRetry(lambda: "foo") == "foo"
        return True


class ProgressTask(Task):
    def do(self) -> bool:
        self.logger.info("Hello, from ProgressTask!")
        for i in self.progress([1, 2, 3], desc="Iterate"):
            self.logger.info("loop #{}".format(i))
        return True


class StubbedTask(Task):
    def __init__(self, stubbedValue=None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.stubbedValue = stubbedValue

    def do(self) -> bool:
        assert self.execute(lambda: "foo", stubbedValue=self.stubbedValue) == self.stubbedValue
        assert self.executeOrRetry(lambda: "foo", stubbedValue=self.stubbedValue) == self.stubbedValue
        return True


class UnexpectedFailureTask(Task):
    def do(self) -> None:
        raise RuntimeError("error")


class FailureTask(Task):
    def failure(self) -> None:
        raise RuntimeError("error")

    def do(self) -> None:
        self.execute(self.failure)


class FailureRetryTask(Task):
    def failure(self) -> None:
        raise RuntimeError("error")

    def do(self) -> None:
        self.executeOrRetry(self.failure, initialdelay=0.1)


class TempsFailureRetryTask(Task):
    def failure(self) -> None:
        self.execs += 1
        if self.execs <= 3:
            raise RuntimeError("error")
        self.logger.info("OK!")

    def do(self) -> None:
        self.execs = 0
        self.executeOrRetry(self.failure, initialdelay=0.1)


def test_nominal(configure) -> None:
    o = NominalTask()
    assert o.loggernamespace == "simpletasks.NominalTask"
    assert o.timestamp == datetime.datetime.now().strftime("%Y-%m-%d")
    assert o.date == datetime.date.today()

    logger = addTestLogger(o)

    o.run()
    assert logger.getvalue() == "simpletasks.NominalTask - INFO - Hello, from NominalTask!\n"


def test_progress(configure) -> None:
    o = ProgressTask(progress=True)
    logger = addTestLogger(o)

    o.run()
    assert (
        logger.getvalue()
        == """simpletasks.ProgressTask - INFO - Hello, from ProgressTask!
simpletasks.ProgressTask - INFO - loop #1
simpletasks.ProgressTask - INFO - loop #2
simpletasks.ProgressTask - INFO - loop #3
"""
    )


def test_progress_hidden(configure) -> None:
    o = ProgressTask(progress=False)
    logger = addTestLogger(o)

    o.run()
    assert (
        logger.getvalue()
        == """simpletasks.ProgressTask - INFO - Hello, from ProgressTask!
simpletasks.ProgressTask - INFO - loop #1
simpletasks.ProgressTask - INFO - loop #2
simpletasks.ProgressTask - INFO - loop #3
"""
    )


def test_options(configure) -> None:
    logging.getLogger("myspace").setLevel(logging.INFO)

    o = NominalTask(
        loggernamespace="myspace",
        showprogress=False,
        quick=True,
        force=True,
        verbose=True,
        timestamp="2020-01-01",
        date=datetime.date(2020, 1, 1),
    )
    assert o.loggernamespace == "myspace"
    assert not o.showprogress
    assert o.force
    assert o.verbose
    assert o.timestamp == "2020-01-01"
    assert o.date == datetime.date(2020, 1, 1)

    logger = addTestLogger(o)

    o.run()
    assert logger.getvalue() == "myspace - INFO - Hello, from NominalTask!\n"


def test_dryrun(configure) -> None:
    o = StubbedTask(dryrun=True)
    logger = addTestLogger(o)

    o.run()
    assert (
        logger.getvalue()
        == "simpletasks.StubbedTask - INFO - Stubbed\nsimpletasks.StubbedTask - INFO - Stubbed\n"
    )


def test_dryrun_stubbedvalue(configure) -> None:
    o = StubbedTask(dryrun=True, stubbedValue="Foo")
    logger = addTestLogger(o)

    o.run()
    assert (
        logger.getvalue()
        == "simpletasks.StubbedTask - INFO - Stubbed\nsimpletasks.StubbedTask - INFO - Stubbed\n"
    )


def test_unexpected_failure(configure) -> None:
    o = UnexpectedFailureTask()
    logger = addTestLogger(o)

    with pytest.raises(RuntimeError) as e:
        o.run()
    assert str(e.value) == "error"
    output = logger.getvalue()
    assert output.startswith(
        "simpletasks.UnexpectedFailureTask - CRITICAL - Got exception: RuntimeError error\n"
    )
    assert output.endswith("RuntimeError: error\n")


def test_failure(configure) -> None:
    o = FailureTask()
    logger = addTestLogger(o)

    with pytest.raises(RuntimeError) as e:
        o.run()
    assert str(e.value) == "error"
    output = logger.getvalue()
    assert output.startswith("simpletasks.FailureTask - CRITICAL - Got exception: RuntimeError error\n")
    assert output.endswith("RuntimeError: error\n")


@pytest.mark.slow
def test_failureretry(configure) -> None:
    o = FailureRetryTask()
    logger = addTestLogger(o)

    with pytest.raises(RuntimeError) as e:
        o.run()
    assert str(e.value) == "error"
    output = logger.getvalue()
    assert output.startswith(
        """simpletasks.FailureRetryTask - WARNING - Failed 1 times (error), retrying in 0 seconds...
simpletasks.FailureRetryTask - WARNING - Failed 2 times (error), retrying in 0 seconds...
simpletasks.FailureRetryTask - WARNING - Failed 3 times (error), retrying in 0 seconds...
simpletasks.FailureRetryTask - WARNING - Failed 4 times (error), retrying in 0 seconds...
simpletasks.FailureRetryTask - WARNING - Failed 5 times (error), retrying in 1 seconds...
simpletasks.FailureRetryTask - WARNING - Too many failures, abandonning
simpletasks.FailureRetryTask - CRITICAL - Got exception: RuntimeError error
"""
    )
    assert output.endswith("RuntimeError: error\n")


@pytest.mark.slow
def test_tempfailureretry(configure) -> None:
    o = TempsFailureRetryTask()
    logger = addTestLogger(o)

    o.run()
    assert (
        logger.getvalue()
        == """simpletasks.TempsFailureRetryTask - WARNING - Failed 1 times (error), retrying in 0 seconds...
simpletasks.TempsFailureRetryTask - WARNING - Failed 2 times (error), retrying in 0 seconds...
simpletasks.TempsFailureRetryTask - WARNING - Failed 3 times (error), retrying in 0 seconds...
simpletasks.TempsFailureRetryTask - INFO - OK!
"""
    )


def test_debugging(configure) -> None:
    Task.DEBUGGING = True
    o = FailureTask()
    logger = addTestLogger(o)

    with pytest.raises(RuntimeError) as e:
        o.run()
    assert str(e.value) == "error"
    assert logger.getvalue() == ""
