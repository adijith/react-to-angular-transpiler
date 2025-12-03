# Architecture Guide

## Overview

The React to Angular Transpiler is designed with a modular architecture that separates concerns into distinct phases: parsing, transformation, and code generation.

## Architecture Components

### 1. Parser Module (`src/parser/`)

The parser module is responsible for parsing React/JSX code into an Abstract Syntax Tree (AST).

- **ParserInterface**: Abstract interface defining the contract for parsers
- **BabelParser**: Full-featured parser using Babel for accurate parsing

### 2. Transformer Module (`src/transformer/`)

The transformer module converts React AST to Angular AST.

- **ASTTransformer**: Main orchestrator for transformations
- **mappings.py**: Defines mappings between React and Angular concepts
- **rules/**: Individual transformation rules
  - `component_rules.py`: Component structure transformations
  - `hooks_rules.py`: React hooks to Angular lifecycle/properties
  - `jsx_rules.py`: JSX to Angular template transformations
  - `event_rules.py`: Event handler transformations

### 3. Generator Module (`src/generator/`)

The generator module produces Angular code from the transformed AST.

- **TypeScriptGenerator**: Generates TypeScript component code
- **HTMLGenerator**: Generates HTML templates
- **CSSGenerator**: Generates CSS stylesheets
- **templates/**: Code templates for Angular components

### 4. Utilities (`src/utils/`)

Shared utility functions used across modules.

- **string_utils.py**: String manipulation functions
- **file_utils.py**: File I/O operations
- **logger.py**: Logging configuration

## Data Flow

```
React Source Code
    ↓
Parser (React AST)
    ↓
Transformer (Angular AST)
    ↓
Generator (Angular Code)
    ↓
Output Files (.ts, .html, .css)
```

## Extension Points

The architecture supports extension through:

1. **Custom Parsers**: Implement `ParserInterface`
2. **Custom Rules**: Add new transformation rules
3. **Custom Generators**: Extend generator classes
4. **Configuration**: Modify `config/default_config.json`

## Design Principles

- **Separation of Concerns**: Each module has a single responsibility
- **Extensibility**: Easy to add new transformation rules
- **Modularity**: Components can be swapped or extended

