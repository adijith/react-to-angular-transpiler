"""
Abstract parser interface.
"""

from abc import ABC, abstractmethod
from typing import Any


class ParserInterface(ABC):
    """Abstract interface for parsers."""

    @abstractmethod
    def parse(self, source_code: str) -> Any:
        """
        Parse source code into an AST.

        Args:
            source_code: The source code to parse

        Returns:
            Abstract Syntax Tree representation
        """
        pass

    @abstractmethod
    def validate(self, source_code: str) -> bool:
        """
        Validate that source code is valid.

        Args:
            source_code: The source code to validate

        Returns:
            True if valid, False otherwise
        """
        pass

