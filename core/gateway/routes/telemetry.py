import time
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
from gateway.database import db
from gateway.store import store

router = APIRouter(prefix="/telemetry", tags=["telemetry"])

@router.get("/bus/{bus_id}", response_model=List[Dict[str, Any]])
def get_bus_telemetry(
    bus_id: int,
    start_time: Optional[int] = Query(None, description="Start timestamp in ms"),
    end_time: Optional[int] = Query(None, description="End timestamp in ms")
):
    if start_time is None:
        start_time = 0
    if end_time is None:
        end_time = int(time.time() * 1000)
    
    results = db.query_bus(bus_id, start_time, end_time)
    return results

@router.get("/line/{line_id}", response_model=List[Dict[str, Any]])
def get_line_telemetry(
    line_id: str,
    start_time: Optional[int] = Query(None, description="Start timestamp in ms"),
    end_time: Optional[int] = Query(None, description="End timestamp in ms")
):
    if start_time is None:
        start_time = 0
    if end_time is None:
        end_time = int(time.time() * 1000)
        
    results = db.query_line(line_id, start_time, end_time)
    return results

@router.get("/generator/{gen_id}", response_model=List[Dict[str, Any]])
def get_generator_telemetry(
    gen_id: int,
    start_time: Optional[int] = Query(None, description="Start timestamp in ms"),
    end_time: Optional[int] = Query(None, description="End timestamp in ms")
):
    if start_time is None:
        start_time = 0
    if end_time is None:
        end_time = int(time.time() * 1000)
        
    results = db.query_gen(gen_id, start_time, end_time)
    return results

@router.get("/latest")
def get_latest_telemetry():
    # Gather latest from database for 39 buses, 35 lines, 11 transformers, and 10 generators
    buses = {}
    for i in range(39):
        b = db.get_latest_bus(i)
        if b:
            # Format compatible keys
            buses[f"Bus_{i+1}"] = b
            
    lines = {}
    for i in range(35):
        lid = f"L_line_{i}"
        l = db.get_latest_line(lid)
        if l:
            lines[lid] = l
            
    for i in range(11):
        tid = f"L_trafo_{i}"
        t = db.get_latest_line(tid)
        if t:
            lines[tid] = t
            
    gens = {}
    for i in range(10):
        g = db.get_latest_gen(i)
        if g:
            gens[f"Gen_{i}"] = g
            
    # Fallback to store if DB is not populated yet
    if not buses and store.latest_telemetry:
        return {
            "source": "memory_store",
            "latest": store.latest_telemetry
        }
        
    return {
        "source": "sqlite_database",
        "timestamp": int(time.time() * 1000),
        "buses": buses,
        "lines": lines,
        "generators": gens
    }

@router.get("/topology")
def get_grid_topology():
    import sys
    import os
    dt_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../digital_twin"))
    if dt_path not in sys.path:
        sys.path.append(dt_path)
    from grid_topology import GridTopology
    topo = GridTopology()
    
    buses = {}
    for i in range(topo.num_buses):
        bus_name = f"Bus_{i+1}"
        buses[bus_name] = {
            "bus_id": i,
            "is_gen": i in topo.generators,
            "is_load": i in topo.loads,
            "name": topo.generators[i]["name"] if i in topo.generators else (topo.loads[i]["name"] if i in topo.loads else f"Junction_{i+1}")
        }
        
    lines = []
    for line in topo.lines:
        lines.append({
            "id": line["id"],
            "from_bus": f"Bus_{line['from'] + 1}",
            "to_bus": f"Bus_{line['to'] + 1}",
            "is_trafo": "trafo" in line["id"]
        })
        
    return {
        "buses": buses,
        "lines": lines
    }
