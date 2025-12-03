"""
Rules for transforming React event handlers to Angular event bindings.
"""

from typing import Any, Dict, Optional
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
        setter_mappings = angular_ast.get("setterMappings", {})

        # Extract event handlers from JSX elements
        if "jsx_elements" in react_ast:
            for jsx_element in react_ast["jsx_elements"]:
                attributes = jsx_element.get("attributes", [])
                
                # Check for two-way binding pattern: value={state} + onChange={setState}
                two_way_binding = self._detect_two_way_binding(attributes, setter_mappings)
                
                if two_way_binding:
                    # Add two-way binding instead of separate event
                    angular_ast["template"]["bindings"].append({
                        "type": "twoWay",
                        "property": two_way_binding["property"],
                        "value": two_way_binding["value"],
                    })
                else:
                    # Process individual event handlers
                    for attr in attributes:
                        attr_name = attr.get("name", "")
                        if attr_name.startswith("on") and len(attr_name) > 2:
                            # Skip onChange if it's part of two-way binding
                            if attr_name == "onChange" and two_way_binding:
                                continue
                            
                            handler_value = attr.get("value", "")
                            angular_event = self._transform_event(attr_name)
                            angular_handler = self._transform_handler(handler_value, setter_mappings)
                            
                            angular_ast["template"]["bindings"].append({
                                "type": "event",
                                "name": angular_event,
                                "handler": angular_handler,
                            })

        return angular_ast

    def _detect_two_way_binding(self, attributes: List[Dict[str, Any]], setter_mappings: Dict[str, str]) -> Optional[Dict[str, str]]:
        """
        Detect two-way binding pattern: value={state} + onChange={(e) => setState(e.target.value)}
        Returns binding info if detected, None otherwise.
        """
        value_attr = None
        onChange_attr = None
        
        for attr in attributes:
            if attr.get("name") == "value":
                value_attr = attr
            elif attr.get("name") == "onChange":
                onChange_attr = attr
        
        if not value_attr or not onChange_attr:
            return None
        
        value = value_attr.get("value", "")
        onChange_value = onChange_attr.get("value", "")
        
        # Check if onChange is an inline arrow function that calls a setter
        # Pattern: (e) => setState(e.target.value)
        if isinstance(onChange_value, str):
            # Check if it matches setter pattern
            for setter_name, state_name in setter_mappings.items():
                if setter_name in onChange_value and value == state_name:
                    # Check if it's accessing e.target.value
                    if "target.value" in onChange_value or ".value" in onChange_value:
                        return {
                            "property": value,
                            "value": value,
                        }
        
        # Also check if onChange is a direct setter call
        # Pattern: onChange={setNewTodo} where setNewTodo is the setter
        if onChange_value in setter_mappings:
            state_name = setter_mappings[onChange_value]
            if value == state_name:
                return {
                    "property": value,
                    "value": value,
                }
        
        return None

    def _transform_handler(self, handler_value: Any, setter_mappings: Dict[str, str]) -> str:
        """
        Transform event handler value to Angular handler.
        
        Handles:
        - Simple function reference: onClick={addTodo} → addTodo()
        - Inline arrow function: onChange={(e) => setNewTodo(e.target.value)} → newTodo = $event.target.value
        """
        if isinstance(handler_value, str):
            # Check if it's an inline arrow function
            if "=>" in handler_value:
                return self._transform_arrow_function_handler(handler_value, setter_mappings)
            else:
                # Simple function reference
                return f"{handler_value}()"
        elif isinstance(handler_value, dict):
            # AST node for arrow function
            if handler_value.get("type") == "ArrowFunctionExpression":
                return self._transform_arrow_function_ast(handler_value, setter_mappings)
            elif handler_value.get("type") == "Identifier":
                # Simple function reference
                func_name = handler_value.get("name", "")
                return f"{func_name}()"
        
        return str(handler_value)

    def _transform_arrow_function_handler(self, handler_str: str, setter_mappings: Dict[str, str]) -> str:
        """Transform inline arrow function handler string."""
        import re
        
        # Pattern: (e) => setState(e.target.value)
        # Pattern: (e) => setState(e.target.value)
        pattern = r'\((\w+)\)\s*=>\s*(\w+)\([^)]*\.value\)'
        match = re.search(pattern, handler_str)
        
        if match:
            event_param = match.group(1)
            setter_name = match.group(2)
            
            # Check if setter maps to a state variable
            if setter_name in setter_mappings:
                state_name = setter_mappings[setter_name]
                return f"{state_name} = $event.target.value"
        
        # Pattern: (e) => expression
        pattern2 = r'\((\w+)\)\s*=>\s*(.+)'
        match2 = re.search(pattern2, handler_str)
        
        if match2:
            event_param = match2.group(1)
            expression = match2.group(2).strip()
            
            # Replace event parameter with $event
            expression = expression.replace(event_param, "$event")
            
            # If it's a setter call, simplify
            for setter_name, state_name in setter_mappings.items():
                if setter_name in expression:
                    # Extract the value being set
                    if ".target.value" in expression or ".value" in expression:
                        return f"{state_name} = $event.target.value"
            
            return expression
        
        return handler_str

    def _transform_arrow_function_ast(self, arrow_func: Dict[str, Any], setter_mappings: Dict[str, str]) -> str:
        """Transform arrow function AST node to Angular handler."""
        params = arrow_func.get("params", [])
        body = arrow_func.get("body", {})
        
        event_param = params[0].get("name", "e") if params else "e"
        
        # Check if body is a call expression to a setter
        if body.get("type") == "CallExpression":
            callee = body.get("callee", {})
            if callee.get("type") == "Identifier":
                setter_name = callee.get("name", "")
                if setter_name in setter_mappings:
                    state_name = setter_mappings[setter_name]
                    arguments = body.get("arguments", [])
                    if arguments:
                        arg = arguments[0]
                        if arg.get("type") == "MemberExpression":
                            # e.target.value pattern
                            return f"{state_name} = $event.target.value"
        
        # Default: convert body to string and replace event param
        body_str = self._ast_to_string(body)
        return body_str.replace(event_param, "$event")

    def _ast_to_string(self, node: Dict[str, Any]) -> str:
        """Convert AST node to string representation."""
        node_type = node.get("type", "")
        
        if node_type == "CallExpression":
            callee = self._ast_to_string(node.get("callee", {}))
            args = [self._ast_to_string(arg) for arg in node.get("arguments", [])]
            return f"{callee}({', '.join(args)})"
        elif node_type == "MemberExpression":
            object_name = self._ast_to_string(node.get("object", {}))
            property_name = self._ast_to_string(node.get("property", {}))
            return f"{object_name}.{property_name}"
        elif node_type == "Identifier":
            return node.get("name", "")
        elif node_type == "Literal":
            return repr(node.get("value", ""))
        
        return ""

    def _transform_event(self, react_event: str) -> str:
        """Transform React event name to Angular event name."""
        # Remove 'on' prefix and convert to lowercase
        if react_event.startswith("on"):
            return f"({react_event[2:].lower()})"
        return react_event

