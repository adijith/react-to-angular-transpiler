"""
TypeScript code generator for Angular components.
"""

import os
import re
from typing import Any, Dict, List, Set
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
            component_name: Name of the component (as discovered from AST)

        Returns:
            Generated TypeScript code
        """
        logger.debug(f"Generating TypeScript for {component_name}")

        class_info = angular_ast.get("class", {})
        class_name = to_pascal_case(component_name) + "Component"

        # Auto-generate properties from template bindings
        auto_properties = self._extract_auto_properties(angular_ast)
        explicit_properties = class_info.get("properties", [])
        all_properties = self._merge_properties(explicit_properties, auto_properties)

        # Methods
        auto_methods = self._extract_auto_methods(angular_ast)
        explicit_methods = class_info.get("methods", [])
        all_methods = self._merge_methods(explicit_methods, auto_methods)

        # Try to normalize method bodies (add `this.` to state/props usage & convert setters)
        setter_mappings = angular_ast.get("setterMappings", {})
        prop_names = [p.get("name") for p in all_properties]
        for method in all_methods:
            body = method.get("body", "") or ""
            normalized = self._normalize_method_body(body, prop_names, setter_mappings)
            method["body"] = normalized

        # Determine lifecycle hooks
        lifecycle_hooks = class_info.get("lifecycleHooks", [])

        # Determine imports
        imports = self._generate_imports(all_properties, angular_ast, lifecycle_hooks)

        # Properties code
        properties_code = self._generate_properties(all_properties)

        # Lifecycle hooks code
        lifecycle_code = self._generate_lifecycle_hooks(lifecycle_hooks)

        # Methods code
        methods_code = self._generate_methods(all_methods)

        # Decorator
        decorator = self._generate_decorator(component_name)

        implements = ""
        if lifecycle_hooks:
            # Only include OnInit/OnDestroy if lifecycle hooks present and include them in imports above.
            impls = []
            if any(h.get("name") == "ngOnInit" for h in lifecycle_hooks):
                impls.append("OnInit")
            if any(h.get("name") == "ngOnDestroy" for h in lifecycle_hooks):
                impls.append("OnDestroy")
            if impls:
                implements = " implements " + ", ".join(impls)

        code = f"""{imports}

