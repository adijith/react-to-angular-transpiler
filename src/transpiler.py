"""
Main transpiler class that orchestrates the conversion process.
"""

import os
from typing import Optional
from .parser import ParserInterface, BabelParser
from .transformer import ASTTransformer
from .generator import TypeScriptGenerator, HTMLGenerator, CSSGenerator
from .utils.logger import get_logger
from .utils.file_utils import read_file, write_file, ensure_directory

logger = get_logger(__name__)


class Transpiler:
    """Main transpiler class that converts React components to Angular."""

    def __init__(self, parser: Optional[ParserInterface] = None):
        """
        Initialize the transpiler.

        Args:
            parser: Parser instance to use. Defaults to BabelParser.
        """
        self.parser = parser or BabelParser()
        self.transformer = ASTTransformer()
        self.ts_generator = TypeScriptGenerator()
        self.html_generator = HTMLGenerator()
        self.css_generator = CSSGenerator()

    def transpile(self, input_path: str, output_dir: str) -> dict:
        """
        Transpile a React component to Angular.

        Args:
            input_path: Path to the React component file
            output_dir: Directory to output Angular files

        Returns:
            Dictionary with paths to generated files
        """
        logger.info(f"Starting transpilation of {input_path}")

        # Read input file
        source_code = read_file(input_path)
        if not source_code:
            raise ValueError(f"Could not read file: {input_path}")

        # Parse React code
        ast = self.parser.parse(source_code)
        logger.debug("Successfully parsed React code")

        # Transform AST
        angular_ast = self.transformer.transform(ast)
        logger.debug("Successfully transformed AST")

        # Generate Angular code
        ensure_directory(output_dir)
        component_name = self._extract_component_name(input_path)

        ts_code = self.ts_generator.generate(angular_ast, component_name)
        html_code = self.html_generator.generate(angular_ast, component_name)
        css_code = self.css_generator.generate(angular_ast, component_name)

        # Write output files
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
        print(f"Successfully transpiled to:")
        for key, path in result.items():
            print(f"  {key}: {path}")
    except Exception as e:
        logger.error(f"Transpilation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

