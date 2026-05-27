import logging
import time
from typing import Dict, Any, List, Set

logger = logging.getLogger("hardware.rogue_monitor")

class RogueDeviceMonitor:
    def __init__(self):
        # Authorized USB devices registry
        self.authorized_devices = {
            "0483:5740": {
                "vendor_id": "0483",
                "product_id": "5740",
                "name": "STM32 Virtual COM Port (ESP32_Bridge)",
                "authorized": True
            },
            "1a86:7523": {
                "vendor_id": "1a86",
                "product_id": "7523",
                "name": "CH340 Serial Converter (PLC_Modbus_Gateway)",
                "authorized": True
            }
        }
        
        # Enumerated devices state
        # list of dicts: {"vendor_id": str, "product_id": str, "name": str, "trusted": bool, "status": str}
        self.connected_devices: List[Dict[str, Any]] = [
            {
                "vendor_id": "0483",
                "product_id": "5740",
                "name": "STM32 Virtual COM Port (ESP32_Bridge)",
                "trusted": True,
                "status": "ACTIVE"
            },
            {
                "vendor_id": "1a86",
                "product_id": "7523",
                "name": "CH340 Serial Converter (PLC_Modbus_Gateway)",
                "trusted": True,
                "status": "ACTIVE"
            }
        ]
        
        # Global hardware trust metrics
        self.hardware_trust_score = 1.0  # 0.0 (distrusted) to 1.0 (fully trusted)
        
        # Quarantine states
        self.quarantined_ports: Set[str] = set()
        
        # Reconnect tracking: device_id -> timestamps list
        self.connection_history: Dict[str, List[float]] = {}
        
        # Stealth device tracking: device_id -> ticks left
        self.stealth_devices: Dict[str, int] = {}
        
        # USB propagation tracking (0.0 to 1.0)
        self.propagation_level = 0.0
        
    def simulate_device_insertion(self, vid: str, pid: str, name: str, stealth_ticks: int = 0) -> bool:
        """
        Simulates USB device discovery. If device is not in authorized_devices list,
        flags a rogue device warning.
        """
        device_id = f"{vid}:{pid}"
        
        # 1. Check Quarantine status first
        port_mapping = self._map_device_to_port(vid, pid)
        if port_mapping in self.quarantined_ports:
            logger.warning(f"Connection blocked: Port {port_mapping} is quarantined. Rejecting device {name}.")
            return False
            
        # 2. Reconnect Abuse Detection
        now = time.time()
        if device_id not in self.connection_history:
            self.connection_history[device_id] = []
        
        timestamps = self.connection_history[device_id]
        timestamps.append(now)
        # Filter within last 10 seconds
        self.connection_history[device_id] = [t for t in timestamps if now - t <= 10.0]
        
        if len(self.connection_history[device_id]) > 2:
            # Reconnect flood abuse detected
            logger.critical(f"USB RECONNECT ABUSE DETECTED: Device {name} ({device_id}) disconnected/reconnected too frequently.")
            self.hardware_trust_score = max(0.0, self.hardware_trust_score - 0.50)
            
            # Auto-block and register as blocked device
            self.connected_devices = [d for d in self.connected_devices if not (d["vendor_id"] == vid and d["product_id"] == pid)]
            self.connected_devices.append({
                "vendor_id": vid,
                "product_id": pid,
                "name": name,
                "trusted": False,
                "status": "BLOCKED"
            })
            return False
            
        # Check if already connected
        for dev in self.connected_devices:
            if dev["vendor_id"] == vid and dev["product_id"] == pid:
                if dev["status"] == "BLOCKED":
                    logger.warning(f"USB Device {device_id} is in BLOCKED state.")
                    return False
                logger.info(f"USB Device {device_id} is already enumerated.")
                return True
                
        is_trusted = vid in self.authorized_devices or device_id in self.authorized_devices
        status = "ACTIVE"
        
        # 3. Stealth device behavior registration
        if stealth_ticks > 0 and not is_trusted:
            self.stealth_devices[device_id] = stealth_ticks
            status = "SILENT"
            logger.info(f"Stealth Rogue USB Device inserted: {name} (will remain SILENT for {stealth_ticks} ticks).")
        
        new_device = {
            "vendor_id": vid,
            "product_id": pid,
            "name": name,
            "trusted": is_trusted,
            "status": status
        }
        self.connected_devices.append(new_device)
        
        if not is_trusted and status == "ACTIVE":
            logger.warning(f"Rogue Device Detected: {name} (VID={vid}, PID={pid}) is NOT authorized!")
            self.hardware_trust_score = max(0.0, self.hardware_trust_score - 0.3)
            
        return is_trusted
        
    def simulate_device_removal(self, vid: str, pid: str):
        device_id = f"{vid}:{pid}"
        self.connected_devices = [d for d in self.connected_devices if not (d["vendor_id"] == vid and d["product_id"] == pid)]
        
        if device_id in self.stealth_devices:
            del self.stealth_devices[device_id]
            
        # Recalculate hardware trust score
        has_untrusted = any(not d["trusted"] and d["status"] != "BLOCKED" for d in self.connected_devices)
        if not has_untrusted:
            self.hardware_trust_score = 1.0
            self.propagation_level = 0.0
            
        logger.info(f"USB Device {vid}:{pid} disconnected.")
        
    def tick(self):
        """
        Executes background state updates for dynamic trust decay, stealth activation,
        and propagation mapping.
        """
        # 1. Process stealth timer updates
        for dev_id in list(self.stealth_devices.keys()):
            self.stealth_devices[dev_id] -= 1
            if self.stealth_devices[dev_id] <= 0:
                del self.stealth_devices[dev_id]
                # Transition device to ACTIVE
                for dev in self.connected_devices:
                    if f"{dev['vendor_id']}:{dev['product_id']}" == dev_id:
                        dev["status"] = "ACTIVE"
                        logger.warning(f"Stealth device {dev['name']} ({dev_id}) became ACTIVE. Anomaly triggered!")
                        self.hardware_trust_score = max(0.0, self.hardware_trust_score - 0.30)
                        
        # 2. Dynamic trust decay for connected untrusted active devices
        has_active_rogue = False
        for dev in self.connected_devices:
            if not dev["trusted"] and dev["status"] in ["ACTIVE", "PROPAGATING"]:
                has_active_rogue = True
                
        if has_active_rogue:
            # Decay trust by 0.05 per tick
            self.hardware_trust_score = max(0.0, self.hardware_trust_score - 0.05)
            # Increase cyber propagation
            self.propagation_level = min(1.0, self.propagation_level + 0.10)
            
            # Transition status to PROPAGATING if level goes high
            if self.propagation_level >= 0.50:
                for dev in self.connected_devices:
                    if not dev["trusted"] and dev["status"] == "ACTIVE":
                        dev["status"] = "PROPAGATING"
                        logger.warning(f"Rogue device {dev['name']} status escalated to PROPAGATING.")
        else:
            self.propagation_level = max(0.0, self.propagation_level - 0.05)
            
    def quarantine_port(self, port_id: str):
        self.quarantined_ports.add(port_id)
        logger.warning(f"Quarantine active on port: {port_id}")
        
        # Disconnect any connected devices on this port
        for dev in list(self.connected_devices):
            dev_port = self._map_device_to_port(dev["vendor_id"], dev["product_id"])
            if dev_port == port_id:
                # Force disconnect / quarantine status
                dev["status"] = "QUARANTINED"
                logger.info(f"Quarantined device {dev['name']} connected on {port_id}.")
                
    def release_port(self, port_id: str):
        if port_id in self.quarantined_ports:
            self.quarantined_ports.remove(port_id)
            logger.info(f"Quarantine released on port: {port_id}")
            # Restore status of devices on this port
            for dev in self.connected_devices:
                dev_port = self._map_device_to_port(dev["vendor_id"], dev["product_id"])
                if dev_port == port_id and dev["status"] == "QUARANTINED":
                    dev["status"] = "ACTIVE"
                    
    def _map_device_to_port(self, vid: str, pid: str) -> str:
        """
        Maps a USB vendor/product ID pair to a virtual physical port ID.
        """
        device_id = f"{vid}:{pid}"
        if device_id == "0483:5740":
            return "ESP32"
        elif device_id == "1a86:7523":
            return "PLC"
        elif vid == "16c0":
            return "Port 7"  # Default rogue serial/HID port
        else:
            return "Port 8"
            
    def get_devices_status(self) -> List[Dict[str, Any]]:
        return self.connected_devices
        
    def get_trust_payload(self) -> Dict[str, Any]:
        return {
            "trust_score": round(self.hardware_trust_score, 2),
            "unauthorized_count": sum(1 for d in self.connected_devices if not d["trusted"]),
            "total_devices": len(self.connected_devices),
            "propagation_level": round(self.propagation_level, 2),
            "quarantined_ports": list(self.quarantined_ports)
        }
        
    def reset(self):
        self.connected_devices = [
            {
                "vendor_id": "0483",
                "product_id": "5740",
                "name": "STM32 Virtual COM Port (ESP32_Bridge)",
                "trusted": True,
                "status": "ACTIVE"
            },
            {
                "vendor_id": "1a86",
                "product_id": "7523",
                "name": "CH340 Serial Converter (PLC_Modbus_Gateway)",
                "trusted": True,
                "status": "ACTIVE"
            }
        ]
        self.hardware_trust_score = 1.0
        self.quarantined_ports.clear()
        self.connection_history.clear()
        self.stealth_devices.clear()
        self.propagation_level = 0.0
        logger.info("Rogue monitor reset to nominal registry state.")