{decorator}
export class {class_name}{implements} {{
{properties_code}
{lifecycle_code if lifecycle_code else ""}
{methods_code if methods_code else ""}
}}
"""
        return code

    # ----------------------------
    # Property & Method extraction
    # ----------------------------
    def _extract_auto_properties(self, angular_ast: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract properties needed from template (two-way bindings, ngFor arrays)."""
        auto_props = []
        seen = set()

        template = angular_ast.get("template", {})
        elements = template.get("elements", [])
        bindings = template.get("bindings", [])

        # From two-way bindings
        for b in bindings:
            if b.get("type") == "twoWay":
                name = b.get("property")
                if name and name not in seen:
                    auto_props.append({"name": name, "type": "string", "initialValue": "''", "decorator": ""})
                    seen.add(name)

        # From elements (ngFor arrays or explicit twoWayBinding attr)
        for el in elements:
            if el.get("twoWayBinding"):
                name = el.get("twoWayBinding")
                if name and name not in seen:
                    auto_props.append({"name": name, "type": "string", "initialValue": "''", "decorator": ""})
                    seen.add(name)
            if el.get("ngFor"):
                array_name = None
                ngfor = el.get("ngFor")
                # ngFor may be dict or string — allow both
                if isinstance(ngfor, dict):
                    array_name = ngfor.get("array")
                elif isinstance(ngfor, str):
                    # attempt to parse "let item of items" -> items
                    m = re.search(r"of\s+(\w+)", ngfor)
                    if m:
                        array_name = m.group(1)
                if array_name and array_name not in seen:
                    auto_props.append({"name": array_name, "type": "any[]", "initialValue": "[]", "decorator": ""})
                    seen.add(array_name)

        return auto_props

    def _extract_auto_methods(self, angular_ast: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract placeholder methods for event handlers found in bindings."""
        auto_methods = []
        seen = set()
        bindings = angular_ast.get("template", {}).get("bindings", [])
        for b in bindings:
            if b.get("type") == "event":
                handler = b.get("handler", "")
                # handler might be "addTodo()" or "addTodo($event)"
                if handler:
                    mname = handler.split("(")[0].strip()
                    if mname and mname not in seen:
                        auto_methods.append({"name": mname, "parameters": [], "body": "// TODO: implement handler"})
                        seen.add(mname)
        return auto_methods

    # ----------------------------
    # Merging utilities
    # ----------------------------
    def _merge_properties(self, explicit: List[Dict[str, Any]], auto: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        explicit_names = {p.get("name") for p in explicit if p.get("name")}
        merged = list(explicit)
        for p in auto:
            if p.get("name") not in explicit_names:
                merged.append(p)
        return merged

    def _merge_methods(self, explicit: List[Dict[str, Any]], auto: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        explicit_names = {m.get("name") for m in explicit if m.get("name")}
        merged = list(explicit)
        for m in auto:
            if m.get("name") not in explicit_names:
                merged.append(m)
        return merged

    # ----------------------------
    # Imports generator
    # ----------------------------
    def _generate_imports(self, properties: List[Dict[str, Any]], angular_ast: Dict[str, Any], lifecycle_hooks: List[Dict[str, Any]]) -> str:
        """Generate import statements based on usage."""
        core_imports = {"Component"}
        # props with decorator @Input()
        has_input = any(str(p.get("decorator", "")).strip().startswith("@Input") for p in properties)
        has_output = any(str(p.get("decorator", "")).strip().startswith("@Output") for p in properties)
        if has_input:
            core_imports.add("Input")
        if has_output:
            core_imports.add("Output")
            core_imports.add("EventEmitter")

        # lifecycle imports
        if lifecycle_hooks:
            if any(h.get("name") == "ngOnInit" for h in lifecycle_hooks):
                core_imports.add("OnInit")
            if any(h.get("name") == "ngOnDestroy" for h in lifecycle_hooks):
                core_imports.add("OnDestroy")

        imports = [f"import {{ {', '.join(sorted(core_imports))} }} from '@angular/core';"]
        # Note for FormsModule if two-way binding was used
        template = angular_ast.get("template", {})
        bindings = template.get("bindings", [])
        has_two_way = any(b.get("type") == "twoWay" for b in bindings)
        # also check elements
        for el in template.get("elements", []):
            if el.get("twoWayBinding"):
                has_two_way = True
                break
        if has_two_way:
            imports.append("")
            imports.append("// NOTE: Add FormsModule to your module's imports array for [(ngModel)] to work")

        return "\n".join(imports)

    # ----------------------------
    # Decorator generator
    # ----------------------------
    def _generate_decorator(self, component_name: str) -> str:
        """Generate component decorator."""
        selector = to_camel_case(component_name)
        # Template and style file names: PascalCase.component.html per your earlier convention
        pascal = component_name
        return f"""@Component({{
  selector: 'app-{selector}',
  templateUrl: './{pascal}.component.html',
  styleUrls: ['./{pascal}.component.css']
}})"""

    # ----------------------------
    # Properties & lifecycle generation
    # ----------------------------
    def _generate_properties(self, properties: List[Dict[str, Any]]) -> str:
        """Generate class properties."""
        if not properties:
            return ""

        lines = []
        for p in properties:
            name = p.get("name", "")
            ptype = p.get("type", "any")
            # Normalize small type hints:
            if ptype == "state":
                ptype = "any"
            # Make sure arrays are typed if value looks like array
            init = p.get("initialValue") or p.get("initial") or p.get("initialValue", "")
            decorator = p.get("decorator", "")
            if decorator:
                lines.append(f"  {decorator}")
            # Ensure arrays have [] when value suggests array
            line = f"  {name}: {ptype}"
            if init:
                line += f" = {init}"
            line += ";"
            lines.append(line)
        return "\n".join(lines) + "\n"

    def _generate_lifecycle_hooks(self, hooks: List[Dict[str, Any]]) -> str:
        """Generate lifecycle hook methods. If none, return empty string."""
        if not hooks:
            return ""

        code_lines = []
        for h in hooks:
            name = h.get("name")
            body = h.get("body", "// TODO: implement hook")
            code_lines.append(f"  {name}(): void {{\n    {body}\n  }}\n")
        return "\n".join(code_lines)

    def _generate_methods(self, methods: List[Dict[str, Any]]) -> str:
        """Generate methods from AST method descriptions."""
        if not methods:
            return ""

        blocks = []
        for m in methods:
            name = m.get("name", "")
            params = m.get("parameters", []) or []
            param_str = ", ".join(params)
            body = m.get("body", "") or ""
            # Indent body lines
            indented = "\n    ".join(line for line in body.splitlines()) if body else ""
            blocks.append(f"  {name}({param_str}) {{\n    {indented}\n  }}")
        return "\n\n".join(blocks)

    # ----------------------------
    # Method body normalization
    # ----------------------------
    def _normalize_method_body(self, body: str, prop_names: List[str], setter_mappings: Dict[str, str]) -> str:
        """
        Normalize a method body string:
        - Replace bare prop/state references with `this.<prop>`
        - Convert setter calls like setX(...) to `this.x = ...` or array push/concat forms
        - Avoid double-replacing if `this.` already present
        """
        if not body:
            return ""

        normalized = body

        # 1) Convert common setter patterns using setter_mappings
        # Example: setNewTodo('') -> this.newTodo = ''
        # Example: setTodos([...todos, newTodo]) -> this.todos = [...this.todos, this.newTodo]
        for setter, state in setter_mappings.items():
            # setX([...state, something])
            pattern_spread = re.compile(
                rf'{re.escape(setter)}\(\s*\[\s*\.\.\.{re.escape(state)}\s*,\s*([^\]]+)\]\s*\)'
            )
            def _rep_spread(m):
                tail = m.group(1).strip()
                tail_norm = self._prefix_this_to_identifiers(tail, prop_names)
                return f"this.{state} = [...this.{state}, {tail_norm}]"
            normalized = pattern_spread.sub(_rep_spread, normalized)

            # setX([something, ...state]) => this.state = [something, ...this.state]
            pattern_spread2 = re.compile(
                rf'{re.escape(setter)}\(\s*\[\s*([^\],]+)\s*,\s*\.\.\.{re.escape(state)}\s*\]\s*\)'
            )
            def _rep_spread2(m):
                head = m.group(1).strip()
                head_norm = self._prefix_this_to_identifiers(head, prop_names)
                return f"this.{state} = [{head_norm}, ...this.{state}]"
            normalized = pattern_spread2.sub(_rep_spread2, normalized)

            # Generic setter call setX(expr) -> this.x = expr
            pattern_setter_generic = re.compile(rf'{re.escape(setter)}\(\s*(.+?)\s*\)', flags=re.S)
            def _rep_setter_generic(m):
                expr = m.group(1).strip()
                expr_norm = self._prefix_this_to_identifiers(expr, prop_names)
                return f"this.{state} = {expr_norm}"
            # Use a single substitution but avoid replacing the previous handled patterns again:
            normalized = pattern_setter_generic.sub(_rep_setter_generic, normalized)

        # 2) Prefix property/state references with this.<prop> (but avoid existing this.prop)
        normalized = self._prefix_this_to_identifiers(normalized, prop_names)

        # 3) Replace common JS -> TS idioms (semicolon, missing ;), ensure semicolons at line-end
        lines = [ln.rstrip() for ln in normalized.splitlines()]
        clean_lines = []
        for ln in lines:
            if ln and not ln.strip().endswith(";") and not ln.strip().endswith("{") and not ln.strip().endswith("}"):
                clean_lines.append(ln + ";")
            else:
                clean_lines.append(ln)
        normalized = "\n".join(clean_lines)

        # 4) Remove accidental double `this.this.` if any (defensive)
        normalized = normalized.replace("this.this.", "this.")

        # 5) Indent multi-line bodies properly when later rendered
        return normalized

    def _prefix_this_to_identifiers(self, text: str, identifiers: List[str]) -> str:
        """
        Prefix occurrences of standalone identifiers with `this.`.
        Avoid changing:
          - identifiers already prefixed with `this.`
          - property access like obj.prop (where obj != this)
          - inside string literals (simple protection)
        This is a heuristic — complex JS expressions may need manual fix.
        """
        if not identifiers:
            return text

        # Quick guard: protect string literals by replacing them with placeholders
        string_placeholders = {}
        def _protect_strings(s):
            def repl(m):
                key = f"__STR_{len(string_placeholders)}__"
                string_placeholders[key] = m.group(0)
                return key
            return re.sub(r"(\".*?\"|'.*?')", repl, s)
        protected = _protect_strings(text)

        for ident in sorted(set(identifiers), key=lambda x: -len(x)):  # longer first
            # pattern: word boundary + ident + word boundary, not preceded by "this." and not preceded by "."
            pattern = re.compile(rf'(?<!this\.)(?<!\.)\b{re.escape(ident)}\b')
            protected = pattern.sub(f"this.{ident}", protected)

        # restore string literals
        for k, v in string_placeholders.items():
            protected = protected.replace(k, v)

        return protected
