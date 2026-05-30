import sys
import os

# Insert the project root at the front of sys.path so that all
# `from core.X.Y import Z` style imports resolve correctly in every test.
# Individual test files should NOT manipulate sys.path themselves.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
