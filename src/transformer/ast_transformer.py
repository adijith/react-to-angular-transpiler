"""
Main AST transformer that converts a React Function Component AST
into an Angular Component AST.

Fixes included:
- ALWAYS pass the extracted FunctionDeclaration node to ALL rules.
- HooksRules receives the function → correct useState/useEffect extraction.
- ComponentRules receives the function → correct name/method parsing.
- JSXRules receives the function → correct template extraction.
- EventRules receives the function → correct (click), (change), ngModel detection.
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
        self.mappings = ReactAngularMappings()
        self.component_rules = ComponentRules()
        self.jsx_rules = JSXRules()
        self.hooks_rules = HooksRules()
        self.event_rules = EventRules()

    # ---------------------------------------------------------
    # Find the component function (FunctionDeclaration)
    # ---------------------------------------------------------
    def _find_component_function(self, node: Any):
        """
        Recursively find the React function component.

        The parser returns a Program:
        {
            type: "Program",
            body: [ ImportDeclaration, FunctionDeclaration, ExportDefault ]
        }

        We must extract the FunctionDeclaration.
        """
        if isinstance(node, dict):
            if node.get("type") == "FunctionDeclaration":
                return node
            for v in node.values():
                found = self._find_component_function(v)
                if found:
                    return found

        elif isinstance(node, list):
            for item in node:
                found = self._find_component_function(item)
                if found:
                    return found

        return None

    # ---------------------------------------------------------
    # MAIN TRANSFORM
    # ---------------------------------------------------------
    def transform(self, react_ast: Any) -> Dict[str, Any]:
        logger.debug("Starting AST transformation")

        # The Angular AST structure we will populate
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

        # --------------------------------------------
        # 1️⃣ Extract the actual Function Component
        # --------------------------------------------
        component_fn = self._find_component_function(react_ast)

        if component_fn is None:
            logger.error("No React Function Component found! Cannot transpile.")
            return angular_ast

        logger.debug(f"Component function found: {component_fn.get('id', {}).get('name')}")

        # --------------------------------------------
        # 2️⃣ Hooks (useState, useEffect)
        # --------------------------------------------
        angular_ast = self.hooks_rules.transform(component_fn, angular_ast)
        print("DEBUG: setterMappings after hooks:", angular_ast.get("setterMappings"))

        # --------------------------------------------
        # 3️⃣ Component metadata (name, methods, props)
        # --------------------------------------------
        angular_ast = self.component_rules.transform(component_fn, angular_ast)

        # --------------------------------------------
        # 4️⃣ JSX → Angular template
        # --------------------------------------------
        angular_ast = self.jsx_rules.transform(component_fn, angular_ast)

        # --------------------------------------------
        # 5️⃣ Event conversion (click, change, ngModel)
        # --------------------------------------------
        angular_ast = self.event_rules.transform(component_fn, angular_ast)

        logger.debug("Completed AST transformation")
        return angular_ast
