import json
import time
import logging
from typing import Dict, Any

logger = logging.getLogger("digital_twin.telemetry")

def safe_get(df, idx, col, default=0.0):
    if df is not None and not df.empty and idx in df.index:
        try:
            return float(df.loc[idx, col])
        except Exception:
            pass
    return default

class ACTelemetryPipeline:
    def __init__(self):
        pass

    def serialize_and_publish(self, client, V, theta, P, Q, line_flows, net, breakers, timestamp=None):
        """
        Serializes solver output to individual AC telemetry payloads and publishes to MQTT.
        """
        if timestamp is None:
            timestamp = int(time.time() * 1000)

        # 1. Bus Telemetry
        for i in range(len(net.bus)):
            bus_id = int(i)
            # Active/reactive powers are injections (positive = injection, negative = consumption)
            payload = {
                "timestamp": timestamp,
                "bus_id": bus_id,
                "voltage_magnitude": round(float(V[i]) if i < len(V) else 1.0, 4),
                "voltage_angle": round(float(theta[i]) if i < len(theta) else 0.0, 4),
                "active_power": round(float(P[i]) * 100.0 if i < len(P) else 0.0, 2),
                "reactive_power": round(float(Q[i]) * 100.0 if i < len(Q) else 0.0, 2)
            }
            client.publish(f"pypy/grid/bus/{bus_id}/metrics", json.dumps(payload))

        # 2. Line Telemetry
        for idx in net.line.index:
            line_id = f"L_line_{idx}"
            loading = safe_get(net.res_line, idx, "loading_percent") if net.line.at[idx, "in_service"] else 0.0
            p_flow = 0.0
            q_flow = 0.0
            if line_id in line_flows:
                p_flow = line_flows[line_id].get("P_flow", 0.0)
                q_flow = line_flows[line_id].get("Q_flow", 0.0)
            payload = {
                "timestamp": timestamp,
                "line_id": line_id,
                "from_bus": int(net.line.at[idx, "from_bus"]),
                "to_bus": int(net.line.at[idx, "to_bus"]),
                "active_power_flow": round(float(p_flow) * 100.0, 2),
                "reactive_power_flow": round(float(q_flow) * 100.0, 2),
                "loading_percent": round(loading, 2)
            }
            client.publish(f"pypy/grid/line/{line_id}/flow", json.dumps(payload))

        # 3. Transformer Telemetry (Mapped under line topics for structural continuity)
        for idx in net.trafo.index:
            trafo_id = f"L_trafo_{idx}"
            loading = safe_get(net.res_trafo, idx, "loading_percent") if net.trafo.at[idx, "in_service"] else 0.0
            p_flow = 0.0
            q_flow = 0.0
            if trafo_id in line_flows:
                p_flow = line_flows[trafo_id].get("P_flow", 0.0)
                q_flow = line_flows[trafo_id].get("Q_flow", 0.0)
            payload = {
                "timestamp": timestamp,
                "line_id": trafo_id,
                "from_bus": int(net.trafo.at[idx, "hv_bus"]),
                "to_bus": int(net.trafo.at[idx, "lv_bus"]),
                "active_power_flow": round(float(p_flow) * 100.0, 2),
                "reactive_power_flow": round(float(q_flow) * 100.0, 2),
                "loading_percent": round(loading, 2)
            }
            client.publish(f"pypy/grid/line/{trafo_id}/flow", json.dumps(payload))

        # 4. Generator Telemetry
        # PV generators
        for idx in net.gen.index:
            gen_id = int(idx)
            bus_id = int(net.gen.at[idx, "bus"])
            p_out = safe_get(net.res_gen, idx, "p_mw") if net.gen.at[idx, "in_service"] else 0.0
            q_out = safe_get(net.res_gen, idx, "q_mvar") if net.gen.at[idx, "in_service"] else 0.0
            payload = {
                "timestamp": timestamp,
                "generator_id": gen_id,
                "bus_id": bus_id,
                "active_power_output": round(p_out, 2),
                "reactive_power_output": round(q_out, 2),
                "voltage_setpoint": round(float(net.gen.at[idx, "vm_pu"]), 4)
            }
            client.publish(f"pypy/grid/gen/{gen_id}/status", json.dumps(payload))

        # Slack Generator (external grid)
        for idx in net.ext_grid.index:
            slack_id = len(net.gen) + int(idx)
            bus_id = int(net.ext_grid.at[idx, "bus"])
            p_out = safe_get(net.res_ext_grid, idx, "p_mw") if net.ext_grid.at[idx, "in_service"] else 0.0
            q_out = safe_get(net.res_ext_grid, idx, "q_mvar") if net.ext_grid.at[idx, "in_service"] else 0.0
            v_set = float(net.ext_grid.at[idx, "vm_pu"]) if hasattr(net.ext_grid, 'vm_pu') else 1.0
            payload = {
                "timestamp": timestamp,
                "generator_id": slack_id,
                "bus_id": bus_id,
                "active_power_output": round(p_out, 2),
                "reactive_power_output": round(q_out, 2),
                "voltage_setpoint": round(v_set, 4)
            }
            client.publish(f"pypy/grid/gen/{slack_id}/status", json.dumps(payload))
            
        logger.debug(f"Published complete AC telemetry sweep at timestamp {timestamp}")
