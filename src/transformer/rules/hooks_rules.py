"""
Rules for transforming React useState hooks to Angular class properties.
"""

from typing import Any, Dict, List
from ...utils.logger import get_logger

logger = get_logger(__name__)


class HooksRules:
    """Rules for transforming React useState hooks to Angular class properties."""

    def transform(self, react_ast: Any, angular_ast: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform React useState hooks to Angular class properties.

        Args:
            react_ast: React AST
            angular_ast: Angular AST being built

        Returns:
            Updated Angular AST
        """
        logger.debug("Applying hooks transformation rules")

        # Extract useState hooks from AST
        hooks = self._extract_usestate_hooks(react_ast)

        for hook in hooks:
            self._transform_usestate(hook, angular_ast)

        return angular_ast

    def _extract_usestate_hooks(self, react_ast: Any) -> List[Dict[str, Any]]:
        """
        Extract useState hooks from React AST.
        
        Looks for patterns like:
        - const [state, setState] = useState(initialValue)
        """
        hooks = []
        
        # Traverse AST to find useState calls
        if isinstance(react_ast, dict):
            # Check for useState patterns in variable declarations
            if "body" in react_ast:
                hooks.extend(self._find_hooks_in_body(react_ast["body"]))
            elif "components" in react_ast:
                # If AST has component structure, look for hooks in component body
                hooks.extend(self._find_hooks_in_component(react_ast))
            elif "statements" in react_ast:
                hooks.extend(self._find_hooks_in_statements(react_ast["statements"]))
        
        return hooks

    def _find_hooks_in_body(self, body: Any) -> List[Dict[str, Any]]:
        """Find hooks in function/component body."""
        hooks = []
        
        if isinstance(body, list):
            for item in body:
                hooks.extend(self._find_hooks_in_statements([item]))
        elif isinstance(body, dict):
            hooks.extend(self._find_hooks_in_statements([body]))
        
        return hooks

    def _find_hooks_in_component(self, react_ast: Any) -> List[Dict[str, Any]]:
        """Find useState hooks in component structure."""
        hooks = []
        
        # Look for variable declarations with useState
        if "variables" in react_ast:
            for var in react_ast["variables"]:
                if self._is_usestate_call(var):
                    hooks.append(self._parse_usestate(var))
        
        return hooks

    def _find_hooks_in_statements(self, statements: List[Any]) -> List[Dict[str, Any]]:
        """Find useState hooks in a list of statements."""
        hooks = []
        
        for stmt in statements:
            if isinstance(stmt, dict):
                # Check for variable declaration with useState
                if stmt.get("type") == "VariableDeclaration":
                    for decl in stmt.get("declarations", []):
                        if self._is_usestate_call(decl):
                            hooks.append(self._parse_usestate(decl))
                
                # Recursively check nested structures
                elif "body" in stmt:
                    hooks.extend(self._find_hooks_in_body(stmt["body"]))
        
        return hooks

    def _is_usestate_call(self, declaration: Any) -> bool:
        """Check if a declaration is a useState call."""
        if isinstance(declaration, dict):
            init = declaration.get("init", {})
            if isinstance(init, dict):
                callee = init.get("callee", {})
                if isinstance(callee, dict):
                    return callee.get("name") == "useState"
                elif isinstance(callee, str):
                    return callee == "useState"
        return False

    def _parse_usestate(self, declaration: Any) -> Dict[str, Any]:
        """
        Parse useState declaration: const [state, setState] = useState(initialValue)
        
        Returns:
            {
                "type": "useState",
                "stateName": "state",
                "setterName": "setState",
                "initialValue": initialValue,
                "valueType": inferred_type
            }
        """
        # Extract variable names from destructuring
        id_node = declaration.get("id", {})
        state_name = ""
        setter_name = ""
        
        if id_node.get("type") == "ArrayPattern":
            elements = id_node.get("elements", [])
            if len(elements) >= 1:
                state_name = elements[0].get("name", "")
            if len(elements) >= 2:
                setter_name = elements[1].get("name", "")
        
        # Extract initial value
        init = declaration.get("init", {})
        initial_value = self._extract_initial_value(init)
        value_type = self._infer_type(initial_value)
        
        return {
            "type": "useState",
            "stateName": state_name,
            "setterName": setter_name,
            "initialValue": initial_value,
            "valueType": value_type,
        }

    def _extract_initial_value(self, init_node: Any) -> str:
        """Extract initial value from useState call."""
        if isinstance(init_node, dict):
            arguments = init_node.get("arguments", [])
            if arguments:
                return self._node_to_string(arguments[0])
        return ""

    def _infer_type(self, initial_value: str) -> str:
        """Infer TypeScript type from initial value."""
        if not initial_value:
            return "any"
        
        # Simple type inference
        if initial_value.startswith("[") and initial_value.endswith("]"):
            # Array - try to infer element type
            if "string" in initial_value.lower() or initial_value.startswith("['"):
                return "string[]"
            elif "number" in initial_value.lower():
                return "number[]"
            return "any[]"
        elif initial_value.startswith('"') or initial_value.startswith("'"):
            return "string"
        elif initial_value.replace(".", "").isdigit():
            return "number"
        elif initial_value in ["true", "false"]:
            return "boolean"
        elif initial_value == "null" or initial_value == "undefined":
            return "any"
        
        return "any"

    def _node_to_string(self, node: Any) -> str:
        """Convert AST node to string representation."""
        if isinstance(node, dict):
            node_type = node.get("type", "")
            
            if node_type == "ArrayExpression":
                elements = node.get("elements", [])
                items = [self._node_to_string(elem) for elem in elements]
                return f"[{', '.join(items)}]"
            elif node_type == "Literal":
                return repr(node.get("value", ""))
            elif node_type == "Identifier":
                return node.get("name", "")
            elif node_type == "StringLiteral":
                return repr(node.get("value", ""))
            elif node_type == "NumericLiteral":
                return str(node.get("value", ""))
            elif node_type == "BooleanLiteral":
                return str(node.get("value", ""))
            elif node_type == "CallExpression":
                callee = self._node_to_string(node.get("callee", {}))
                args = [self._node_to_string(arg) for arg in node.get("arguments", [])]
                return f"{callee}({', '.join(args)})"
        
        return str(node)

    def _transform_usestate(self, hook: Dict[str, Any], angular_ast: Dict[str, Any]) -> None:
        """Transform useState hook to Angular class property."""
        state_name = hook.get("stateName", "")
        value_type = hook.get("valueType", "any")
        initial_value = hook.get("initialValue", "")
        setter_name = hook.get("setterName", "")
        
        if not state_name:
            return
        
        # Create Angular property
        property_def = {
            "name": state_name,
            "type": value_type,
            "initialValue": initial_value,
            "decorator": "",
        }
        
        angular_ast["class"]["properties"].append(property_def)
        
        # Store setter mapping for two-way binding detection
        if setter_name:
            if "setterMappings" not in angular_ast:
                angular_ast["setterMappings"] = {}
            angular_ast["setterMappings"][setter_name] = state_name
        
        logger.debug(f"Transformed useState: {state_name} -> {value_type} = {initial_value}")
