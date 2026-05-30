import time
import logging
from typing import Dict, Any, List, Optional
from core.assistant.federated_memory_manager import FederatedMemoryManager
from core.assistant.distributed_consensus_engine import DistributedConsensusEngine
from core.assistant.edge_mesh_orchestrator import EdgeMeshOrchestrator
from core.assistant.swarm_anomaly_fusion_engine import SwarmAnomalyFusionEngine

logger = logging.getLogger("assistant.swarm_coordination")

class SwarmCoordinationEngine:
    def __init__(
        self,
        federated_memory: FederatedMemoryManager,
        distributed_consensus: DistributedConsensusEngine,
        edge_mesh: EdgeMeshOrchestrator,
        anomaly_fusion: SwarmAnomalyFusionEngine
    ):
        self.agent_name = "SwarmCoordinationEngine"
        self.status = "NOMINAL"
        self.federated_memory = federated_memory
        self.distributed_consensus = distributed_consensus
        self.edge_mesh = edge_mesh
        self.anomaly_fusion = anomaly_fusion
        
        self.coordination_chain: List[str] = []
        self.coordination_logs: List[str] = []
        self.simulation_mode: Optional[str] = None
        self.last_coordination_time = time.time()
        self.cooldown_period = 2.0  # coordination cooldown to prevent synchronization storm loops

    def coordinate_swarm(
        self,
        telemetry: Dict[str, Any],
        sync_states: Dict[str, Any],
        edge_summary: Dict[str, Any],
        relay_summary: Dict[str, Any],
        security_summary: Dict[str, Any],
        active_attacks: List[str]
    ) -> Dict[str, Any]:
        """Tics all swarm sub-components and coordinates federated actions, consensus voting, and topology awareness."""
        self.coordination_logs.clear()
        self.coordination_chain.clear()

        current_time = time.time()

        # Extract underlying lists of anomalies/alerts
        telemetry_anoms = []
        # Construct simple anomaly list from voltage/load telemetry
        for k, v in telemetry.items():
            if isinstance(v, (int, float)):
                if k.startswith("bus_") and (v < 0.90 or v > 1.10):
                    telemetry_anoms.append({"variable": k, "value": v, "severity": "HIGH", "confidence": 0.85, "description": f"Voltan {k} terkeluar."})
                elif k.startswith("line_") and v > 100.0:
                    telemetry_anoms.append({"variable": k, "value": v, "severity": "CRITICAL", "confidence": 0.95, "description": f"Overload pada {k}."})

        relay_anoms = relay_summary.get("anomalies", [])
        security_alerts = security_summary.get("threat_alerts", [])
        edge_anoms = edge_summary.get("anomalies", {})

        # 1. Run Swarm Anomaly Fusion
        fusion_summary = self.anomaly_fusion.fuse_anomalies(
            telemetry_anoms,
            relay_anoms,
            security_alerts,
            edge_anoms,
            simulation_mode=self.simulation_mode
        )

        # 2. Run Edge Mesh Orchestration
        mesh_summary = self.edge_mesh.tick_mesh_orchestrator(
            edge_summary,
            telemetry,
            simulation_mode=self.simulation_mode
        )

        # 3. Simulate Swarm Delegation Chain & Prevent Escalation Loops
        # We model routing actions from Mesh -> Memory Sync -> Anomaly Fusion -> Consensus Vote
        depth = 0
        self.coordination_chain.append("EdgeMeshOrchestrator")
        
        # Determine if we initiate swarm routing
        if fusion_summary.get("swarm_threat_score", 0.0) > 2.0 or self.simulation_mode:
            depth += 1
            self.coordination_chain.append("FederatedMemoryManager")
            self.coordination_logs.append("[Mesh ➔ Memory]: Memulakan replikasi memori berikutan anomali dikesan.")
            
            # Sync memory across zones (simulate sync payload exchange)
            dummy_remote_mem = {
                "grid_anomaly_detected": {"value": True, "clock": 5, "timestamp": current_time},
                "last_attacker_signature": {"value": "MODBUS_FLOOD" if active_attacks else "NONE", "clock": 3, "timestamp": current_time}
            }
            self.federated_memory.synchronize_memory("esp32_zone3", dummy_remote_mem, simulation_mode=self.simulation_mode)
            
            depth += 1
            self.coordination_chain.append("SwarmAnomalyFusionEngine")
            self.coordination_logs.append("[Memory ➔ Fusion]: Data memori kongsi digunakan untuk melengkapkan matriks korelasi ancaman.")
            
            depth += 1
            self.coordination_chain.append("DistributedConsensusEngine")
            self.coordination_logs.append("[Fusion ➔ Consensus]: Memulakan sesi pengundian konsensus bagi pelan pemulihan grid.")

        # Handle simulation modes affecting depth
        if self.simulation_mode == "swarm_consensus_instability":
            self.coordination_logs.append("[Swarm]: Percubaan pengundian berulang kali mengakibatkan ketidakstabilan pengundian.")
        elif self.simulation_mode == "distributed_drift_escalation":
            depth = 5  # Force exceed loop bounds
            self.coordination_logs.append("[Swarm]: Pengundian mengalami drift tak terhingga.")
            
        # Recursive Swarm loop protection (Max depth = 4)
        if depth > 4:
            self.coordination_logs.append("ALARM: Swarm coordination melebihi had kedalaman maksimum (kedalaman > 4). Menghentikan recursive routing loops!")
            self.status = "LOOP_PREVENTED"
            # Invalidate consensus when loop is prevented
            self.distributed_consensus.consensus_state = "BLOCKED (LOOP_PREVENTED)"
            self.distributed_consensus.consensus_score = 0.0
            return self.get_status_summary()

        # 4. Distributed Consensus Arbitration
        # Generate votes dynamically from active edge nodes based on threat level
        node_votes = {}
        nodes_list = ["esp32_zone1", "esp32_zone2", "esp32_zone3", "plc_primary", "plc_backup"]
        
        # Decide recovery action based on threat score
        threat_score = fusion_summary.get("swarm_threat_score", 0.0)
        proposed_action = "NONE"
        if threat_score > 6.0:
            proposed_action = "ISOLATE_ZONE_A"
        elif threat_score > 3.0:
            proposed_action = "CALIBRATE_SOLENOIDS"
            
        for node in nodes_list:
            node_health = edge_summary.get("nodes", {}).get(node, {}).get("health", 1.0)
            
            # Simulated vote conflicts
            if self.simulation_mode == "collaborative_recovery_failures" and node == "esp32_zone3":
                node_votes[node] = {"decision": "KEEP_ONLINE", "confidence": 0.90}
            elif proposed_action != "NONE":
                # Healthy nodes vote with high confidence, degraded nodes with lower confidence
                node_votes[node] = {
                    "decision": proposed_action,
                    "confidence": float(round(node_health, 2))
                }

        consensus_summary = self.distributed_consensus.arbitrate_consensus(
            node_votes,
            simulation_mode=self.simulation_mode
        )

        # Set Global Swarm Coordination state
        statuses = [
            self.federated_memory.status,
            self.distributed_consensus.status,
            self.edge_mesh.status,
            self.anomaly_fusion.status
        ]

        if "CRITICAL" in statuses or self.status == "LOOP_PREVENTED":
            self.status = "CRITICAL"
        elif "STORM_MITIGATED" in statuses:
            self.status = "STORM_MITIGATED"
        elif "HIGH" in statuses or "DEGRADED" in statuses:
            self.status = "DEGRADED"
        else:
            self.status = "NOMINAL"

        return self.get_status_summary()

    def handle_query(self, query: str) -> Optional[str]:
        """Intercepts and resolves Malay commands regarding swarm cognition."""
        q = query.lower().strip()

        # 1. "swarm consensus report"
        if "swarm consensus report" in q or "laporan konsensus swarm" in q or "status konsensus swarm" in q:
            c_summary = self.distributed_consensus.get_status_summary()
            logs_str = ", ".join(c_summary.get("consensus_logs", []))
            votes_count = len(c_summary.get("votes", {}))
            return (
                f"Laporan Konsensus Swarm: Status adalah {c_summary.get('consensus_state')}. "
                f"Skor Konsensus: {c_summary.get('consensus_score')}, Drift: {c_summary.get('consensus_drift')}. "
                f"Jumlah pengundi: {votes_count} nod. Log: {logs_str}."
            )

        # 2. "node mana paling kritikal dalam mesh"
        if "node mana paling kritikal dalam mesh" in q or "nod paling kritikal" in q or "mesh nod kritikal" in q:
            worst = self.edge_mesh.get_status_summary().get("worst_node")
            node_states = self.edge_mesh.get_status_summary().get("nodes", {})
            if worst:
                return f"Nod paling kritikal dalam mesh komunikasi ialah '{worst}' dengan perkumpulan '{node_states.get(worst, {}).get('group')}'."
            return "Semua nod mesh berada dalam status nominal dan seimbang."

        # 3. "gabungkan semua anomaly findings"
        if "gabungkan semua anomaly findings" in q or "gabung anomali" in q or "ringkasan fusion anomali" in q:
            f_summary = self.anomaly_fusion.get_status_summary()
            anom_count = len(f_summary.get("fused_anomalies", []))
            score = f_summary.get("swarm_threat_score", 0.0)
            return (
                f"Hasil gabungan anomali (Anomaly Fusion): Dikesan sebanyak {anom_count} anomali "
                f"merentasi pelbagai lapisan sistem. Skor ancaman keseluruhan swarm: {score}/10.0."
            )

        # 4. "buat distributed recovery coordination"
        if "buat distributed recovery coordination" in q or "koordinasi pemulihan" in q or "distributed recovery" in q:
            c_summary = self.distributed_consensus.get_status_summary()
            state = c_summary.get("consensus_state")
            score = c_summary.get("consensus_score")
            
            if state == "APPROVED":
                # Find majority decision
                votes = c_summary.get("votes", {})
                decisions = [v.get("decision") for v in votes.values()]
                majority_decision = max(set(decisions), key=decisions.count) if decisions else "NONE"
                
                return (
                    f"Koordinasi Pemulihan Teragih: Konsensus DIPERSETUJUI (Skor: {score}). "
                    f"Tindakan pemulihan disyorkan: '{majority_decision}'. "
                    f"Menunggu kelulusan manual operator SCADA untuk meneruskan."
                )
            else:
                return (
                    f"Koordinasi Pemulihan Teragih gagal dimulakan. Status Konsensus: {state}. "
                    f"Skor konsensus {score} tidak mencukupi atau terdapat konflik aktif."
                )

        # 5. "berapa confidence swarm sekarang"
        if "berapa confidence swarm sekarang" in q or "keyakinan swarm" in q or "confidence swarm" in q:
            score = self.distributed_consensus.consensus_score
            state = self.distributed_consensus.consensus_state
            return f"Skor keyakinan (confidence score) semasa swarm ialah {score:.2f} dengan status konsensus: {state}."

        return None

    def get_status_summary(self) -> Dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "status": self.status,
            "coordination_chain": self.coordination_chain,
            "coordination_logs": self.coordination_logs,
            "simulation_mode": self.simulation_mode,
            "federated_memory": self.federated_memory.get_status_summary(),
            "distributed_consensus": self.distributed_consensus.get_status_summary(),
            "edge_mesh": self.edge_mesh.get_status_summary(),
            "anomaly_fusion": self.anomaly_fusion.get_status_summary()
        }

    def reset_engine(self):
        self.status = "NOMINAL"
        self.coordination_chain.clear()
        self.coordination_logs.clear()
        self.simulation_mode = None
        self.federated_memory.reset_agent()
        self.distributed_consensus.reset_engine()
        self.edge_mesh.reset_orchestrator()
        self.anomaly_fusion.reset_engine()
