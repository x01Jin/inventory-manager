import tempfile
from pathlib import Path

from inventory_app.utils.logger import setup_logger


def read_log(path: Path) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def test_email_redaction_and_truncation():
    with tempfile.TemporaryDirectory() as td:
        log_dir = Path(td)
        logger = setup_logger(logs_dir=log_dir, redact_max_length=100)

        long_note = "A" * 200
        logger.info("User submitted note: %s", long_note)
        logger.info("Contact: %s", "user@example.com")

        # Flush and close handlers
        for h in list(logger.handlers):
            h.flush()
            logger.removeHandler(h)
            h.close()

        log_file = log_dir / "logs.txt"
        content = read_log(log_file)

        # Email should be redacted
        assert "<REDACTED_EMAIL>" in content

        # Long note should be truncated (we set max 100)
        assert "..." in content
        # Original long note should not appear verbatim
        assert long_note not in content
        # Ensure small message is still visible
        assert "User submitted note:" in content


def test_phone_and_ssn_redaction():
    with tempfile.TemporaryDirectory() as td:
        log_dir = Path(td)
        logger = setup_logger(logs_dir=log_dir)

        logger.warning("Phone: %s", "+1 (555) 123-4567")
        logger.warning("SSN: %s", "123-45-6789")

        for h in list(logger.handlers):
            h.flush()
            logger.removeHandler(h)
            h.close()

        content = read_log(log_dir / "logs.txt")
        assert "<REDACTED_PHONE>" in content
        assert "<REDACTED_SSN>" in content
