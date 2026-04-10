"""
SDS storage service.
Stores uploaded SDS files in a local `sds` directory beside the application.
"""

from __future__ import annotations

import mimetypes
import re
import shutil
from pathlib import Path
from typing import Optional, Dict

from inventory_app.utils.logger import logger


class SDSStorageService:
    """Handle filesystem operations for SDS file uploads."""

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or Path("sds")

    def ensure_storage_dir(self) -> Path:
        """Ensure SDS storage directory exists."""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        return self.base_dir

    def _sanitize_filename(self, filename: str) -> str:
        """Remove unsafe characters from a user-provided filename."""
        cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", filename.strip())
        return cleaned[:180] if cleaned else "sds_file"

    def _build_stored_name(self, item_id: int, original_filename: str) -> str:
        """Build deterministic SDS filename by item ID."""
        original_path = Path(original_filename)
        ext = original_path.suffix.lower()
        safe_stem = self._sanitize_filename(original_path.stem)
        if not ext:
            ext = ".pdf"
        return f"item_{item_id}_{safe_stem}{ext}"

    def store_file(
        self, item_id: int, source_file_path: str
    ) -> Optional[Dict[str, str]]:
        """Copy source file into SDS storage and return persisted metadata."""
        try:
            source = Path(source_file_path)
            if not source.exists() or not source.is_file():
                logger.error(f"SDS source file does not exist: {source_file_path}")
                return None

            storage_dir = self.ensure_storage_dir()
            stored_name = self._build_stored_name(item_id, source.name)
            destination = storage_dir / stored_name
            shutil.copy2(source, destination)

            guessed_mime, _ = mimetypes.guess_type(destination.name)
            return {
                "stored_filename": stored_name,
                "original_filename": source.name,
                "file_path": str(destination.resolve()),
                "mime_type": guessed_mime or "application/octet-stream",
            }
        except Exception as e:
            logger.error(f"Failed to store SDS file for item {item_id}: {e}")
            return None

    def remove_file(self, stored_file_path: Optional[str]) -> bool:
        """Delete a stored SDS file if it exists."""
        if not stored_file_path:
            return True

        try:
            target = Path(stored_file_path)
            if target.exists() and target.is_file():
                target.unlink()
            return True
        except Exception as e:
            logger.error(f"Failed to remove SDS file {stored_file_path}: {e}")
            return False


sds_storage_service = SDSStorageService()
