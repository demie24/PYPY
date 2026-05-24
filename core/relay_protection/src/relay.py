#!/usr/bin/env python3
"""
Relay Protection (IED Emulator)
Monitors bus/line conditions and triggers breaker trip commands.
"""
import time

class ProtectionRelay:
    def __init__(self, overcurrent_limit=5.0, undervoltage_limit=0.90):
        self.overcurrent_limit = overcurrent_limit
        self.undervoltage_limit = undervoltage_limit
        self.tripped = False

    def evaluate(self, current, voltage):
        """
        Evaluate conditions to see if relay protection triggers (Trips).
        """
        trip_reasons = []
        
        # ANSI 50/51: Overcurrent Protection
        if current > self.overcurrent_limit:
            trip_reasons.append(f"ANSI 50/51: Overcurrent detected ({current} A > {self.overcurrent_limit} A)")
            
        # ANSI 27: Undervoltage Protection
        if voltage < self.undervoltage_limit:
            trip_reasons.append(f"ANSI 27: Undervoltage detected ({voltage} p.u. < {self.undervoltage_limit} p.u.)")
            
        if trip_reasons:
            self.tripped = True
            return {
                "action": "TRIP_BREAKER",
                "tripped": True,
                "reasons": trip_reasons,
                "timestamp": int(time.time() * 1000)
            }
            
        return {
            "action": "KEEP_CLOSED",
            "tripped": False,
            "reasons": [],
            "timestamp": int(time.time() * 1000)
        }

if __name__ == "__main__":
    relay = ProtectionRelay(overcurrent_limit=10.0, undervoltage_limit=0.92)
    print("Normal conditions (Current: 5A, Voltage: 0.98):", relay.evaluate(5.0, 0.98))
    print("Overcurrent trip (Current: 12A, Voltage: 0.95):", relay.evaluate(12.0, 0.95))
    print("Undervoltage trip (Current: 4A, Voltage: 0.88):", relay.evaluate(4.0, 0.88))
