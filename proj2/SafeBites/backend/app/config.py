"""
Configuration Module for SafeBites

- Loads environment variables using dotenv.
- Defines MongoDB connection URIs and database names.
- Sets up JWT secret for authentication.
- Configures logging with both console and rotating file handlers.
- Supports colored console logs and separate error log file.

Usage:
    from app.config import MONGO_URI, DB_NAME, setup_logging
    setup_logging()
"""
import os
import logging
import logging.config
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
from langsmith import utils as langsmith_utils

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME")
TEST_DB_NAME = os.getenv("TEST_DB_NAME", "foodapp_test")
JWT_SECRET = os.getenv("JWT_SECRET", "change_me")


LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, "safebites.log")
ERROR_LOG_FILE = os.path.join(LOG_DIR, "errors.log")

LOG_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(name)s | "
    "%(filename)s:%(lineno)d | %(message)s"
)

def setup_logging():
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": LOG_FORMAT
            },
            "colored": {
                "()": "colorlog.ColoredFormatter",
                "format": "%(log_color)s%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                "log_colors": {
                    "DEBUG": "cyan",
                    "INFO": "green",
                    "WARNING": "yellow",
                    "ERROR": "red",
                    "CRITICAL": "bold_red",
                },
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "colored",
                "level": "INFO",
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "standard",
                "filename": LOG_FILE,
                "maxBytes": 5 * 1024 * 1024,  # 5 MB per file
                "backupCount": 5,              # Keep last 5 files
                "level": "DEBUG",
                "encoding": "utf-8",
                "delay":True
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "standard",
                "filename": ERROR_LOG_FILE,
                "maxBytes": 2 * 1024 * 1024,  # 2 MB per file
                "backupCount": 3,
                "level": "ERROR",
                "encoding": "utf-8",
                "delay":True
            },
        },
        "root": {
            "handlers": ["console", "file", "error_file"],
            "level": "DEBUG",
        },
    }

    logging.config.dictConfig(logging_config)
    logger = logging.getLogger(__name__)
    logger.info("✅ Logging configured successfully.")

    if os.getenv("LANGSMITH_TRACING", "").lower() == "true":
        logger.info(f"Langsmith tracing enabled: {langsmith_utils.tracing_is_enabled()}")
    else:
        logger.info(f"Langsmith is disabled.")