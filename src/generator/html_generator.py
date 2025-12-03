"""
HTML template generator for Angular components.
"""

from typing import Any, Dict, List
from ..utils.logger import get_logger

logger = get_logger(__name__)


class HTMLGenerator:
    """Generates HTML templates for Angular components."""

    def generate(self, angular_ast: Dict[str, Any], component_name: str) -> str:
        """
        Generate HTML template from Angular AST.

        Args:
            angular_ast: The Angular AST
            component_name: Name of the component

        Returns:
            Generated HTML code
        """
        logger.debug(f"Generating HTML for {component_name}")

        template = angular_ast.get("template", {})
        elements = template.get("elements", [])
        bindings = template.get("bindings", [])

        if not elements:
            return "<!-- Generated Angular template -->\n<div></div>"

        html_lines = []
        for element in elements:
            html_lines.append(self._generate_element(element, bindings))

        return "\n".join(html_lines)

    def _generate_element(self, element: Dict[str, Any], bindings: List[Dict[str, Any]]) -> str:
        """Generate HTML for a single element."""
        tag = element.get("tag", "div")
        attributes = element.get("attributes", [])
        children = element.get("children", "")
        ng_for = element.get("ngFor")
        two_way_binding = element.get("twoWayBinding")

        # Build attribute string
        attr_parts = []
        
        # Add *ngFor directive if present
        if ng_for:
            ng_for_str = f"*ngFor=\"let {ng_for['item']} of {ng_for['array']}; let {ng_for['index']} = index\""
            attr_parts.append(ng_for_str)
        
        # Add two-way binding [(ngModel)]
        if two_way_binding:
            attr_parts.append(f"[(ngModel)]=\"{two_way_binding}\"")
        
        # Add regular attributes
        for attr in attributes:
            name = attr.get("name", "")
            value = attr.get("value", "")
            
            # Skip value attribute if we have two-way binding
            if name == "value" and two_way_binding:
                continue
            
            if value:
                attr_parts.append(f'{name}="{value}"')
            else:
                attr_parts.append(name)
        
        # Add event bindings from template bindings
        element_bindings = self._get_element_bindings(tag, bindings)
        attr_parts.extend(element_bindings)

        attr_str = " " + " ".join(attr_parts) if attr_parts else ""

        # Generate opening and closing tags
        if children:
            return f"<{tag}{attr_str}>{children}</{tag}>"
        else:
            return f"<{tag}{attr_str}></{tag}>"

    def _get_element_bindings(self, tag: str, bindings: List[Dict[str, Any]]) -> List[str]:
        """Get event bindings for this element."""
        binding_strs = []
        
        for binding in bindings:
            binding_type = binding.get("type", "")
            
            if binding_type == "event":
                event_name = binding.get("name", "")
                handler = binding.get("handler", "")
                binding_strs.append(f'{event_name}="{handler}"')
            elif binding_type == "twoWay":
                # Two-way bindings are handled per-element, not globally
                pass
        
        return binding_strs

