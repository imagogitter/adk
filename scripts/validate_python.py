#!/usr/bin/env python
"""
Validate Python version and package compatibility.

This script checks if the current Python version is 3.13
and verifies compatibility of key packages.
"""

import importlib
import sys

from packaging import version


def check_python_version() -> bool:
    """Check if Python version is 3.13.x."""
    required = "3.13"
    current = f"{sys.version_info.major}.{sys.version_info.minor}"

    if current != required:
        print(f"Error: Python {required} required, but {current} detected.")
        print(f"Please install Python {required} to continue.")
        return False

    print(f"✓ Python {current} detected (required: {required})")
    return True


def check_package_version(package_name: str, min_version: str | None = None) -> bool:
    """Check if package is installed and meets minimum version requirements."""
    try:
        pkg = importlib.import_module(package_name)
        pkg_version = getattr(pkg, "__version__", "unknown")

        if min_version and pkg_version != "unknown":
            if version.parse(pkg_version) < version.parse(min_version):
                print(
                    f"⚠ {package_name} version {pkg_version} detected, "
                    f"but >= {min_version} recommended"
                )
                return False

        print(f"✓ {package_name} {pkg_version} detected")
        return True
    except ImportError:
        print(f"✗ {package_name} not installed")
        return False


def main() -> None:
    """Run all validation checks."""
    if not check_python_version():
        sys.exit(1)

    # Check key packages
    packages = [
        ("ccxt", "4.2.0"),
        ("pandas", "2.2.0"),
        ("numpy", "1.26.0"),
        ("influxdb_client", "1.38.0"),
    ]

    all_ok = True
    for pkg, ver in packages:
        if not check_package_version(pkg, ver):
            all_ok = False

    if not all_ok:
        print("\nSome packages may not be fully compatible with Python 3.13.")
        print("Consider updating to the recommended versions.")
    else:
        print("\nAll package requirements met!")


if __name__ == "__main__":
    main()
