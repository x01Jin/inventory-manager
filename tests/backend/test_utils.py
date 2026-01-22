import tempfile
from pathlib import Path
from inventory_app.utils.logger import setup_logger


def test_logger_redaction():
    """Verify that the logger correctly redacts sensitive information."""
    with tempfile.TemporaryDirectory() as td:
        log_dir = Path(td)
        logger = setup_logger(logs_dir=log_dir, redact_max_length=50)

        logger.info("Email: test@example.com")
        logger.info("Phone: +1-234-567-8901")
        logger.info("Long: " + "X" * 100)

        # Cleanup
        for h in list(logger.handlers):
            h.flush()
            logger.removeHandler(h)
            h.close()

        content = (log_dir / "logs.txt").read_text(encoding="utf-8")
        assert "<REDACTED_EMAIL>" in content
        assert "<REDACTED_PHONE>" in content
        assert "..." in content
