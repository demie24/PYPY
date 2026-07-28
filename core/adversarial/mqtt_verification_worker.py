import time
from typing import Dict, Any, Tuple, Set
from core.adversarial.blockchain_integrity import verify_hash

class MqttVerificationWorker:
    """
    Verification worker simulating MQTT broker-side/cloud-side telemetry validation.
    Performs sequence verification, duplicate detection, sliding-window latency checks,
    and cryptographic hash chain verification.
    """
    def __init__(self, trust_recovery_rate: float = 0.05, max_delay_ms: int = 500):
        self.trust_recovery_rate = trust_recovery_rate
        self.max_delay_ms = max_delay_ms
        
        # State tracking: bus_id -> state dict
        # state contains: last_sequence, last_hash, seen_nonces, trust_score
        self.bus_states: Dict[int, Dict[str, Any]] = {}

    def get_trust_state(self, trust_score: float) -> str:
        """
        Maps numerical trust score to categorical Trust State.
        """
        if trust_score > 0.9:
            return "VERIFIED"
        elif trust_score > 0.7:
            return "TRUSTED"
        elif trust_score > 0.4:
            return "DEGRADED"
        elif trust_score > 0.2:
            return "SUSPICIOUS"
        else:
            return "COMPROMISED"

    def process_packet(self, packet: Dict[str, Any], current_time_ms: int) -> Tuple[str, str, float]:
        """
        Processes an incoming telemetry packet, performs cryptographic and sequence verification,
        and computes updated trust scores and classifications.
        
        Returns:
            classification: One of "VERIFIED", "DEGRADED", "SUSPICIOUS", "COMPROMISED"
            error_reason: Detailed error string ("NONE", "HASH_MISMATCH", "REPLAY_ATTACK", "DELAYED_PACKET", "OUT_OF_ORDER")
            trust_score: Updated float trust score [0.0, 1.0]
        """
        bus_id = int(packet.get("bus_id", 0))
        seq_num = int(packet.get("sequence_number", 0))
        timestamp = int(packet.get("timestamp", 0))
        nonce = str(packet.get("nonce", ""))
        prev_hash = packet.get("previous_hash", "")
        curr_hash = packet.get("current_hash", "")

        # Initialize bus state if unseen
        if bus_id not in self.bus_states:
            self.bus_states[bus_id] = {
                "last_sequence": seq_num - 1,
                "last_hash": prev_hash,
                "seen_nonces": set(),
                "trust_score": 1.0
            }

        state = self.bus_states[bus_id]
        trust = state["trust_score"]

        # --- 1. REPLAY ATTACK & DUPLICATE DETECTION ---
        # A. Check sequence number monotonicity
        if seq_num <= state["last_sequence"]:
            trust = max(0.0, trust - 0.50)
            state["trust_score"] = trust
            return self.get_trust_state(trust), "REPLAY_ATTACK", trust

        # B. Check nonce freshness (to prevent replay of same message signature)
        if nonce in state["seen_nonces"]:
            trust = max(0.0, trust - 0.50)
            state["trust_score"] = trust
            return self.get_trust_state(trust), "REPLAY_ATTACK", trust

        # --- 2. SEQUENCE CONTINUITY (OUT-OF-ORDER CHECK) ---
        is_out_of_order = False
        if seq_num != state["last_sequence"] + 1:
            # We missed some packets or received them out-of-order
            is_out_of_order = True

        # --- 3. TIMESTAMPS / SLIDING WINDOW LATENCY VALIDATION ---
        delay = current_time_ms - timestamp
        is_delayed = False
        if delay > self.max_delay_ms:
            is_delayed = True
            trust = max(0.0, trust - 0.10)
            state["trust_score"] = trust

        # --- 4. HASH CHAIN VERIFICATION ---
        # Note: If the packet claims to chain from state["last_hash"] but mismatch exists
        if prev_hash != state["last_hash"] or not verify_hash(packet, state["last_hash"]):
            # If the packet is internally consistent (valid signature relative to its declared previous_hash)
            # but there is a sequence gap, classify it as OUT_OF_ORDER rather than HASH_MISMATCH
            if seq_num > state["last_sequence"] + 1 and verify_hash(packet, prev_hash):
                trust = max(0.0, trust - 0.20)
                state["trust_score"] = trust
                return self.get_trust_state(trust), "OUT_OF_ORDER", trust
                
            trust = 0.0
            state["trust_score"] = trust
            return "COMPROMISED", "HASH_MISMATCH", trust

        # --- 5. VERIFICATION SUCCESS & TRUST HEALING ---
        # If hash is valid, we accept the packet and update our running state
        state["last_sequence"] = seq_num
        state["last_hash"] = curr_hash
        state["seen_nonces"].add(nonce)

        # Apply trust healing if no delay penalties were triggered
        if not is_delayed:
            trust = min(1.0, trust + self.trust_recovery_rate * (1.0 - trust))
            state["trust_score"] = trust

        classification = self.get_trust_state(trust)
        
        if is_delayed:
            return classification, "DELAYED_PACKET", trust
        elif is_out_of_order:
            return classification, "OUT_OF_ORDER", trust
        else:
            return classification, "NONE", trust
