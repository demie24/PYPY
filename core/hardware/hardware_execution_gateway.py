import time
import logging
from typing import Dict, Any, List, Tuple, Optional

from deployment_profiles import DeploymentProfiles
from edge_reliability_monitor import EdgeReliabilityMonitor
from safe_relay_guard import SafeRelayGuard
from edge_device_manager import EdgeDeviceManager
from hardware_command_router import HardwareCommandRouter

logger = logging.getLogger("hardware.execution_gateway")

class HardwareExecutionGateway:
    def __init__(self,
                 device_manager: EdgeDeviceManager,
                 profiles: DeploymentProfiles,
                 safety_guard: SafeRelayGuard,
                 reliability_monitor: EdgeReliabilityMonitor,
                 command_router: HardwareCommandRouter):
        self.device_manager = device_manager
        self.profiles = profiles
        self.safety_guard = safety_guard
        self.reliability_monitor = reliability_monitor
        self.command_router = command_router
        
        # Mirror command router attributes for drop-in proxy compatibility
        self.routing_table = getattr(command_router, "routing_table", {})
        self.redundancy_coordinator = None
        
        # Track execution queue logs for HMI console

        self.execution_log: List[Dict[str, Any]] = []
        
        # Track explicitly marked compromised zones
        self.compromised_zones = set()
        
        # Breaker to Zone mapping
        self.breaker_to_zone = {
            "L1_4": "zone_1",
            "L2_7": "zone_1",
            "L3_9": "zone_2",
            "L4_5": "zone_2",
            "L4_9": "zone_3",
            "L5_6": "zone_3",
            "L6_7": "plc_zone",
            "L7_8": "plc_zone",
            "L8_9": "plc_zone"
        }
        
        # Authorized sources
        self.authorized_sources = {
            "SCADA", "SCADA_OPERATOR", "AGENT_CONSENSUS",
            "AI_ORCHESTRATOR", "LOCAL_PROTECTION", "SAFETY_GUARD", "FLISR"
        }

    def set_zone_compromised(self, zone: str, compromised: bool):
        """
        Marks a grid zone as compromised or clean.
        """
        if compromised:
            self.compromised_zones.add(zone)
            logger.warning(f"Zone {zone} marked as COMPROMISED in Execution Gateway.")
        else:
            self.compromised_zones.discard(zone)
            logger.info(f"Zone {zone} marked as CLEAN in Execution Gateway.")

    def execute_command(self, payload: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validates permission, capability, safety interlocks, and routes the command.
        Registers the command in the reliability monitor upon dispatch.
        """
        now = int(time.time() * 1000)
        command_type = payload.get("command")
        target = payload.get("target")
        source = payload.get("source", "UNKNOWN")
        
        log_entry = {
            "timestamp": now,
            "command": command_type,
            "target": target,
            "source": source,
            "status": "PENDING",
            "details": ""
        }
        
        # 1. Source Authorization validation
        if source not in self.authorized_sources:
            msg = f"PERMISSION_DENIED: Unrecognized/unauthorized control source: {source}."
            log_entry["status"] = "BLOCKED"
            log_entry["details"] = msg
            self._add_to_log(log_entry)
            logger.error(msg)
            return False, msg
            
        # 2. Emergency Stop check (highest priority safety guard block)
        if self.safety_guard.emergency_stop_active and source != "SAFETY_GUARD":
            msg = "BLOCKED: Emergency Stop is active. All control commands locked out."
            log_entry["status"] = "BLOCKED"
            log_entry["details"] = msg
            self._add_to_log(log_entry)
            logger.warning(msg)
            return False, msg

        # 3. Check for compromised/quarantined zones or devices
        if target:
            zone = self.breaker_to_zone.get(target, "unknown")
            controlling_dev, route_mode = self.device_manager.get_controlling_device(target)
            dev_info = self.device_manager.fleet.get(controlling_dev, {})
            dev_status = dev_info.get("status", "OFFLINE")
            
            # If target zone is compromised or controlling device is quarantined:
            # Block control commands unless they originate from the Safety Guard emergency override
            is_compromised = (zone in self.compromised_zones) or (dev_status == "QUARANTINED")
            if is_compromised and source != "SAFETY_GUARD":
                msg = f"BLOCKED: Zone {zone} / device {controlling_dev} is quarantined/compromised. Commands rejected."
                log_entry["status"] = "BLOCKED"
                log_entry["details"] = msg
                self._add_to_log(log_entry)
                logger.error(msg)
                return False, msg

        # 4. Capability Compatibility Validation
        if target:
            controlling_dev, _ = self.device_manager.get_controlling_device(target)
            compat, compat_msg = self.profiles.validate_command_compatibility(controlling_dev, payload)
            if not compat:
                msg = f"INCOMPATIBLE: {compat_msg}"
                log_entry["status"] = "BLOCKED"
                log_entry["details"] = msg
                self._add_to_log(log_entry)
                logger.error(msg)
                return False, msg

        # 5. Safety Interlocks & Anti-Cascade checks
        current_state = self.command_router.state_manager.get_all_states()
        safe, safety_msg = self.safety_guard.validate_command(payload, current_state)
        if not safe:
            msg = f"SAFETY_VIOLATION: {safety_msg}"
            log_entry["status"] = "BLOCKED"
            log_entry["details"] = msg
            self._add_to_log(log_entry)
            logger.warning(msg)
            return False, msg

        # 6. Command routing execution
        if getattr(self, "redundancy_coordinator", None):
            commands_to_run = self.redundancy_coordinator.route_redundant_command(payload, controlling_dev)
        else:
            commands_to_run = [payload]
            
        primary_success = False
        backup_success = False
        primary_reason = ""
        backup_reason = ""
        
        for cmd in commands_to_run:
            is_backup = "redundant_route" in cmd
            succ, reason = self.command_router.route_command(cmd)
            if is_backup:
                backup_success = succ
                backup_reason = reason
            else:
                primary_success = succ
                primary_reason = reason
                
        # Register command to track timeout transitions in Reliability Monitor if primary succeeded
        if primary_success and target and command_type in ["OPEN", "CLOSE", "CLOSED"]:
            self.reliability_monitor.register_relay_command(target, command_type, controlling_dev)
            
        # Arbitrate responses
        if len(commands_to_run) > 1:
            success, reason = self.redundancy_coordinator.arbitrate_responses(primary_success, backup_success, controlling_dev)
        else:
            success, reason = primary_success, primary_reason
            
        if success:
            log_entry["status"] = "EXECUTED"
            log_entry["details"] = f"Routed to {controlling_dev}. {reason}"
        else:
            log_entry["status"] = "FAILED"
            log_entry["details"] = f"Execution failed: {reason}"
            
        self._add_to_log(log_entry)
        return success, reason

    def route_command(self, payload: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Alias for execute_command to support drop-in compatibility.
        """
        return self.execute_command(payload)

    def _add_to_log(self, entry: Dict[str, Any]):
        self.execution_log.append(entry)
        if len(self.execution_log) > 50:
            self.execution_log.pop(0)

    def get_telemetry_payload(self) -> Dict[str, Any]:
        """
        Serializes current execution gateway telemetry.
        """
        return {
            "timestamp": int(time.time() * 1000),
            "execution_log": self.execution_log,
            "compromised_zones": list(self.compromised_zones),
            "status": "NOMINAL" if not self.compromised_zones else "DEGRADED"
        }
