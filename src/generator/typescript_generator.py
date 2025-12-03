"""
TypeScript code generator for Angular components.
"""

import os
from typing import Any, Dict, Set
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

        # Auto-generate properties from template bindings
        auto_properties = self._extract_auto_properties(angular_ast)
        
        # Merge with explicit properties
        explicit_properties = class_info.get("properties", [])
        all_properties = self._merge_properties(explicit_properties, auto_properties)

        # Generate imports
        imports = self._generate_imports(angular_ast, all_properties)

        # Generate class properties
        properties = self._generate_properties(all_properties)

        # Generate lifecycle hooks
        lifecycle_hooks = self._generate_lifecycle_hooks(
            class_info.get("lifecycleHooks", [])
        )

        # Generate methods (including event handlers)
        auto_methods = self._extract_auto_methods(angular_ast)
        explicit_methods = class_info.get("methods", [])
        all_methods = self._merge_methods(explicit_methods, auto_methods)
        methods = self._generate_methods(all_methods)

        # Generate decorator
        decorator = self._generate_decorator(component_name)

        # Combine all parts
        code = f"""{imports}

{decorator}
export class {class_name} implements OnInit, OnDestroy {{
{properties}
{lifecycle_hooks}
{methods}
}}
"""

        return code

    def _extract_auto_properties(self, angular_ast: Dict[str, Any]) -> list:
        """Extract properties needed from template (two-way bindings, ngFor arrays)."""
        auto_props = []
        seen_props = set()
        
        template = angular_ast.get("template", {})
        elements = template.get("elements", [])
        bindings = template.get("bindings", [])
        
        # Extract from two-way bindings
        for binding in bindings:
            if binding.get("type") == "twoWay":
                prop_name = binding.get("property", "")
                if prop_name and prop_name not in seen_props:
                    auto_props.append({
                        "name": prop_name,
                        "type": "string",
                        "initialValue": "''",
                        "decorator": ""
                    })
                    seen_props.add(prop_name)
        
        # Extract from elements
        for element in elements:
            # Two-way binding
            if element.get("twoWayBinding"):
                prop_name = element.get("twoWayBinding")
                if prop_name and prop_name not in seen_props:
                    auto_props.append({
                        "name": prop_name,
                        "type": "string",
                        "initialValue": "''",
                        "decorator": ""
                    })
                    seen_props.add(prop_name)
            
            # ngFor array
            if element.get("ngFor"):
                array_name = element.get("ngFor", {}).get("array", "")
                if array_name and array_name not in seen_props:
                    auto_props.append({
                        "name": array_name,
                        "type": "any[]",
                        "initialValue": "[]",
                        "decorator": ""
                    })
                    seen_props.add(array_name)
        
        return auto_props

    def _extract_auto_methods(self, angular_ast: Dict[str, Any]) -> list:
        """Extract methods needed from template (event handlers)."""
        auto_methods = []
        seen_methods = set()
        
        template = angular_ast.get("template", {})
        bindings = template.get("bindings", [])
        
        for binding in bindings:
            if binding.get("type") == "event":
                handler = binding.get("handler", "")
                # Extract method name (e.g., "onClick()" -> "onClick")
                method_name = handler.split("(")[0].strip() if handler else ""
                
                if method_name and method_name not in seen_methods:
                    auto_methods.append({
                        "name": method_name,
                        "parameters": [],
                        "body": "// TODO: Implement event handler"
                    })
                    seen_methods.add(method_name)
        
        return auto_methods

    def _merge_properties(self, explicit: list, auto: list) -> list:
        """Merge explicit and auto-generated properties, preferring explicit."""
        explicit_names = {p.get("name") for p in explicit}
        merged = list(explicit)
        
        for prop in auto:
            if prop.get("name") not in explicit_names:
                merged.append(prop)
        
        return merged

    def _merge_methods(self, explicit: list, auto: list) -> list:
        """Merge explicit and auto-generated methods, preferring explicit."""
        explicit_names = {m.get("name") for m in explicit}
        merged = list(explicit)
        
        for method in auto:
            if method.get("name") not in explicit_names:
                merged.append(method)
        
        return merged

    def _generate_imports(self, angular_ast: Dict[str, Any], properties: list) -> str:
        """Generate import statements."""
        imports = []
        core_imports = {"Component", "OnInit", "OnDestroy"}
        
        # Check for Input/Output decorators
        has_input = any("@Input()" in str(p.get("decorator", "")) for p in properties)
        has_output = any("@Output()" in str(p.get("decorator", "")) for p in properties)
        
        if has_input:
            core_imports.add("Input")
        if has_output:
            core_imports.add("Output")
            core_imports.add("EventEmitter")
        
        imports.append(f"import {{ {', '.join(sorted(core_imports))} }} from '@angular/core';")
        
        # Check for two-way bindings ([(ngModel)])
        template = angular_ast.get("template", {})
        bindings = template.get("bindings", [])
        has_two_way_binding = any(b.get("type") == "twoWay" for b in bindings)
        
        elements = template.get("elements", [])
        for element in elements:
            if element.get("twoWayBinding"):
                has_two_way_binding = True
                break

        if has_two_way_binding:
            imports.append("")
            imports.append("// NOTE: Add FormsModule to your module's imports array for [(ngModel)] to work")

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

            if decorator:
                prop_lines.append(f"  {decorator}")
            
            prop_line = f"  {name}: {prop_type}"
            if initial_value:
                prop_line += f" = {initial_value}"
            prop_line += ";"

            prop_lines.append(prop_line)

        return "\n".join(prop_lines) + "\n" if prop_lines else ""

    def _generate_lifecycle_hooks(self, hooks: list) -> str:
        """Generate lifecycle hook methods."""
        if not hooks:
            # Provide default implementations
            default_hooks = """  ngOnInit(): void {
    // Component initialization logic here
  }

  ngOnDestroy(): void {
    // Cleanup logic here
  }"""
            return default_hooks + "\n"

        hook_lines = []
        for hook in hooks:
            hook_type = hook.get("type", "")
            body = hook.get("body", "")
            
            # Add proper return type
            return_type = "void"
            hook_lines.append(f"  {hook_type}(): {return_type} {{\n    {body}\n  }}")

        return "\n\n".join(hook_lines) + "\n" if hook_lines else ""

    def _generate_methods(self, methods: list) -> str:
        """Generate class methods."""
        if not methods:
            return ""

        method_lines = []
        for method in methods:
            name = method.get("name", "")
            params = method.get("parameters", [])
            return_type = method.get("returnType", "void")
            body = method.get("body", "")
            
            param_str = ", ".join(params)
            method_lines.append(f"  {name}({param_str}): {return_type} {{\n    {body}\n  }}")

        return "\n\n".join(method_lines) if method_lines else ""