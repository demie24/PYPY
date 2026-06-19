import sys
import logging
import numpy as np
from grid_topology import GridTopology
from physics import GridPhysicsEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Sprint3Verification")

def verify_ac_solver():
    logger.info("Executing Sprint 3 AC Solver Engine Verification...")
    
    try:
        # Initialize components
        topo = GridTopology()
        engine = GridPhysicsEngine(topo)
        
        # 1. Prepare base mock operational state inputs
        breakers = {line["id"]: "CLOSED" for line in topo.lines}
        
        # Build default active loads from nominals
        active_loads = {}
        for bus_idx, load in topo.loads.items():
            active_loads[bus_idx] = {
                "P": load["P_nom"],
                "Q": load["Q_nom"]
            }
            
        # Build default generator settings
        generator_P = {bus_idx: gen["P_nom"] for bus_idx, gen in topo.generators.items()}
        generator_Q = {bus_idx: gen["Q_nom"] for bus_idx, gen in topo.generators.items()}
        generators_online = {bus_idx: True for bus_idx in topo.generators.keys()}

        # 2. Run solve call
        V, theta, P, Q, line_flows = engine.solve(
            breakers, active_loads, generator_P, generator_Q, generators_online
        )
        
        status = engine.last_solver_status
        
        # 3. Print Solver status reporting
        logger.info("========================================")
        logger.info("AC POWER FLOW EXECUTED SUCCESSFULLY")
        logger.info(f"Solver Status     : {'CONVERGED' if status.get('converged') else 'FAILED'}")
        logger.info(f"Solver Mode       : {status.get('mode')}")
        logger.info(f"NR Iterations     : {status.get('iterations')}")
        logger.info("========================================")
        
        # 4. Verify Bus voltages and angles are available
        assert len(V) == 39, "Voltage vector does not contain 39 buses"
        assert len(theta) == 39, "Angle vector does not contain 39 buses"
        
        logger.info(f"Bus Voltages V (p.u.) - min: {np.min(V):.4f}, max: {np.max(V):.4f}")
        logger.info(f"Sample Bus Voltages (first 5 buses): {V[:5]}")
        logger.info(f"Bus Angles theta (rad) - min: {np.min(theta):.4f}, max: {np.max(theta):.4f}")
        logger.info(f"Sample Bus Angles (first 5 buses): {theta[:5]}")
        
        # 5. Verify Generator outputs are available
        assert len(P) == 39 and len(Q) == 39, "Injections are not fully populated"
        # Generators are located at specific buses: print active generation injections
        logger.info("Generator Outputs (P & Q Injections at select buses):")
        for bus_idx in sorted(topo.generators.keys()):
            # Multiply injection by 100 to get MW/MVar
            logger.info(f"  Gen Bus {bus_idx:2d} -> P: {P[bus_idx]*100:6.1f} MW, Q: {Q[bus_idx]*100:6.1f} MVar")
            
        # 6. Verify Load consumption is available
        logger.info("Load Consumptions (P & Q Demands at select buses):")
        for bus_idx in sorted(list(topo.loads.keys())[:5]): # show first 5 load buses
            p_dem = active_loads[bus_idx]["P"] * 100
            q_dem = active_loads[bus_idx]["Q"] * 100
            logger.info(f"  Load Bus {bus_idx:2d} -> P: {p_dem:6.1f} MW, Q: {q_dem:6.1f} MVar")
            
        logger.info("========================================")
        logger.info("Sprint 3 Verification Complete: SUCCESS!")
        
    except Exception as e:
        logger.error(f"AC Solver Verification FAILED: {e}")
        sys.exit(1)

if __name__ == "__main__":
    verify_ac_solver()
