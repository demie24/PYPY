import time
import uuid
import logging
from typing import Dict, Any, List, Tuple, Optional

from core.hardware.hardware_state_manager import HardwareStateManager
from core.hardware.hardware_command_router import HardwareCommandRouter
from core.hardware.hardware_synchronization_engine import HardwareSynchronizationEngine
from core.hardware.distributed_command_bus import DistributedCommandBus
from core.hardware.edge_device_manager import EdgeDeviceManager
from core.hardware.relay_execution_planner import RelayExecutionPlanner

logger = logging.getLogger("hardware.orchestrator")

class HardwareOrchestrator:
    # Arbitration priorities: lower values indicate higher precedence
    PRIORITY_LEVELS = {
        "LOCAL_PROTECTION": 1,
        "AGENT_CONSENSUS": 2,
        "SCADA": 3,
        "UNKNOWN": 4
    }
    
    def __init__(self, state_manager: HardwareStateManager, command_router: HardwareCommandRouter):
        self.state_manager = state_manager
        self.command_router = command_router
        
        # Instantiate orchestration modules
        self.sync_engine = HardwareSynchronizationEngine()
        self.command_bus = DistributedCommandBus()
        self.device_manager = EdgeDeviceManager(state_manager)
        self.relay_planner = RelayExecutionPlanner(state_manager)
        
        # Track active lockouts per breaker (breaker_id -> retaining details)
        self.breaker_locks: Dict[str, Dict[str, Any]] = {}
        # Conflict logs for dashboard visualization
        self.conflicts: List[Dict[str, Any]] = []
        
    def tick(self):
        """
        Main execution step. Executed at 1Hz in the main daemon loop.
        Coordinates timing synchronization, device failovers, and bus message execution.
        """
        now = time.time()
        
        # 1. Sync clock and fleet device checks
        self.sync_engine.tick()
        self.device_manager.tick()
        
        # 2. Tick the distributed command bus to execute delivered packets
        delivered = self.command_bus.process_bus_tick(lambda dev_id: self.device_manager.fleet.get(dev_id))
        
        for tx_id, cmd_payload, target_device in delivered:
            success, reason = self._execute_routed_command(cmd_payload, target_device)
            # Acknowledge completion back to the bus
            self.command_bus.acknowledge_command(tx_id, success, reason)
            
            # Map feedback into active switching plans
            for plan_id, plan in list(self.relay_planner.active_plans.items()):
                if plan["active_tx_id"] == tx_id:
                    self.relay_planner.mark_step_result(plan_id, plan["current_step_idx"], success, tx_id, reason)
                    
        # 3. Tick switching plans and enqueue ready steps
        staged_steps = self.relay_planner.tick_plans(now)
        for plan_id, step_idx, step_cmd in staged_steps:
            tx_id = f"tx_plan_{plan_id}_{step_idx}_{uuid.uuid4().hex[:6]}"
            target_breaker = step_cmd["target"]
            controlling_dev, route_mode = self.device_manager.get_controlling_device(target_breaker)
            
            # Retrieve base latency for this channel
            dev_info = self.device_manager.fleet.get(controlling_dev)
            base_latency = dev_info.get("latency_ms", 20.0) if dev_info else 20.0
            
            # Wrap as command payload
            cmd_payload = {
                "command": step_cmd["command"],
                "target": target_breaker,
                "source": "LOCAL_PROTECTION"  # Planned sequences have high priority
            }
            
            self.command_bus.send_command(tx_id, cmd_payload, controlling_dev, base_latency)
            
            # Update the plan with the dispatched tx_id
            plan = self.relay_planner.active_plans.get(plan_id)
            if plan:
                plan["active_tx_id"] = tx_id
                
        # Clean expired breaker locks
        self._prune_locks(now)

    def submit_command(self, payload: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Intercepts proposed commands, checks priority arbitration, and routes them.
        """
        cmd = payload.get("command")
        target = payload.get("target")
        source = payload.get("source", "UNKNOWN")
        
        # 1. Handle multi-step execution sequences
        if cmd == "LAUNCH_PLAN":
            plan_id = payload.get("plan_id", f"plan_{uuid.uuid4().hex[:6]}")
            steps = payload.get("steps", [])
            success, msg = self.relay_planner.create_switching_plan(plan_id, steps)
            return success, msg
            
        if not target or not cmd:
            return False, "Missing target or command parameters."
            
        proposed_priority = self.PRIORITY_LEVELS.get(source, self.PRIORITY_LEVELS["UNKNOWN"])
        
        # 2. Priority Arbitration Check
        retaining = self.breaker_locks.get(target)
        if retaining:
            retaining_priority = retaining["priority"]
            if proposed_priority > retaining_priority:
                # Proposed command has lower priority (higher value) -> reject!
                reason = f"Blocked command from {source} (Priority {proposed_priority}) on locked breaker {target} controlled by {retaining['source']} (Priority {retaining_priority})."
                self._log_conflict(target, source, proposed_priority, retaining["source"], retaining_priority, "BLOCKED")
                logger.warning(reason)
                return False, reason
            elif proposed_priority < retaining_priority:
                # Override active lock with higher priority command
                logger.info(f"Overriding lock on {target}: new command from {source} overrides {retaining['source']}.")
                self._log_conflict(target, source, proposed_priority, retaining["source"], retaining_priority, "OVERRIDDEN")
                self.breaker_locks[target] = {
                    "source": source,
                    "priority": proposed_priority,
                    "expire_time": time.time() + 5.0
                }
            else:
                # Same priority level -> update expiration time
                self.breaker_locks[target]["expire_time"] = time.time() + 5.0
        else:
            # Create a lock retaining control over the breaker
            self.breaker_locks[target] = {
                "source": source,
                "priority": proposed_priority,
                "expire_time": time.time() + 5.0
            }
            
        # 3. Schedule on the Command Bus
        tx_id = f"tx_cmd_{uuid.uuid4().hex[:6]}"
        controlling_dev, route_mode = self.device_manager.get_controlling_device(target)
        dev_info = self.device_manager.fleet.get(controlling_dev)
        base_latency = dev_info.get("latency_ms", 20.0) if dev_info else 20.0
        
        self.command_bus.send_command(tx_id, payload, controlling_dev, base_latency)
        return True, f"Command submitted on bus to {controlling_dev} (tx_id={tx_id}, route={route_mode})."

    def _execute_routed_command(self, payload: Dict[str, Any], target_device: str) -> Tuple[bool, str]:
        """
        Invokes the underlying command router to update state manager and write physical interfaces.
        """
        # Retrieve mapped variables for router compatibility
        target_breaker = payload.get("target")
        route_table = self.command_router.routing_table.get(target_breaker)
        if not route_table:
            return False, f"Breaker {target_breaker} routing path not found."
            
        # Call command router directly
        success, reason = self.command_router.route_command(payload)
        
        # Feed back target telemetry representation to synchronization engine
        if success:
            self.sync_engine.record_telemetry_state(
                self.sync_engine.tick_counter,
                target_device,
                self.state_manager.relays[target_breaker]
            )
            # Replicate state to standby backups
            fallback_dev = self.sync_engine.failover_pairs.get(target_device)
            if fallback_dev:
                self.sync_engine.replicate_state(
                    target_device,
                    fallback_dev,
                    self.state_manager.relays[target_breaker]
                )
                
        return success, reason

    def _prune_locks(self, now: float):
        for target, lock in list(self.breaker_locks.items()):
            if now >= lock["expire_time"]:
                self.breaker_locks.pop(target, None)

    def _log_conflict(self, breaker: str, proposed_src: str, proposed_pri: int, retaining_src: str, retaining_pri: int, action: str):
        conflict_entry = {
            "timestamp": int(time.time() * 1000),
            "breaker": breaker,
            "proposed_source": proposed_src,
            "proposed_priority": proposed_pri,
            "retaining_source": retaining_src,
            "retaining_priority": retaining_pri,
            "action": action
        }
        self.conflicts.append(conflict_entry)
        if len(self.conflicts) > 30:
            self.conflicts.pop(0)

    def get_orchestration_telemetry(self) -> Dict[str, Any]:
        """
        Telemetry overview for hardware/orchestration topic.
        """
        return {
            "timestamp": int(time.time() * 1000),
            "active_locks": {k: {"source": v["source"], "priority": v["priority"]} for k, v in self.breaker_locks.items()},
            "orchestrator_status": "NOMINAL" if not self.conflicts else "CONFLICT_ALERT",
            "active_plans_count": len(self.relay_planner.active_plans)
        }

    def get_conflicts_telemetry(self) -> Dict[str, Any]:
        """
        Telemetry representing blocked commands for hardware/orchestration_conflicts.
        """
        return {
            "timestamp": int(time.time() * 1000),
            "conflicts": self.conflicts
        }
