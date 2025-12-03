#!/bin/bash

# Setup script for React to Angular Transpiler

echo "Setting up React to Angular Transpiler..."

# Check Python version
python_version=$(python3 --version 2>&1)
echo "Python: $python_version"

# Check Node.js version
node_version=$(node --version 2>&1)
echo "Node.js: $node_version"

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Install Node.js dependencies
echo "Installing Node.js dependencies..."
npm install

# Create output directory if it doesn't exist
mkdir -p output

echo "Setup complete!"

