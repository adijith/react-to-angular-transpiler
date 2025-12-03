"""
HTML template generator for Angular components.
Converts JSX AST → Angular HTML.
"""

from typing import Any, Dict, List
from ..utils.logger import get_logger

logger = get_logger(__name__)


class HTMLGenerator:
    """Generates Angular HTML template from Angular AST."""

    def generate(self, angular_ast: Dict[str, Any], component_name: str) -> str:
        """
        Generate HTML template code.

        Args:
            angular_ast: Angular AST
            component_name: name of component

        Returns:
            HTML template string
        """

        elements = angular_ast.get("template", {}).get("elements", [])
        bindings = angular_ast.get("template", {}).get("bindings", [])

        # Build HTML
        html_lines = []
        for el in elements:
            html_lines.append(self._render_element(el, bindings))

        return "\n".join(html_lines)

    # --------------------------------------------------------------------
    # ELEMENT RENDERING
    # --------------------------------------------------------------------

    def _render_element(self, el: Dict[str, Any], bindings: List[Dict]) -> str:
        """Render a single JSX element → Angular HTML."""
        tag = el.get("tag", "div")
        attrs = self._render_attributes(el, bindings)
        children = el.get("children", [])

        # If children include nested elements, they must be rendered recursively
        rendered_children = self._render_children(children, bindings)

        # Self-closing if no children
        if not rendered_children.strip():
            return f"<{tag}{attrs} />"

        return f"<{tag}{attrs}>\n{rendered_children}\n</{tag}>"

    # --------------------------------------------------------------------
    # CHILDREN RENDERING
    # --------------------------------------------------------------------

    def _render_children(self, children, bindings):
        if not children:
            return ""

        if isinstance(children, str):
            return f"  {children}"

        rendered = []
        for child in children:
            if isinstance(child, str):
                rendered.append(f"  {child}")
            elif isinstance(child, dict):  # nested JSX element
                rendered.append("  " + self._render_element(child, bindings))

        return "\n".join(rendered)

    # --------------------------------------------------------------------
    # ATTRIBUTE RENDERING
    # --------------------------------------------------------------------

    def _render_attributes(self, el: Dict[str, Any], bindings: List[Dict]) -> str:
        attrs = []

        # 1. Standard JSX → Angular attributes
        for a in el.get("attributes", []):
            name = a.get("name")
            value = a.get("value")

            if value is None or value == "":
                attrs.append(f"{name}")
            else:
                attrs.append(f'{name}="{value}"')

        # 2. Two-way binding ([(ngModel)])
        if el.get("twoWayBinding"):
            prop = el["twoWayBinding"]
            attrs.append(f'[(ngModel)]="{prop}"')

        # 3. ngFor directive
        if el.get("ngFor"):
            ng = el["ngFor"]
            item = ng["item"]
            array = ng["array"]
            index = ng["index"]
            attrs.append(f'*ngFor="let {item} of {array}; let {index} = index"')

        # 4. Event bindings
        for b in bindings:
            if b.get("type") == "event":
                # Apply only if event belongs to this element
                # (right now apply globally)
                event_name = b["name"]
                handler = b["handler"]
                attrs.append(f'{event_name}="{handler}"')

        # Join with spaces
        if attrs:
            return " " + " ".join(attrs)
        return ""
