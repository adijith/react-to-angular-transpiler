"""
TypeScript code generator for Angular components.
"""

import os
from typing import Any, Dict
from ..utils.logger import get_logger
from ..utils.string_utils import to_pascal_case, to_camel_case

logger = get_logger(__name__)


class TypeScriptGenerator:
    """Generates TypeScript code for Angular components."""

    def __init__(self):
        """Initialize the generator."""
        self.template_path = os.path.join(
            os.path.dirname(__file__), "templates", "component.ts.template"
        )

    def generate(self, angular_ast: Dict[str, Any], component_name: str) -> str:
        """
        Generate TypeScript code from Angular AST.

        Args:
            angular_ast: The Angular AST
            component_name: Name of the component

        Returns:
            Generated TypeScript code
        """
        logger.debug(f"Generating TypeScript for {component_name}")

        class_info = angular_ast.get("class", {})
        class_name = to_pascal_case(component_name) + "Component"

        # Generate imports
        imports = self._generate_imports(angular_ast)

        # Generate class properties
        properties = self._generate_properties(class_info.get("properties", []))

        # Generate lifecycle hooks
        lifecycle_hooks = self._generate_lifecycle_hooks(
            class_info.get("lifecycleHooks", [])
        )

        # Generate methods
        methods = self._generate_methods(class_info.get("methods", []))

        # Generate decorator
        decorator = self._generate_decorator(component_name)

        # Combine all parts
        code = f"""{imports}

{decorator}
export class {class_name} {{
{properties}
{lifecycle_hooks}
{methods}
}}
"""

        return code

    def _generate_imports(self, angular_ast: Dict[str, Any]) -> str:
        """Generate import statements."""
        imports = [
            "import { Component, OnInit, OnDestroy } from '@angular/core';",
        ]

        # Add Input/Output if needed
        has_input_output = any("Input" in str(p) for p in angular_ast.get("class", {}).get("properties", []))
        if has_input_output:
            imports[0] = imports[0].replace(
                "Component, OnInit, OnDestroy",
                "Component, OnInit, OnDestroy, Input, Output"
            )

        # Check for two-way bindings ([(ngModel)])
        template = angular_ast.get("template", {})
        bindings = template.get("bindings", [])
        has_two_way_binding = any(b.get("type") == "twoWay" for b in bindings)
        
        # Also check elements for two-way binding
        elements = template.get("elements", [])
        for element in elements:
            if element.get("twoWayBinding"):
                has_two_way_binding = True
                break

        if has_two_way_binding:
            imports.append("// Note: Import FormsModule in your module for [(ngModel)] to work")
            imports.append("// import { FormsModule } from '@angular/forms';")

        return "\n".join(imports)

    def _generate_decorator(self, component_name: str) -> str:
        """Generate component decorator."""
        selector = to_camel_case(component_name)
        return f"""@Component({{
  selector: 'app-{selector}',
  templateUrl: './{component_name}.component.html',
  styleUrls: ['./{component_name}.component.css']
}})"""

    def _generate_properties(self, properties: list) -> str:
        """Generate class properties."""
        if not properties:
            return ""

        prop_lines = []
        for prop in properties:
            name = prop.get("name", "")
            prop_type = prop.get("type", "any")
            initial_value = prop.get("initialValue", "")
            decorator = prop.get("decorator", "")

            prop_line = f"  {decorator}\n  " if decorator else "  "
            prop_line += f"{name}: {prop_type}"
            if initial_value:
                prop_line += f" = {initial_value}"
            prop_line += ";"

            prop_lines.append(prop_line)

        return "\n".join(prop_lines) + "\n" if prop_lines else ""

    def _generate_lifecycle_hooks(self, hooks: list) -> str:
        """Generate lifecycle hook methods."""
        if not hooks:
            return ""

        hook_lines = []
        for hook in hooks:
            hook_type = hook.get("type", "")
            body = hook.get("body", "")
            hook_lines.append(f"  {hook_type}() {{\n    {body}\n  }}")

        return "\n\n".join(hook_lines) + "\n" if hook_lines else ""

    def _generate_methods(self, methods: list) -> str:
        """Generate class methods."""
        if not methods:
            return ""

        method_lines = []
        for method in methods:
            name = method.get("name", "")
            params = method.get("parameters", [])
            body = method.get("body", "")
            param_str = ", ".join(params)
            method_lines.append(f"  {name}({param_str}) {{\n    {body}\n  }}")

        return "\n\n".join(method_lines) if method_lines else ""

