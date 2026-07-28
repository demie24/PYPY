import sys
import json
import time
import logging
from typing import Dict, List, Any
import paho.mqtt.client as mqtt
from core.digital_twin.grid_topology import GridTopology
from core.digital_twin.physics import GridPhysicsEngine
from core.digital_twin.telemetry import ACTelemetryPipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Sprint4Verification")

class TelemetryVerifier:
    def __init__(self, broker: str = "mqtt", port: int = 1883):
        self.broker = broker
        self.port = port
        self.client = mqtt.Client(client_id="sprint4_verifier_node")
        
        # In-memory storage for captured messages
        self.bus_messages: List[Dict[str, Any]] = []
        self.line_messages: List[Dict[str, Any]] = []
        self.gen_messages: List[Dict[str, Any]] = []
        
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def on_connect(self, client, userdata, flags, rc):
        logger.info(f"Verifier connected to broker with result code {rc}")
        # Subscribe to all new hierarchical topics
        client.subscribe("pypy/grid/bus/+/metrics")
        client.subscribe("pypy/grid/line/+/flow")
        client.subscribe("pypy/grid/gen/+/status")

    def on_message(self, client, userdata, msg):
        topic = msg.topic
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            if "pypy/grid/bus" in topic:
                self.bus_messages.append(payload)
            elif "pypy/grid/line" in topic:
                self.line_messages.append(payload)
            elif "pypy/grid/gen" in topic:
                self.gen_messages.append(payload)
        except Exception as e:
            logger.error(f"Error parsing message on {topic}: {e}")

    def run_verification(self):
        # 1. Connect to broker
        try:
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            sys.exit(1)

        # Wait to establish subscription
        time.sleep(1.0)

        # 2. Initialize Digital Twin & Solve
        logger.info("Initializing grid model and executing power flow...")
        topo = GridTopology()
        engine = GridPhysicsEngine(topo)
        
        breakers = {line["id"]: "CLOSED" for line in topo.lines}
        active_loads = {bus_idx: {"P": load["P_nom"], "Q": load["Q_nom"]} for bus_idx, load in topo.loads.items()}
        generator_P = {bus_idx: gen["P_nom"] for bus_idx, gen in topo.generators.items()}
        generator_Q = {bus_idx: gen["Q_nom"] for bus_idx, gen in topo.generators.items()}
        generators_online = {bus_idx: True for bus_idx in topo.generators.keys()}

        V, theta, P, Q, line_flows = engine.solve(
            breakers, active_loads, generator_P, generator_Q, generators_online
        )
        
        # 3. Serialize and Publish using the pipeline
        logger.info("Publishing AC telemetry sweep to MQTT...")
        pipeline = ACTelemetryPipeline()
        pipeline.serialize_and_publish(
            self.client, V, theta, P, Q, line_flows, engine.solver.net, breakers
        )

        # 4. Wait for messages to arrive over the broker
        logger.info("Waiting for MQTT message loops to capture payloads...")
        time.sleep(2.0)
        self.client.loop_stop()
        self.client.disconnect()

        # 5. Evaluate captured messages
        logger.info("Evaluating captured MQTT payloads...")
        
        # Check Bus Telemetry
        if not self.bus_messages:
            logger.error("Fail: No Bus telemetry messages captured.")
            sys.exit(1)
        
        sample_bus = self.bus_messages[0]
        logger.info(f"Captured {len(self.bus_messages)} bus messages. Sample: {sample_bus}")
        bus_keys = ["timestamp", "bus_id", "voltage_magnitude", "voltage_angle", "active_power", "reactive_power"]
        for key in bus_keys:
            assert key in sample_bus, f"Bus key '{key}' missing"
        
        # Check Line Telemetry
        if not self.line_messages:
            logger.error("Fail: No Line telemetry messages captured.")
            sys.exit(1)
            
        sample_line = self.line_messages[0]
        logger.info(f"Captured {len(self.line_messages)} line/transformer messages. Sample: {sample_line}")
        line_keys = ["timestamp", "line_id", "from_bus", "to_bus", "active_power_flow", "reactive_power_flow", "loading_percent"]
        for key in line_keys:
            assert key in sample_line, f"Line key '{key}' missing"

        # Check Generator Telemetry
        if not self.gen_messages:
            logger.error("Fail: No Generator telemetry messages captured.")
            sys.exit(1)
            
        sample_gen = self.gen_messages[0]
        logger.info(f"Captured {len(self.gen_messages)} generator messages. Sample: {sample_gen}")
        gen_keys = ["timestamp", "generator_id", "bus_id", "active_power_output", "reactive_power_output", "voltage_setpoint"]
        for key in gen_keys:
            assert key in sample_gen, f"Generator key '{key}' missing"

        logger.info("=========================================")
        logger.info("Telemetry MQTT structures: VALIDATED")
        logger.info("P, Q, V, theta payload fields: CORRECT")
        logger.info("Sprint 4 Verification Complete: SUCCESS!")
        logger.info("=========================================")

if __name__ == "__main__":
    verifier = TelemetryVerifier()
    verifier.run_verification()
