import logging
import sys
from grid_loader import IEEE39BusLoader

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Sprint2Verification")

def verify_topology():
    logger.info("Executing Sprint 2 Topology Verification...")
    
    try:
        # Load the IEEE 39-bus topology
        loader = IEEE39BusLoader()
        net = loader.get_net()
        
        # 1. Output structural details
        logger.info("========================================")
        logger.info("TOPOLOGY LOADED SUCCESSFULLY")
        logger.info(f"Number of Buses       : {loader.num_buses}")
        logger.info(f"Number of Lines       : {loader.num_lines}")
        logger.info(f"Number of Generators  : {loader.num_generators}")
        logger.info(f"Number of Loads       : {loader.num_loads}")
        logger.info(f"Number of Transformers: {loader.num_trafos}")
        logger.info(f"Number of Ext Grids   : {loader.num_ext_grids}")
        logger.info("========================================")
        
        # 2. Verify access to buses
        buses = loader.get_buses()
        assert not buses.empty, "Bus dataframe is empty"
        logger.info(f"Sample Buses (first 3):\n{buses[['name', 'vn_kv']].head(3)}")
        
        # 3. Verify access to lines
        lines = loader.get_lines()
        assert not lines.empty, "Line dataframe is empty"
        logger.info(f"Sample Lines (first 3):\n{lines[['from_bus', 'to_bus', 'length_km']].head(3)}")
        
        # 4. Verify access to generators
        gens = loader.get_generators()
        assert not gens.empty, "Generator dataframe is empty"
        logger.info(f"Sample Generators (first 3):\n{gens[['bus', 'p_mw', 'vm_pu']].head(3)}")
        
        # 5. Verify access to loads
        loads = loader.get_loads()
        assert not loads.empty, "Load dataframe is empty"
        logger.info(f"Sample Loads (first 3):\n{loads[['bus', 'p_mw', 'q_mvar']].head(3)}")
        
        # 6. Verify access to transformers
        trafos = loader.get_transformers()
        assert not trafos.empty, "Transformer dataframe is empty"
        logger.info(f"Sample Transformers (first 3):\n{trafos[['hv_bus', 'lv_bus', 'sn_mva']].head(3)}")
        
        logger.info("All elements verified successfully!")
        
    except Exception as e:
        logger.error(f"Topology Verification FAILED: {e}")
        sys.exit(1)

if __name__ == "__main__":
    verify_topology()
