import logging

from app.infrastructure.correlation import get_correlation_id
from app.infrastructure.settings import Settings


class _CorrelationIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id() or "-"
        return True


def configure_logging(settings: Settings) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)s [%(correlation_id)s] %(name)s: %(message)s",
        )
    )
    handler.addFilter(_CorrelationIdFilter())

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(settings.log_level)
