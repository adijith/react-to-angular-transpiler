# API Documentation

## Transpiler Class

### `Transpiler(parser=None)`

Main transpiler class.

**Parameters:**
- `parser` (ParserInterface, optional): Parser instance. Defaults to JsxParser.

**Methods:**

#### `transpile(input_path: str, output_dir: str) -> dict`

Transpile a React component to Angular.

**Parameters:**
- `input_path` (str): Path to React component file
- `output_dir` (str): Output directory for Angular files

**Returns:**
- `dict`: Dictionary with paths to generated files:
  - `typescript`: Path to .component.ts file
  - `html`: Path to .component.html file
  - `css`: Path to .component.css file

**Raises:**
- `ValueError`: If input file cannot be read

## Parser Classes

### `JsxParser`

Babel-based parser for React/JSX code.

**Methods:**

#### `parse(source_code: str) -> Any`

Parse React/JSX source code into AST.

#### `validate(source_code: str) -> bool`

Validate that source code is valid.

## Transformer Classes

### `ASTTransformer`

Transforms React AST to Angular AST.

**Methods:**

#### `transform(react_ast: Any) -> dict`

Transform React AST to Angular AST.

## Generator Classes

### `TypeScriptGenerator`

Generates TypeScript component code.

**Methods:**

#### `generate(angular_ast: dict, component_name: str) -> str`

Generate TypeScript code from Angular AST.

### `HTMLGenerator`

Generates HTML templates.

**Methods:**

#### `generate(angular_ast: dict, component_name: str) -> str`

Generate HTML template from Angular AST.

### `CSSGenerator`

Generates CSS stylesheets.

**Methods:**

#### `generate(angular_ast: dict, component_name: str) -> str`

Generate CSS from Angular AST.

## Utility Functions

### String Utilities

- `to_pascal_case(text: str) -> str`: Convert to PascalCase
- `to_camel_case(text: str) -> str`: Convert to camelCase
- `to_kebab_case(text: str) -> str`: Convert to kebab-case

### File Utilities

- `read_file(file_path: str) -> Optional[str]`: Read file content
- `write_file(file_path: str, content: str) -> bool`: Write file content
- `ensure_directory(directory: str) -> bool`: Ensure directory exists

### Logger

- `get_logger(name: Optional[str]) -> Logger`: Get logger instance
- `set_log_level(level: str) -> None`: Set logging level

