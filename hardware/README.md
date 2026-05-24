# ESP32 Grid Node / Substation RTU Firmware

This module contains Arduino C++ / ESP-IDF source code for running on ESP32 microcontrollers. The ESP32 simulates a physical substation Terminal Unit (RTU) or Intelligent Electronic Device (IED).

## Features
- **WiFi & MQTT Connectivity**: Connects to the local network and the MQTT Gateway broker.
- **Physical Relays / Breakers**: Maps ESP32 GPIO pins to control active relays or status LEDs representing grid breakers.
- **Modbus/TCP Server**: Exposes internal telemetry registers (e.g., simulated Voltage on Bus 3, Breaker Status, current flowing through the line) to the digital twin or SCADA host.
- **Local Protection Backup**: Optional overcurrent detection logic that operates directly on-chip for hardware protection redundancy.

## Setup Instructions

1. Install [PlatformIO IDE](https://platformio.org/) or [Arduino IDE].
2. Configure `config.h` with your local Wi-Fi SSID, password, and MQTT broker IP address.
3. Build and upload firmware to the ESP32 board.
