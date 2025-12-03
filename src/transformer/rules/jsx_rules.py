"""
Rules for transforming JSX to Angular templates.
"""

from typing import Any, Dict, List
from ...utils.logger import get_logger

logger = get_logger(__name__)


class JSXRules:
    """Rules for JSX to Angular template transformations."""

    def transform(self, react_ast: Any, angular_ast: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform JSX elements to Angular template syntax.

        Args:
            react_ast: React AST
            angular_ast: Angular AST being built

        Returns:
            Updated Angular AST
        """
        logger.debug("Applying JSX transformation rules")

        if "jsx_elements" in react_ast:
            for jsx_element in react_ast["jsx_elements"]:
                angular_element = self._transform_jsx_element(jsx_element, angular_ast)
                angular_ast["template"]["elements"].append(angular_element)

        return angular_ast

    def _transform_jsx_element(self, jsx_element: Dict[str, Any], angular_ast: Dict[str, Any]) -> Dict[str, Any]:
        """Transform a single JSX element to Angular template element."""
        tag = jsx_element.get("tag", "")
        attributes = jsx_element.get("attributes", [])
        children = jsx_element.get("children", "")

        angular_attrs = []
        ng_for_directive = None
        two_way_binding = None
        
        for attr in attributes:
            name = attr.get("name", "")
            value = attr.get("value", "")

            # Map React attributes to Angular
            if name == "className":
                name = "class"
            elif name == "key":
                # Skip key attribute (Angular uses trackBy instead)
                continue
            elif name.startswith("on"):
                # Event handlers are handled by EventRules
                continue
            elif name == "value":
                # Check for two-way binding pattern (value + onChange)
                # This will be handled by event_rules, but we mark it here
                two_way_binding = value
                continue

            angular_attrs.append({"name": name, "value": value})

        # Transform children - handle JSX expressions
        transformed_children = self._transform_children(children, angular_ast)
        
        # Check if children contain .map() expression for *ngFor
        if isinstance(children, str) and ".map(" in children:
            ng_for_directive = self._extract_ngfor_from_map(children)

        element = {
            "type": "Element",
            "tag": tag,
            "attributes": angular_attrs,
            "children": transformed_children,
        }
        
        if ng_for_directive:
            element["ngFor"] = ng_for_directive
        
        if two_way_binding:
            element["twoWayBinding"] = two_way_binding

        return element

    def _transform_children(self, children: Any, angular_ast: Dict[str, Any]) -> str:
        """Transform JSX children, handling expressions and interpolation."""
        if not children:
            return ""
        
        if isinstance(children, str):
            # Transform JSX expressions: {variable} → {{variable}}
            transformed = self._transform_jsx_expressions(children)
            return transformed
        elif isinstance(children, dict):
            # Handle complex children structures
            return self._transform_complex_children(children, angular_ast)
        elif isinstance(children, list):
            # Handle list of children
            transformed_items = []
            for child in children:
                if isinstance(child, str):
                    transformed_items.append(self._transform_jsx_expressions(child))
                elif isinstance(child, dict):
                    transformed_items.append(self._transform_complex_children(child, angular_ast))
            return "".join(transformed_items)
        
        return str(children)

    def _transform_jsx_expressions(self, text: str) -> str:
        """
        Transform JSX expressions to Angular interpolation.
        {variable} → {{variable}}
        {todos.map(...)} → detect for *ngFor
        """
        import re
        
        # Pattern to match JSX expressions: {expression}
        pattern = r'\{([^}]+)\}'
        
        def replace_expression(match):
            expr = match.group(1).strip()
            
            # Check if it's a .map() call for *ngFor
            if ".map(" in expr:
                return f"<!-- ngFor: {expr} -->"
            
            # Simple variable interpolation
            return f"{{{{{expr}}}}}"
        
        return re.sub(pattern, replace_expression, text)

    def _extract_ngfor_from_map(self, map_expression: str) -> Dict[str, str]:
        """
        Extract *ngFor directive from .map() expression.
        Example: todos.map((todo, index) => ...) → *ngFor="let todo of todos; let index = index"
        """
        import re
        
        # Pattern: arrayName.map((item, index) => ...)
        pattern = r'(\w+)\.map\s*\(\s*\((\w+)(?:,\s*(\w+))?\)\s*=>'
        match = re.search(pattern, map_expression)
        
        if match:
            array_name = match.group(1)
            item_name = match.group(2)
            index_name = match.group(3) or "index"
            
            return {
                "array": array_name,
                "item": item_name,
                "index": index_name,
            }
        
        return None

    def _transform_complex_children(self, child_node: Dict[str, Any], angular_ast: Dict[str, Any]) -> str:
        """Transform complex child nodes (nested JSX elements)."""
        if child_node.get("type") == "JSXExpressionContainer":
            expression = child_node.get("expression", {})
            return self._transform_expression(expression, angular_ast)
        elif child_node.get("type") == "JSXElement":
            return self._transform_jsx_element(child_node, angular_ast)
        
        return ""
    
    def _transform_expression(self, expression: Dict[str, Any], angular_ast: Dict[str, Any]) -> str:
        """Transform JSX expression to Angular template expression."""
        expr_type = expression.get("type", "")
        
        if expr_type == "CallExpression":
            callee = expression.get("callee", {})
            if callee.get("type") == "MemberExpression":
                # Check for .map() call
                if callee.get("property", {}).get("name") == "map":
                    return self._transform_map_expression(expression, angular_ast)
        
        # Default: convert to interpolation
        expr_str = self._expression_to_string(expression)
        return f"{{{{{expr_str}}}}}"
    
    def _transform_map_expression(self, expression: Dict[str, Any], angular_ast: Dict[str, Any]) -> str:
        """Transform .map() expression to *ngFor directive."""
        callee = expression.get("callee", {})
        object_name = callee.get("object", {}).get("name", "")
        arguments = expression.get("arguments", [])
        
        if arguments:
            arrow_func = arguments[0]
            if arrow_func.get("type") == "ArrowFunctionExpression":
                params = arrow_func.get("params", [])
                item_name = params[0].get("name", "") if params else "item"
                index_name = params[1].get("name", "") if len(params) > 1 else "index"
                
                return f"*ngFor=\"let {item_name} of {object_name}; let {index_name} = index\""
        
        return ""
    
    def _expression_to_string(self, expression: Dict[str, Any]) -> str:
        """Convert expression AST node to string."""
        expr_type = expression.get("type", "")
        
        if expr_type == "Identifier":
            return expression.get("name", "")
        elif expr_type == "Literal":
            return repr(expression.get("value", ""))
        elif expr_type == "MemberExpression":
            object_name = self._expression_to_string(expression.get("object", {}))
            property_name = self._expression_to_string(expression.get("property", {}))
            return f"{object_name}.{property_name}"
        
        return ""

