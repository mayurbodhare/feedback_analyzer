import logging
import sys
from datetime import datetime


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for different log levels"""

    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"
    BOLD = "\033[1m"

    def format(self, record):
        # Add color to level name
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = (
                f"{self.COLORS[levelname]}{self.BOLD}{levelname:<8}{self.RESET}"
            )

        # Color the timestamp
        timestamp = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        colored_timestamp = f"\033[90m{timestamp}\033[0m"  # Gray color

        # Color the logger name
        colored_name = f"\033[94m{record.name:<20}\033[0m"  # Blue color

        # Format the message
        message = record.getMessage()

        # Combine all parts
        log_message = (
            f"{colored_timestamp} | {record.levelname} | {colored_name} | {message}"
        )

        # Add exception info if present
        if record.exc_info:
            log_message += "\n" + self.formatException(record.exc_info)

        return log_message


class SimpleFileFormatter(logging.Formatter):
    """Simple formatter for file output without colors"""

    def format(self, record):
        timestamp = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        levelname = f"{record.levelname:<8}"
        message = record.getMessage()

        log_message = f"\n{timestamp} | {levelname} | {record.name:<20} | {message}"

        if record.exc_info:
            log_message += "\n" + self.formatException(record.exc_info)

        return log_message


# Configure logging
def setup_logging():
    """Setup colored logging for console and plain logging for file"""

    # Create handlers
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(ColoredFormatter())

    file_handler = logging.FileHandler("app.log", encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(SimpleFileFormatter())

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    return root_logger


# Initialize logging
root_logger = setup_logging()
