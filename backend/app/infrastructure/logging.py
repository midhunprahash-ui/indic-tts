from __future__ import annotations

import logging
import sys

import structlog


LOG_CONFIGURED = False


def configure_logging(level: str = "INFO") -> None:
    global LOG_CONFIGURED
    if LOG_CONFIGURED:
        return

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper(), logging.INFO),
    )

    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level.upper(), logging.INFO)),
    )

    LOG_CONFIGURED = True


def get_logger(name: str):
    configure_logging()
    return structlog.get_logger(name)
