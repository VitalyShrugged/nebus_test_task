import json
import logging
import os
from traceback import format_exception

from loguru import logger
from orjson import dumps, OPT_SERIALIZE_NUMPY
from sys import stderr
from inspect import currentframe


class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        # Get corresponding Loguru level if it exists.
        level: str | int
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message.
        frame, depth = currentframe(), 0
        while frame and (depth == 0 or frame.f_code.co_filename == logging.__file__):
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def log_serializer(message: str) -> None:
    record = json.loads(message)["record"]
    exception = record.get("exception")
    try:
        if exception:
            # Serialize the exception traceback as a string
            exc_type, exc_value, exc_tb = exception
            exception_str = "".join(format_exception(exc_type, exc_value, exc_tb))
        else:
            exception_str = None
    except Exception:
        exception_str = str(exception)

    log_format = {
        "level": record["level"]["name"],
        "message": record.get("message"),
        "datetime": record["time"]["repr"],
        "timestamp": record["time"]["timestamp"],
        "module": record.get("module"),
        "file": record["file"]["name"],
        "function": record.get("function"),
        "line": record.get("line"),
        "exception": str(record.get("exception")),
        "traceback": exception_str
    }
    serialized = dumps(log_format, option=OPT_SERIALIZE_NUMPY).decode("utf-8")
    print(serialized, file=stderr)


log_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "default": {
            "class": "app.modules.infra.logs.setting.InterceptHandler",  # InterceptHandler class path
        },
    },
    "loggers": {
        "": {"handlers": ["default"], "level": "INFO", "propagate": False},  # app logs

        "uvicorn": {"handlers": ["default"], "level": "INFO", "propagate": False},  # uvicorn logs
        "uvicorn.error": {"handlers": ["default"], "level": "ERROR", "propagate": False},  # uvicorn error logs
        "uvicorn.access": {"handlers": ["default"], "level": "INFO", "propagate": False},  # uvicorn access logs
    },
}

logging.basicConfig(level=0, handlers=(InterceptHandler(),), force=True)
logger.remove(0)
logger.add(
    sink=log_serializer,
    level=(os.getenv("LOG_LEVEL", "")
           if os.getenv("LOG_LEVEL", "") in ["INFO", "ERROR", "DEBUG", "WARNING"]
           else "ERROR"),
    colorize=True,
    backtrace=True,
    diagnose=False,
    serialize=True
)
