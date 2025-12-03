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
            return "<!-- Generated Angular template -->\n<div class=\"container\">\n  <!-- Add your template content here -->\n</div>"

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
        ng_if = element.get("ngIf")
        two_way_binding = element.get("twoWayBinding")
        property_binding = element.get("propertyBinding")
        indent = element.get("indent", 0)

        # Build attribute string
        attr_parts = []
        
        # Add structural directives first (*ngFor, *ngIf)
        if ng_for:
            item = ng_for.get('item', 'item')
            array = ng_for.get('array', 'items')
            index = ng_for.get('index', 'i')
            ng_for_str = f'*ngFor="let {item} of {array}; let {index} = index"'
            attr_parts.append(ng_for_str)
        
        if ng_if:
            attr_parts.append(f'*ngIf="{ng_if}"')
        
        # Add two-way binding [(ngModel)]
        if two_way_binding:
            attr_parts.append(f'[(ngModel)]="{two_way_binding}"')
        
        # Add property binding [property]
        if property_binding:
            for prop_name, prop_value in property_binding.items():
                attr_parts.append(f'[{prop_name}]="{prop_value}"')
        
        # Add regular attributes
        for attr in attributes:
            name = attr.get("name", "")
            value = attr.get("value", "")
            binding_type = attr.get("bindingType")
            
            # Skip value attribute if we have two-way binding
            if name == "value" and two_way_binding:
                continue
            
            # Handle different binding types
            if binding_type == "property":
                attr_parts.append(f'[{name}]="{value}"')
            elif binding_type == "event":
                attr_parts.append(f'({name})="{value}"')
            elif binding_type == "twoWay":
                attr_parts.append(f'[({name})]="{value}"')
            else:
                # Regular attribute
                if value:
                    attr_parts.append(f'{name}="{value}"')
                else:
                    attr_parts.append(name)
        
        # Add event bindings from template bindings
        element_bindings = self._get_element_bindings(tag, element, bindings)
        attr_parts.extend(element_bindings)

        attr_str = " " + " ".join(attr_parts) if attr_parts else ""
        
        # Apply indentation
        indent_str = "  " * indent

        # Generate opening and closing tags
        if children:
            # Check if children is a list (nested elements)
            if isinstance(children, list):
                child_html = "\n".join(
                    self._generate_element(child, bindings) 
                    for child in children
                )
                return f"{indent_str}<{tag}{attr_str}>\n{child_html}\n{indent_str}</{tag}>"
            else:
                # String content (interpolation or text)
                return f"{indent_str}<{tag}{attr_str}>{children}</{tag}>"
        else:
            # Self-closing tags for certain elements
            if tag in ["input", "img", "br", "hr", "meta", "link"]:
                return f"{indent_str}<{tag}{attr_str}>"
            else:
                return f"{indent_str}<{tag}{attr_str}></{tag}>"

    def _get_element_bindings(self, tag: str, element: Dict[str, Any], bindings: List[Dict[str, Any]]) -> List[str]:
        """Get event bindings for this element."""
        binding_strs = []
        
        # Check if element has an ID or class to match bindings
        element_id = None
        for attr in element.get("attributes", []):
            if attr.get("name") == "id":
                element_id = attr.get("value")
                break
        
        for binding in bindings:
            binding_type = binding.get("type", "")
            target = binding.get("target")
            
            # If binding has a target, only apply to matching element
            if target and target != element_id:
                continue
            
            if binding_type == "event":
                event_name = binding.get("name", "")
                handler = binding.get("handler", "")
                # Angular event binding syntax: (event)="handler()"
                binding_strs.append(f'({event_name})="{handler}"')
            elif binding_type == "property":
                prop_name = binding.get("name", "")
                value = binding.get("value", "")
                # Angular property binding syntax: [property]="value"
                binding_strs.append(f'[{prop_name}]="{value}"')
            elif binding_type == "twoWay":
                # Two-way bindings are typically handled per-element
                prop_name = binding.get("property", "")
                if prop_name:
                    binding_strs.append(f'[(ngModel)]="{prop_name}"')
        
        return binding_strs

    def _format_interpolation(self, text: str) -> str:
        """Format text with Angular interpolation syntax."""
        # This is a simple implementation - you may want to enhance it
        # to handle more complex interpolation scenarios
        return text