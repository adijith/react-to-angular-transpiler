"""
Rules for transforming React components to Angular components.

This ComponentRules intentionally does NOT extract useState values --
HooksRules handles useState -> properties + setterMappings.

Improvements in this version:
- Does NOT add a placeholder ngOnInit (HooksRules is authoritative for effects)
- Safely finds the FunctionDeclaration if the program AST or function node is passed
- Extracts component name, props and methods from the actual function node
- Avoids duplicate properties/methods
"""

from typing import Any, Dict, List
from ...utils.logger import get_logger

logger = get_logger(__name__)


class ComponentRules:
    """
    Extracts:
    - Component name
    - Props (function parameters)
    - Methods (arrow functions)
    - Does NOT inject useEffect → ngOnInit (HooksRules handles that)
    """

    def transform(self, react_ast: Dict[str, Any], angular_ast: Dict[str, Any]) -> Dict[str, Any]:
        logger.debug("Applying Component transformation rules")

        # If the caller passed the whole program, find the FunctionDeclaration
        fn_node = self._find_function_node(react_ast) or react_ast

        # a function node usually contains a "body" which is a BlockStatement
        fn_body = fn_node.get("body", {}) if isinstance(fn_node, dict) else {}

        # ----------------------------------------------------------
        # Component Name
        # ----------------------------------------------------------
        component_name = self._extract_component_name(fn_node)
        angular_ast["class"]["name"] = component_name

        # ----------------------------------------------------------
        # Props (function parameters)
        # ----------------------------------------------------------
        props = self._extract_props(fn_node)
        for p in props:
            if not self._property_exists(angular_ast, p):
                angular_ast["class"]["properties"].append({
                    "name": p,
                    "type": "any",
                    "initialValue": "''",
                    "decorator": "@Input()",
                })

        # ----------------------------------------------------------
        # Methods (arrow functions assigned to const)
        # ----------------------------------------------------------
        methods = self._extract_methods(fn_body)
        for m in methods:
            if not self._method_exists(angular_ast, m.get("name")):
                angular_ast["class"]["methods"].append(m)

        # NOTE:
        # Do NOT create lifecycle hooks for useEffect here.
        # HooksRules is responsible for detecting and populating lifecycleHooks
        # so we avoid any placeholder that would overwrite real hook bodies.

        return angular_ast

    # ============================================================
    # Find the component function in a Program or return it if provided
    # ============================================================
    def _find_function_node(self, node: Any):
        """Return the first FunctionDeclaration found in the AST (or None)."""
        if not isinstance(node, (dict, list)):
            return None

        if isinstance(node, dict):
            if node.get("type") == "FunctionDeclaration":
                return node
            # some ASTs place the program body under "body"
            for k, v in node.items():
                found = self._find_function_node(v)
                if found:
                    return found

        if isinstance(node, list):
            for item in node:
                found = self._find_function_node(item)
                if found:
                    return found

        return None

    # ============================================================
    # COMPONENT NAME
    # ============================================================
    def _extract_component_name(self, fn_node):
        # If a function node is given, return its id.name
        if isinstance(fn_node, dict) and fn_node.get("type") == "FunctionDeclaration":
            return fn_node.get("id", {}).get("name", "") or "MyComponent"
        # otherwise attempt to find it inside program/body
        fn = self._find_function_node(fn_node)
        if fn:
            return fn.get("id", {}).get("name", "") or "MyComponent"
        return "MyComponent"

    # ============================================================
    # PROPS
    # ============================================================
    def _extract_props(self, fn_node):
        """Extract function parameter names as props."""
        params = []
        if isinstance(fn_node, dict) and fn_node.get("type") == "FunctionDeclaration":
            for p in fn_node.get("params", []):
                if isinstance(p, dict) and p.get("type") == "Identifier":
                    params.append(p["name"])
        return params

    # ============================================================
    # METHODS
    # ============================================================
    def _extract_methods(self, fn_body):
        """Scan the function body for const <name> = () => { } patterns."""
        result = []

        for node in self._walk(fn_body):
            if node.get("type") == "VariableDeclaration":
                for decl in node.get("declarations", []):
                    init = decl.get("init", {}) or {}
                    # Arrow function assigned to const/let/var
                    if init.get("type") == "ArrowFunctionExpression":
                        method_name = decl.get("id", {}).get("name", "")
                        params = self._extract_param_names(init.get("params", []))
                        body_str = self._block_to_string(init.get("body", {}))
                        result.append({
                            "name": method_name,
                            "parameters": params,
                            "body": body_str,
                            "returnType": "void"
                        })
        return result

    # ============================================================
    # HELPERS
    # ============================================================
    def _property_exists(self, angular_ast, name):
        props = angular_ast["class"]["properties"]
        return any(p.get("name") == name for p in props)

    def _method_exists(self, angular_ast, name):
        if not name:
            return False
        methods = angular_ast["class"]["methods"]
        return any(m.get("name") == name for m in methods)

    def _lifecycle_exists(self, angular_ast, hook_name):
        hooks = angular_ast["class"].get("lifecycleHooks", [])
        return any(h.get("name") == hook_name for h in hooks)

    def _walk(self, node):
        """Recursive generator to traverse AST nodes safely."""
        if isinstance(node, dict):
            yield node
            for v in node.values():
                # avoid recursing into non-dict/list values
                if isinstance(v, (dict, list)):
                    for x in self._walk(v):
                        yield x
        elif isinstance(node, list):
            for item in node:
                for x in self._walk(item):
                    yield x

    def _extract_param_names(self, params):
        names = []
        for p in params:
            if isinstance(p, dict) and p.get("type") == "Identifier":
                names.append(p["name"])
        return names

    # ============================================================
    # METHOD BODY STRINGIFY
    # ============================================================
    def _block_to_string(self, body):
        if not isinstance(body, dict):
            return ""
        if body.get("type") != "BlockStatement":
            return self._node_to_str(body)

        out = []
        for stmt in body.get("body", []):
            out.append(self._node_to_str(stmt))
        return "\n".join(out)

    def _node_to_str(self, node):
        if not isinstance(node, dict):
            return ""

        t = node.get("type")

        if t == "ExpressionStatement":
            return self._node_to_str(node["expression"])

        if t == "IfStatement":
            test = self._node_to_str(node["test"])
            cons = self._block_to_string(node["consequent"])
            return f"if ({test}) {{\n    {cons}\n}}"

        if t == "CallExpression":
            callee = self._node_to_str(node["callee"])
            args = [self._node_to_str(a) for a in node.get("arguments", [])]
            return f"{callee}({', '.join(args)})"

        if t == "MemberExpression":
            return f"{self._node_to_str(node['object'])}.{self._node_to_str(node['property'])}"

        if t == "Identifier":
            return node.get("name", "")

        if t == "Literal":
            return repr(node.get("value", ""))

        if t == "SpreadElement":
            return f"...{self._node_to_str(node['argument'])}"

        if t == "ArrayExpression":
            return "[" + ", ".join(self._node_to_str(e) for e in node["elements"]) + "]"

        return ""
