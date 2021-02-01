import io
import logging
from typing import Optional

from .task import Task


def addTestLogger(task: Task, level: int = logging.DEBUG, fmt: Optional[str] = None) -> io.StringIO:
    log_stream = io.StringIO()
    ch = logging.StreamHandler(log_stream)
    ch.setLevel(level)
    ch.setFormatter(logging.Formatter(fmt if fmt else "%(name)s - %(levelname)s - %(message)s"))
    task.logger.addHandler(ch)
    return log_stream
