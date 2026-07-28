import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EnvVerification")

def run_checks():
    logger.info("Starting PYPY v9.0 Env Verification...")
    
    # 1. Check Python Version
    logger.info(f"Python Version: {sys.version}")
    
    # 2. Check Package Imports
    try:
        import numpy as np
        import pandas as pd
        import scipy
        import numba
        import pandapower as pp
        import fastapi
        import paho.mqtt.client as mqtt
        logger.info("Package imports: SUCCESS")
    except ImportError as e:
        logger.error(f"Import Failure: {e}")
        sys.exit(1)
        
    # 3. Test Pandapower Base Initialization & AC Solve
    try:
        net = pp.create_empty_network()
        pp.create_bus(net, vn_kv=110.)
        pp.create_bus(net, vn_kv=110.)
        pp.create_line_from_parameters(
            net, from_bus=0, to_bus=1, length_km=1.0, 
            r_ohm_per_km=0.1, x_ohm_per_km=0.2, c_nf_per_km=10.0, max_i_ka=0.4
        )
        pp.create_ext_grid(net, bus=0)
        pp.create_load(net, bus=1, p_mw=1.0, q_mvar=0.5)
        
        # Execute small AC test power flow (Newton-Raphson)
        pp.runpp(net, algorithm="nr")
        logger.info("Pandapower solver loop: SUCCESS")
        
        # Assert bus voltage magnitudes are calculated
        v_mag = net.res_bus.vm_pu.values
        logger.info(f"Calculated Voltages (p.u.): {v_mag}")
        assert len(v_mag) == 2, "Unexpected number of bus results"
        
    except Exception as e:
        logger.error(f"Pandapower execution failure: {e}")
        sys.exit(1)

    logger.info("Env Verification complete. Ready for Sprint 2.")

if __name__ == "__main__":
    run_checks()
