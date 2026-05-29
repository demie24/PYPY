import time
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("gateway.store")

class MemoryStore:
    def __init__(self, max_history: int = 100):
        self.max_history = max_history
        self.latest_telemetry: Optional[Dict[str, Any]] = None
        self.events: List[Dict[str, Any]] = []
        self.alerts: List[Dict[str, Any]] = []
        self.latest_config: Dict[str, Any] = {}
        self.latest_threat: Optional[Dict[str, Any]] = None
        self.latest_ai_prediction: Optional[Dict[str, Any]] = None
        self.latest_ai_forecast_multi_bus: Optional[Dict[str, Any]] = None
        self.latest_ai_threat_forecast: Optional[Dict[str, Any]] = None
        self.latest_pinn_forecast: Optional[Dict[str, Any]] = None
        self.latest_physics_validation: Optional[Dict[str, Any]] = None
        self.latest_trust_scores: Optional[Dict[str, Any]] = None
        self.latest_adaptive_filter: Optional[Dict[str, Any]] = None
        self.latest_ai_orchestrator: Optional[Dict[str, Any]] = None
        self.latest_recommended_actions: Optional[Dict[str, Any]] = None
        self.latest_pre_rl: Optional[Dict[str, Any]] = None
        self.latest_defense: Optional[Dict[str, Any]] = None
        self.latest_l6_recovery: Optional[Dict[str, Any]] = None
        self.latest_l6_adaptive_recovery: Optional[Dict[str, Any]] = None
        self.latest_l6_containment: Optional[Dict[str, Any]] = None
        self.latest_l6_degraded_mode: Optional[Dict[str, Any]] = None
        self.latest_l6_survival: Optional[Dict[str, Any]] = None
        self.latest_l6_islanding: Optional[Dict[str, Any]] = None
        self.latest_l6_blackstart: Optional[Dict[str, Any]] = None
        self.latest_l6_balancing: Optional[Dict[str, Any]] = None
        self.latest_l6_predictive_stability: Optional[Dict[str, Any]] = None
        self.latest_l6_survival_forecast: Optional[Dict[str, Any]] = None
        self.latest_l6_proactive_actions: Optional[Dict[str, Any]] = None
        self.latest_l6_self_preservation: Optional[Dict[str, Any]] = None
        self.latest_l6_agents: Optional[Dict[str, Any]] = None
        self.latest_l6_agent_consensus: Optional[Dict[str, Any]] = None
        self.latest_l6_agent_conflicts: Optional[Dict[str, Any]] = None
        self.latest_l6_distributed_state: Optional[Dict[str, Any]] = None
        self.latest_l6_agent_confidence: Optional[Dict[str, Any]] = None
        self.latest_hardware_relay: Optional[Dict[str, Any]] = None
        self.latest_hardware_gpio: Optional[Dict[str, Any]] = None
        self.latest_hardware_sensor: Optional[Dict[str, Any]] = None
        self.latest_hardware_device_health: Optional[Dict[str, Any]] = None
        self.latest_hardware_command_log: Optional[Dict[str, Any]] = None
        self.latest_hardware_faults: Optional[Dict[str, Any]] = None
        self.latest_hardware_relay_faults: Optional[Dict[str, Any]] = None
        self.latest_hardware_anomalies: Optional[List[Dict[str, Any]]] = None
        self.latest_hardware_virtual_devices: Optional[Dict[str, Any]] = None
        self.latest_hardware_spoofed_telemetry: Optional[Dict[str, Any]] = None
        self.latest_hardware_fault_propagation: Optional[Dict[str, Any]] = None
        self.latest_hardware_usb_events: Optional[Dict[str, Any]] = None
        self.latest_hardware_rogue_devices: Optional[Dict[str, Any]] = None
        self.latest_hardware_badusb: Optional[Dict[str, Any]] = None
        self.latest_hardware_intrusion_alerts: Optional[Dict[str, Any]] = None
        self.latest_hardware_device_trust: Optional[Dict[str, Any]] = None
        self.latest_hardware_attack_state: Optional[Dict[str, Any]] = None
        self.latest_hardware_attack_propagation: Optional[Dict[str, Any]] = None
        self.latest_hardware_orchestration: Optional[Dict[str, Any]] = None
        self.latest_hardware_edge_devices: Optional[Dict[str, Any]] = None
        self.latest_hardware_relay_execution: Optional[Dict[str, Any]] = None
        self.latest_hardware_distributed_bus: Optional[Dict[str, Any]] = None
        self.latest_hardware_synchronization: Optional[Dict[str, Any]] = None
        self.latest_hardware_orchestration_conflicts: Optional[Dict[str, Any]] = None
        self.latest_hardware_execution_gateway: Optional[Dict[str, Any]] = None
        self.latest_hardware_reliability: Optional[Dict[str, Any]] = None
        self.latest_hardware_safety_guard: Optional[Dict[str, Any]] = None
        self.latest_hardware_deployment_profiles: Optional[Dict[str, Any]] = None
        self.latest_hardware_telemetry_validation: Optional[Dict[str, Any]] = None
        self.latest_hardware_resilience: Optional[Dict[str, Any]] = None
        self.latest_hardware_disaster_recovery: Optional[Dict[str, Any]] = None
        self.latest_hardware_redundancy: Optional[Dict[str, Any]] = None
        self.latest_hardware_deployment_hardening: Optional[Dict[str, Any]] = None
        self.latest_hardware_large_scale_sync: Optional[Dict[str, Any]] = None
        
        # Add initial system startup event
        self.add_event({
            "timestamp": int(time.time() * 1000),
            "source": "GATEWAY",
            "event": "Gateway communication service initialized. Standing by for telemetry...",
            "severity": "INFO"
        })

    def update_telemetry(self, telemetry: Dict[str, Any]):
        self.latest_telemetry = telemetry

    def update_config(self, config: Dict[str, Any]):
        self.latest_config.update(config)

    def update_threat(self, threat: Dict[str, Any]):
        self.latest_threat = threat

    def update_ai_prediction(self, ai_pred: Dict[str, Any]):
        self.latest_ai_prediction = ai_pred

    def update_ai_forecast_multi_bus(self, ai_forecast: Dict[str, Any]):
        self.latest_ai_forecast_multi_bus = ai_forecast

    def update_ai_threat_forecast(self, ai_threat: Dict[str, Any]):
        self.latest_ai_threat_forecast = ai_threat

    def update_pinn_forecast(self, pinn_forecast: Dict[str, Any]):
        self.latest_pinn_forecast = pinn_forecast

    def update_physics_validation(self, physics_val: Dict[str, Any]):
        self.latest_physics_validation = physics_val

    def update_trust_scores(self, trust_scores: Dict[str, Any]):
        self.latest_trust_scores = trust_scores

    def update_adaptive_filter(self, adaptive_filter: Dict[str, Any]):
        self.latest_adaptive_filter = adaptive_filter

    def update_ai_orchestrator(self, ai_orchestrator: Dict[str, Any]):
        self.latest_ai_orchestrator = ai_orchestrator

    def update_recommended_actions(self, recommended_actions: Dict[str, Any]):
        self.latest_recommended_actions = recommended_actions

    def update_pre_rl(self, pre_rl: Dict[str, Any]):
        self.latest_pre_rl = pre_rl

    def update_defense(self, defense: Dict[str, Any]):
        self.latest_defense = defense

    def update_l6_recovery(self, l6_recovery: Dict[str, Any]):
        self.latest_l6_recovery = l6_recovery

    def update_l6_adaptive_recovery(self, l6_adaptive_recovery: Dict[str, Any]):
        self.latest_l6_adaptive_recovery = l6_adaptive_recovery

    def update_l6_containment(self, l6_containment: Dict[str, Any]):
        self.latest_l6_containment = l6_containment

    def update_l6_degraded_mode(self, l6_degraded_mode: Dict[str, Any]):
        self.latest_l6_degraded_mode = l6_degraded_mode

    def update_l6_survival(self, payload: Dict[str, Any]):
        self.latest_l6_survival = payload

    def update_l6_islanding(self, payload: Dict[str, Any]):
        self.latest_l6_islanding = payload

    def update_l6_blackstart(self, payload: Dict[str, Any]):
        self.latest_l6_blackstart = payload

    def update_l6_balancing(self, payload: Dict[str, Any]):
        self.latest_l6_balancing = payload

    def update_l6_predictive_stability(self, payload: Dict[str, Any]):
        self.latest_l6_predictive_stability = payload

    def update_l6_survival_forecast(self, payload: Dict[str, Any]):
        self.latest_l6_survival_forecast = payload

    def update_l6_proactive_actions(self, payload: Dict[str, Any]):
        self.latest_l6_proactive_actions = payload

    def update_l6_self_preservation(self, payload: Dict[str, Any]):
        self.latest_l6_self_preservation = payload

    def update_l6_agents(self, payload: Dict[str, Any]):
        self.latest_l6_agents = payload

    def update_l6_agent_consensus(self, payload: Dict[str, Any]):
        self.latest_l6_agent_consensus = payload

    def update_l6_agent_conflicts(self, payload: Dict[str, Any]):
        self.latest_l6_agent_conflicts = payload

    def update_l6_distributed_state(self, payload: Dict[str, Any]):
        self.latest_l6_distributed_state = payload

    def update_l6_agent_confidence(self, payload: Dict[str, Any]):
        self.latest_l6_agent_confidence = payload

    def update_hardware_relay(self, payload: Dict[str, Any]):
        self.latest_hardware_relay = payload

    def update_hardware_gpio(self, payload: Dict[str, Any]):
        self.latest_hardware_gpio = payload

    def update_hardware_sensor(self, payload: Dict[str, Any]):
        self.latest_hardware_sensor = payload

    def update_hardware_device_health(self, payload: Dict[str, Any]):
        self.latest_hardware_device_health = payload

    def update_hardware_command_log(self, payload: Dict[str, Any]):
        self.latest_hardware_command_log = payload

    def update_hardware_faults(self, payload: Dict[str, Any]):
        self.latest_hardware_faults = payload

    def update_hardware_relay_faults(self, payload: Dict[str, Any]):
        self.latest_hardware_relay_faults = payload

    def update_hardware_anomalies(self, payload: List[Dict[str, Any]]):
        self.latest_hardware_anomalies = payload

    def update_hardware_virtual_devices(self, payload: Dict[str, Any]):
        self.latest_hardware_virtual_devices = payload

    def update_hardware_spoofed_telemetry(self, payload: Dict[str, Any]):
        self.latest_hardware_spoofed_telemetry = payload

    def update_hardware_fault_propagation(self, payload: Dict[str, Any]):
        self.latest_hardware_fault_propagation = payload

    def update_hardware_usb_events(self, payload: Dict[str, Any]):
        self.latest_hardware_usb_events = payload

    def update_hardware_rogue_devices(self, payload: Dict[str, Any]):
        self.latest_hardware_rogue_devices = payload

    def update_hardware_badusb(self, payload: Dict[str, Any]):
        self.latest_hardware_badusb = payload

    def update_hardware_intrusion_alerts(self, payload: Dict[str, Any]):
        self.latest_hardware_intrusion_alerts = payload

    def update_hardware_device_trust(self, payload: Dict[str, Any]):
        self.latest_hardware_device_trust = payload

    def update_hardware_attack_state(self, payload: Dict[str, Any]):
        self.latest_hardware_attack_state = payload

    def update_hardware_attack_propagation(self, payload: Dict[str, Any]):
        self.latest_hardware_attack_propagation = payload

    def update_hardware_orchestration(self, payload: Dict[str, Any]):
        self.latest_hardware_orchestration = payload

    def update_hardware_edge_devices(self, payload: Dict[str, Any]):
        self.latest_hardware_edge_devices = payload

    def update_hardware_relay_execution(self, payload: Dict[str, Any]):
        self.latest_hardware_relay_execution = payload

    def update_hardware_distributed_bus(self, payload: Dict[str, Any]):
        self.latest_hardware_distributed_bus = payload

    def update_hardware_synchronization(self, payload: Dict[str, Any]):
        self.latest_hardware_synchronization = payload

    def update_hardware_orchestration_conflicts(self, payload: Dict[str, Any]):
        self.latest_hardware_orchestration_conflicts = payload

    def update_hardware_execution_gateway(self, payload: Dict[str, Any]):
        self.latest_hardware_execution_gateway = payload

    def update_hardware_reliability(self, payload: Dict[str, Any]):
        self.latest_hardware_reliability = payload

    def update_hardware_safety_guard(self, payload: Dict[str, Any]):
        self.latest_hardware_safety_guard = payload

    def update_hardware_deployment_profiles(self, payload: Dict[str, Any]):
        self.latest_hardware_deployment_profiles = payload

    def update_hardware_telemetry_validation(self, payload: Dict[str, Any]):
        self.latest_hardware_telemetry_validation = payload

    def update_hardware_resilience(self, payload: Dict[str, Any]):
        self.latest_hardware_resilience = payload

    def update_hardware_disaster_recovery(self, payload: Dict[str, Any]):
        self.latest_hardware_disaster_recovery = payload

    def update_hardware_redundancy(self, payload: Dict[str, Any]):
        self.latest_hardware_redundancy = payload

    def update_hardware_deployment_hardening(self, payload: Dict[str, Any]):
        self.latest_hardware_deployment_hardening = payload

    def update_hardware_large_scale_sync(self, payload: Dict[str, Any]):
        self.latest_hardware_large_scale_sync = payload


    def add_event(self, event: Dict[str, Any]):
        self.events.append(event)
        if len(self.events) > self.max_history:
            self.events.pop(0)

    def add_alert(self, alert: Dict[str, Any]):
        self.alerts.append(alert)
        if len(self.alerts) > self.max_history:
            self.alerts.pop(0)
            
    def get_bootstrap_payload(self) -> Dict[str, Any]:
        """
        Returns the initialization payload for newly connected clients.
        """
        return {
            "type": "BOOTSTRAP",
            "telemetry": self.latest_telemetry,
            "events": self.events,
            "alerts": self.alerts,
            "config": self.latest_config,
            "threat": self.latest_threat,
            "ai_prediction": self.latest_ai_prediction,
            "ai_forecast_multi_bus": self.latest_ai_forecast_multi_bus,
            "ai_threat_forecast": self.latest_ai_threat_forecast,
            "pinn_forecast": self.latest_pinn_forecast,
            "physics_validation": self.latest_physics_validation,
            "trust_scores": self.latest_trust_scores,
            "adaptive_filter": self.latest_adaptive_filter,
            "ai_orchestrator": self.latest_ai_orchestrator,
            "recommended_actions": self.latest_recommended_actions,
            "pre_rl": self.latest_pre_rl,
            "defense": self.latest_defense,
            "l6_recovery": self.latest_l6_recovery,
            "l6_adaptive_recovery": self.latest_l6_adaptive_recovery,
            "l6_containment": self.latest_l6_containment,
            "l6_degraded_mode": self.latest_l6_degraded_mode,
            "l6_survival": self.latest_l6_survival,
            "l6_islanding": self.latest_l6_islanding,
            "l6_blackstart": self.latest_l6_blackstart,
            "l6_balancing": self.latest_l6_balancing,
            "l6_predictive_stability": self.latest_l6_predictive_stability,
            "l6_survival_forecast": self.latest_l6_survival_forecast,
            "l6_proactive_actions": self.latest_l6_proactive_actions,
            "l6_self_preservation": self.latest_l6_self_preservation,
            "l6_agents": self.latest_l6_agents,
            "l6_agent_consensus": self.latest_l6_agent_consensus,
            "l6_agent_conflicts": self.latest_l6_agent_conflicts,
            "l6_distributed_state": self.latest_l6_distributed_state,
            "l6_agent_confidence": self.latest_l6_agent_confidence,
            "hardware_relay": self.latest_hardware_relay,
            "hardware_gpio": self.latest_hardware_gpio,
            "hardware_sensor": self.latest_hardware_sensor,
            "hardware_device_health": self.latest_hardware_device_health,
            "hardware_command_log": self.latest_hardware_command_log,
            "hardware_faults": self.latest_hardware_faults,
            "hardware_relay_faults": self.latest_hardware_relay_faults,
            "hardware_anomalies": self.latest_hardware_anomalies,
            "hardware_virtual_devices": self.latest_hardware_virtual_devices,
            "hardware_spoofed_telemetry": self.latest_hardware_spoofed_telemetry,
            "hardware_fault_propagation": self.latest_hardware_fault_propagation,
            "hardware_usb_events": self.latest_hardware_usb_events,
            "hardware_rogue_devices": self.latest_hardware_rogue_devices,
            "hardware_badusb": self.latest_hardware_badusb,
            "hardware_intrusion_alerts": self.latest_hardware_intrusion_alerts,
            "hardware_device_trust": self.latest_hardware_device_trust,
            "hardware_attack_state": self.latest_hardware_attack_state,
            "hardware_attack_propagation": self.latest_hardware_attack_propagation,
            "hardware_orchestration": self.latest_hardware_orchestration,
            "hardware_edge_devices": self.latest_hardware_edge_devices,
            "hardware_relay_execution": self.latest_hardware_relay_execution,
            "hardware_distributed_bus": self.latest_hardware_distributed_bus,
            "hardware_synchronization": self.latest_hardware_synchronization,
            "hardware_orchestration_conflicts": self.latest_hardware_orchestration_conflicts,
            "hardware_execution_gateway": self.latest_hardware_execution_gateway,
            "hardware_reliability": self.latest_hardware_reliability,
            "hardware_safety_guard": self.latest_hardware_safety_guard,
            "hardware_deployment_profiles": self.latest_hardware_deployment_profiles,
            "hardware_telemetry_validation": self.latest_hardware_telemetry_validation,
            "hardware_resilience": self.latest_hardware_resilience,
            "hardware_disaster_recovery": self.latest_hardware_disaster_recovery,
            "hardware_redundancy": self.latest_hardware_redundancy,
            "hardware_deployment_hardening": self.latest_hardware_deployment_hardening,
            "hardware_large_scale_sync": self.latest_hardware_large_scale_sync
        }

    def clear_alerts(self):
        self.alerts = []
        self.add_event({
            "timestamp": int(time.time() * 1000),
            "source": "GATEWAY",
            "event": "Alert history cleared by operator command.",
            "severity": "INFO"
        })

store = MemoryStore()
