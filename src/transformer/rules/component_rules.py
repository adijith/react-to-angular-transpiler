"""
Rules for transforming React components to Angular components.
"""

from typing import Any, Dict, List
from ...utils.logger import get_logger

logger = get_logger(__name__)


class ComponentRules:
    """
    Extracts:
    - Component name
    - Props (function parameters)
    - State (useState)
    - Methods (arrow functions)
    - Lifecycle hooks (useEffect)
    """

    # ============================================================
    # MAIN TRANSFORM ENTRYPOINT
    # ============================================================
    def transform(self, react_ast: Dict[str, Any], angular_ast: Dict[str, Any]) -> Dict[str, Any]:
        logger.debug("Applying Component transformation rules")

        body = react_ast.get("body", [])

        # ----------------------------------------------------------
        # Component Name
        # ----------------------------------------------------------
        component_name = self._extract_component_name(body)
        angular_ast["class"]["name"] = component_name

        # ----------------------------------------------------------
        # Props
        # ----------------------------------------------------------
        props = self._extract_props(body)
        for p in props:
            if not self._property_exists(angular_ast, p):
                angular_ast["class"]["properties"].append({
                    "name": p,
                    "type": "any",
                    "initialValue": "''",
                    "decorator": "@Input()",
                })

        # ----------------------------------------------------------
        # State (useState)
        # ----------------------------------------------------------
        states = self._extract_state(body)
        for state in states:
            name = state["name"]
            if not self._property_exists(angular_ast, name):
                angular_ast["class"]["properties"].append({
                    "name": name,
                    "type": "string" if isinstance(state["initialValue"], str) else "any",
                    "initialValue": state["initialValue"],
                    "decorator": "",
                })

        # ----------------------------------------------------------
        # Methods
        # ----------------------------------------------------------
        methods = self._extract_methods(body)
        for m in methods:
            angular_ast["class"]["methods"].append(m)

        # ----------------------------------------------------------
        # useEffect → ngOnInit
        # ----------------------------------------------------------
        if self._has_use_effect(body):
            angular_ast["class"]["lifecycleHooks"].append({
                "name": "ngOnInit",
                "body": "// TODO: move useEffect logic here",
            })

        return angular_ast

    # ============================================================
    # COMPONENT NAME
    # ============================================================
    def _extract_component_name(self, body):
        for node in body:
            if node.get("type") == "FunctionDeclaration":
                return node.get("id", {}).get("name", "")
        return "MyComponent"

    # ============================================================
    # PROPS
    # ============================================================
    def _extract_props(self, body):
        """function TodoList(props) → props extraction"""
        for node in body:
            if node.get("type") == "FunctionDeclaration":
                names = []
                for p in node.get("params", []):
                    if p.get("type") == "Identifier":
                        names.append(p["name"])
                return names
        return []

    # ============================================================
    # STATE (useState)
    # ============================================================
    def _extract_state(self, body):
        """const [state, setState] = useState(init)"""
        states = []

        for node in self._walk(body):
            if node.get("type") == "VariableDeclaration":
                for decl in node.get("declarations", []):
                    init = decl.get("init", {})

                    if (
                        init.get("type") == "CallExpression"
                        and init.get("callee", {}).get("name") == "useState"
                    ):
                        array_pattern = decl.get("id", {})
                        if array_pattern.get("type") != "ArrayPattern":
                            continue

                        state_name = array_pattern["elements"][0]["name"]
                        init_arg = init.get("arguments", [])

                        initial = self._literal_to_string(init_arg[0]) if init_arg else "''"

                        states.append({
                            "name": state_name,
                            "initialValue": initial
                        })

        return states

    # ============================================================
    # METHODS
    # ============================================================
    def _extract_methods(self, body):
        """const addTodo = () => {...}"""
        result = []

        for node in self._walk(body):
            if node.get("type") == "VariableDeclaration":
                for decl in node.get("declarations", []):
                    init = decl.get("init", {})

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
    # USE EFFECT
    # ============================================================
    def _has_use_effect(self, body):
        for node in self._walk(body):
            if node.get("type") == "ExpressionStatement":
                call = node.get("expression", {})
                if (
                    call.get("type") == "CallExpression"
                    and call.get("callee", {}).get("name") == "useEffect"
                ):
                    return True
        return False

    # ============================================================
    # HELPERS
    # ============================================================
    def _property_exists(self, angular_ast, name):
        props = angular_ast["class"]["properties"]
        return any(p["name"] == name for p in props)

    def _walk(self, node):
        """Recursive generator to traverse AST"""
        if isinstance(node, dict):
            yield node
            for v in node.values():
                yield from self._walk(v)

        elif isinstance(node, list):
            for item in node:
                yield from self._walk(item)

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
        if body.get("type") != "BlockStatement":
            return self._node_to_str(body)

        out = []
        for stmt in body.get("body", []):
            out.append(self._node_to_str(stmt))
        return "\n".join(out)

    def _node_to_str(self, node):
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
            return node["name"]

        if t == "Literal":
            return repr(node["value"])

        if t == "SpreadElement":
            return f"...{self._node_to_str(node['argument'])}"

        if t == "ArrayExpression":
            return "[" + ", ".join(self._node_to_str(e) for e in node["elements"]) + "]"

        return ""

    # ============================================================
    # INITIAL VALUE STRINGIFY
    # ============================================================
    def _literal_to_string(self, node):
        t = node.get("type")

        if t == "Literal":
            return repr(node["value"])

        if t == "ArrayExpression":
            return "[" + ", ".join(
                self._literal_to_string(e) for e in node["elements"]
            ) + "]"

        return "''"
