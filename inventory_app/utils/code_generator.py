"""
Code generator utility for creating unique LAB-XXXX identifiers.
Provides functions for generating unique alphanumeric codes.
"""

import secrets
import string
from typing import Optional

from inventory_app.database.connection import db
from inventory_app.utils.logger import logger


class CodeGenerator:
    """Utility class for generating unique LAB codes."""

    # Character set: uppercase, lowercase, and digits (62 characters total)
    CHARSET = string.ascii_letters + string.digits

    @staticmethod
    def generate_lab_code() -> str:
        """
        Generate a unique LAB-XXXX code.

        Returns:
            str: A unique LAB code in format LAB-XXXX
        """
        max_attempts = 100  # Prevent infinite loops
        attempts = 0

        while attempts < max_attempts:
            # Generate 4 random characters
            code = ''.join(secrets.choice(CodeGenerator.CHARSET) for _ in range(4))
            lab_code = f"LAB-{code}"

            # Check if code is unique
            if CodeGenerator._is_code_unique(lab_code):
                logger.debug(f"Generated unique code: {lab_code}")
                return lab_code

            attempts += 1
            logger.debug(f"Code {lab_code} already exists, trying again ({attempts}/{max_attempts})")

        # Fallback if we can't generate a unique code (very unlikely)
        logger.error("Failed to generate unique code after maximum attempts")
        raise RuntimeError("Unable to generate unique LAB code")

    @staticmethod
    def _is_code_unique(code: str) -> bool:
        """
        Check if a LAB code is unique in the database.

        Args:
            code: The LAB code to check

        Returns:
            bool: True if code is unique, False otherwise
        """
        try:
            query = "SELECT COUNT(*) as count FROM Items WHERE unique_code = ?"
            result = db.execute_query(query, (code,))
            return result[0]['count'] == 0 if result else True
        except Exception as e:
            logger.error(f"Error checking code uniqueness: {e}")
            return False

    @staticmethod
    def validate_lab_code(code: str) -> bool:
        """
        Validate that a code follows the LAB-XXXX format.

        Args:
            code: The code to validate

        Returns:
            bool: True if valid, False otherwise
        """
        if not code or not code.startswith("LAB-"):
            return False

        # Check the 4-character part
        chars = code[4:]  # Everything after "LAB-"
        if len(chars) != 4:
            return False

        # Check all characters are in our charset
        return all(c in CodeGenerator.CHARSET for c in chars)


def generate_unique_lab_code() -> str:
    """
    Convenience function to generate a unique LAB code.

    Returns:
        str: A unique LAB-XXXX code
    """
    return CodeGenerator.generate_lab_code()


def validate_lab_code_format(code: str) -> bool:
    """
    Convenience function to validate LAB code format.

    Args:
        code: The code to validate

    Returns:
        bool: True if valid format, False otherwise
    """
    return CodeGenerator.validate_lab_code(code)
