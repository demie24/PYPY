"""
Pytest configuration and shared fixtures for the Smart Grid Cybersecurity Platform.

This conftest is authoritative — individual test files must NOT manipulate sys.path.
"""

import sys
import os
import asyncio
import logging
import pytest
from pathlib import Path
from unittest.mock import MagicMock

# ============================================================================
# PATH SETUP — Insert project root so all `from core.X.Y import Z` imports work
# ============================================================================
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ============================================================================
# PYTEST CONFIGURATION
# ============================================================================

def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test (requires live services)")
    config.addinivalue_line("markers", "slow: mark test as slow running")


# ============================================================================
# SESSION-LEVEL FIXTURES
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create a shared event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# MQTT FIXTURES
# ============================================================================

@pytest.fixture
def mock_mqtt_client():
    """Mock MQTT client for unit testing without a live broker."""
    client = MagicMock()
    client.connect = MagicMock(return_value=None)
    client.publish = MagicMock(return_value=(0, 1))   # (rc, mid)
    client.subscribe = MagicMock(return_value=(0, 1))
    client.loop_start = MagicMock()
    client.loop_stop = MagicMock()
    client.disconnect = MagicMock()
    return client


@pytest.fixture
def mqtt_broker_config():
    """MQTT broker connection configuration (used by integration tests)."""
    return {
        "host": os.environ.get("MQTT_BROKER", "localhost"),
        "port": int(os.environ.get("MQTT_PORT", 1883)),
        "keepalive": 60,
    }


# ============================================================================
# DIGITAL TWIN FIXTURES
# ============================================================================

@pytest.fixture
def grid_config():
    """Standard IEEE 9-Bus grid configuration."""
    return {
        "buses": 9,
        "branches": 9,
        "generators": 3,
        "loads": 3,
        "simulation_step": 0.01,
        "base_mva": 100,
    }


@pytest.fixture
def sample_grid_state():
    """A snapshot of a healthy IEEE 9-Bus grid state."""
    return {
        "timestamp": 1609459200,
        "buses": [
            {"id": 1, "voltage": 1.04, "angle": 0.0},
            {"id": 2, "voltage": 1.025, "angle": -5.48},
            {"id": 3, "voltage": 1.025, "angle": -7.87},
        ],
        "branches": [
            {"from_bus": 1, "to_bus": 2, "power_flow": 0.73},
            {"from_bus": 1, "to_bus": 3, "power_flow": 0.92},
        ],
        "generators": [
            {"bus": 1, "power_output": 2.32, "voltage": 1.04},
            {"bus": 2, "power_output": 1.63, "voltage": 1.025},
            {"bus": 3, "power_output": 0.85, "voltage": 1.025},
        ],
    }


# ============================================================================
# AI DETECTION FIXTURES
# ============================================================================

@pytest.fixture
def sample_normal_telemetry():
    """Nominal grid telemetry — no attacks."""
    return {
        "timestamp": 1609459200,
        "voltage_readings": [1.04, 1.025, 1.025, 0.99, 0.97, 0.95],
        "current_readings": [5.2, 3.1, 2.8, 4.5, 3.2, 2.1],
        "frequency": 60.0,
        "reactive_power": [0.5, 0.3, 0.2, 0.4, 0.2, 0.1],
    }


@pytest.fixture
def sample_attack_telemetry():
    """Telemetry with a False Data Injection Attack (FDIA) signature."""
    return {
        "timestamp": 1609459205,
        "voltage_readings": [2.5, 0.5, 0.3, 0.85, 0.92, 1.1],   # Anomalous
        "current_readings": [15.2, 0.1, 0.2, 4.5, 3.2, 2.1],    # Anomalous
        "frequency": 59.2,                                          # Slightly off
        "reactive_power": [2.5, 0.03, 0.02, 0.4, 0.2, 0.1],      # Anomalous
    }


# ============================================================================
# SELF-HEALING FIXTURES
# ============================================================================

@pytest.fixture
def fault_scenario():
    """A branch fault scenario for self-healing restoration testing."""
    return {
        "fault_type": "branch_fault",
        "fault_location": {"from_bus": 1, "to_bus": 2},
        "fault_impedance": 0.001,
        "fault_time": 1609459210,
    }


@pytest.fixture
def restoration_action():
    """A sample FLISR restoration action."""
    return {
        "action_type": "breaker_open",
        "location": {"from_bus": 1, "to_bus": 2},
        "timestamp": 1609459212,
        "confidence": 0.95,
    }


# ============================================================================
# GATEWAY FIXTURES
# ============================================================================

@pytest.fixture
def sample_websocket_message():
    """A sample gateway control message."""
    return {
        "type": "control",
        "command": "open_breaker",
        "payload": {
            "breaker_id": "BR_1_2",
            "reason": "fault_isolation",
        },
        "timestamp": 1609459200,
    }


# ============================================================================
# UTILITY FIXTURES
# ============================================================================

@pytest.fixture
def temp_log_dir(tmp_path):
    """Provide a temporary directory for log file output."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    return log_dir


@pytest.fixture
def mock_logger(temp_log_dir):
    """A real logger pointing to a temp file (useful for log-assertion tests)."""
    logger = logging.getLogger("test")
    handler = logging.FileHandler(temp_log_dir / "test.log")
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    return logger
