"""
Clean JSX parser using esprima.
Removes stringified nodes, removes regex hacks, returns pure JSON-safe AST.
"""

import json
from typing import Any, Dict
from .parser_interface import ParserInterface
from ..utils.logger import get_logger

logger = get_logger(__name__)

class JSXParser(ParserInterface):
    def __init__(self):
        try:
            import esprima
            self._parser = esprima
            logger.info("Using esprima for JSX parsing")
        except ImportError:
            logger.error("esprima missing — install: pip install esprima")
            self._parser = None

    def parse(self, source_code: str) -> Dict[str, Any]:
        if not self._parser:
            raise RuntimeError("Esprima not available. Cannot parse JSX.")

        try:
            ast = self._parser.parseModule(
                source_code,
                jsx=True,
                tolerant=True,
                loc=True,
                range=True,
                tokens=True,
                comment=True
            )

            # Convert esprima nodes → pure python dicts
            ast_dict = self._node_to_dict(ast)

            # Add original source
            ast_dict["raw"] = source_code

            return ast_dict

        except Exception as e:
            logger.error(f"JSX parsing failed: {e}")
            raise

    # -------------------------------------------------------------------------
    # Convert esprima Node → python dict
    # -------------------------------------------------------------------------
    def _node_to_dict(self, node):
        if isinstance(node, list):
            return [self._node_to_dict(n) for n in node]

        # primitive values
        if not hasattr(node, '__dict__'):
            return node

        result = {"type": node.type}

        for key, value in node.__dict__.items():

            if key in ("type",):  
                continue

            if isinstance(value, list):
                result[key] = [self._node_to_dict(v) for v in value]

            elif hasattr(value, '__dict__'):
                result[key] = self._node_to_dict(value)

            else:
                result[key] = value

        return result

    # -------------------------------------------------------------------------
    def validate(self, source_code: str) -> bool:
        try:
            ast = self.parse(source_code)
            return isinstance(ast, dict) and ast.get("type") == "Program"
        except Exception:
            return False
