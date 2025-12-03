"""
File utility functions.
"""

import os
from typing import Optional
from .logger import get_logger

logger = get_logger(__name__)


def read_file(file_path: str) -> Optional[str]:
    """
    Read content from a file.

    Args:
        file_path: Path to the file

    Returns:
        File content as string, or None if error
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Failed to read file {file_path}: {e}")
        return None


def write_file(file_path: str, content: str) -> bool:
    """
    Write content to a file.

    Args:
        file_path: Path to the file
        content: Content to write

    Returns:
        True if successful, False otherwise
    """
    try:
        ensure_directory(os.path.dirname(file_path))
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.debug(f"Successfully wrote file: {file_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to write file {file_path}: {e}")
        return False


def ensure_directory(directory: str) -> bool:
    """
    Ensure a directory exists, creating it if necessary.

    Args:
        directory: Path to the directory

    Returns:
        True if successful, False otherwise
    """
    try:
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            logger.debug(f"Created directory: {directory}")
        return True
    except Exception as e:
        logger.error(f"Failed to create directory {directory}: {e}")
        return False

