import logging
from typing import Dict, Any, List

logger = logging.getLogger("self_healing.blackstart_engine")

class BlackstartEngine:
    """
    Manages progressive blackstart recovery sequencing after total grid collapse.
    Coordinates sequential generator synchronization and controlled bus energization.
    """
    def __init__(self):
        # FSM state: COLLAPSED, START_MAIN_GEN, ENERGIZE_PATH_1, ENERGIZE_PATH_2, SYNC_GEN_3, ENERGIZE_PATH_3, SYNC_GEN_2, LOAD_RESTORATION, COMPLETE
        self.state = "COMPLETE"
        self.step_counter = 0

    def evaluate_blackstart(self, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Monitors grid voltages to detect blackouts and suggests sequential blackstart commands.
        """
        if not telemetry:
            return {
                "active_blackstart": False,
                "blackstart_state": self.state,
                "step_description": "Waiting for telemetry",
                "recommended_command": None,
                "progress_percentage": 100.0
            }

        state_data = telemetry.get("state", {})
        buses = state_data.get("buses", {})
        breakers = state_data.get("breakers", {})

        # 1. Detect total collapse (All load and generator voltages < 0.20 p.u.)
        total_voltages = [buses.get(b, {}).get("voltage_pu", 1.0) for b in buses.keys()]
        is_collapsed = len(total_voltages) > 0 and all(v < 0.20 for v in total_voltages)

        if is_collapsed and self.state == "COMPLETE":
            self.state = "COLLAPSED"
            self.step_counter = 0
            logger.warning("Total grid collapse detected! Entering Blackstart COLLAPSED mode.")

        if not is_collapsed and self.state != "COMPLETE" and all(buses.get(b, {}).get("voltage_pu", 0.0) > 0.85 for b in ["Bus_1", "Bus_2", "Bus_3"]):
            # Grid has fully recovered
            self.state = "COMPLETE"
            self.step_counter = 0
            logger.info("Grid fully restored. Blackstart completed.")

        if self.state == "COMPLETE":
            return {
                "active_blackstart": False,
                "blackstart_state": "COMPLETE",
                "step_description": "Grid fully operational. Nominal mode.",
                "recommended_command": None,
                "progress_percentage": 100.0
            }

        # Blackstart logic
        active_blackstart = True
        recommended_command = None
        step_description = ""
        progress_percentage = 0.0

        # Step 0: Collapsed -> Start blackstart generator Bus_1
        if self.state == "COLLAPSED":
            step_description = "Collapse state. Requesting blackstart-capable generator Bus_1 start."
            recommended_command = {
                "command": "START_GEN",
                "target": "Bus_1",
                "source": "BLACKSTART_ENGINE"
            }
            progress_percentage = 10.0
            # Transition on next evaluation if Bus_1 is online
            if buses.get("Bus_1", {}).get("voltage_pu", 0.0) > 0.8:
                self.state = "START_MAIN_GEN"
                self.step_counter += 1

        # Step 1: Start Main Gen -> Energize Bus_4 (close L1_4)
        elif self.state == "START_MAIN_GEN":
            step_description = "Bus_1 online. Energizing Bus_4 via line L1_4 breaker."
            recommended_command = {
                "command": "CLOSE",
                "target": "L1_4",
                "source": "BLACKSTART_ENGINE"
            }
            progress_percentage = 25.0
            if breakers.get("L1_4", "OPEN") == "CLOSED":
                self.state = "ENERGIZE_PATH_1"
                self.step_counter += 1

        # Step 2: Energize Path 1 -> Energize Bus_9 (close L4_9)
        elif self.state == "ENERGIZE_PATH_1":
            step_description = "Bus_4 energized. Routing path to Bus_9 via L4_9."
            recommended_command = {
                "command": "CLOSE",
                "target": "L4_9",
                "source": "BLACKSTART_ENGINE"
            }
            progress_percentage = 40.0
            if breakers.get("L4_9", "OPEN") == "CLOSED":
                self.state = "ENERGIZE_PATH_2"
                self.step_counter += 1

        # Step 3: Energize Path 2 -> Sync generator Bus_3 (connected to Bus_9 via L3_9)
        elif self.state == "ENERGIZE_PATH_2":
            # We need to make sure L3_9 is closed to reach Bus_3 generator
            if breakers.get("L3_9", "OPEN") == "OPEN":
                step_description = "Bus_9 energized. Closing line L3_9 breaker to reach generator Bus_3."
                recommended_command = {
                    "command": "CLOSE",
                    "target": "L3_9",
                    "source": "BLACKSTART_ENGINE"
                }
            else:
                step_description = "Generator Bus_3 path connected. Synchronizing and starting Bus_3."
                recommended_command = {
                    "command": "START_GEN",
                    "target": "Bus_3",
                    "source": "BLACKSTART_ENGINE"
                }
                if buses.get("Bus_3", {}).get("voltage_pu", 0.0) > 0.8:
                    self.state = "SYNC_GEN_3"
                    self.step_counter += 1
            progress_percentage = 55.0

        # Step 4: Sync Gen 3 -> Energize path to Bus_2 via Bus_4 -> Bus_5 -> Bus_6 -> Bus_7
        elif self.state == "SYNC_GEN_3":
            # Close L4_5 first
            if breakers.get("L4_5", "OPEN") == "OPEN":
                step_description = "Generator Bus_3 online. Closing L4_5 to energize Bus_5."
                recommended_command = {
                    "command": "CLOSE",
                    "target": "L4_5",
                    "source": "BLACKSTART_ENGINE"
                }
            # Close L5_6
            elif breakers.get("L5_6", "OPEN") == "OPEN":
                step_description = "Bus_5 energized. Closing L5_6 to energize Bus_6."
                recommended_command = {
                    "command": "CLOSE",
                    "target": "L5_6",
                    "source": "BLACKSTART_ENGINE"
                }
            # Close L6_7
            elif breakers.get("L6_7", "OPEN") == "OPEN":
                step_description = "Bus_6 energized. Closing L6_7 to energize Bus_7."
                recommended_command = {
                    "command": "CLOSE",
                    "target": "L6_7",
                    "source": "BLACKSTART_ENGINE"
                }
            # Close L2_7 to reach Bus_2 generator
            elif breakers.get("L2_7", "OPEN") == "OPEN":
                step_description = "Bus_7 energized. Closing L2_7 to connect Bus_2 generator."
                recommended_command = {
                    "command": "CLOSE",
                    "target": "L2_7",
                    "source": "BLACKSTART_ENGINE"
                }
            else:
                step_description = "Path to Bus_2 complete. Starting and synchronizing generator Bus_2."
                recommended_command = {
                    "command": "START_GEN",
                    "target": "Bus_2",
                    "source": "BLACKSTART_ENGINE"
                }
                if buses.get("Bus_2", {}).get("voltage_pu", 0.0) > 0.8:
                    self.state = "SYNC_GEN_2"
                    self.step_counter += 1
            progress_percentage = 75.0

        # Step 5: Sync Gen 2 -> Restore remaining load ties and connections
        elif self.state == "SYNC_GEN_2":
            # Close L7_8 to restore remaining loads (Normally open tie, but useful for full grid blackstart)
            if breakers.get("L7_8", "OPEN") == "OPEN":
                step_description = "All generators synchronized. Closing tie breaker L7_8 to complete loop."
                recommended_command = {
                    "command": "CLOSE",
                    "target": "L7_8",
                    "source": "BLACKSTART_ENGINE"
                }
            elif breakers.get("L8_9", "OPEN") == "OPEN":
                step_description = "Closing L8_9 to restore full load loop mesh."
                recommended_command = {
                    "command": "CLOSE",
                    "target": "L8_9",
                    "source": "BLACKSTART_ENGINE"
                }
            else:
                self.state = "LOAD_RESTORATION"
                self.step_counter += 1
            progress_percentage = 90.0

        elif self.state == "LOAD_RESTORATION":
            step_description = "Load restoration completed. Finalizing sync checks."
            self.state = "COMPLETE"
            progress_percentage = 100.0

        return {
            "active_blackstart": active_blackstart,
            "blackstart_state": self.state,
            "step_description": step_description,
            "recommended_command": recommended_command,
            "progress_percentage": progress_percentage
        }

    def reset(self):
        self.state = "COMPLETE"
        self.step_counter = 0
