# Code Style Guide

This document outlines the coding standards for the Autonomous Trading Platform project.

## Python Version

This project uses Python 3.13. All code should be compatible with this version and leverage its features where appropriate.

## General Guidelines

1. Follow PEP 8 style guidelines with the modifications specified in our `.flake8` config.
2. Maximum line length is 100 characters.
3. Use 4 spaces for indentation (no tabs).
4. Use double quotes for docstrings and single quotes for other strings.

## Python 3.13 Features

Where appropriate, take advantage of Python 3.13 features such as:
- Enhanced type annotations
- F-strings with = formatting
- Pattern matching improvements
- Other relevant new features

## Imports

1. Imports should be grouped in the following order:
   - Standard library imports
   - Related third-party imports
   - Local application/library specific imports
2. Use absolute imports rather than relative imports.
3. Use `isort` to automatically organize imports.

## Documentation

1. All modules, classes, and functions should have docstrings.
2. Use Google-style docstrings.
   ```python
   def example_function(param1, param2):
       """Short description of the function.

       Longer description if needed.

       Args:
           param1 (type): Description of param1.
           param2 (type): Description of param2.

       Returns:
           type: Description of return value.

       Raises:
           ExceptionType: When and why this exception is raised.
       """
       pass
