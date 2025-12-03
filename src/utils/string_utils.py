"""
String utility functions.
"""

import re


def to_pascal_case(text: str) -> str:
    """Convert string to PascalCase."""
    # Remove special characters and split
    words = re.findall(r"[a-zA-Z0-9]+", text)
    return "".join(word.capitalize() for word in words)


def to_camel_case(text: str) -> str:
    """Convert string to camelCase."""
    pascal = to_pascal_case(text)
    if not pascal:
        return ""
    return pascal[0].lower() + pascal[1:]


def to_kebab_case(text: str) -> str:
    """Convert string to kebab-case."""
    # Insert hyphens before uppercase letters
    text = re.sub(r"(?<!^)(?=[A-Z])", "-", text)
    return text.lower()


def to_snake_case(text: str) -> str:
    """Convert string to snake_case."""
    # Insert underscores before uppercase letters
    text = re.sub(r"(?<!^)(?=[A-Z])", "_", text)
    return text.lower()

