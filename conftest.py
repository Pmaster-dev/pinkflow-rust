"""Pytest configuration: add repository root to sys.path."""
import os
import sys

# Ensure project packages (api/, core/, providers/, policy/, utils/) are
# importable when tests are run from the repository root.
sys.path.insert(0, os.path.dirname(__file__))
