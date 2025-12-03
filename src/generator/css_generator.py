"""
CSS generator for Angular components.
"""

from typing import Any, Dict
from ..utils.logger import get_logger

logger = get_logger(__name__)


class CSSGenerator:
    """Generates CSS styles for Angular components."""

    def generate(self, angular_ast: Dict[str, Any], component_name: str) -> str:
        """
        Generate CSS from Angular AST.

        Args:
            angular_ast: The Angular AST
            component_name: Name of the component

        Returns:
            Generated CSS code
        """
        logger.debug(f"Generating CSS for {component_name}")

        styles = angular_ast.get("styles", [])

        if not styles:
            return f"/* Styles for {component_name} component */\n"

        css_lines = []
        for style in styles:
            selector = style.get("selector", "")
            rules = style.get("rules", {})
            css_lines.append(self._generate_rule(selector, rules))

        return "\n".join(css_lines)

    def _generate_rule(self, selector: str, rules: Dict[str, str]) -> str:
        """Generate a CSS rule."""
        if not rules:
            return ""

        rule_lines = [f"{selector} {{"]
        for property_name, value in rules.items():
            rule_lines.append(f"  {property_name}: {value};")
        rule_lines.append("}")

        return "\n".join(rule_lines)

