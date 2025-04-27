#!/bin/bash
set -e

# Verify Python version
py_version=$(python --version | cut -d' ' -f2)
if [[ $(echo "$py_version" | cut -d. -f1-2) != "3.13" ]]; then
    echo "Warning: You're using Python $py_version. This project is configured for Python 3.13."
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "Installing development dependencies..."
pip install -r requirements-dev.txt

echo "Setting up pre-commit hooks..."
pre-commit install

echo "Creating initial environment for type checking..."
python -m mypy --install-types

echo "Linting setup complete! You can now run:"
echo "  - pre-commit run --all-files (to check all files)"
echo "  - flake8 . (to run flake8 separately)"
echo "  - mypy . (to run type checking separately)"
