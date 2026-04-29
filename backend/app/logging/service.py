"""
Logger Service
"""

import threading

from app.logging.logger_dao import LoggerDAO
from app.logging.Model.Log import Log, LogLevel

import logging
logger = logging.getLogger(__name__)

class LoggerService():
    def __init__(self, service_name: str, logger_dao: LoggerDAO | None = None) -> None:
        self._dao = logger_dao or LoggerDAO()
        self.service_name = service_name

    # Helpers
    def _log(self, log_level: LogLevel, message: str, user_id: str | None = None, event_id: str | None = None) -> None:
        log = Log(log_level=log_level, message=message, service_name=self.service_name, user_id=user_id, event_id=event_id)
        self._dao.insert(log)

    # Fire and forget log
    def info(self, message: str, user_id: str | None = None, event_id: str | None = None) -> None:
        logger.info(message)
        threading.Thread(target=self._log, daemon=True, args=(LogLevel.INFO, message, user_id, event_id)).start()

    def warning(self, message: str, user_id: str | None = None, event_id: str | None = None) -> None:
        logger.warning(message)
        threading.Thread(target=self._log, daemon=True, args=(LogLevel.WARNING, message, user_id, event_id)).start()

    def error(self, message: str, user_id: str | None = None, event_id: str | None = None) -> None:
        logger.error(message)
        threading.Thread(target=self._log, daemon=True, args=(LogLevel.ERROR, message, user_id, event_id)).start()

    def critical(self, message: str, user_id: str | None = None, event_id: str | None = None) -> None:
        logger.critical(message)
        threading.Thread(target=self._log, daemon=True, args=(LogLevel.CRITICAL, message, user_id, event_id)).start()


