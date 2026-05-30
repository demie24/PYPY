import unittest
import sys
import os
import time

# Adjust path to import from core/hardware
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

from core.hardware.hardware_state_manager import HardwareStateManager
from core.hardware.virtual_esp32 import VirtualESP32
from core.hardware.virtual_plc import VirtualPLC
from core.hardware.virtual_sensor_faults import VirtualSensorFaults
from core.hardware.virtual_relay_faults import VirtualRelayFaults
from core.hardware.hardware_fault_orchestrator import HardwareFaultOrchestrator

class TestHardwareFaultOrchestrator(unittest.TestCase):
    def setUp(self):
        self.mgr = HardwareStateManager()
        self.relay = VirtualRelayFaults(self.mgr)
        self.esp = VirtualESP32(self.mgr, self.relay)
        self.plc = VirtualPLC(self.mgr, self.relay)
        self.sensor = VirtualSensorFaults(self.mgr)
        self.orch = HardwareFaultOrchestrator(self.mgr, self.esp, self.plc, self.sensor, self.relay)
        
    def test_fault_injection_routing(self):
        # 1. ESP32 packet drop
        self.orch.inject_fault("esp32", "packet_drop_rate", "all", 0.5)
        self.assertEqual(self.esp.packet_drop_rate, 0.5)
        
        # 2. PLC delay
        self.orch.inject_fault("plc", "write_delay", "all", 2.0)
        self.assertEqual(self.plc.write_delay_duration, 2.0)
        
        # 3. Sensor bias
        self.orch.inject_fault("sensor", "spoofing_bias", "bus_5_v", -0.1)
        self.assertEqual(self.sensor.spoofing_biases["bus_5_v"], -0.1)
        
        # 4. Relay welding
        self.orch.inject_fault("relay", "welded_contact", "L4_5", True)
        self.assertIn("L4_5", self.relay.welded_contacts)
        
    def test_clear_all_faults(self):
        self.orch.inject_fault("esp32", "packet_drop_rate", "all", 0.5)
        self.orch.inject_fault("plc", "write_delay", "all", 2.0)
        self.orch.inject_fault("sensor", "spoofing_bias", "bus_5_v", -0.1)
        self.orch.inject_fault("relay", "welded_contact", "L4_5", True)
        
        self.orch.clear_all_faults()
        
        self.assertEqual(self.esp.packet_drop_rate, 0.0)
        self.assertEqual(self.plc.write_delay_duration, 0.0)
        self.assertEqual(len(self.sensor.spoofing_biases), 0)
        self.assertEqual(len(self.relay.welded_contacts), 0)
        self.assertEqual(self.orch.severity_score, 0.0)
        self.assertEqual(len(self.orch.anomalies_log), 1) # Contains RESET_ALL
        
    def test_anomaly_scanning_and_severity_score(self):
        # Inject welded relay
        self.orch.inject_fault("relay", "welded_contact", "L4_5", True)
        # Inject offline PLC
        self.orch.inject_fault("plc", "comms_failure", "all", True)
        
        anomalies = self.orch.check_anomalies()
        self.assertGreater(len(anomalies), 0)
        self.assertGreater(self.orch.severity_score, 0.0)
        
    def test_scenario_execution_dos(self):
        self.orch.launch_scenario("dos_propagation")
        self.assertEqual(self.orch.active_scenario, "dos_propagation")
        
        # Simulate time ticks
        self.orch.scenario_start_time = time.time() - 2.0
        self.orch.tick_scenario()
        self.assertFalse(self.esp.is_connected) # Step 0 triggers immediately
        
        self.orch.scenario_start_time = time.time() - 6.0
        self.orch.tick_scenario()
        self.assertEqual(self.esp.packet_drop_rate, 0.8) # Step 1 triggers after 5s
        
    def test_propagation_status_payload(self):
        self.orch.inject_fault("sensor", "spoofing_bias", "bus_5_v", -0.15)
        status = self.orch.get_propagation_status_payload() if hasattr(self.orch, "get_propagation_status_payload") else self.orch.get_fault_propagation_status()
        self.assertIn("propagation_paths", status)
        self.assertGreater(len(status["propagation_paths"]), 0)
        self.assertEqual(status["propagation_paths"][0]["source"], "sensor_interface")

if __name__ == "__main__":
    unittest.main()
