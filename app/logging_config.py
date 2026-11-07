import logging

from app.config import settings

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    """Настроить логирование по значениям из окружения (LOG_LEVEL, LOG_FORMAT)."""
    level = settings.log_level.upper()
    logging.basicConfig(format=settings.log_format)
    logging.getLogger("app").setLevel(level)
    logger.info("Логирование настроено, уровень: %s", level)
