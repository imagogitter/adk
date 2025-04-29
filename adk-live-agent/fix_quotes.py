"""Script to convert quotes in Python files.

- Convert string literals to single quotes
- Convert docstrings to double quotes
"""

import re
from pathlib import Path


def replace_with_double_quotes(match):
    """Replace triple quotes with double quotes, preserving content."""
    content = match.group(0)
    if content.startswith("'''"):
        return '"""' + content[3:-3] + '"""'
    return content


def fix_quotes(content: str) -> str:
    """Convert string quotes according to style guide."""
    # First find and replace docstrings with a pattern that matches both single and double
    docstring_pattern = r'(?:\'\'\'[\s\S]*?\'\'\'|"""[\s\S]*?""")'
    content = re.sub(docstring_pattern, replace_with_double_quotes, content)

    # Split content into lines to handle string literals
    lines = content.split('\n')
    for i, line in enumerate(lines):
        # Skip lines that are part of docstrings
        if '"""' in line:
            continue

        # Handle f-strings with double quotes
        fstring_pattern = r'f"[^"]*"'
        line = re.sub(fstring_pattern, lambda m: f"f'{m.group(0)[2:-1]}'", line)

        # Handle regular double quoted strings
        string_pattern = r'"([^"]*)"'

        def replace_quotes(match):
            # Skip single character strings
            if len(match.group(1)) == 1:
                return match.group(0)
            return f"'{match.group(1)}'"

        line = re.sub(string_pattern, replace_quotes, line)

        # Remove trailing whitespace
        lines[i] = line.rstrip()

    # Join lines with newlines
    return '\n'.join(lines) + '\n'


def main():
    """Process Python files in the current directory."""
    python_files = Path('.').glob('*.py')
    for file_path in python_files:
        if file_path.name == 'fix_quotes.py':
            continue

        print(f'Processing {file_path}...')
        content = file_path.read_text()
        fixed_content = fix_quotes(content)

        if content != fixed_content:
            file_path.write_text(fixed_content)
            print(f'Updated {file_path}')
        else:
            print(f'No changes needed for {file_path}')


if __name__ == '__main__':
    main()
