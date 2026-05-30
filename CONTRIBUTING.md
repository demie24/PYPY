# Contributing to Smart Grid Cybersecurity Platform

Thank you for contributing! This document covers the development workflow, code standards, and how to get your changes reviewed.

---

## Getting Started

```bash
# Clone
git clone https://github.com/demie24/smart-grid-security.git
cd smart-grid-security

# Install in editable mode (enables `from core.X.Y import Z` everywhere)
pip install -e .

# Install all dependencies
pip install -r core/requirements.txt -r core/requirements-ai.txt
```

---

## Development Workflow

1. **Create a feature branch**
   ```bash
   git checkout -b feature/my-feature
   # or for fixes:
   git checkout -b fix/description-of-bug
   ```

2. **Write code + tests** — every new feature or bug fix should include a test in `tests/unit/`

3. **Run tests locally before pushing**
   ```bash
   # Fast check (no external services needed)
   pytest tests/ -m "not integration" -q

   # Full unit suite
   pytest tests/unit/ -v
   ```

4. **Commit with a clear message**
   ```bash
   git commit -m "feat: add XYZ anomaly detection threshold config"
   # Prefixes: feat / fix / refactor / docs / test / chore / ci
   ```

5. **Push and open a Pull Request** targeting `main`

---

## Code Standards

| Tool | Command | Rule |
|------|---------|------|
| **Style** | `black core/` | PEP 8, 127 char line limit |
| **Lint** | `flake8 core/` | No syntax errors, no undefined names |
| **Imports** | — | Always use `from core.X.Y import Z` — never add `sys.path` hacks |
| **Types** | — | Type hints encouraged for public functions |

---

## Adding a New Core Module

1. Create `core/my_module/__init__.py`
2. Place logic in `core/my_module/my_file.py`
3. Add tests in `tests/unit/test_my_module.py`
4. If it's a standalone service, add a `core/my_module/Dockerfile` and register in `docker-compose.yml`

### Import convention
```python
# ✅ Correct — package-aware
from core.self_healing.autonomous_balancer import AutonomousBalancer

# ❌ Wrong — flat import (breaks after test reorganization)
from autonomous_balancer import AutonomousBalancer
```

---

## Testing Guidelines

- **Unit tests** go in `tests/unit/` — must run with `pytest -m "not integration"`
- **Integration tests** go in `tests/integration/` and are marked `@pytest.mark.integration`
- Use fixtures from `tests/conftest.py` (mock MQTT, sample grid state, etc.)
- Test files must be named `test_<module>.py`

```python
# Example test using conftest fixtures
def test_anomaly_detected(sample_attack_telemetry, mock_mqtt_client):
    detector = AnomalyDetector(client=mock_mqtt_client)
    result = detector.check(sample_attack_telemetry)
    assert result.is_anomaly
```

---

## Directory Map

```
smart-grid-cybersecurity/
├── core/               # All backend Python packages
├── dashboard/          # React frontend
├── hardware/           # ESP32 firmware (pending)
├── tests/              # Test suite
├── docs/               # API and MQTT reference docs
├── logs/               # Service log output (gitignored)
├── checkpoints/        # RL model checkpoints (gitignored)
├── analytics/          # Training analytics (gitignored)
└── .github/workflows/  # CI/CD
```

---

## Questions?

Open a [GitHub Issue](https://github.com/demie24/smart-grid-security/issues) or start a [Discussion](https://github.com/demie24/smart-grid-security/discussions).
