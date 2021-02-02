import io
import logging
from typing import Optional

from .task import Task


def addTestLogger(task: Task, level: int = logging.DEBUG, fmt: Optional[str] = None) -> io.StringIO:
    """Adds a StringIO logger to a task.

    Usage:
    ```
    o = MyTask()
    logger = addTestLogger(o)
    o.run()
    assert logger.getvalue() == "simpletasks.MyTask - INFO - Hello, from MyTask!\n"
    ```

    Args:
    - task (Task): Task to attach the logger to
    - level (int, optional): Level of logger. Defaults to logging.DEBUG.
    - fmt (Optional[str], optional): Logger formatting. Defaults to `%(name)s - %(levelname)s - %(message)s`.

    Returns:
    - io.StringIO: StringIO
    """
    log_stream = io.StringIO()
    ch = logging.StreamHandler(log_stream)
    ch.setLevel(level)
    ch.setFormatter(logging.Formatter(fmt if fmt else "%(name)s - %(levelname)s - %(message)s"))
    task.logger.addHandler(ch)
    return log_stream
