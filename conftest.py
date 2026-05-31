"""
Global pytest configuration for PYPY research platform.

This file centralizes Python import paths for all test modules
to improve portability, maintainability, and test reliability
across different execution environments.
"""

import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))

CORE_PATHS = [
    "core",
    "core/ai_detection",
    "core/ai_prediction",
    "core/assistant",
    "core/attack_simulator",
    "core/cyber_defense",
    "core/data_collector",
    "core/digital_twin",
    "core/gateway",
    "core/hardware",
    "core/orchestrator",
    "core/physics_validation",
    "core/relay_protection",
    "core/self_healing",
    "core/self_healing/rl",
    "core/threat_engine",
]

for subpath in CORE_PATHS:
    full_path = os.path.join(ROOT, subpath)

    if full_path not in sys.path:
        sys.path.insert(0, full_path)
