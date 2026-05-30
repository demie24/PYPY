import time
import logging
from typing import Dict, Any, List, Optional, Tuple
from core.hardware.hardware_state_manager import HardwareStateManager

logger = logging.getLogger("hardware.device_manager")

class EdgeDeviceManager:
    def __init__(self, state_manager: HardwareStateManager):
        self.state_manager = state_manager
        
        # Virtual ESP32 Fleet Definition
        self.fleet: Dict[str, Dict[str, Any]] = {
            "esp32_zone1": {
                "name": "ESP32 Controller Zone 1",
                "status": "ONLINE",
                "latency_ms": 15.0,
                "trust": 1.0,
                "last_seen": time.time(),
                "type": "microcontroller",
                "breakers": ["L1_4", "L2_7"],
                "role": "PRIMARY"
            },
            "esp32_zone2": {
                "name": "ESP32 Controller Zone 2",
                "status": "ONLINE",
                "latency_ms": 18.0,
                "trust": 1.0,
                "last_seen": time.time(),
                "type": "microcontroller",
                "breakers": ["L3_9", "L4_5"],
                "role": "PRIMARY"
            },
            "esp32_zone3": {
                "name": "ESP32 Controller Zone 3",
                "status": "ONLINE",
                "latency_ms": 22.0,
                "trust": 1.0,
                "last_seen": time.time(),
                "type": "microcontroller",
                "breakers": ["L4_9", "L5_6"],
                "role": "PRIMARY"
            },
            "plc_primary": {
                "name": "Industrial Modbus PLC (Primary)",
                "status": "ONLINE",
                "latency_ms": 25.0,
                "trust": 1.0,
                "last_seen": time.time(),
                "type": "plc",
                "breakers": ["L6_7", "L7_8", "L8_9"],
                "role": "PRIMARY"
            },
            # Backup Standby Devices
            "esp32_backup": {
                "name": "Standby Backup ESP32",
                "status": "ONLINE",
                "latency_ms": 20.0,
                "trust": 1.0,
                "last_seen": time.time(),
                "type": "microcontroller",
                "breakers": [],
                "role": "STANDBY"
            },
            "plc_backup": {
                "name": "Modbus PLC (Backup Standby)",
                "status": "ONLINE",
                "latency_ms": 30.0,
                "trust": 1.0,
                "last_seen": time.time(),
                "type": "plc",
                "breakers": [],
                "role": "STANDBY"
            }
        }
        
        # Track active failover mappings (breaker -> current controller)
        self.failover_routes: Dict[str, str] = {}
        
    def tick(self):
        """
        Periodically checks timeouts for all fleet devices and updates failovers.
        """
        now = time.time()
        for device_id, dev in self.fleet.items():
            # If heartbeat is older than 5.0 seconds, mark as OFFLINE
            if now - dev["last_seen"] > 5.0 and dev["status"] not in ["OFFLINE", "QUARANTINED"]:
                dev["status"] = "OFFLINE"
                dev["latency_ms"] = -1.0
                dev["trust"] = max(0.1, dev["trust"] - 0.2)
                logger.error(f"Fleet device offline timeout: {device_id}")
                
        # Resolve active failover routing maps
        self._recompute_failover_routes()
        
    def _recompute_failover_routes(self):
        """
        Dynamically routes control to backup devices if primary controllers are compromised/offline.
        """
        new_routes = {}
        for device_id, dev in self.fleet.items():
            if dev["role"] == "PRIMARY":
                is_active = dev["status"] == "ONLINE" and dev["trust"] >= 0.4
                
                for breaker in dev["breakers"]:
                    if is_active:
                        # Direct routing to primary
                        new_routes[breaker] = device_id
                    else:
                        # Reroute to appropriate standby device
                        if dev["type"] == "microcontroller":
                            if self.fleet["esp32_backup"]["status"] == "ONLINE":
                                new_routes[breaker] = "esp32_backup"
                            else:
                                new_routes[breaker] = "plc_primary" # Failover to PLC as ultimate backup
                        elif dev["type"] == "plc":
                            if self.fleet["plc_backup"]["status"] == "ONLINE":
                                new_routes[breaker] = "plc_backup"
                            else:
                                new_routes[breaker] = "esp32_backup"
                                
        self.failover_routes = new_routes

    def get_controlling_device(self, breaker_id: str) -> Tuple[str, str]:
        """
        Returns (device_id, route_mode) for controlling a specific breaker.
        route_mode is either 'PRIMARY' or 'FAILOVER'.
        """
        self._recompute_failover_routes()
        controller = self.failover_routes.get(breaker_id)
        if not controller:
            # Fallback default configuration if all backups are offline
            if breaker_id in ["L6_7", "L7_8", "L8_9"]:
                return "plc_primary", "PRIMARY"
            else:
                return "esp32_zone1", "PRIMARY"
                
        # Determine if it is primary or fallback failover
        primary_dev = None
        for dev_id, dev in self.fleet.items():
            if dev["role"] == "PRIMARY" and breaker_id in dev["breakers"]:
                primary_dev = dev_id
                break
                
        mode = "PRIMARY" if controller == primary_dev else "FAILOVER"
        return controller, mode

    def update_device_heartbeat(self, device_id: str, latency_ms: float):
        """
        Maintains heartbeat records for fleet devices.
        """
        if device_id in self.fleet:
            dev = self.fleet[device_id]
            # Cannot restore heartbeat if quarantined
            if dev["status"] == "QUARANTINED":
                return
            dev["status"] = "ONLINE"
            dev["latency_ms"] = latency_ms
            dev["last_seen"] = time.time()
            dev["trust"] = min(1.0, dev["trust"] + 0.02)
            
            # Mirror to primary state manager if relevant
            if device_id == "esp32_zone1" or device_id == "esp32_zone2" or device_id == "esp32_zone3":
                self.state_manager.update_device_heartbeat("esp32", latency_ms)
            elif device_id == "plc_primary":
                self.state_manager.update_device_heartbeat("plc", latency_ms)

    def set_device_quarantine(self, device_id: str, quarantined: bool):
        """
        Quarantines or releases a fleet device.
        """
        if device_id in self.fleet:
            dev = self.fleet[device_id]
            if quarantined:
                dev["status"] = "QUARANTINED"
                dev["trust"] = 0.1
                logger.warning(f"Fleet device placed in QUARANTINE: {device_id}")
            else:
                dev["status"] = "ONLINE"
                dev["last_seen"] = time.time()
                dev["trust"] = 0.5 # starts with moderate trust on release
                logger.info(f"Fleet device released from quarantine: {device_id}")
            self._recompute_failover_routes()

    def get_fleet_trust(self) -> float:
        """
        Returns average trust score across active primary units.
        """
        primaries = [dev["trust"] for dev in self.fleet.values() if dev["role"] == "PRIMARY"]
        if not primaries:
            return 0.0
        return round(sum(primaries) / len(primaries), 3)

    def get_telemetry_payload(self) -> Dict[str, Any]:
        """
        Aggregates fleet status payload for MQTT transmission.
        """
        self.tick()
        return {
            "timestamp": int(time.time() * 1000),
            "fleet": {k: {
                "name": v["name"],
                "status": v["status"],
                "latency_ms": round(v["latency_ms"], 1),
                "trust": round(v["trust"], 3),
                "role": v["role"]
            } for k, v in self.fleet.items()},
            "failover_routes": self.failover_routes,
            "average_trust": self.get_fleet_trust()
        }
