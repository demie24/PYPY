import copy
import logging

logger = logging.getLogger("physics_validation.adaptive_filter")

class AdaptiveTelemetryFilter:
    def __init__(self, alpha_base=0.80, trust_threshold=0.40):
        self.alpha_base = alpha_base
        self.trust_threshold = trust_threshold
        
        # Cache for previous filtered values to compute EMA statefully
        self.prev_state = None
        
        # Last Known Good (LKG) values for recovery when trust drops
        self.lkg_buses = {}
        self.lkg_lines = {}
        
    def filter(self, telemetry, trust_scores):
        """
        Applies adaptive trust-weighted smoothing and impossible-state rejection to telemetry.
        Returns:
            filtered_telemetry (dict): The cleaned telemetry copy.
            filter_actions (dict): Metadata mapping actions ('PASSED', 'SMOOTHED', 'REJECTED') taken per node.
        """
        filtered_tel = copy.deepcopy(telemetry)
        filter_actions = {}
        
        try:
            buses = filtered_tel["state"]["buses"]
            lines = filtered_tel["state"]["lines"]
            breakers = filtered_tel["state"]["breakers"]
        except KeyError as e:
            logger.error(f"Cannot filter telemetry, missing keys: {e}")
            return filtered_tel, {}
            
        # 1. Filter Bus Telemetry
        for bus_name, bus_data in buses.items():
            trust = trust_scores.get(bus_name, 1.0)
            v_raw = float(bus_data.get("voltage_pu", 1.0))
            theta_raw = float(bus_data.get("angle_rad", 0.0))
            p_raw = float(bus_data.get("P_mw", 0.0))
            q_raw = float(bus_data.get("Q_mvar", 0.0))
            
            # Retrieve previous values for EMA
            v_prev = v_raw
            theta_prev = theta_raw
            p_prev = p_raw
            q_prev = q_raw
            if self.prev_state and bus_name in self.prev_state["state"]["buses"]:
                prev_bus = self.prev_state["state"]["buses"][bus_name]
                v_prev = float(prev_bus.get("voltage_pu", v_raw))
                theta_prev = float(prev_bus.get("angle_rad", theta_raw))
                p_prev = float(prev_bus.get("P_mw", p_raw))
                q_prev = float(prev_bus.get("Q_mvar", q_raw))
                
            # Cache Last Known Good (LKG) when trust is high
            if trust >= 0.60:
                self.lkg_buses[bus_name] = {
                    "voltage_pu": v_raw,
                    "angle_rad": theta_raw,
                    "P_mw": p_raw,
                    "Q_mvar": q_raw
                }
                
            # Filter action decision
            if trust < self.trust_threshold or v_raw < 0.85 or v_raw > 1.15:
                # REJECT: Trust is too low, use LKG or default nominal values
                action = "REJECTED"
                lkg = self.lkg_buses.get(bus_name, {
                    "voltage_pu": 1.0,
                    "angle_rad": 0.0,
                    "P_mw": 0.0,
                    "Q_mvar": 0.0
                })
                v_filt = lkg["voltage_pu"]
                theta_filt = lkg["angle_rad"]
                p_filt = lkg["P_mw"]
                q_filt = lkg["Q_mvar"]
            else:
                # Smooth or Pass based on trust
                alpha = self.alpha_base * trust
                v_filt = v_prev * (1.0 - alpha) + v_raw * alpha
                theta_filt = theta_prev * (1.0 - alpha) + theta_raw * alpha
                p_filt = p_prev * (1.0 - alpha) + p_raw * alpha
                q_filt = q_prev * (1.0 - alpha) + q_raw * alpha
                
                action = "SMOOTHED" if trust < 0.90 else "PASSED"
                
            # Update telemetry values
            bus_data["voltage_pu"] = round(v_filt, 4)
            bus_data["angle_rad"] = round(theta_filt, 4)
            bus_data["P_mw"] = round(p_filt, 2)
            bus_data["Q_mvar"] = round(q_filt, 2)
            
            filter_actions[bus_name] = {
                "action": action,
                "trust_score": round(trust * 100, 1),
                "raw_voltage": round(v_raw, 4),
                "filtered_voltage": round(v_filt, 4)
            }
            
        # 2. Filter Line Telemetry
        for line_id, line_data in lines.items():
            trust = trust_scores.get(line_id, 1.0)
            breaker_status = breakers.get(line_id, "CLOSED")
            
            p_raw = float(line_data.get("P_mw", 0.0))
            q_raw = float(line_data.get("Q_mvar", 0.0))
            i_raw = float(line_data.get("current_pu", 0.0))
            i_amp_raw = float(line_data.get("current_amp", 0.0))
            
            # Retrieve previous values
            p_prev = p_raw
            q_prev = q_raw
            i_prev = i_raw
            i_amp_prev = i_amp_raw
            if self.prev_state and line_id in self.prev_state["state"]["lines"]:
                prev_line = self.prev_state["state"]["lines"][line_id]
                p_prev = float(prev_line.get("P_mw", p_raw))
                q_prev = float(prev_line.get("Q_mvar", q_raw))
                i_prev = float(prev_line.get("current_pu", i_raw))
                i_amp_prev = float(prev_line.get("current_amp", i_amp_raw))
                
            # Cache LKG when trust is high
            if trust >= 0.60:
                self.lkg_lines[line_id] = {
                    "P_mw": p_raw,
                    "Q_mvar": q_raw,
                    "current_pu": i_raw,
                    "current_amp": i_amp_raw
                }
                
            # Filter action decision
            if breaker_status == "OPEN":
                # Force zero flows if breaker is OPEN (physical validation correction)
                action = "REJECTED"
                p_filt = 0.0
                q_filt = 0.0
                i_filt = 0.0
                i_amp_filt = 0.0
            elif trust < self.trust_threshold:
                action = "REJECTED"
                lkg = self.lkg_lines.get(line_id, {
                    "P_mw": 0.0,
                    "Q_mvar": 0.0,
                    "current_pu": 0.0,
                    "current_amp": 0.0
                })
                p_filt = lkg["P_mw"]
                q_filt = lkg["Q_mvar"]
                i_filt = lkg["current_pu"]
                i_amp_filt = lkg["current_amp"]
            else:
                alpha = self.alpha_base * trust
                p_filt = p_prev * (1.0 - alpha) + p_raw * alpha
                q_filt = q_prev * (1.0 - alpha) + q_raw * alpha
                i_filt = i_prev * (1.0 - alpha) + i_raw * alpha
                i_amp_filt = i_amp_prev * (1.0 - alpha) + i_amp_raw * alpha
                
                action = "SMOOTHED" if trust < 0.90 else "PASSED"
                
            line_data["P_mw"] = round(p_filt, 2)
            line_data["Q_mvar"] = round(q_filt, 2)
            line_data["current_pu"] = round(i_filt, 4)
            line_data["current_amp"] = round(i_amp_filt, 2)
            
            filter_actions[line_id] = {
                "action": action,
                "trust_score": round(trust * 100, 1),
                "raw_flow_mw": round(p_raw, 2),
                "filtered_flow_mw": round(p_filt, 2)
            }
            
        # Store state for next cycle
        self.prev_state = filtered_tel
        
        return filtered_tel, filter_actions
