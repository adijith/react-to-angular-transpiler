"""
Main AST transformer that converts React AST to Angular AST.
"""

from typing import Any, Dict
from .mappings import ReactAngularMappings
from .rules.component_rules import ComponentRules
from .rules.jsx_rules import JSXRules
from .rules.hooks_rules import HooksRules
from .rules.event_rules import EventRules
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ASTTransformer:
    """Transforms React AST to Angular AST."""

    def __init__(self):
        """Initialize the transformer with rules."""
        self.mappings = ReactAngularMappings()
        self.component_rules = ComponentRules()
        self.jsx_rules = JSXRules()
        self.hooks_rules = HooksRules()
        self.event_rules = EventRules()

    def transform(self, react_ast: Any) -> Dict[str, Any]:
        """
        Transform React AST to Angular AST.

        Args:
            react_ast: The React AST to transform

        Returns:
            Angular AST representation
        """
        logger.debug("Starting AST transformation")

        angular_ast = {
            "type": "AngularComponent",
            "class": {
                "name": "",
                "properties": [],
                "methods": [],
                "lifecycleHooks": [],
            },
            "template": {
                "elements": [],
                "bindings": [],
            },
            "styles": [],
        }

        # Apply transformation rules
        angular_ast = self.component_rules.transform(react_ast, angular_ast)
        angular_ast = self.jsx_rules.transform(react_ast, angular_ast)
        angular_ast = self.event_rules.transform(react_ast, angular_ast)

        logger.debug("Completed AST transformation")
        return angular_ast

