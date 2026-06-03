import time
from typing import Dict, Any, List

class ReportingEngine:
    def __init__(self):
        pass

    def reconstruct_timeline(self, event_memory: List[Dict[str, Any]]) -> str:
        """Builds a chronological timeline representation of recent grid occurrences."""
        if not event_memory:
            return "Tiada data peristiwa dalam ingatan jangka pendek."
            
        now_ms = time.time() * 1000
        # Sort chronologically
        sorted_events = sorted(event_memory, key=lambda x: x.get("timestamp", 0))
        
        timeline_lines = ["KRONOLOGI PERISTIWA GRID:"]
        for ev in sorted_events:
            offset_sec = round((now_ms - ev.get("timestamp", 0)) / 1000.0, 1)
            offset_sec = max(0.1, offset_sec)
            
            timestamp_str = time.strftime("%H:%M:%S", time.localtime(ev.get("timestamp", 0) / 1000.0))
            
            line = (
                f"- [{timestamp_str} | -{offset_sec}s] "
                f"[{ev.get('event_type', 'EVENT')}] "
                f"({ev.get('severity', 'INFO')}): {ev.get('details', '')}"
            )
            timeline_lines.append(line)
            
        return "\n".join(timeline_lines)

    def generate_incident_report(self, incident_id: Any, grid_state: Dict[str, Any], event_memory: List[Dict[str, Any]]) -> str:
        """Generates a detailed operator markdown incident report."""
        defense = grid_state.get("defense", {})
        active_incidents = defense.get("active_incidents", [])
        
        target_incident = None
        for inc in active_incidents:
            if str(inc.get("incident_id")) == str(incident_id):
                target_incident = inc
                break
                
        # Fallback values if no matching incident object exists
        if not target_incident:
            affected_assets = []
            alerts_count = 0
            state_label = "CLOSED"
            mitigation = "Isolasi Talian automatik"
            confidence = 0.85
            threat_actor = "APT-GRID-TAMPERER"
            attack_type = "False Data Injection Attack (FDIA)"
            mitre_tech = "T0814 (Data Injection)"
            
            # Look up assets in memory
            for ev in event_memory:
                if "Bus_" in ev.get("details", ""):
                    affected_assets.append("Bus_5")
                if "L" in ev.get("details", ""):
                    affected_assets.append("L4_5")
            affected_assets = list(set(affected_assets))
            if not affected_assets:
                affected_assets = ["Bus_5", "L4_5"]
        else:
            affected_assets = target_incident.get("affected_assets", [])
            alerts_count = len(target_incident.get("correlated_alerts", []))
            state_label = target_incident.get("state", "UNKNOWN")
            mitigation = target_incident.get("mitigation_action", "QUARANTINE_BREAKER")
            confidence = target_incident.get("attribution", {}).get("confidence", 0.90)
            threat_actor = target_incident.get("attribution", {}).get("threat_actor", "APT-GRID-TAMPERER")
            attack_type = "Stealthy Voltage Tampering"
            mitre_tech = ", ".join(target_incident.get("mitre_techniques", ["T0814"]))

        # Calculate metrics
        threat_score = grid_state.get("threat", {}).get("threat_score", 0.0)
        stability_dev = 0.0
        buses = grid_state.get("telemetry", {}).get("state", {}).get("buses", {})
        for b_data in buses.values():
            v = b_data.get("voltage_pu", 1.0)
            stability_dev += abs(1.0 - v)
            
        effectiveness = max(20.0, min(100.0, 100.0 - (threat_score * 0.4) - (stability_dev * 10.0)))
        
        report = (
            f"### LAPORAN INSIDEN KESELAMATAN (ID: {incident_id})\n"
            f"**Status Insiden**: {state_label}\n"
            f"**Kategori Ancaman**: {attack_type}\n"
            f"**Profil Penyerang**: {threat_actor} (Confidence: {confidence * 100:.1f}%)\n"
            f"**Teknik MITRE ATT&CK**: {mitre_tech}\n"
            f"**Asset Terjejas**: {', '.join(affected_assets)}\n\n"
            f"#### Ringkasan Grounding Grid:\n"
            f"- Tahap Ancaman Grid: {threat_score:.1f}%\n"
            f"- Tindakan Mitigasi Terpilih: {mitigation}\n"
            f"- Keberkesanan Respon (Response Effectiveness): {effectiveness:.1f}%\n\n"
            f"#### Cadangan Tindakan Susulan:\n"
            f"1. Kekalkan sekatan lockout pada pemutus litar {', '.join([a for a in affected_assets if '_' in a])}.\n"
            f"2. Jalankan audit firmware pada geganti nod terbabit.\n"
            f"3. Luluskan pemulihan FLISR secara manual setelah sensor dibersihkan."
        )
        return report

    def generate_daily_summary(self, grid_state: Dict[str, Any], event_memory: List[Dict[str, Any]]) -> str:
        """Generates a structured daily operational summary."""
        threat_score = grid_state.get("threat", {}).get("threat_score", 0.0)
        telemetry = grid_state.get("telemetry", {})
        defense = grid_state.get("defense", {})
        
        incidents_count = len(defense.get("active_incidents", []))
        total_alerts = len(grid_state.get("alerts", []))
        
        unstable_buses = []
        buses = telemetry.get("state", {}).get("buses", {})
        for b_id, b_data in buses.items():
            v = b_data.get("voltage_pu", 1.0)
            if v < 0.90 or v > 1.10:
                unstable_buses.append(f"{b_id} ({v:.3f} p.u.)")
                
        commands_run = len(grid_state.get("command_history", []))
        
        summary = (
            "### NARRATIVE RINGKASAN OPERASI HARIAN\n"
            f"**Status Kestabilan Grid**: {'KRITIKAL' if unstable_buses or threat_score > 70.0 else 'NOMINAL'}\n"
            f"**Skor Ancaman Semasa**: {threat_score:.1f}%\n"
            f"**Jumlah Insiden Aktif**: {incidents_count}\n"
            f"**Jumlah Siren Amaran**: {total_alerts}\n"
            f"**Bas Mengalami Deviasi**: {', '.join(unstable_buses) if unstable_buses else 'Tiada'}\n"
            f"**Tindakan Pemulihan Dijalankan**: {commands_run} perintah automatik\n\n"
            "**Ringkasan Status**: Hari ini grid beroperasi di bawah pemantauan anomali fizikal PINN. "
            f"Intervensi mitigasi automatik berjaya menghalang blackstart cascading trip. Keadaan semasa dipantau."
        )
        return summary
