import datetime
import logging

import pytest

from simpletasks.task import Task

try:
    import click
    from click.testing import CliRunner

    from simpletasks.cli import Cli, CliParams

    @click.group()
    def cli():
        pass


except ImportError:
    pytest.skip("Skipping Cli tests - click not installed", allow_module_level=True)


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


def test_nominal(configure) -> None:
    @Cli(cli)
    class NominalTask(Task):
        def do(self) -> bool:
            click.echo("Hello, from NominalTask!")
            return True

    runner = CliRunner()
    result = runner.invoke(cli, ["nominal"])
    assert result.exit_code == 0
    assert result.output == "Hello, from NominalTask!\n"


def test_options(configure) -> None:
    @Cli(
        cli,
        "mytask",
        [
            CliParams.date(),
            CliParams.include_archives(),
            CliParams.force(),
            CliParams.verbose(),
            CliParams.fail_on_exception(),
            CliParams.timestamp_deprecated(),
        ],
    )
    class OptionsTask(Task):
        def do(self) -> bool:
            click.echo("Hello, from MyTask!")
            return True

    runner = CliRunner()
    result = runner.invoke(cli, ["mytask"])
    assert result.exit_code == 0
    assert result.output == "Hello, from MyTask!\n"


def test_date(configure) -> None:
    @Cli(
        cli,
        params=[
            CliParams.date(),
        ],
    )
    class DateTask(Task):
        def do(self) -> None:
            assert self.date is not None
            assert type(self.date) == datetime.date
            click.echo(self.date.strftime("%Y-%m-%d"))

    runner = CliRunner()
    result = runner.invoke(cli, ["date", "--date", "2020-01-01"])
    assert result.exit_code == 0
    assert result.output == "2020-01-01\n"

    result = runner.invoke(cli, ["date"])
    assert result.exit_code == 0
    assert result.output == "{:%Y-%m-%d}\n".format(datetime.date.today())

    result = runner.invoke(cli, ["date", "--date", "invalid-date"])
    assert result.exit_code == 2
    assert "Error: Invalid value for '--date': timestamp must be in format YYYY-MM-DD" in result.output
