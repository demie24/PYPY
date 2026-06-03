import time
import logging
from typing import Dict, Any, List, Set, Optional

logger = logging.getLogger("cyber_defense.threat_correlation")

class Incident:
    """
    Data model representing a correlated, multi-stage cyber-physical grid incident.
    """
    def __init__(self, incident_id: int, start_time: float):
        self.incident_id = incident_id
        self.start_time = int(start_time * 1000)
        self.last_updated = int(start_time * 1000)
        
        self.state = "DETECT"  # DETECT, VALIDATE, CORRELATE, CLASSIFY, CONTAIN, MITIGATE, RECOVER, MONITOR, CLOSE
        self.severity = 10.0    # 0 to 100 scale
        self.affected_assets: Set[str] = set()
        self.correlated_alerts: List[Dict[str, Any]] = []
        self.events_list: List[Dict[str, Any]] = []
        
        # Security/Attribution metadata
        self.mitre_techniques: List[str] = []
        self.attribution: Dict[str, Any] = {
            "threat_actor": "UNKNOWN",
            "confidence": 0.0,
            "indicators_matched": []
        }
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "start_time": self.start_time,
            "last_updated": self.last_updated,
            "state": self.state,
            "severity": int(self.severity),
            "affected_assets": sorted(list(self.affected_assets)),
            "correlated_alerts_count": len(self.correlated_alerts),
            "events_count": len(self.events_list),
            "mitre_techniques": self.mitre_techniques,
            "attribution": self.attribution
        }

class ThreatCorrelationEngine:
    """
    Correlates heterogeneous alerts, events, physics anomalies, and trust violations
    across the digital twin into unified stateful incidents.
    """
    def __init__(self, correlation_window_seconds: float = 60.0):
        self.correlation_window = correlation_window_seconds
        self.active_incidents: Dict[int, Incident] = {}
        self.incident_id_seq = 100

    def correlate_signals(self, 
                          alerts: List[Dict[str, Any]], 
                          events: List[Dict[str, Any]], 
                          physics_val: Dict[str, Any], 
                          trust_scores: Dict[str, Any]) -> List[Incident]:
        """
        Processes incoming alerts and events to dynamically update or spawn correlated incidents.
        """
        now = time.time()
        
        # 1. Identify target assets in this tick's inputs
        alert_assets = set()
        for alert in alerts:
            target = alert.get("suspect_node") or alert.get("target")
            if target:
                alert_assets.add(target)
                
        event_assets = set()
        for event in events:
            source = event.get("source")
            if source and source not in ["SYSTEM", "FLISR", "AUTO_DEFENSE", "RESToration"]:
                event_assets.add(source)
                
        all_assets = alert_assets.union(event_assets)
        
        # Add physics anomalies and trust degradation targets
        if physics_val and physics_val.get("physics_anomaly_score", 0.0) > 30.0:
            for violation in physics_val.get("violations", []):
                # Try to extract asset name from violation message
                for bus_id in [f"Bus_{i}" for i in range(1, 10)]:
                    if bus_id in violation:
                        all_assets.add(bus_id)
                for line_id in ["L1_4", "L2_7", "L3_9", "L4_5", "L4_9", "L5_6", "L6_7", "L7_8", "L8_9"]:
                    if line_id in violation:
                        all_assets.add(line_id)

        if trust_scores:
            for category in ["bus_trust", "line_trust"]:
                scores = trust_scores.get(category, {})
                for asset, score in scores.items():
                    if score < 60.0:
                        all_assets.add(asset)
                        
        # 2. Correlate with active incidents
        incident = None
        if all_assets:
            incident = self._find_matching_incident(all_assets, now)
            
        if not incident and (alerts or events):
            # Create a new incident if new alerts or events are present
            incident = self._spawn_incident(now)
            
        if incident:
            # Update last updated timestamp
            incident.last_updated = int(now * 1000)
            
            # Incorporate new assets and alerts
            for asset in all_assets:
                incident.affected_assets.add(asset)
                
            for alert in alerts:
                if alert not in incident.correlated_alerts:
                    incident.correlated_alerts.append(alert)
                    
            for event in events:
                if event not in incident.events_list:
                    incident.events_list.append(event)
                    
            # Auto-advance to CORRELATE if we have alerts from multiple sources
            if len(incident.correlated_alerts) > 1 or len(incident.affected_assets) > 1:
                if incident.state == "DETECT":
                    incident.state = "CORRELATE"
                    
        # Prune / auto-close incidents inactive for more than 180s (3 minutes)
        expired_ids = []
        for inc_id, inc in self.active_incidents.items():
            if now - (inc.last_updated / 1000.0) > 180.0:
                expired_ids.append(inc_id)
                
        for inc_id in expired_ids:
            logger.info(f"Auto-closing inactive incident {inc_id}.")
            self.active_incidents.pop(inc_id)
            
        return list(self.active_incidents.values())

    def _find_matching_incident(self, assets: Set[str], now: float) -> Optional[Incident]:
        """
        Finds an active incident that shares assets or is within the correlation time window.
        """
        for incident in self.active_incidents.values():
            # Check for temporal overlap (updated within correlation window)
            if now - (incident.last_updated / 1000.0) < self.correlation_window:
                # Check for asset overlap or general proximity
                if incident.affected_assets.intersection(assets):
                    return incident
                    
        # Fallback: if there is any active incident that is very recent, associate with it
        for incident in self.active_incidents.values():
            if now - (incident.last_updated / 1000.0) < 15.0:
                return incident
                
        return None

    def _spawn_incident(self, now: float) -> Incident:
        self.incident_id_seq += 1
        incident = Incident(self.incident_id_seq, now)
        self.active_incidents[self.incident_id_seq] = incident
        logger.warning(f"[CORRELATOR] Spawned new incident track: {incident.incident_id}")
        return incident

    def clear(self):
        self.active_incidents.clear()
        logger.info("Threat Correlation Engine state cleared.")
