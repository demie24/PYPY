#!/bin/bash
# Script to organize test files into tests/ directory
# Run from root of PYPY repository

set -e  # Exit on error

echo "🔄 Organizing test files..."

# Create tests directory if it doesn't exist
mkdir -p tests/unit
mkdir -p tests/integration
mkdir -p tests/fixtures

echo "📁 Created tests/ directory structure"

# Move all test_*.py files to tests/unit/
# Identify if test is unit or integration based on content (optional)
for file in test_*.py; do
    if [ -f "$file" ]; then
        # Check if file mentions docker, mqtt, service integration
        if grep -q -E "docker|mqtt|integration|e2e|service" "$file"; then
            mv "$file" tests/integration/
            echo "  ➜ $file → tests/integration/"
        else
            mv "$file" tests/unit/
            echo "  ➜ $file → tests/unit/"
        fi
    fi
done

# Create pytest configuration if doesn't exist
if [ ! -f "tests/conftest.py" ]; then
    cat > tests/conftest.py << 'EOF'
"""Pytest configuration and shared fixtures."""

import pytest
import sys
from pathlib import Path

# Add core directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "core"))


@pytest.fixture
def mqtt_broker():
    """Mock MQTT broker fixture."""
    # Configure mock MQTT for tests
    pass


@pytest.fixture
def digital_twin_simulator():
    """Digital twin simulator fixture."""
    pass


@pytest.fixture
def ai_detection_model():
    """AI detection model fixture."""
    pass
EOF
    echo "✅ Created tests/conftest.py"
else
    echo "⏭️  tests/conftest.py already exists, skipping"
fi

# Create __init__.py files
touch tests/__init__.py
touch tests/unit/__init__.py
touch tests/integration/__init__.py

echo ""
echo "✅ Test files organized successfully!"
echo ""
echo "Next steps:"
echo "  1. Review tests/conftest.py and add proper fixtures"
echo "  2. Run: pytest tests/ -v"
echo "  3. Update CI/CD workflows if needed"
