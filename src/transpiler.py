"""
Main transpiler class that orchestrates the conversion process.
"""

import os
import json
from typing import Optional
from .parser import ParserInterface, JSXParser
from .transformer import ASTTransformer
from .generator import TypeScriptGenerator, HTMLGenerator, CSSGenerator
from .utils.logger import get_logger
from .utils.file_utils import read_file, write_file, ensure_directory

logger = get_logger(__name__)

# ---------------------------
# Clean AST Pretty Printer
# ---------------------------

SKIP_KEYS = {"loc", "range", "start", "end", "tokens", "comments", "raw"}
INDENT = "   "


def print_angular_ast(angular_ast):
    """Pretty print Angular AST after full transformation."""
    print("\n================ ANGULAR AST ================\n")

    cls = angular_ast.get("class", {})
    tmpl = angular_ast.get("template", {})

    # Component Name
    print(f"Component: {cls.get('name')}\n")

    # Properties
    print("PROPERTIES:")
    if cls.get("properties"):
        for p in cls["properties"]:
            name = p.get("name")
            typ = p.get("type", "")
            init = p.get("initial", "")
            print(f"  - {name} ({typ}) = {init}")
    else:
        print("  (none)")
    print()

    # Methods
    print("METHODS:")
    if cls.get("methods"):
        for m in cls["methods"]:
            print(f"  {m['name']}({', '.join(m.get('parameters', []))}):")
            print(f"    {m['body']}\n")
    else:
        print("  (none)")
    print()

    # Lifecycle Hooks
    print("LIFECYCLE HOOKS:")
    if cls.get("lifecycleHooks"):
        for h in cls["lifecycleHooks"]:
            print(f"  - {h['name']}")
    else:
        print("  (none)")
    print()

    # Template Elements
    print("TEMPLATE ELEMENTS:")
    elements = tmpl.get("elements", [])
    if elements:
        for el in elements:
            tag = el.get("tag", "")
            print(f"  - <{tag}>")
    else:
        print("  (none)")

    print("\n============== END ANGULAR AST ==============\n")



def print_ast_tree(node, indent=0):
    """Pretty-print only meaningful AST structure (clean, readable)."""

    # LIST → print each item
    if isinstance(node, list):
        for n in node:
            print_ast_tree(n, indent)
        return

    # DICT → AST node
    if isinstance(node, dict):

        node_type = node.get("type")
        if not node_type:
            return

        # labels for better readability
        label = ""

        if node_type == "Identifier":
            label = f" ({node.get('name')})"

        if node_type == "Literal":
            label = f" ({node.get('value')})"

        if node_type == "JSXIdentifier":
            label = f" <{node.get('name')}>"

        print(f"{INDENT * indent}- {node_type}{label}")

        # Recurse into children nodes
        for key, value in node.items():
            if key in SKIP_KEYS or key == "type":
                continue
            print_ast_tree(value, indent + 1)


# ---------------------------
# Transpiler Class
# ---------------------------

class Transpiler:
    """Main transpiler class that converts React components to Angular."""

    def __init__(self, parser: Optional[ParserInterface] = None):
        """
        Initialize the transpiler.

        Args:
            parser: Parser instance to use. Defaults to JSXParser.
        """
        self.parser = parser or JSXParser()
        self.transformer = ASTTransformer()
        self.ts_generator = TypeScriptGenerator()
        self.html_generator = HTMLGenerator()
        self.css_generator = CSSGenerator()

    def transpile(self, input_path: str, output_dir: str) -> dict:
        """
        Transpile a React component to Angular.
        """
        logger.info(f"Starting transpilation of {input_path}")

        # Read input file
        source_code = read_file(input_path)
        if not source_code:
            raise ValueError(f"Could not read file: {input_path}")

        # Parse React code
        ast = self.parser.parse(source_code)
        logger.debug("Successfully parsed React code")

        print("\n=== AST STRUCTURE ===")
        print_ast_tree(ast["body"])   # print only meaningful nodes
        print("=== END AST STRUCTURE ===\n")

        # Transform AST
        angular_ast = self.transformer.transform(ast)
        logger.debug("Successfully transformed AST")
        print_angular_ast(angular_ast)

        # Generate Angular code
        ensure_directory(output_dir)
        component_name = self._extract_component_name(input_path)

        ts_code = self.ts_generator.generate(angular_ast, component_name)
        html_code = self.html_generator.generate(angular_ast, component_name)
        css_code = self.css_generator.generate(angular_ast, component_name)

        # Write output
        ts_path = os.path.join(output_dir, f"{component_name}.component.ts")
        html_path = os.path.join(output_dir, f"{component_name}.component.html")
        css_path = os.path.join(output_dir, f"{component_name}.component.css")

        write_file(ts_path, ts_code)
        write_file(html_path, html_code)
        write_file(css_path, css_code)

        logger.info(f"Successfully transpiled to {output_dir}")

        return {
            "typescript": ts_path,
            "html": html_path,
            "css": css_path,
        }

    def _extract_component_name(self, file_path: str) -> str:
        """Extract component name from file path."""
        base_name = os.path.basename(file_path)
        return os.path.splitext(base_name)[0]


def main():
    """CLI entry point."""
    import sys
    import argparse

    parser = argparse.ArgumentParser(description="Transpile React to Angular")
    parser.add_argument("input", help="Input React component file")
    parser.add_argument("output", help="Output directory")
    args = parser.parse_args()

    transpiler = Transpiler()
    try:
        result = transpiler.transpile(args.input, args.output)
        print("Successfully transpiled to:")
        for key, path in result.items():
            print(f"  {key}: {path}")
    except Exception as e:
        logger.error(f"Transpilation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
