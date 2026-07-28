import hashlib
import json
from typing import Dict, Any, List, Tuple

def compute_packet_hash(
    device_id: str,
    bus_id: int,
    timestamp: int,
    sequence_number: int,
    nonce: str,
    P: float,
    Q: float,
    V: float,
    theta: float,
    previous_hash: str
) -> str:
    """
    Computes a deterministic SHA-256 hash for a telemetry packet.
    """
    payload_str = (
        f"{device_id}|{bus_id}|{timestamp}|{sequence_number}|{nonce}|"
        f"{P:.6f}|{Q:.6f}|{V:.6f}|{theta:.6f}|{previous_hash}"
    )
    return hashlib.sha256(payload_str.encode("utf-8")).hexdigest()

def generate_hash(packet: Dict[str, Any], previous_hash: str) -> str:
    """
    Generates and returns the SHA-256 hash for a telemetry packet dictionary.
    """
    return compute_packet_hash(
        device_id=packet.get("device_id", ""),
        bus_id=packet.get("bus_id", 0),
        timestamp=packet.get("timestamp", 0),
        sequence_number=packet.get("sequence_number", 0),
        nonce=str(packet.get("nonce", "")),
        P=float(packet.get("P", 0.0)),
        Q=float(packet.get("Q", 0.0)),
        V=float(packet.get("V", 1.0)),
        theta=float(packet.get("theta", 0.0)),
        previous_hash=previous_hash
    )

def verify_hash(packet: Dict[str, Any], previous_hash: str) -> bool:
    """
    Verifies that the current_hash in the packet matches the computed hash.
    """
    received_hash = packet.get("current_hash", "")
    computed_hash = generate_hash(packet, previous_hash)
    return received_hash == computed_hash

def verify_chain(packets: List[Dict[str, Any]], initial_hash: str) -> Tuple[bool, int]:
    """
    Verifies the continuity of a sequence of telemetry packets.
    Returns:
        is_valid: bool indicating if the chain is fully valid.
        failed_index: int index of the first packet that failed validation (-1 if all valid).
    """
    prev_hash = initial_hash
    for idx, pkt in enumerate(packets):
        # 1. Verify previous_hash match in packet
        if pkt.get("previous_hash", "") != prev_hash:
            return False, idx
            
        # 2. Verify current hash computation
        if not verify_hash(pkt, prev_hash):
            return False, idx
            
        prev_hash = pkt.get("current_hash", "")
        
    return True, -1
