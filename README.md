React → Angular Transpiler

A lightweight transpiler that converts React Function Components into equivalent Angular Components.
This project demonstrates AST parsing, transformation logic, and template generation—designed for interview evaluation.

⭐ Features

Converts JSX → Angular template syntax

Translates useState → Angular class properties

Translates useEffect → ngOnInit / ngOnDestroy

Maps React events (onClick, onChange) → Angular bindings

Automatically detects two-way binding → [(ngModel)]

Outputs clean TypeScript, HTML, and CSS files

🧠 Approach Overview (How the Transpiler Works)

This transpiler is built around a 4-step transformation pipeline:

1️⃣ Parse React Code into an AST

The input .jsx file is parsed using Esprima to generate a complete JavaScript AST.

The AST contains:

function components

JSX elements

hooks (useState, useEffect)

event handlers

return structure

This AST is used as the single source of truth for conversion.

2️⃣ Apply Transformation Rules

Several rule modules process the AST in a specific order:

a) HooksRules – convert React hooks

useState(...) → Angular class property

useEffect(...) → lifecycle hooks (ngOnInit, ngOnDestroy)

Maps setter functions (setText) so Angular can detect two-way binding (text).

b) ComponentRules – extract metadata

Determines component name

Extracts methods such as const add = () => {}

Extracts props

Ensures Angular class structure is correctly built

c) JSXRules – convert JSX → Angular template

Maps:

{variable} → {{ variable }}

className → class

{array.map(...)} → *ngFor

<input value={text} onChange={...} /> →
<input [(ngModel)]="text" /> (if detected)

d) EventRules – convert event handlers

onClick={fn} → (click)="fn()"

onChange → (change)=...

Handles inline expressions like count + 1

Supports:

assignment transformation

setter-based transformations

binary expressions

3️⃣ Generate Angular Output

Produces:

ComponentName.component.ts

ComponentName.component.html

ComponentName.component.css

These file contents come from the transformed Angular AST.

4️⃣ Output Saved to Directory

All generated Angular files appear in the specified output folder.

▶️ Usage
python -m src.transpiler <input_file.jsx> <output_folder>


Example:

python -m src.transpiler examples/simple/Todo.jsx output/

📦 Installation
pip install -r requirements.txt

📂 Project Structure
src/
  parser/          # JSX parser (Esprima wrapper)
  transformer/
     hooks_rules.py
     event_rules.py
     jsx_rules.py
     component_rules.py
     ast_transformer.py
  generator/
     ts_generator.py
  transpiler.py     # CLI entry point
examples/
output/