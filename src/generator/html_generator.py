"""
HTML template generator for Angular components.
"""

from typing import Any, Dict, List
from ..utils.logger import get_logger

logger = get_logger(__name__)


class HTMLGenerator:
    """Generates Angular HTML template from Angular AST."""

    def generate(self, angular_ast: Dict[str, Any], component_name: str) -> str:
        elements = angular_ast.get("template", {}).get("elements", [])
        bindings = angular_ast.get("template", {}).get("bindings", [])

        html_lines = []
        for el in elements:
            html_lines.append(self._render_element(el, bindings))

        return "\n".join(html_lines)

    # ---------------------------------------------------------------
    def _render_element(self, el: Dict[str, Any], bindings: List[Dict]) -> str:
        tag = el.get("tag", "div")
        attrs = self._render_attributes(el, bindings)
        children = el.get("children", [])

        rendered_children = self._render_children(children, bindings)

        if not rendered_children.strip():
            return f"<{tag}{attrs} />"

        return f"<{tag}{attrs}>\n{rendered_children}\n</{tag}>"

    # ---------------------------------------------------------------
    def _render_children(self, children, bindings):
        if not children:
            return ""

        rendered = []
        for child in children:
            if isinstance(child, str):
                rendered.append(f"  {child}")
            elif isinstance(child, dict):
                rendered.append("  " + self._render_element(child, bindings))

        return "\n".join(rendered)

    # ---------------------------------------------------------------
    def _render_attributes(self, el: Dict[str, Any], bindings: List[Dict]) -> str:
        attrs = []
        el_id = el.get("id")

        # --- 1. Normal JSX attributes --------------------------------
        for a in el.get("attributes", []):
            name = a.get("name")
            value = a.get("value")
            if value:
                attrs.append(f'{name}="{value}"')
            else:
                attrs.append(name)

        # --- 2. ngFor -----------------------------------------------
        if el.get("ngFor"):
            ng = el["ngFor"]
            attrs.append(
                f'*ngFor="let {ng["item"]} of {ng["array"]}; let {ng["index"]} = index"'
            )

        # --- 3. Two-way binding -------------------------------------
        if el.get("twoWayBinding"):
            model = el["twoWayBinding"]
            attrs.append(f'[(ngModel)]="{model}"')

        # --- 4. Event bindings - APPLY ONLY IF TARGET MATCHES --------
        for b in bindings:
            if b.get("type") == "event" and b.get("target") == el_id:
                event = b["name"]
                handler = b["handler"]
                attrs.append(f'({event})="{handler}"')

        # Join
        return (" " + " ".join(attrs)) if attrs else ""
