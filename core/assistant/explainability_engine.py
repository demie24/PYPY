import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("assistant.explainability")

class ExplainabilityEngine:
    def __init__(self):
        pass

    def explain_isolation(self, target: str, grid_state: Dict[str, Any]) -> str:
        """Explains why a specific bus, line, or breaker was isolated or quarantined."""
        normalized = target.replace(" ", "_").capitalize()
        if normalized.startswith("Bus") and not normalized.startswith("Bus_"):
            normalized = normalized.replace("Bus", "Bus_")
        elif normalized.startswith("L") and "_" not in normalized and len(normalized) == 3:
            normalized = f"L{normalized[1]}_{normalized[2]}"

        # Extract states
        defense = grid_state.get("defense", {})
        trust_scores = grid_state.get("trust_scores", {})
        telemetry = grid_state.get("telemetry", {})
        
        # Check if quarantined or lockdown targets
        lockdown_targets = defense.get("breaker_lockdown_targets", [])
        strategies = defense.get("strategies", [])
        
        # Gather trust
        bus_trust = trust_scores.get("bus_trust", {})
        line_trust = trust_scores.get("line_trust", {})
        
        score = None
        target_type = " Nod"
        if normalized.startswith("Bus_"):
            score = bus_trust.get(normalized, 100.0)
            target_type = "Bas"
        elif normalized.startswith("L"):
            score = line_trust.get(normalized, 100.0)
            target_type = "Talian/Breaker"

        # Check if connected to a quarantined bus
        is_quarantined = normalized in lockdown_targets
        for action in defense.get("recommended_defense_actions", []):
            if action.get("target") == normalized and action.get("action") == "QUARANTINE_BREAKER":
                is_quarantined = True

        reasons = []
        if score is not None and score < 100.0:
            reasons.append(f"kebolehpercayaan (trust score) {target_type} tersebut jatuh kepada {score:.1f}%")
            
        # Check physics mismatch
        physics_val = grid_state.get("physics_val", {})
        kcl_mismatches = physics_val.get("kcl_mismatches", {})
        kvl_violations = physics_val.get("violations", [])
        
        if normalized in kcl_mismatches:
            reasons.append(f"ralat Hukum Arus Kirchhoff (KCL) dikesan sebanyak {kcl_mismatches[normalized]:.2f} MW")
        
        # Check active alerts
        attack_status = telemetry.get("attack_status", {})
        compromised = attack_status.get("compromised_nodes", {})
        if normalized in compromised:
            reasons.append("dikesan kompromi aktif di bawah pencerobohan siber")
            
        alerts = grid_state.get("alerts", [])
        for a in alerts:
            if a.get("suspect_node") == normalized:
                reasons.append(f"siren amaran siber mendapati aktiviti '{a.get('type')}'")

        if reasons:
            explanation = (
                f"Sistem mengasingkan/mengkuarantin {target_type} [{normalized}] kerana: "
                f"{', dan '.join(reasons)}. "
                "Tindakan pengasingan automatik ini dilaksanakan oleh Cybersecurity Defense Layer bagi menyelamatkan grid."
            )
            return explanation
            
        # Fallback if no specific data
        if is_quarantined:
            return f"Talian/Breaker [{normalized}] diletakkan di bawah kuarantin keselamatan berikutan arahan pertahanan Layer 8."
            
        return f"Tiada rekod pengasingan aktif atau kecacatan dikesan bagi [{normalized}]. Status nominal."

    def explain_blocked_restoration(self, grid_state: Dict[str, Any]) -> str:
        """Explains why self-healing or FLISR recovery actions are blocked or locked down."""
        defense = grid_state.get("defense", {})
        trust_scores = grid_state.get("trust_scores", {})
        recovery_state = grid_state.get("l6_recovery", {})
        
        escalation_level = defense.get("escalation_level", "ADVISORY")
        lockdown_active = defense.get("restoration_lockdown_active", False)
        
        reasons = []
        
        # 1. Check restoration lockdown from defense
        if lockdown_active:
            reasons.append(f"Restoration Lockdown aktif di bawah tahap kecemasan '{escalation_level}'")
            
        # 2. Check critical nodes trust
        bus_trust = trust_scores.get("bus_trust", {})
        for bus in ["Bus_5", "Bus_8"]:
            score = bus_trust.get(bus, 100.0)
            if score < 60.0:
                reasons.append(f"nod kritikal [{bus}] (Hospital/Industri) terjejas dengan trust score rendah {score:.1f}%")
                
        # 3. Check cooldown interlocks
        cooldown_breakers = recovery_state.get("cooldown_active_breakers", [])
        if cooldown_breakers:
            reasons.append(f"breaker {', '.join(cooldown_breakers)} berada di bawah tempoh bertenang (switching cooldown 30s)")

        # 4. Check operator overrides
        operator_mode = grid_state.get("operator_mode", "AUTO")
        if operator_mode in ["MANUAL", "ADVISORY"]:
            reasons.append(f"mod operasi operator ditetapkan kepada '{operator_mode}' (memerlukan kelulusan manual)")

        if reasons:
            return (
                "Langkah pemulihan grid (FLISR/RL Restoration) disekat kerana: "
                f"{'; '.join(reasons)}. "
                "Sila atasi isu integriti data atau tunggu cooldown selesai sebelum mencuba semula."
            )
            
        return "Pemulihan grid berada dalam keadaan sedia. Tiada sekatan pemulihan aktif dikesan."

    def explain_trust_reduction(self, target: str, grid_state: Dict[str, Any]) -> str:
        """Explains why trust score for a node or asset degraded."""
        normalized = target.replace(" ", "_").capitalize()
        if normalized.startswith("Bus") and not normalized.startswith("Bus_"):
            normalized = normalized.replace("Bus", "Bus_")
        elif normalized.startswith("L") and "_" not in normalized and len(normalized) == 3:
            normalized = f"L{normalized[1]}_{normalized[2]}"

        trust_scores = grid_state.get("trust_scores", {})
        physics_val = grid_state.get("physics_val", {})
        telemetry = grid_state.get("telemetry", {})
        
        bus_trust = trust_scores.get("bus_trust", {})
        line_trust = trust_scores.get("line_trust", {})
        
        score = bus_trust.get(normalized) if normalized.startswith("Bus_") else line_trust.get(normalized)
        
        if score is None:
            return f"Tiada rekod kebolehpercayaan (trust score) ditemui untuk [{normalized}]."

        reasons = []
        
        # Physics mismatch KCL/KVL
        kcl_mismatches = physics_val.get("kcl_mismatches", {})
        if normalized in kcl_mismatches:
            reasons.append(f"ralat Kirchhoff Current Law (KCL) sebanyak {kcl_mismatches[normalized]:.2f} MW dikesan")
            
        violations = physics_val.get("violations", [])
        for v in violations:
            if normalized in v:
                reasons.append(f"pelanggaran fizik grid dikesan: '{v}'")

        # Telemetry rolling variance (White noise / packet tampering)
        tel_variance = telemetry.get("state_variance", {})
        if normalized in tel_variance and tel_variance[normalized] > 2.0:
            reasons.append(f"varians isyarat tinggi ({tel_variance[normalized]:.2f}) mencadangkan gangguan data")
            
        # Cyber attacks
        alerts = grid_state.get("alerts", [])
        for a in alerts:
            if a.get("suspect_node") == normalized:
                reasons.append(f"isyarat amaran pencerobohan siber aktif: '{a.get('type')}'")

        if reasons:
            return (
                f"Kebolehpercayaan [{normalized}] dikurangkan kepada {score:.1f}% kerana: "
                f"{', dan '.join(reasons)}."
            )
            
        return f"Kebolehpercayaan [{normalized}] berada pada 100.0% nominal. Tiada kecacatan dikesan."

    def explain_rejected_recovery(self, grid_state: Dict[str, Any]) -> str:
        """Explains why the orchestrator or self-healing rejected a recovery proposal."""
        defense = grid_state.get("defense", {})
        trust_scores = grid_state.get("trust_scores", {})
        
        reasons = []
        
        # Check consensus score
        consensus_score = grid_state.get("consensus_score", 1.0)
        consensus_state = grid_state.get("consensus_state", "APPROVED")
        if consensus_state != "APPROVED" or consensus_score < 0.70:
            reasons.append(f"skor konsensus multi-agent ({consensus_score:.2f}) berada di bawah paras kelulusan 0.70")
            
        # Check if targeted compromised zones
        active_incident_count = len(defense.get("active_incidents", []))
        if active_incident_count > 0:
            reasons.append(f"terdapat {active_incident_count} insiden siber aktif sedang ditangani")

        if reasons:
            return (
                "Pelan pemulihan dicadangkan telah ditolak (REJECTED) kerana: "
                f"{', dan '.join(reasons)}. "
                "Orchestrator memerlukan pengesahan manual operator SCADA demi keselamatan fizikal grid."
            )
            
        return "Proposal pemulihan sedia diproses. Tiada alasan penolakan dikesan."
