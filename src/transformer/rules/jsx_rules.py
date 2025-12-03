"""
Rules for transforming JSX → Angular template AST.
- Ensures only ONE root JSX element is used.
- Generates unique IDs for each element so EventRules & HTMLGenerator can target correctly.
- Converts JSX children, text, expressions, and array.map → *ngFor properly.
"""

from typing import Any, Dict, List, Optional
from uuid import uuid4
from ...utils.logger import get_logger

logger = get_logger(__name__)


class JSXRules:
    """Rules for JSX → Angular AST transformation."""

    def transform(self, react_ast: Any, angular_ast: Dict[str, Any]) -> Dict[str, Any]:
        # Find root JSX element inside return statement
        root_jsx = self._find_root_jsx(react_ast)
        if not root_jsx:
            return angular_ast

        converted = self._convert_jsx_to_angular(root_jsx)
        if converted:
            angular_ast["template"]["elements"].append(converted)

        return angular_ast

    # ------------------------------------------------------------------
    # Find root JSX element (the element returned by the component)
    # ------------------------------------------------------------------
    def _find_root_jsx(self, node: Any) -> Optional[Dict[str, Any]]:
        if isinstance(node, dict):
            if node.get("type") == "ReturnStatement":
                arg = node.get("argument")
                if isinstance(arg, dict) and arg.get("type") == "JSXElement":
                    return arg

            for v in node.values():
                result = self._find_root_jsx(v)
                if result:
                    return result

        elif isinstance(node, list):
            for item in node:
                result = self._find_root_jsx(item)
                if result:
                    return result

        return None

    # ------------------------------------------------------------------
    # Convert JSX element → Angular AST element
    # ------------------------------------------------------------------
    def _convert_jsx_to_angular(self, jsx: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(jsx, dict):
            return None

        opening = jsx.get("openingElement", {})
        children = jsx.get("children", [])

        # tag
        tag = ""
        name_node = opening.get("name")
        if isinstance(name_node, dict):
            tag = name_node.get("name", "")

        # Convert JSX attributes → Angular attrs (string only)
        raw_attrs = opening.get("attributes", [])
        attrs = self._convert_attributes(raw_attrs)

        # Unique element ID so we can attach event bindings correctly
        element_id = str(uuid4())

        # Convert children
        ang_children: List[Any] = []
        for child in children:
            converted = self._convert_child(child)
            if converted not in (None, "", []):
                ang_children.append(converted)

        return {
            "id": element_id,
            "type": "Element",
            "tag": tag or "div",
            "attributes": attrs,
            "rawJSXAttributes": raw_attrs,   # For EventRules to examine
            "children": ang_children,
        }

    # ------------------------------------------------------------------
    # Convert raw JSX attributes → Angular simple attributes
    # Event attributes are ignored here and handled by EventRules later
    # ------------------------------------------------------------------
    def _convert_attributes(self, attributes: List[Any]) -> List[Dict[str, Any]]:
        out = []
        for attr in attributes:
            if not isinstance(attr, dict):
                continue

            name_node = attr.get("name", {})
            value_node = attr.get("value", {})

            if not isinstance(name_node, dict):
                continue

            name = name_node.get("name", "")
            value = self._extract_attribute_value(value_node)

            # React → Angular rename
            if name == "className":
                name = "class"

            # Ignore React "key"
            if name == "key":
                continue

            # Event attributes are handled in EventRules
            if name.startswith("on"):
                continue

            out.append({"name": name, "value": value})

        return out

    # ------------------------------------------------------------------
    # Extract JSX attribute value
    # ------------------------------------------------------------------
    def _extract_attribute_value(self, val: Any) -> str:
        if isinstance(val, dict):
            if val.get("type") == "Literal":
                return str(val.get("value", ""))

            if val.get("type") == "JSXExpressionContainer":
                expr = val.get("expression", {})
                return self._expression_to_string(expr)

        return ""

    # ------------------------------------------------------------------
    # Convert JSX children
    # ------------------------------------------------------------------
    def _convert_child(self, child: Any) -> Any:
        if isinstance(child, str):
            return child.strip()

        if not isinstance(child, dict):
            return None

        ctype = child.get("type")

        # TEXT
        if ctype == "JSXText":
            return child.get("value", "").strip()

        # EXPRESSION: Could be {todo}, or {todos.map(...)}
        if ctype == "JSXExpressionContainer":
            expr = child.get("expression", {})
            if not isinstance(expr, dict):
                return ""

            # array.map() → *ngFor
            if expr.get("type") == "CallExpression":
                if self._is_map_expression(expr):
                    return self._convert_map_expression(expr)

            # fallback → interpolation like {{ todo }}
            return f"{{{{ {self._expression_to_string(expr)} }}}}"

        # NESTED JSX ELEMENT
        if ctype == "JSXElement":
            return self._convert_jsx_to_angular(child)

        return None

    # ------------------------------------------------------------------
    # Detect if expression is array.map(...)
    # ------------------------------------------------------------------
    def _is_map_expression(self, expr: Dict[str, Any]) -> bool:
        if expr.get("type") != "CallExpression":
            return False

        callee = expr.get("callee", {})
        if isinstance(callee, dict) and callee.get("type") == "MemberExpression":
            prop = callee.get("property", {})
            return prop.get("name") == "map"

        return False

    # ------------------------------------------------------------------
    # Convert arr.map((item, i) => <li>...</li>)
    # → Angular element with *ngFor
    # ------------------------------------------------------------------
    def _convert_map_expression(self, expr: Dict[str, Any]):
        callee = expr.get("callee", {})
        array_name = ""

        obj = callee.get("object", {})
        if isinstance(obj, dict):
            array_name = obj.get("name", "")

        fn = expr.get("arguments", [None])[0]
        params = fn.get("params", []) if isinstance(fn, dict) else []

        item = params[0].get("name", "item") if len(params) > 0 else "item"
        index = params[1].get("name", "index") if len(params) > 1 else "index"

        # Body may be JSXElement or block with return
        body = fn.get("body", {})
        jsx_body = None

        if body.get("type") == "JSXElement":
            jsx_body = body
        elif body.get("type") == "BlockStatement":
            # find return
            for stmt in body.get("body", []):
                if stmt.get("type") == "ReturnStatement":
                    ret = stmt.get("argument")
                    if isinstance(ret, dict) and ret.get("type") == "JSXElement":
                        jsx_body = ret
                        break

        if not jsx_body:
            # fallback
            return {
                "id": str(uuid4()),
                "type": "Element",
                "tag": "li",
                "attributes": [],
                "ngFor": {"array": array_name, "item": item, "index": index},
                "children": [f"{{{{ {item} }}}}"],
            }

        converted = self._convert_jsx_to_angular(jsx_body)
        converted["ngFor"] = {"array": array_name, "item": item, "index": index}
        return converted

    # ------------------------------------------------------------------
    # Convert expression AST to string
    # ------------------------------------------------------------------
    def _expression_to_string(self, expr: Any) -> str:
        if not isinstance(expr, dict):
            return ""

        etype = expr.get("type")

        if etype == "Identifier":
            return expr.get("name", "")

        if etype == "Literal":
            return str(expr.get("value", ""))

        if etype == "MemberExpression":
            obj = self._expression_to_string(expr.get("object"))
            prop = self._expression_to_string(expr.get("property"))
            return f"{obj}.{prop}"

        if etype == "CallExpression":
            callee = self._expression_to_string(expr.get("callee"))
            args = [self._expression_to_string(a) for a in expr.get("arguments", [])]
            return f"{callee}({', '.join(args)})"

        return ""
