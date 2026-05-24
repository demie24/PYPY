# Core Self-Healing Grid Engine (FLISR)

The Self-Healing Service implements FLISR (Fault Location, Isolation, and Service Restoration) logic. When a fault is detected and isolated by protection relays, the FLISR service calculates the restoration path to restore power to affected de-energized buses using available tie switches.

## Operation Flow
1. **Fault Alert**: Receives notice of breaker trip.
2. **Isolate**: Determines which breaker operations are needed to isolate the faulted line segment.
3. **Restore**: Identifies normally-open tie switches to close, routing power from alternate feeders.
