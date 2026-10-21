import logging
import re
import sys
from backend.app.core.config import settings

class SecretRedactingFormatter(logging.Formatter):
    """Logging formatter that redacts known secrets and sensitive patterns."""
    def __init__(self, fmt=None, datefmt=None, style='%'):
        super().__init__(fmt=fmt, datefmt=datefmt, style=style)
        self.sensitive_patterns = []
        if settings.GROQ_API_KEY:
            self.sensitive_patterns.append(re.escape(settings.GROQ_API_KEY))
        if settings.LANGSMITH_API_KEY:
            self.sensitive_patterns.append(re.escape(settings.LANGSMITH_API_KEY))
        # Generic API key pattern
        self.sensitive_patterns.append(r"gsk_[a-zA-Z0-9]{32,}")

    def format(self, record: logging.LogRecord) -> str:
        orig = super().format(record)
        for pat in self.sensitive_patterns:
            orig = re.sub(pat, "[REDACTED_SECRET]", orig)
        return orig

def setup_logger(name: str = "agentic_evaluator") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = SecretRedactingFormatter(
            fmt="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger

logger = setup_logger()
