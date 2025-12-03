"""
Rules for transforming React event handlers to Angular event bindings.
"""

from typing import Any, Dict, List, Optional
from ...utils.logger import get_logger

logger = get_logger(__name__)


class EventRules:
    """Rules for event handler transformations."""

    EVENT_PREFIX_MAP = {
        "onClick": "click",
        "onChange": "change",
        "onSubmit": "submit",
        "onFocus": "focus",
        "onBlur": "blur",
    }

    def transform(self, react_ast: Any, angular_ast: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform React event handlers to Angular event bindings.
        """
        logger.debug("Applying event transformation rules")

        # Extract setter mappings created by HooksRules
        setter_mappings = angular_ast.get("setterMappings", {}) or {}

        # Flatten Angular AST elements so we can attach events correctly
        all_elements = self._flatten_elements(
            angular_ast.get("template", {}).get("elements", [])
        )

        # Process each element's raw JSX attributes (provided by JSXRules)
        for el in all_elements:
            raw_jsx_attrs = el.get("rawJSXAttributes", [])
            el_id = el.get("id")

            for attr in raw_jsx_attrs:
                name_node = attr.get("name", {})
                value_node = attr.get("value", {})

                attr_name = name_node.get("name", "")
                if not attr_name.startswith("on"):
                    continue

                # Convert event name
                angular_event = self._transform_event(attr_name)

                # Normalize handler expression to clean AST or string
                handler_val = self._normalize_attribute_value(value_node)

                # Convert function to Angular format: addTodo() or newTodo = $event.target.value
                handler = self._transform_handler(handler_val, setter_mappings)

                # Add event binding attached to the specific element
                angular_ast.setdefault("template", {}).setdefault("bindings", []).append({
                    "type": "event",
                    "name": angular_event,
                    "handler": handler,
                    "target": el_id,
                })

        return angular_ast

    # -----------------------------------------
    # SUPPORT FUNCTIONS
    # -----------------------------------------

    def _flatten_elements(self, elements):
        """Return all element nodes (recursive flatten)."""
        out = []
        for el in elements:
            out.append(el)
            for child in el.get("children", []):
                if isinstance(child, dict) and child.get("type") == "Element":
                    out.extend(self._flatten_elements([child]))
        return out

    def _collect_jsx_nodes(self, node, output):
        """Legacy fallback (still used indirectly)."""
        if isinstance(node, dict):
            if node.get("type") == "JSXElement":
                output.append(node)
            for v in node.values():
                self._collect_jsx_nodes(v, output)
        elif isinstance(node, list):
            for x in node:
                self._collect_jsx_nodes(x, output)

    def _normalize_attribute_value(self, raw: Any) -> Any:
        """Unwrap JSXExpressionContainer, return expression AST."""
        if isinstance(raw, dict) and raw.get("type") == "JSXExpressionContainer":
            return raw.get("expression")
        return raw

    # -----------------------------------------
    # TWO-WAY BINDING DETECTION
    # -----------------------------------------

    def _detect_two_way_binding(self, attributes, setter_mappings):
        value_attr = None
        on_change_attr = None

        for attr in attributes:
            if attr.get("name") == "value":
                value_attr = attr
            if attr.get("name") == "onChange":
                on_change_attr = attr

        if not value_attr or not on_change_attr:
            return None

        val = self._normalize_attribute_value(value_attr.get("value"))
        change = self._normalize_attribute_value(on_change_attr.get("value"))

        # Extract state variable name from value
        state_name = None
        if isinstance(val, dict) and val.get("type") == "Identifier":
            state_name = val["name"]
        elif isinstance(val, str):
            state_name = val

        if not state_name:
            return None

        # Check if setState is used
        if isinstance(change, dict):
            if change.get("type") == "ArrowFunctionExpression":
                body = change.get("body", {})
                if body and body.get("type") == "CallExpression":
                    callee = body.get("callee", {})
                    if callee.get("type") == "Identifier":
                        setter = callee.get("name")
                        if setter in setter_mappings and setter_mappings[setter] == state_name:
                            return {"property": state_name, "value": state_name}

        return None

    # -----------------------------------------
    # HANDLER TRANSFORMATION
    # -----------------------------------------

    def _transform_handler(self, handler_value, setter_mappings):
        """Convert handler AST or string into Angular event handler."""

        # Identifier → addTodo()
        if isinstance(handler_value, dict):
            if handler_value.get("type") == "Identifier":
                return handler_value["name"] + "()"

            # Arrow function → newTodo = $event.target.value
            if handler_value.get("type") == "ArrowFunctionExpression":
                return self._transform_arrow_function_ast(handler_value, setter_mappings)

            # CallExpression → foo(bar)
            if handler_value.get("type") == "CallExpression":
                return self._ast_to_string(handler_value)

            return self._ast_to_string(handler_value)

        # String reference → addTodo()
        if isinstance(handler_value, str):
            if "(" in handler_value:
                return handler_value
            return handler_value + "()"

        return ""

    def _transform_arrow_function_ast(self, arrow_func, setter_mappings):
        """Convert arrow function AST → Angular handler expression."""
        params = arrow_func.get("params", [])
        event_var = params[0].get("name", "e") if params else "e"
        body = arrow_func.get("body", {})

        # setX(e.target.value)
        if body.get("type") == "CallExpression":
            callee = body.get("callee", {})
            if callee.get("type") == "Identifier":
                setter_name = callee.get("name")
                if setter_name in setter_mappings:
                    state_var = setter_mappings[setter_name]
                    arg = body.get("arguments", [None])[0]

                    if isinstance(arg, dict) and arg.get("type") == "MemberExpression":
                        return f"{state_var} = $event.target.value"

        # Fallback: stringify arrow
        txt = self._ast_to_string(body)
        return txt.replace(event_var, "$event")

    # -----------------------------------------
    # AST → STRING
    # -----------------------------------------

    def _ast_to_string(self, node):
        if not isinstance(node, dict):
            return str(node)

        t = node.get("type")

        if t == "Identifier":
            return node.get("name", "")

        if t == "Literal":
            return str(node.get("value", ""))

        if t == "MemberExpression":
            return (
                self._ast_to_string(node.get("object"))
                + "."
                + self._ast_to_string(node.get("property"))
            )

        if t == "CallExpression":
            callee = self._ast_to_string(node.get("callee"))
            args = [self._ast_to_string(a) for a in node.get("arguments", [])]
            return f"{callee}({', '.join(args)})"

        return str(node)

    # -----------------------------------------
    # EVENT NAME TRANSFORMATION
    # -----------------------------------------

    def _transform_event(self, react_event: str) -> str:
        if react_event in self.EVENT_PREFIX_MAP:
            return self.EVENT_PREFIX_MAP[react_event]
        if react_event.startswith("on"):
            return react_event[2:].lower()
        return react_event
