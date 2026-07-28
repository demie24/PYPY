import os
import sys
import csv
import time
import random
import copy
import numpy as np

# Ensure digital_twin is in path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(os.path.dirname(current_dir), "digital_twin"))

from grid_topology import GridTopology
from physics import GridPhysicsEngine
from scenario_library import GridScenarioLibrary
from physics_validator import validate_physics

def run_dataset_generation():
    print("Initializing IEEE 39-Bus AC Grid for Expanded Dataset Generation...")
    
    # 1. Initialize digital twin grid components
    topo = GridTopology()
    engine = GridPhysicsEngine(topo)
    library = GridScenarioLibrary(topo)
    
    # 2. Setup output file paths
    data_dir = os.path.abspath(os.path.join(current_dir, "..", "data_collector", "data"))
    os.makedirs(data_dir, exist_ok=True)
    dataset_path = os.path.join(data_dir, "ieee39_telemetry_dataset.csv")
    print(f"Target dataset storage: {dataset_path}")
    
    # 3. Create flat CSV headers
    headers = ["timestamp", "scenario_id", "scenario_type"]
    for b in range(1, 40):
        headers.append(f"bus_{b}_P")
    for b in range(1, 40):
        headers.append(f"bus_{b}_Q")
    for b in range(1, 40):
        headers.append(f"bus_{b}_V")
    for b in range(1, 40):
        headers.append(f"bus_{b}_theta")
    headers.append("label")
    
    # 4. Scenario mapping
    generator_funcs = {
        "NORMAL": library.generate_normal,
        "N1_LINE": library.generate_n1_line,
        "N1_GENERATOR": library.generate_n1_generator,
        "N2": library.generate_n2,
        "VOLTAGE_INSTABILITY": library.generate_voltage_instability,
        "FDIA": library.generate_fdia,
        "REPLAY": library.generate_replay,
        "DOS": library.generate_dos
    }
    
    # Target of exactly 1300 VALID samples per label -> 10,400 valid total
    valid_target = 1300
    normal_solved_pool = []
    
    # Sequential timestamps
    start_timestamp = int(time.time() * 1000)
    current_time_offset = 0
    
    all_rows = []
    scenario_counter = 1
    
    # Solve nominal state first as baseline for DoS initialization
    b_breakers, b_loads, b_gen_P, b_gen_Q, b_gen_online = library.get_base_state()
    b_V, b_theta, b_P, b_Q, _ = engine.solve(b_breakers, b_loads, b_gen_P, b_gen_Q, b_gen_online)
    last_valid_state = {
        "P": b_P * 100.0,
        "Q": b_Q * 100.0,
        "V": b_V,
        "theta": b_theta
    }
    
    # We execute NORMAL first to fully populate normal_solved_pool for Replay attack use
    ordered_labels = ["NORMAL", "N1_LINE", "N1_GENERATOR", "N2", "VOLTAGE_INSTABILITY", "FDIA", "REPLAY", "DOS"]
    
    for label in ordered_labels:
        print(f"Generating valid samples for label '{label}' (Target: {valid_target})...")
        valid_count = 0
        attempts = 0
        
        while valid_count < valid_target:
            attempts += 1
            if attempts > 5000:
                print(f"Warning: Hit max generation attempts limit (5000) for label '{label}'")
                break
                
            # Reset res_bus solver outputs to clean defaults to prevent init="results" failure propagation
            if hasattr(engine.solver.net, "res_bus") and engine.solver.net.res_bus is not None and len(engine.solver.net.res_bus) > 0:
                if "vm_pu" in engine.solver.net.res_bus.columns:
                    engine.solver.net.res_bus.vm_pu.values.fill(1.0)
                if "va_degree" in engine.solver.net.res_bus.columns:
                    engine.solver.net.res_bus.va_degree.values.fill(0.0)
            
            # Generate 1 scenario config
            scen = generator_funcs[label](1)[0]
            
            # Solve AC power flow
            V, theta, P, Q, _ = engine.solve(
                scen["breakers"],
                scen["active_loads"],
                scen["generator_P"],
                scen["generator_Q"],
                scen["generators_online"]
            )
            
            # Copy output metrics and convert to MW/Mvar
            P_mw = np.copy(P) * 100.0
            Q_mvar = np.copy(Q) * 100.0
            V_pu = np.copy(V)
            theta_rad = np.copy(theta)
            
            # Cache original NaN status before sanitization
            had_nan_inf = np.any(np.isnan(V_pu)) or np.any(np.isnan(theta_rad)) or np.any(np.isnan(P_mw)) or np.any(np.isnan(Q_mvar))
            
            # Ensure no NaNs or Infs enter the numeric payload
            for b in range(39):
                if np.isnan(V_pu[b]) or np.isinf(V_pu[b]):
                    V_pu[b] = 1.0
                if np.isnan(theta_rad[b]) or np.isinf(theta_rad[b]):
                    theta_rad[b] = 0.0
                if np.isnan(P_mw[b]) or np.isinf(P_mw[b]):
                    P_mw[b] = 0.0
                if np.isnan(Q_mvar[b]) or np.isinf(Q_mvar[b]):
                    Q_mvar[b] = 0.0
                    
            # Check convergence
            is_converged = engine.last_solver_status.get("converged", False)
            
            # Apply Cyber Attack logic if active
            attack = scen["attack"]
            if attack is not None:
                if attack["type"] == "FDIA":
                    # Inject false measurements
                    for target in attack["targets"]:
                        bus_id = target["bus_id"]
                        fake_v = V_pu[bus_id] * target["v_scale"] + target["v_bias"]
                        # Clamp stealthy fake voltage to [0.86, 1.14] to pass physics check
                        V_pu[bus_id] = max(0.86, min(1.14, fake_v))
                        P_mw[bus_id] *= target["p_scale"]
                        Q_mvar[bus_id] *= target["q_scale"]
                        
                elif attack["type"] == "REPLAY":
                    # Replace with a randomly sampled normal state
                    if normal_solved_pool:
                        replay_ref = random.choice(normal_solved_pool)
                        P_mw = copy.deepcopy(replay_ref["P"])
                        Q_mvar = copy.deepcopy(replay_ref["Q"])
                        V_pu = copy.deepcopy(replay_ref["V"])
                        theta_rad = copy.deepcopy(replay_ref["theta"])
                    else:
                        P_mw = copy.deepcopy(last_valid_state["P"])
                        Q_mvar = copy.deepcopy(last_valid_state["Q"])
                        V_pu = copy.deepcopy(last_valid_state["V"])
                        theta_rad = copy.deepcopy(last_valid_state["theta"])
                        
                elif attack["type"] == "DOS":
                    # Freeze telemetry to last valid state
                    P_mw = copy.deepcopy(last_valid_state["P"])
                    Q_mvar = copy.deepcopy(last_valid_state["Q"])
                    V_pu = copy.deepcopy(last_valid_state["V"])
                    theta_rad = copy.deepcopy(last_valid_state["theta"])
            
            # Run physics validation
            is_phys_valid, reasons = validate_physics(P_mw, Q_mvar, V_pu, theta_rad)
            
            # Isolate failed solves or physical violations into separate labels
            final_label = label
            if not is_converged or had_nan_inf:
                if np.all(V_pu < 0.1):
                    final_label = "BLACKOUT"
                else:
                    final_label = "NON_CONVERGED"
            elif not is_phys_valid:
                final_label = "INVALID_STATE"
                
            # If the output meets all convergence and physics criteria, count as valid
            if final_label == label:
                valid_count += 1
                if label == "NORMAL":
                    normal_solved_pool.append({
                        "P": copy.deepcopy(P_mw),
                        "Q": copy.deepcopy(Q_mvar),
                        "V": copy.deepcopy(V_pu),
                        "theta": copy.deepcopy(theta_rad)
                    })
                # Cache valid baseline
                last_valid_state = {
                    "P": copy.deepcopy(P_mw),
                    "Q": copy.deepcopy(Q_mvar),
                    "V": copy.deepcopy(V_pu),
                    "theta": copy.deepcopy(theta_rad)
                }
                
            # Format row
            timestamp = start_timestamp + current_time_offset * 1000
            current_time_offset += 1
            
            row = [timestamp, scenario_counter, scen["scenario_type"]]
            for b in range(39):
                row.append(round(float(P_mw[b]), 4))
            for b in range(39):
                row.append(round(float(Q_mvar[b]), 4))
            for b in range(39):
                row.append(round(float(V_pu[b]), 6))
            for b in range(39):
                row.append(round(float(theta_rad[b]), 6))
            row.append(final_label)
            
            all_rows.append(row)
            scenario_counter += 1
            
        print(f"Completed '{label}'. Total samples generated: {attempts} (Valid: {valid_count})")
        
    # Write to CSV
    print(f"Writing dataset to {dataset_path}...")
    with open(dataset_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(all_rows)
        
    print(f"Successfully generated expanded dataset with {len(all_rows)} samples!")
    print(f"Output columns: {len(headers)} columns.")
    
if __name__ == "__main__":
    run_dataset_generation()
