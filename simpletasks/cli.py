import datetime
from typing import Any, Callable, List, Optional, Type, TypeVar

import click

from .task import Task

_F = TypeVar("_F")
_click_parameter = Callable[[_F], _F]


class CliParams:
    @staticmethod
    def validate_date(ctx, param, value: str) -> Optional[datetime.date]:
        if not value:
            return None

        try:
            date = datetime.datetime.strptime(value, "%Y-%m-%d")
            return date
        except ValueError:
            raise click.BadParameter("timestamp must be in format YYYY-MM-DD")

    @staticmethod
    def progress() -> _click_parameter:
        return click.option(
            "--progress/--no-progress",
            is_flag=True,
            default=True,
            help="Show or hide progress bar",
        )

    @staticmethod
    def date() -> _click_parameter:
        return click.option("--date", default=None, help="Date YYYY-MM-DD", callback=CliParams.validate_date)

    @staticmethod
    def timestamp_deprecated() -> _click_parameter:
        return click.option("--timestamp", default=None, help="Date YYYY-MM-DD")

    @staticmethod
    def dryrun() -> _click_parameter:
        return click.option("--dryrun", is_flag=True, default=False, help="Do not make changes")

    @staticmethod
    def quick() -> _click_parameter:
        return click.option("--quick", is_flag=True, default=False, help="Quick")

    @staticmethod
    def include_archives() -> _click_parameter:
        return click.option(
            "--includearchives/--no-archives", is_flag=True, default=False, help="Include archives"
        )

    @staticmethod
    def force() -> _click_parameter:
        return click.option("--force", "-F", is_flag=True, default=False, help="Force")

    @staticmethod
    def verbose() -> _click_parameter:
        return click.option("--verbose/--no-verbose", "-v/ ", is_flag=True, default=False, help="Verbose")

    @staticmethod
    def fail_on_exception() -> _click_parameter:
        return click.option(
            "--fail-on-exception/--no-fail-on-exception",
            "-F/ ",
            is_flag=True,
            default=False,
            help="Fail and exit task on exception",
        )


class Cli(object):
    def __init__(
        self,
        group: click.Group,
        name: Optional[str] = None,
        params: Optional[List[_click_parameter]] = None,
        **kwargs,
    ) -> None:
        """Creates a Click command within a group

        Args:
            group (click.Group): Group to add the command to
            name: Name of the command (optional, taken from the name of the class in lowercase)
            params: List of options and arguments accepted by the command (optional)
            kwargs: Other parameters to pass to the command constructor
        """
        self.group = group
        self.args = kwargs
        self.name = name

        if params:
            self._task_options = params
        else:
            self._task_options = [
                CliParams.progress(),
                CliParams.timestamp_deprecated(),
                CliParams.dryrun(),
                CliParams.quick(),
            ]

    def task_options(self, func):
        for option in reversed(self._task_options):
            func = option(func)
        return func

    # from https://stackoverflow.com/questions/53147525/is-it-possible-to-dynamically-generate-commands-in-python-click
    def bind_function(self, name, c, cls) -> Callable[..., Any]:
        @self.task_options
        def func(**kwargs):
            # print("I am the '{}' command, ran with arguments: {}".format(c, kwargs))
            return cls(**kwargs).run()

        func.__name__ = name
        return func

    def __call__(self, cls: Type[Task]) -> Type[Task]:
        if self.name:
            name = self.name
        else:
            name = cls.__name__.replace("Task", "").lower()

        f = self.bind_function("_f", name, cls)
        _f = self.group.command(name=name, **self.args)(f)  # noqa: F841
        return cls
