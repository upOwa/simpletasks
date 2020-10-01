import io
import logging

from .task import Task


def addTestLogger(task: Task) -> io.StringIO:
    log_stream = io.StringIO()
    ch = logging.StreamHandler(log_stream)
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(logging.Formatter("%(name)s - %(levelname)s - %(message)s"))
    task.logger.addHandler(ch)
    return log_stream
