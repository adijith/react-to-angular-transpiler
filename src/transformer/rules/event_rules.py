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

        Args:
            react_ast: React AST
            angular_ast: Angular AST being built

        Returns:
            Updated Angular AST
        """
        logger.debug("Applying event transformation rules")

        # Get setter mappings from hooks_rules for two-way binding detection
        setter_mappings = angular_ast.get("setterMappings", {}) or {}

        # Find JSX nodes robustly (support different parser outputs)
        jsx_nodes = []
        if isinstance(react_ast, dict):
            if "jsx_elements" in react_ast and isinstance(react_ast["jsx_elements"], list):
                jsx_nodes = react_ast["jsx_elements"]
            elif "jsx" in react_ast and isinstance(react_ast["jsx"], list):
                jsx_nodes = react_ast["jsx"]
            else:
                # Fallback: collect all JSXElement nodes by traversing AST
                self._collect_jsx_nodes(react_ast, jsx_nodes)

        # Process each JSX node's attributes
        for jsx_element in jsx_nodes:
            attributes = jsx_element.get("attributes", []) or []

            # Detect two-way binding pattern first
            two_way_binding = self._detect_two_way_binding(attributes, setter_mappings)

            if two_way_binding:
                angular_ast.setdefault("template", {}).setdefault("bindings", []).append({
                    "type": "twoWay",
                    "property": two_way_binding["property"],
                    "value": two_way_binding["value"],
                })
                # If two-way found, skip adding separate onChange event for same node
                continue

            # Otherwise, convert individual event attributes
            for attr in attributes:
                attr_name = attr.get("name", "")
                if not isinstance(attr_name, str):
                    continue

                if not attr_name.startswith("on") or len(attr_name) <= 2:
                    continue

                # Transform event name to Angular format: (click), (change), etc.
                angular_event = self._transform_event(attr_name)

                # Extract handler value in a normalized form (string or AST)
                raw_value = attr.get("value", "")
                handler_value = self._normalize_attribute_value(raw_value)

                angular_handler = self._transform_handler(handler_value, setter_mappings)

                angular_ast.setdefault("template", {}).setdefault("bindings", []).append({
                    "type": "event",
                    "name": angular_event,
                    "handler": angular_handler,
                })

        return angular_ast

    # -------------------------
    # Helpers
    # -------------------------

    def _collect_jsx_nodes(self, node: Any, output: List[Dict]):
        """Traverse AST and collect JSXElement nodes."""
        if isinstance(node, dict):
            if node.get("type") == "JSXElement":
                output.append(node)
            for v in node.values():
                if isinstance(v, (dict, list)):
                    self._collect_jsx_nodes(v, output)
        elif isinstance(node, list):
            for item in node:
                self._collect_jsx_nodes(item, output)

    def _normalize_attribute_value(self, raw: Any) -> Any:
        """
        Normalize attribute value to either:
         - a python string (if parser already serialized),
         - an AST node (dict) representing the expression
        """
        # If it's a dict AST (e.g., JSXExpressionContainer), unwrap expression
        if isinstance(raw, dict):
            # Handle JSXExpressionContainer { expression: ... }
            if raw.get("type") == "JSXExpressionContainer" and "expression" in raw:
                return raw["expression"]
            return raw

        # leave strings as-is
        return raw

    def _detect_two_way_binding(self, attributes: List[Dict[str, Any]], setter_mappings: Dict[str, str]) -> Optional[Dict[str, str]]:
        """
        Detect two-way binding pattern: value={state} + onChange={(e) => setState(e.target.value)}
        Returns binding info if detected, None otherwise.
        """
        value_attr = None
        on_change_attr = None

        for attr in attributes:
            name = attr.get("name")
            if name == "value":
                value_attr = attr
            elif name == "onChange":
                on_change_attr = attr

        if not value_attr or not on_change_attr:
            return None

        value_val = self._normalize_attribute_value(value_attr.get("value"))
        on_change_val = self._normalize_attribute_value(on_change_attr.get("value"))

        # value_val expected to be Identifier AST or string name of state variable
        state_name = None
        if isinstance(value_val, dict) and value_val.get("type") == "Identifier":
            state_name = value_val.get("name")
        elif isinstance(value_val, str):
            state_name = value_val

        # Check common patterns for onChange:
        # 1) ArrowFunctionExpression AST calling a setter with e.target.value
        if isinstance(on_change_val, dict):
            if on_change_val.get("type") == "ArrowFunctionExpression":
                # Look inside body: if it's CallExpression and callee is a setter
                body = on_change_val.get("body")
                if isinstance(body, dict) and body.get("type") == "CallExpression":
                    callee = body.get("callee", {})
                    if callee.get("type") == "Identifier":
                        setter_name = callee.get("name")
                        if setter_name in setter_mappings and setter_mappings[setter_name] == state_name:
                            return {"property": state_name, "value": state_name}

            # Directly provided setter identifier: onChange={setNewTodo}
            if on_change_val.get("type") == "Identifier":
                setter_id = on_change_val.get("name")
                if setter_id in setter_mappings and setter_mappings[setter_id] == state_name:
                    return {"property": state_name, "value": state_name}

        # 2) Inline string representation: "(e) => setNewTodo(e.target.value)"
        if isinstance(on_change_val, str):
            # crude textual match: setter name present + ".target.value" or ".value"
            for setter_name, mapped_state in setter_mappings.items():
                if setter_name in on_change_val and mapped_state == state_name:
                    if "target.value" in on_change_val or ".value" in on_change_val:
                        return {"property": state_name, "value": state_name}

            # direct setter string reference: "setNewTodo"
            for setter_name, mapped_state in setter_mappings.items():
                if on_change_val.strip() == setter_name and mapped_state == state_name:
                    return {"property": state_name, "value": state_name}

        return None

    def _transform_handler(self, handler_value: Any, setter_mappings: Dict[str, str]) -> str:
        """
        Transform event handler value to Angular handler.

        Handles:
        - Simple function reference: onClick={addTodo} → addTodo()
        - Inline arrow function AST: onChange={(e) => setNewTodo(e.target.value)} → newTodo = $event.target.value
        - Inline arrow function string: onChange={(e) => setNewTodo(e.target.value)} (string form)
        """
        # AST node
        if isinstance(handler_value, dict):
            node_type = handler_value.get("type", "")
            # Arrow function AST
            if node_type == "ArrowFunctionExpression":
                return self._transform_arrow_function_ast(handler_value, setter_mappings)
            # Identifier AST => function reference
            if node_type == "Identifier":
                return f"{handler_value.get('name', '')}()"
            # CallExpression AST => convert to string
            if node_type == "CallExpression":
                return self._ast_to_string(handler_value)
            # JSXExpressionContainer unlikely here (we normalized), but be safe:
            if node_type == "JSXExpressionContainer" and "expression" in handler_value:
                return self._transform_handler(handler_value["expression"], setter_mappings)

            # default fallback
            return self._ast_to_string(handler_value)

        # Plain string (parser or earlier code produced string)
        if isinstance(handler_value, str):
            # Inline arrow function textual form
            if "=>" in handler_value:
                return self._transform_arrow_function_handler(handler_value, setter_mappings)
            # simple reference like "addTodo" or "addTodo()"
            stripped = handler_value.strip()
            if "(" in stripped and ")" in stripped:
                return stripped  # already looks like a call
            # else treat as a function reference
            return f"{stripped}()"

        # Fallback: stringify
        return str(handler_value)

    def _transform_arrow_function_handler(self, handler_str: str, setter_mappings: Dict[str, str]) -> str:
        """Transform inline arrow function handler string into Angular-friendly expression."""
        import re

        # Pattern: (e) => setState(e.target.value)
        pattern = r'\(\s*(\w+)\s*\)\s*=>\s*(\w+)\s*\(\s*\1(?:\.target)?\.value\s*\)'
        m = re.search(pattern, handler_str)
        if m:
            setter = m.group(2)
            if setter in setter_mappings:
                state_name = setter_mappings[setter]
                return f"{state_name} = $event.target.value"

        # More general: replace event param with $event
        pattern2 = r'\(\s*(\w+)\s*\)\s*=>\s*(.+)'
        m2 = re.search(pattern2, handler_str)
        if m2:
            event_param = m2.group(1)
            expression = m2.group(2).strip()
            expression = expression.replace(event_param, "$event")
            # simplify setter calls inside expression if possible
            for setter_name, state_name in setter_mappings.items():
                if setter_name in expression:
                    if ".target.value" in expression or ".value" in expression:
                        return f"{state_name} = $event.target.value"
            return expression

        return handler_str

    def _transform_arrow_function_ast(self, arrow_func: Dict[str, Any], setter_mappings: Dict[str, str]) -> str:
        """Transform arrow function AST node to Angular handler."""
        params = arrow_func.get("params", [])
        body = arrow_func.get("body", {})

        event_param = params[0].get("name", "e") if params else "e"

        # body is CallExpression to setter?
        if isinstance(body, dict) and body.get("type") == "CallExpression":
            callee = body.get("callee", {})
            if callee.get("type") == "Identifier":
                setter_name = callee.get("name", "")
                if setter_name in setter_mappings:
                    state_name = setter_mappings[setter_name]
                    args = body.get("arguments", [])
                    if args:
                        first_arg = args[0]
                        # if first_arg is MemberExpression (e.target.value)
                        if first_arg.get("type") == "MemberExpression":
                            return f"{state_name} = $event.target.value"
                        # if arg is Identifier (direct), we can map param replacement
                        if first_arg.get("type") == "Identifier":
                            # e.g., (e) => setX(e)
                            return f"{state_name} = $event"
                    # fallback to setter call converted to string
                    return f"{state_name} = {self._ast_to_string(args[0]) if args else ''}"

        # For single-expression bodies, print body and replace event param name with $event
        body_str = self._ast_to_string(body)
        return body_str.replace(event_param, "$event")

    def _ast_to_string(self, node: Dict[str, Any]) -> str:
        """Convert AST node to string representation (simple cases)."""
        if not isinstance(node, dict):
            return str(node)

        node_type = node.get("type", "")

        if node_type == "CallExpression":
            callee = self._ast_to_string(node.get("callee", {}))
            args = [self._ast_to_string(a) for a in node.get("arguments", [])]
            return f"{callee}({', '.join(args)})"
        if node_type == "MemberExpression":
            obj = self._ast_to_string(node.get("object", {}))
            prop = self._ast_to_string(node.get("property", {}))
            return f"{obj}.{prop}"
        if node_type == "Identifier":
            return node.get("name", "")
        if node_type == "Literal":
            return repr(node.get("value", ""))
        if node_type == "ArrowFunctionExpression":
            params = ", ".join([p.get("name", "") for p in node.get("params", [])])
            body = node.get("body", {})
            return f"({params}) => {self._ast_to_string(body)}"
        if node_type == "JSXExpressionContainer" and "expression" in node:
            return self._ast_to_string(node["expression"])

        # unknown nodes: fallback to str()
        return str(node)

    def _transform_event(self, react_event: str) -> str:
        """Transform React event name to Angular event name with parentheses."""
        # Prefer explicit map if available
        if react_event in self.EVENT_PREFIX_MAP:
            return f"({self.EVENT_PREFIX_MAP[react_event]})"

        # Fallback: strip 'on' and lowercase
        if react_event.startswith("on"):
            return f"({react_event[2:].lower()})"
        return react_event
