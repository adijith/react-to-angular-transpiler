"""
Rules for transforming React components to Angular components.
"""

from typing import Any, Dict, List
from ...utils.logger import get_logger

logger = get_logger(__name__)


class ComponentRules:
    """Rules for component transformations."""

    def transform(self, react_ast: Any, angular_ast: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform React component structure to Angular.

        Args:
            react_ast: React AST
            angular_ast: Angular AST being built

        Returns:
            Updated Angular AST
        """
        logger.debug("Applying component transformation rules")

        # Extract component name
        if "components" in react_ast and react_ast["components"]:
            component_name = react_ast["components"][0]
            angular_ast["class"]["name"] = component_name

        # Transform props to @Input()
        if "props" in react_ast:
            for prop in react_ast["props"]:
                angular_ast["class"]["properties"].append({
                    "name": prop,
                    "type": "Input",
                    "decorator": "@Input()",
                })

        # Extract methods from component body
        methods = self._extract_methods(react_ast)
        for method in methods:
            angular_ast["class"]["methods"].append(method)

        return angular_ast

    def _extract_methods(self, react_ast: Any) -> List[Dict[str, Any]]:
        """Extract methods from React component."""
        methods = []
        
        # Look for methods in various AST structures
        if isinstance(react_ast, dict):
            # Check for methods in body
            if "body" in react_ast:
                methods.extend(self._find_methods_in_body(react_ast["body"]))
            # Check for methods in statements
            elif "statements" in react_ast:
                methods.extend(self._find_methods_in_statements(react_ast["statements"]))
            # Check for methods array
            elif "methods" in react_ast:
                for method_node in react_ast["methods"]:
                    methods.append(self._parse_method(method_node))
        
        return methods

    def _find_methods_in_body(self, body: Any) -> List[Dict[str, Any]]:
        """Find methods in function/component body."""
        methods = []
        
        if isinstance(body, list):
            for item in body:
                methods.extend(self._find_methods_in_statements([item]))
        elif isinstance(body, dict):
            methods.extend(self._find_methods_in_statements([body]))
        
        return methods

    def _find_methods_in_statements(self, statements: List[Any]) -> List[Dict[str, Any]]:
        """Find methods in a list of statements."""
        methods = []
        
        for stmt in statements:
            if isinstance(stmt, dict):
                # Check for const/let/var function declarations
                if stmt.get("type") == "VariableDeclaration":
                    for decl in stmt.get("declarations", []):
                        init = decl.get("init", {})
                        if isinstance(init, dict):
                            # Arrow function: const addTodo = () => {...}
                            if init.get("type") == "ArrowFunctionExpression":
                                method_name = decl.get("id", {}).get("name", "")
                                if method_name:
                                    methods.append(self._parse_arrow_function(method_name, init))
                            # Function expression: const addTodo = function() {...}
                            elif init.get("type") == "FunctionExpression":
                                method_name = decl.get("id", {}).get("name", "")
                                if method_name:
                                    methods.append(self._parse_function_expression(method_name, init))
                
                # Check for function declarations: function addTodo() {...}
                elif stmt.get("type") == "FunctionDeclaration":
                    method_name = stmt.get("id", {}).get("name", "")
                    if method_name:
                        methods.append(self._parse_function_declaration(method_name, stmt))
                
                # Recursively check nested structures
                elif "body" in stmt:
                    methods.extend(self._find_methods_in_body(stmt["body"]))
        
        return methods

    def _parse_method(self, method_node: Any) -> Dict[str, Any]:
        """Parse a method node into Angular method structure."""
        return {
            "name": method_node.get("name", ""),
            "parameters": method_node.get("parameters", []),
            "body": self._extract_method_body(method_node),
            "returnType": method_node.get("returnType", "void"),
        }

    def _parse_arrow_function(self, name: str, func_node: Any) -> Dict[str, Any]:
        """Parse arrow function: const name = () => {...}"""
        params = self._extract_parameters(func_node.get("params", []))
        body = self._extract_method_body(func_node.get("body", {}))
        
        return {
            "name": name,
            "parameters": params,
            "body": body,
            "returnType": "void",
        }

    def _parse_function_expression(self, name: str, func_node: Any) -> Dict[str, Any]:
        """Parse function expression: const name = function() {...}"""
        params = self._extract_parameters(func_node.get("params", []))
        body = self._extract_method_body(func_node.get("body", {}))
        
        return {
            "name": name,
            "parameters": params,
            "body": body,
            "returnType": "void",
        }

    def _parse_function_declaration(self, name: str, func_node: Any) -> Dict[str, Any]:
        """Parse function declaration: function name() {...}"""
        params = self._extract_parameters(func_node.get("params", []))
        body = self._extract_method_body(func_node.get("body", {}))
        
        return {
            "name": name,
            "parameters": params,
            "body": body,
            "returnType": "void",
        }

    def _extract_parameters(self, params: List[Any]) -> List[str]:
        """Extract parameter names from function parameters."""
        parameter_names = []
        for param in params:
            if isinstance(param, dict):
                param_name = param.get("name", "") or param.get("id", {}).get("name", "")
                if param_name:
                    parameter_names.append(param_name)
            elif isinstance(param, str):
                parameter_names.append(param)
        return parameter_names

    def _extract_method_body(self, body_node: Any) -> str:
        """Extract method body as string."""
        if isinstance(body_node, dict):
            if body_node.get("type") == "BlockStatement":
                statements = body_node.get("body", [])
                return self._statements_to_string(statements)
            else:
                # Single expression (arrow function without braces)
                return self._node_to_string(body_node)
        return ""

    def _statements_to_string(self, statements: List[Any]) -> str:
        """Convert statements to string representation."""
        result = []
        for stmt in statements:
            result.append(self._node_to_string(stmt))
        return "\n    ".join(result)

    def _node_to_string(self, node: Any) -> str:
        """Convert AST node to string representation."""
        if isinstance(node, dict):
            node_type = node.get("type", "")
            
            if node_type == "IfStatement":
                test = self._node_to_string(node.get("test", {}))
                consequent = self._node_to_string(node.get("consequent", {}))
                alternate = node.get("alternate")
                if alternate:
                    alternate_str = self._node_to_string(alternate)
                    return f"if ({test}) {{\n    {consequent}\n}} else {{\n    {alternate_str}\n}}"
                return f"if ({test}) {{\n    {consequent}\n}}"
            elif node_type == "ExpressionStatement":
                return self._node_to_string(node.get("expression", {}))
            elif node_type == "CallExpression":
                callee = self._node_to_string(node.get("callee", {}))
                args = [self._node_to_string(arg) for arg in node.get("arguments", [])]
                return f"{callee}({', '.join(args)})"
            elif node_type == "MemberExpression":
                object_name = self._node_to_string(node.get("object", {}))
                property_name = self._node_to_string(node.get("property", {}))
                return f"{object_name}.{property_name}"
            elif node_type == "Identifier":
                return node.get("name", "")
            elif node_type == "Literal":
                return repr(node.get("value", ""))
            elif node_type == "ArrayExpression":
                elements = node.get("elements", [])
                items = [self._node_to_string(elem) for elem in elements]
                return f"[{', '.join(items)}]"
            elif node_type == "SpreadElement":
                argument = self._node_to_string(node.get("argument", {}))
                return f"...{argument}"
            elif node_type == "BinaryExpression":
                left = self._node_to_string(node.get("left", {}))
                operator = node.get("operator", "")
                right = self._node_to_string(node.get("right", {}))
                return f"{left} {operator} {right}"
            elif node_type == "BlockStatement":
                statements = node.get("body", [])
                return self._statements_to_string(statements)
        
        return str(node)

