"""
Rules for transforming JSX to Angular templates.

- Converts the *root* JSX element (the one returned by the component) into
  a single Angular AST element to avoid duplicates.
- Properly converts array.map(...) whose arrow returns JSXElement into an
  Element node with an `ngFor` dict attached.
- Minimal prints for tracing.
"""

from typing import Any, Dict, List, Optional
from ...utils.logger import get_logger

logger = get_logger(__name__)


class JSXRules:
    """Rules for JSX to Angular template transformations."""

    def transform(self, react_ast: Any, angular_ast: Dict[str, Any]) -> Dict[str, Any]:
        print("[JSXRules] transform()")
        # find the *root* JSX element (first JSXElement inside the return)
        root_jsx = self._find_root_jsx(react_ast)
        if not root_jsx:
            print("[JSXRules] No root JSX found.")
            return angular_ast

        converted = self._convert_jsx_to_angular(root_jsx)
        if converted:
            angular_ast["template"]["elements"].append(converted)
        return angular_ast

    # ---------- helpers to find the root JSX element ----------
    def _find_root_jsx(self, node: Any) -> Optional[Dict[str, Any]]:
        """
        Walk the AST and return the first JSXElement found inside a ReturnStatement
        (or the first JSXElement if a return-specific one isn't found).
        """
        print("[JSXRules] _find_root_jsx()")
        candidate = None

        if isinstance(node, dict):
            # Prefer JSX inside ReturnStatement.argument
            if node.get("type") == "ReturnStatement":
                arg = node.get("argument")
                if isinstance(arg, dict) and arg.get("type") == "JSXElement":
                    print("[JSXRules] Found JSX inside ReturnStatement.")
                    return arg

            # search children
            for v in node.values():
                found = self._find_root_jsx(v)
                if found:
                    return found

        elif isinstance(node, list):
            for item in node:
                found = self._find_root_jsx(item)
                if found:
                    return found

        return candidate

    # ---------- conversion (recursive) ----------
    def _convert_jsx_to_angular(self, jsx_element: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        print("[JSXRules] _convert_jsx_to_angular()")
        if not isinstance(jsx_element, dict):
            return None

        opening = jsx_element.get("openingElement", {})
        children = jsx_element.get("children", [])

        # tag
        tag = ""
        if isinstance(opening, dict):
            name = opening.get("name", {})
            if isinstance(name, dict):
                tag = name.get("name", "")

        # attributes
        attrs_raw = opening.get("attributes", [])
        attrs = self._convert_attributes(attrs_raw)

        # convert children (list)
        converted_children: List[Any] = []
        if isinstance(children, list):
            for child in children:
                converted = self._convert_child(child)
                # skip empty/None results
                if converted not in (None, "", []):
                    # If converted is an element and contains ngFor as directive-object,
                    # keep it as an element; if it's a simple string keep string.
                    converted_children.append(converted)

        element: Dict[str, Any] = {
            "type": "Element",
            "tag": tag or "div",
            "attributes": attrs,
            "children": converted_children
        }

        return element

    # ---------- attributes ----------
    def _convert_attributes(self, attributes: List[Any]) -> List[Dict[str, Any]]:
        print("[JSXRules] _convert_attributes()")
        out: List[Dict[str, str]] = []
        if not isinstance(attributes, list):
            return out

        for attr in attributes:
            if not isinstance(attr, dict):
                continue

            name_node = attr.get("name", {})
            value_node = attr.get("value", {})

            if not isinstance(name_node, dict):
                continue

            name = name_node.get("name", "")
            value = self._extract_attribute_value(value_node)

            # mappings
            if name == "className":
                name = "class"
            if name == "key":
                continue
            if name.startswith("on"):
                # event attributes handled by EventRules later
                continue

            out.append({"name": name, "value": value})

        return out

    def _extract_attribute_value(self, val: Any) -> str:
        # basic extraction (literal or expression)
        if isinstance(val, dict):
            vtype = val.get("type")
            if vtype == "Literal":
                return str(val.get("value", ""))
            if vtype == "JSXExpressionContainer":
                expr = val.get("expression", {})
                return self._expression_to_string(expr)
        return ""

    # ---------- children conversion ----------
    def _convert_child(self, child: Any) -> Any:
        print("[JSXRules] _convert_child()")
        # text nodes can be dict (JSXText) or raw strings
        if isinstance(child, str):
            return child.strip()

        if not isinstance(child, dict):
            return None

        ctype = child.get("type")

        # text
        if ctype == "JSXText":
            return child.get("value", "").strip()

        # expression container -> could be identifier interpolation or a .map() call
        if ctype == "JSXExpressionContainer":
            expr = child.get("expression", {})
            if not isinstance(expr, dict):
                return ""

            # detect .map() call -> produce an element with ngFor
            if expr.get("type") == "CallExpression":
                callee = expr.get("callee", {})
                # callee could be MemberExpression with property 'map'
                if isinstance(callee, dict) and callee.get("type") == "MemberExpression":
                    prop = callee.get("property", {})
                    if isinstance(prop, dict) and prop.get("name") == "map":
                        # transform map expression into ngFor-bearing element(s)
                        ngfor_element = self._convert_map_expression_to_element(expr)
                        return ngfor_element

            # default: produce interpolation string
            expr_str = self._expression_to_string(expr)
            return f"{{{{ {expr_str} }}}}"

        # nested JSX element
        if ctype == "JSXElement":
            return self._convert_jsx_to_angular(child)

        return None

    # ---------- expression to string ----------
    def _expression_to_string(self, expr: Any) -> str:
        if not isinstance(expr, dict):
            return ""

        etype = expr.get("type", "")

        if etype == "Identifier":
            return expr.get("name", "")

        if etype == "Literal":
            val = expr.get("value", "")
            return str(val)

        if etype == "MemberExpression":
            # object.property or nested
            obj = self._expression_to_string(expr.get("object"))
            prop = self._expression_to_string(expr.get("property"))
            if obj and prop:
                return f"{obj}.{prop}"
            return obj or prop

        if etype == "CallExpression":
            # produce callee(...) or detect simple callee
            callee_node = expr.get("callee")
            callee_str = self._expression_to_string(callee_node) if callee_node else ""
            args = expr.get("arguments", [])
            if args:
                arg_strs = [self._expression_to_string(a) for a in args]
                return f"{callee_str}({', '.join(arg_strs)})"
            return callee_str

        if etype == "ArrowFunctionExpression":
            # e.g. (x) => x or (x, i) => <JSXElement>
            params = expr.get("params", [])
            pnames = [p.get("name", "") for p in params if isinstance(p, dict)]
            return f"({', '.join(pnames)}) => ..."

        return ""

    # ---------- convert map expression into an element with ngFor ----------
    def _convert_map_expression_to_element(self, expr: Dict[str, Any]) -> Any:
        """
        Convert: todos.map((todo, index) => <li key={index}>{todo}</li>)
        into an Element node with ngFor set on the li element.

        Result example:
        {
            "type": "Element",
            "tag": "li",
            "attributes": [...],
            "ngFor": {"array":"todos","item":"todo","index":"index"},
            "children": ["{{ todo }}"]
        }
        """
        print("[JSXRules] _convert_map_expression_to_element()")
        if not isinstance(expr, dict):
            return None

        callee = expr.get("callee", {})
        array_name = ""
        if isinstance(callee, dict):
            obj = callee.get("object", {})
            if isinstance(obj, dict):
                array_name = obj.get("name", "")

        args = expr.get("arguments", [])
        if not args:
            return None

        fn = args[0]
        if not isinstance(fn, dict):
            return None

        # params / arrow function body
        params = fn.get("params", [])
        item_name = params[0].get("name", "item") if len(params) > 0 and isinstance(params[0], dict) else "item"
        index_name = params[1].get("name", "index") if len(params) > 1 and isinstance(params[1], dict) else "index"

        # arrow body may be a JSXElement or BlockStatement returning a JSXElement
        body = fn.get("body")
        jsx_body = None
        if isinstance(body, dict) and body.get("type") == "JSXElement":
            jsx_body = body
        elif isinstance(body, dict) and body.get("type") == "BlockStatement":
            # try find a ReturnStatement inside
            for stmt in body.get("body", []):
                if isinstance(stmt, dict) and stmt.get("type") == "ReturnStatement":
                    candidate = stmt.get("argument")
                    if isinstance(candidate, dict) and candidate.get("type") == "JSXElement":
                        jsx_body = candidate
                        break

        if not jsx_body:
            # fallback: produce generic li with interpolation of item
            return {
                "type": "Element",
                "tag": "li",
                "attributes": [],
                "ngFor": {"array": array_name, "item": item_name, "index": index_name},
                "children": [f"{{{{ {item_name} }}}}"]
            }

        # convert the jsx_body into element node
        converted_inner = self._convert_jsx_to_angular(jsx_body)
        # attach ngFor on the converted element
        # if the converted element is not li, we still attach ngFor on it (same semantics)
        converted_inner["ngFor"] = {"array": array_name, "item": item_name, "index": index_name}

        return converted_inner
