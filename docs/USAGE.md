# Usage Guide

## Installation

### Prerequisites

- Python 3.8 or higher
- Node.js 14 or higher
- npm or yarn

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd react-to-angular-transpiler
```

2. Run the setup script:
```bash
bash scripts/setup.sh
```

Or manually:
```bash
pip install -r requirements.txt
npm install
```

## Basic Usage

### Command Line

Transpile a single React component:

```bash
python -m src.transpiler examples/simple/Counter.jsx output/
```

This will generate:
- `Counter.component.ts`
- `Counter.component.html`
- `Counter.component.css`

### Python API

```python
from src.transpiler import Transpiler

transpiler = Transpiler()
result = transpiler.transpile("input.jsx", "output/")

print(result)
# {
#   "typescript": "output/Counter.component.ts",
#   "html": "output/Counter.component.html",
#   "css": "output/Counter.component.css"
# }
```

## Advanced Usage

### Custom Parser

You can implement a custom parser by extending `ParserInterface`:

```python
from src.transpiler import Transpiler
from src.parser import ParserInterface, BabelParser

# Use default BabelParser
transpiler = Transpiler()

# Or use a custom parser
class CustomParser(ParserInterface):
    # Implement parse() and validate() methods
    pass

transpiler = Transpiler(parser=CustomParser())
```

### Configuration

Modify `config/default_config.json` to customize behavior:

```json
{
  "parser": {
    "type": "babel"
  },
  "generator": {
    "indentSize": 4,
    "includeSpecs": true
  }
}
```

## Examples

See the `examples/` directory for sample React components:
- `simple/Counter.jsx`: Basic counter with state
- `medium/TodoList.jsx`: Todo list with multiple state variables
- `complex/Dashboard.jsx`: Complex component with hooks and context

## Troubleshooting

### Common Issues

1. **Parser errors**: Ensure your React code is valid JSX
2. **Import errors**: Check that all dependencies are installed
3. **Output directory**: Ensure output directory exists or is writable

### Getting Help

- Check the [API documentation](API.md)
- Review the [Architecture guide](ARCHITECTURE.md)
- Open an issue on GitHub

