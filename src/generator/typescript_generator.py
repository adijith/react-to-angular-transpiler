"""
Hardened TypeScript generator that:
- avoids generating methods for inline assignment handlers,
- ensures FormsModule note when two-way bindings present,
- prefixes `this.` safely without double-prefixing,
- converts React setState([...state, value]) → this.state.push(value),
- does not create duplicate properties/methods.
"""

import os
import re
from typing import Any, Dict, List
from ..utils.logger import get_logger
from ..utils.string_utils import to_pascal_case, to_camel_case

logger = get_logger(__name__)


class TypeScriptGenerator:
    def __init__(self):
        self.template_path = os.path.join(
            os.path.dirname(__file__), "templates", "component.ts.template"
        )

    # ----------------------------------------------------------------------
    def generate(self, angular_ast: Dict[str, Any], component_name: str) -> str:
        logger.debug("Generating TypeScript for %s", component_name)

        class_info = angular_ast.get("class", {}) or {}
        class_name = to_pascal_case(component_name) + "Component"

        # PROPERTIES
        auto_properties = self._extract_auto_properties(angular_ast)
        explicit_properties = class_info.get("properties", []) or []
        all_properties = self._merge_properties(explicit_properties, auto_properties)

        # METHODS
        auto_methods = self._extract_auto_methods(angular_ast)
        explicit_methods = class_info.get("methods", []) or []
        auto_methods = [
            m for m in auto_methods if not self._is_assignment_handler_name(m.get("name"))
        ]
        all_methods = self._merge_methods(explicit_methods, auto_methods)

        # Normalize method bodies
        setter_mappings = angular_ast.get("setterMappings", {}) or {}
        prop_names = [p.get("name") for p in all_properties]

        for method in all_methods:
            method["body"] = self._normalize_method_body(
                method.get("body", "") or "",
                prop_names,
                setter_mappings,
            )

        lifecycle_hooks = class_info.get("lifecycleHooks", []) or []
        imports = self._generate_imports(all_properties, angular_ast, lifecycle_hooks)
        properties_code = self._generate_properties(all_properties)
        lifecycle_code = self._generate_lifecycle_hooks(lifecycle_hooks)
        methods_code = self._generate_methods(all_methods)
        decorator = self._generate_decorator(component_name)

        implements = ""
        if lifecycle_hooks:
            impls = []
            if any(h.get("name") == "ngOnInit" for h in lifecycle_hooks):
                impls.append("OnInit")
            if any(h.get("name") == "ngOnDestroy" for h in lifecycle_hooks):
                impls.append("OnDestroy")
            if impls:
                implements = " implements " + ", ".join(impls)

        return f"""{imports}

{decorator}
export class {class_name}{implements} {{
{properties_code}
{lifecycle_code if lifecycle_code else ""}
{methods_code if methods_code else ""}
}}
"""

    # ----------------------------------------------------------------------
    # AUTO PROPERTIES
    # ----------------------------------------------------------------------
    def _extract_auto_properties(self, angular_ast: Dict[str, Any]) -> List[Dict[str, Any]]:
        template = angular_ast.get("template", {}) or {}
        bindings = template.get("bindings", []) or []
        elements = template.get("elements", []) or []

        auto = []
        seen = set()

        for b in bindings:
            if b.get("type") == "twoWay":
                name = b.get("property")
                if name and name not in seen:
                    auto.append({
                        "name": name,
                        "type": "string",
                        "initialValue": "''",
                        "decorator": "",
                    })
                    seen.add(name)

        for el in elements:
            tw = el.get("twoWayBinding")
            if tw and tw not in seen:
                auto.append({
                    "name": tw,
                    "type": "string",
                    "initialValue": "''",
                    "decorator": "",
                })
                seen.add(tw)

            if el.get("ngFor"):
                array_name = None
                ngfor = el.get("ngFor")
                if isinstance(ngfor, dict):
                    array_name = ngfor.get("array")
                elif isinstance(ngfor, str):
                    m = re.search(r"of\s+(\w+)", ngfor)
                    if m:
                        array_name = m.group(1)

                if array_name and array_name not in seen:
                    auto.append({
                        "name": array_name,
                        "type": "any[]",
                        "initialValue": "[]",
                        "decorator": "",
                    })
                    seen.add(array_name)

        return auto

    # ----------------------------------------------------------------------
    def _extract_auto_methods(self, angular_ast: Dict[str, Any]) -> List[Dict[str, Any]]:
        auto = []
        seen = set()
        bindings = angular_ast.get("template", {}).get("bindings", []) or []

        for b in bindings:
            if b.get("type") == "event":
                handler = b.get("handler", "")
                if not handler:
                    continue

                # Skip inline assignments like x = $event.target.value
                if "=" in handler and "(" not in handler:
                    continue

                name = handler.split("(")[0].strip()
                if name and name not in seen:
                    auto.append({
                        "name": name,
                        "parameters": [],
                        "body": "// TODO: implement handler",
                    })
                    seen.add(name)

        return auto

    # ----------------------------------------------------------------------
    def _merge_properties(self, explicit, auto):
        explicit_names = {p.get("name") for p in explicit}
        return explicit + [p for p in auto if p["name"] not in explicit_names]

    def _merge_methods(self, explicit, auto):
        explicit_names = {m.get("name") for m in explicit}
        return explicit + [m for m in auto if m["name"] not in explicit_names]

    # ----------------------------------------------------------------------
    def _generate_imports(self, properties, angular_ast, lifecycle_hooks):
        core_imports = {"Component"}

        has_input = any(str(p.get("decorator", "")).startswith("@Input") for p in properties)
        has_output = any(str(p.get("decorator", "")).startswith("@Output") for p in properties)

        if has_input:
            core_imports.add("Input")
        if has_output:
            core_imports.add("Output")
            core_imports.add("EventEmitter")

        if lifecycle_hooks:
            if any(h.get("name") == "ngOnInit" for h in lifecycle_hooks):
                core_imports.add("OnInit")
            if any(h.get("name") == "ngOnDestroy" for h in lifecycle_hooks):
                core_imports.add("OnDestroy")

        lines = [f"import {{ {', '.join(sorted(core_imports))} }} from '@angular/core';"]

        # FormsModule note for ngModel
        template = angular_ast.get("template", {}) or {}
        bindings = template.get("bindings", []) or []
        has_two_way = any(b.get("type") == "twoWay" for b in bindings)

        for el in template.get("elements", []):
            if el.get("twoWayBinding"):
                has_two_way = True
                break

        if has_two_way:
            lines.append("")
            lines.append("// NOTE: Add FormsModule to your module imports for [(ngModel)]")

        return "\n".join(lines)

    # ----------------------------------------------------------------------
    def _generate_decorator(self, component_name: str) -> str:
        selector = to_camel_case(component_name)
        pascal = component_name
        return f"""@Component({{
  selector: 'app-{selector}',
  templateUrl: './{pascal}.component.html',
  styleUrls: ['./{pascal}.component.css']
}})"""

    # ----------------------------------------------------------------------
    def _generate_properties(self, properties):
        out = []
        for p in properties:
            n = p.get("name")
            t = p.get("type", "any")
            init = p.get("initialValue") or ""
            decorator = p.get("decorator", "")

            if decorator:
                out.append(f"  {decorator}")

            line = f"  {n}: {t}"
            if init:
                line += f" = {init}"
            line += ";"
            out.append(line)

        return "\n".join(out) + "\n"

    # ----------------------------------------------------------------------
    def _generate_lifecycle_hooks(self, hooks):
        if not hooks:
            return ""

        out = []
        for h in hooks:
            name = h.get("name")
            body = h.get("body", "// TODO")
            out.append(f"  {name}(): void {{\n    {body}\n  }}\n")

        return "\n".join(out)

    # ----------------------------------------------------------------------
    def _generate_methods(self, methods):
        if not methods:
            return ""

        out = []
        for m in methods:
            name = m.get("name")
            params = ", ".join(m.get("parameters", []))
            body = m.get("body", "")

            indented = "\n    ".join(body.splitlines()) if body else ""

            out.append(f"  {name}({params}) {{\n    {indented}\n  }}")

        return "\n\n".join(out)

    # ----------------------------------------------------------------------
    # ** NORMALIZE METHOD BODY **
    # ----------------------------------------------------------------------
    def _normalize_method_body(self, body: str, prop_names, setter_mappings):
        if not body:
            return ""

        normalized = body

        # Convert setX([...state, value]) → this.state.push(value)
        for setter, state in setter_mappings.items():

            # Match spread array pattern
            pattern = re.compile(
                rf"{setter}\(\s*\[\s*\.\.\.\s*{state}\s*,\s*([^\]]+?)\s*\]\s*\)",
                flags=re.S,
            )

            def repl(m):
                tail = m.group(1).strip()
                tail_norm = self._prefix_this_to_identifiers(tail, prop_names)

                # Simple pushable values
                if re.fullmatch(r"[A-Za-z_]\w*", tail) or \
                   re.fullmatch(r'"[^"]*"|\'[^\']*\'|\d+', tail):
                    return f"this.{state}.push({tail_norm})"

                # fallback to spread
                return f"this.{state} = [...this.{state}, {tail_norm}]"

            normalized = pattern.sub(repl, normalized)

            # Generic setter pattern setX(value) → this.x = value
            pattern2 = re.compile(
                rf"{setter}\(\s*(.+?)\s*\)",
                flags=re.S,
            )

            def repl2(m):
                expr = m.group(1).strip()
                expr_norm = self._prefix_this_to_identifiers(expr, prop_names)
                return f"this.{state} = {expr_norm}"

            normalized = pattern2.sub(repl2, normalized)

        # Prefix identifiers with this.
        normalized = self._prefix_this_to_identifiers(normalized, prop_names)

        # Ensure semicolons
        lines = []
        for ln in normalized.splitlines():
            ln2 = ln.rstrip()
            if ln2 and not ln2.endswith((";", "{", "}")):
                ln2 += ";"
            lines.append(ln2)

        normalized = "\n".join(lines)

        # FINAL: clean accidental this.this.
        normalized = re.sub(r"\bthis\.this\.", "this.", normalized)

        return normalized

    # ----------------------------------------------------------------------
    def _prefix_this_to_identifiers(self, text: str, identifiers: List[str]) -> str:
        if not identifiers:
            return text

        # Protect string literals
        string_placeholders = {}

        def protect(m):
            key = f"__STR{len(string_placeholders)}__"
            string_placeholders[key] = m.group(0)
            return key

        protected = re.sub(r"(\".*?\"|'.*?')", protect, text)

        # Prefix identifiers
        for ident in sorted(set(identifiers), key=lambda x: -len(x)):
            # DO NOT prefix if already "this.ident"
            pattern = re.compile(rf"(?<!this\.)\b{re.escape(ident)}\b")
            protected = pattern.sub(f"this.{ident}", protected)

        # Restore string literals
        for key, val in string_placeholders.items():
            protected = protected.replace(key, val)

        return protected

    # ----------------------------------------------------------------------
    def _is_assignment_handler_name(self, name: str) -> bool:
        return not name or "=" in name
