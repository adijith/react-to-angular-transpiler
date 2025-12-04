"""
Optimized rules for transforming React event handlers to Angular event bindings.
Now includes:
- BinaryExpression support (count + 1)
- Safe handler transformation
- Proper assignment extraction
"""

from typing import Any, Dict, List, Optional
from ...utils.logger import get_logger

logger = get_logger(__name__)


class EventRules:
    EVENT_PREFIX_MAP = {
        "onClick": "click",
        "onChange": "change",
        "onSubmit": "submit",
        "onFocus": "focus",
        "onBlur": "blur",
    }

    def transform(self, react_ast: Any, angular_ast: Dict[str, Any]) -> Dict[str, Any]:
        logger.debug("EventRules.transform start")

        setter_mappings = angular_ast.get("setterMappings") or {}

        elements = angular_ast.get("template", {}).get("elements", [])
        all_elements = self._flatten_elements(elements)

        bindings = angular_ast.setdefault("template", {}).setdefault("bindings", [])

        for el in all_elements:
            el_id = el.get("id")
            raw_attrs = el.get("rawJSXAttributes", []) or el.get("attributes", [])

            # Two-way binding check for value + onChange
            tw = self._detect_two_way_binding(raw_attrs, setter_mappings)
            if tw:
                bindings.append({
                    "type": "twoWay",
                    "property": tw["property"],
                    "target": el_id,
                })

                el["attributes"] = [
                    a for a in el.get("attributes", [])
                    if a.get("name") != "value"
                ]

                el["twoWayBinding"] = tw["property"]
                continue

            # Normal event handlers
            for attr in raw_attrs:
                name_node = attr.get("name")
                value_node = attr.get("value")

                attr_name = name_node.get("name") if isinstance(name_node, dict) else name_node

                if not attr_name or not str(attr_name).startswith("on"):
                    continue

                angular_event = self._transform_event(attr_name)
                handler_value = self._normalize_attribute_value(value_node)
                handler = self._transform_handler(handler_value, setter_mappings)

                if not handler:
                    continue

                # Inline assignment like: count = count + 1
                if "=" in handler and "(" not in handler:
                    bindings.append({
                        "type": "event",
                        "name": angular_event,
                        "handler": handler,
                        "target": el_id,
                    })
                    continue

                # Normal handler call
                bindings.append({
                    "type": "event",
                    "name": angular_event,
                    "handler": handler,
                    "target": el_id,
                })

        logger.debug("EventRules.transform end")
        return angular_ast

    # ----------------------------------------------------------------------
    # Helper functions
    # ----------------------------------------------------------------------

    def _flatten_elements(self, elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out = []
        for el in elements:
            out.append(el)
            for child in el.get("children", []):
                if isinstance(child, dict) and child.get("type") in ("Element", "JSXElement"):
                    out.extend(self._flatten_elements([child]))
        return out

    def _normalize_attribute_value(self, raw: Any) -> Any:
        if isinstance(raw, dict) and raw.get("type") == "JSXExpressionContainer":
            return raw.get("expression")
        return raw

    def _transform_event(self, react_event: str) -> str:
        if react_event in self.EVENT_PREFIX_MAP:
            return self.EVENT_PREFIX_MAP[react_event]
        if react_event.startswith("on"):
            return react_event[2:].lower()
        return react_event

    # ----------------------------------------------------------------------
    # Two-way binding detection
    # ----------------------------------------------------------------------

    def _detect_two_way_binding(self, attributes: List[Any], setter_mappings: Dict[str, str]):
        value_attr = None
        change_attr = None

        for attr in attributes:
            name_node = attr.get("name")
            attr_name = name_node.get("name") if isinstance(name_node, dict) else name_node

            if attr_name == "value":
                value_attr = attr
            elif attr_name == "onChange":
                change_attr = attr

        if not value_attr or not change_attr:
            return None

        val_expr = self._normalize_attribute_value(value_attr.get("value"))
        change_expr = self._normalize_attribute_value(change_attr.get("value"))

        if isinstance(val_expr, dict) and val_expr.get("type") == "Identifier":
            state_name = val_expr.get("name")
        else:
            return None

        # Detect arrow function: (e) => setX(e.target.value)
        if isinstance(change_expr, dict) and change_expr.get("type") == "ArrowFunctionExpression":
            body = change_expr.get("body", {})
            if body.get("type") == "CallExpression":
                setter = body.get("callee", {}).get("name")
                if setter in setter_mappings and setter_mappings[setter] == state_name:
                    return {"property": state_name}

        return None

    # ----------------------------------------------------------------------
    # Handler Transform
    # ----------------------------------------------------------------------

    def _transform_handler(self, handler_value: Any, setter_mappings: Dict[str, str]) -> str:
        if handler_value is None:
            return ""

        if isinstance(handler_value, dict):
            t = handler_value.get("type")

            if t == "Identifier":
                return f"{handler_value['name']}()"

            if t == "CallExpression":
                return self._ast_to_string(handler_value)

            if t == "ArrowFunctionExpression":
                return self._transform_arrow_function(handler_value, setter_mappings)

            return self._ast_to_string(handler_value)

        if isinstance(handler_value, str):
            return handler_value + "()" if "(" not in handler_value else handler_value

        return ""

    def _transform_arrow_function(self, arrow_func: Dict[str, Any], setter_mappings: Dict[str, str]):
        params = arrow_func.get("params", [])
        event_var = params[0].get("name", "e") if params else "e"
        body = arrow_func.get("body")

        # (e) => setX(e.target.value)
        if body.get("type") == "CallExpression":
            setter = body.get("callee", {}).get("name")
            state = setter_mappings.get(setter) or self._guess_state(setter)

            arg0 = body.get("arguments", [None])[0]

            # setter: state = e.target.value
            if arg0 and arg0.get("type") == "MemberExpression":
                return f"{state} = $event.target.value"

            # setter: state = expression
            return f"{state} = {self._ast_to_string(arg0)}"

        # fallback: replace event param
        expr = self._ast_to_string(body)
        return expr.replace(event_var, "$event")

    def _guess_state(self, setter_name: str) -> str:
        if setter_name.startswith("set"):
            state = setter_name[3:]
            return state[0].lower() + state[1:]
        return setter_name

    # ----------------------------------------------------------------------
    # AST → string
    # ----------------------------------------------------------------------

    def _ast_to_string(self, node: Any) -> str:
        """Convert AST node → readable JS expression."""
        if not isinstance(node, dict):
            return str(node)

        t = node.get("type")

        if t == "Identifier":
            return node.get("name", "")

        if t == "Literal":
            return repr(node.get("value", ""))

        if t == "MemberExpression":
            obj = self._ast_to_string(node.get("object"))
            prop = self._ast_to_string(node.get("property"))
            return f"{obj}.{prop}"

        if t == "CallExpression":
            callee = self._ast_to_string(node.get("callee"))
            args = ", ".join(self._ast_to_string(a) for a in node.get("arguments", []))
            return f"{callee}({args})"

        # ⭐ FIXED: count + 1 now works
        if t == "BinaryExpression":
            left = self._ast_to_string(node.get("left"))
            right = self._ast_to_string(node.get("right"))
            op = node.get("operator")
            return f"{left} {op} {right}"

        return ""
