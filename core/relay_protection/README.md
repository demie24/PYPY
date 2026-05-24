# Core Relay Protection (IED Emulator)

The Relay Protection service emulates Digital Protective Relays (Intelligent Electronic Devices - IEDs) placed at substations. It runs local protective functions to trip circuit breakers if unsafe conditions occur.

## Implemented Functions (ANSI/IEEE C37.2)
- **ANSI 50/51**: Overcurrent protection (instantaneous & time-delay)
- **ANSI 59**: Overvoltage protection
- **ANSI 27**: Undervoltage protection

## Usage
1. Start service:
   ```bash
   python src/relay.py
   ```
