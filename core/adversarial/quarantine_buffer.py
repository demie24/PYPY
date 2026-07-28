from typing import Dict, Any, List

class QuarantineBuffer:
    """
    Quarantine buffer archiving failed packets (tampered, replayed, or injected).
    Maintains circular queue storage to avoid memory overflows.
    """
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.buffer: List[Dict[str, Any]] = []

    def quarantine(self, packet: Dict[str, Any], reason: str, trust_score: float) -> None:
        """
        Pushes a failed telemetry packet to the quarantine storage buffer.
        """
        record = {
            "packet": packet,
            "quarantine_reason": reason,
            "final_trust_score": trust_score
        }
        
        self.buffer.append(record)
        
        # Enforce circular size limit
        if len(self.buffer) > self.max_size:
            self.buffer.pop(0)

    def get_all(self) -> List[Dict[str, Any]]:
        """
        Retrieves all quarantined records.
        """
        return self.buffer

    def get_by_bus(self, bus_id: int) -> List[Dict[str, Any]]:
        """
        Retrieves quarantined packets for a specific bus.
        """
        return [item for item in self.buffer if item["packet"].get("bus_id") == bus_id]

    def clear(self) -> None:
        """
        Clears the quarantine buffer.
        """
        self.buffer.clear()
        
    def size(self) -> int:
        """
        Returns current count of quarantined packets.
        """
        return len(self.buffer)
