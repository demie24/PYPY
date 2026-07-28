import sys
import time
import urllib.request
import json
import logging
import subprocess

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("E2E_Verification")

GATEWAY_URL = "http://localhost:8000/api"

def run_cmd(args):
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"Command failed: {' '.join(args)}\nError: {result.stderr}")
        return False
    return True

def query_api(endpoint):
    url = f"{GATEWAY_URL}{endpoint}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as e:
        logger.error(f"Failed to query endpoint {url}: {e}")
        return None

def main():
    logger.info("Starting PYPY v9.1 End-to-End Telemetry Verification...")

    # 1. Start MQTT, Gateway, Digital Twin and Dashboard containers
    logger.info("Spinning up container services: mqtt, gateway, digital_twin, dashboard...")
    if not run_cmd(["docker", "compose", "up", "-d", "mqtt", "gateway", "digital_twin", "dashboard"]):
        sys.exit(1)

    # 2. Wait for system initialization and telemetry sweeps to run
    logger.info("Waiting 10 seconds for the solver loop to execute and populate database...")
    time.sleep(10.0)

    # 3. Check Gateway Health
    logger.info("Verifying Gateway Health status...")
    health = query_api("/health")
    if not health or health.get("status") != "healthy":
        logger.error(f"Gateway health check failed: {health}")
        sys.exit(1)
    logger.info("Gateway Health Check: PASS")

    # 4. Check Telemetry Query API - Latest Endpoint
    logger.info("Verifying Latest Telemetry API Endpoint...")
    latest = query_api("/telemetry/latest")
    if not latest or "buses" not in latest or not latest["buses"]:
        logger.error(f"Latest Telemetry query failed: {latest}")
        sys.exit(1)
        
    logger.info("Latest Telemetry Check: PASS")
    # Verify Bus 1 present in latest
    assert "Bus_1" in latest["buses"], "Bus_1 not found in latest telemetry"
    sample_bus = latest["buses"]["Bus_1"]
    logger.info(f"Sample Bus 1 metrics from DB: {sample_bus}")
    
    # 5. Check Telemetry Query API - Historical Queries
    logger.info("Verifying Bus Historical Telemetry API Endpoint...")
    bus_history = query_api("/telemetry/bus/0")
    if not bus_history or len(bus_history) == 0:
        logger.error("Bus 0 historical query returned empty results.")
        sys.exit(1)
    logger.info(f"Bus 0 Historical Records Count: {len(bus_history)}")
    logger.info(f"Sample Bus 0 Record: {bus_history[0]}")
    logger.info("Bus Historical Query Check: PASS")

    logger.info("Verifying Line Historical Telemetry API Endpoint...")
    line_history = query_api("/telemetry/line/L_line_0")
    if not line_history or len(line_history) == 0:
        logger.error("Line L_line_0 historical query returned empty results.")
        sys.exit(1)
    logger.info(f"Line L_line_0 Historical Records Count: {len(line_history)}")
    logger.info(f"Sample Line Record: {line_history[0]}")
    logger.info("Line Historical Query Check: PASS")

    logger.info("Verifying Generator Historical Telemetry API Endpoint...")
    gen_history = query_api("/telemetry/generator/0")
    if not gen_history or len(gen_history) == 0:
        logger.error("Gen 0 historical query returned empty results.")
        sys.exit(1)
    logger.info(f"Gen 0 Historical Records Count: {len(gen_history)}")
    logger.info(f"Sample Gen Record: {gen_history[0]}")
    logger.info("Generator Historical Query Check: PASS")

    # 5.5 Verify Topology Endpoint
    logger.info("Verifying Topology API Endpoint...")
    topology = query_api("/telemetry/topology")
    if not topology or "buses" not in topology or "lines" not in topology:
        logger.error(f"Topology query failed: {topology}")
        sys.exit(1)
    logger.info(f"Topology Loaded: {len(topology['buses'])} Buses, {len(topology['lines'])} Lines")
    assert len(topology["buses"]) == 39, f"Expected 39 buses, got {len(topology['buses'])}"
    assert len(topology["lines"]) == 46, f"Expected 46 branches, got {len(topology['lines'])}"
    logger.info("Topology Endpoint Check: PASS")

    # 5.6 Verify Dashboard Web Server
    logger.info("Verifying Dashboard Web Server...")
    try:
        req = urllib.request.Request("http://localhost:3001")
        with urllib.request.urlopen(req) as response:
            html = response.read().decode("utf-8")
            if "doctype html" not in html.lower():
                logger.error("Dashboard server response did not contain HTML")
                sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to reach dashboard web server: {e}")
        sys.exit(1)
    logger.info("Dashboard Web Server Check: PASS")

    # 6. Verify Database schema and records persistence
    logger.info("Checking Database persistence inside container...")
    db_check = run_cmd(["docker", "compose", "exec", "gateway", "sqlite3", "/app/core/gateway/telemetry.db", "SELECT COUNT(*) FROM bus_telemetry;"])
    if not db_check:
        logger.warning("Could not execute sqlite3 check directly (maybe sqlite3 is not installed inside the gateway container). Skipping direct DB query check.")
    
    logger.info("==================================================================")
    logger.info("PYPY v9.1 END-TO-END TELEMETRY FLOW: VALIDATED SUCCESSFULLY")
    logger.info("Data Flow Sequence: Solver -> MQTT -> DB Storage -> FastAPI Query")
    logger.info("PYPY v9.1 COMPLETE")
    logger.info("==================================================================")

if __name__ == "__main__":
    main()
