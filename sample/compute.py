from typing import cast

import click

from simpletasks import Cli, CliParams, Task


@click.group()
def cli():
    pass


@Cli(cli, params=[click.argument("n", type=int), CliParams.progress()])
class FibonacciTask(Task):
    def compute(self, n: int) -> int:
        self.logger.debug(f"Called with n={n}")
        f1, f2 = 0, 1
        if n == 0:
            return f1
        if n == 1:
            return f2
        for _ in self.progress(range(1, n)):
            f1, f2 = f2, f1 + f2
        return f2

    def do(self) -> None:
        n = cast(int, self.options.get("n"))
        result = self.compute(n)
        print(f"f({n}) = {result}")


@Cli(cli, params=[click.argument("n", type=int), CliParams.progress()])
class FactorialTask(Task):
    def compute(self, n: int) -> int:
        self.logger.debug(f"Called with n={n}")
        if n == 0:
            return 1
        else:
            F = 1
            for k in self.progress(range(2, n + 1)):
                F = F * k
            return F

    def do(self) -> None:
        n = cast(int, self.options.get("n"))
        result = self.compute(n)
        print(f"f({n}) = {result}")


if __name__ == "__main__":
    cli()
