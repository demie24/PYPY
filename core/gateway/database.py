import os
import sqlite3
import time
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("gateway.database")

DB_DIR = "/app/data" if os.path.exists("/app") else "./core/gateway"
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, "telemetry.db")

class TelemetryDB:
    def __init__(self):
        self.db_path = DB_PATH
        self._initialize_db()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize_db(self):
        logger.info(f"Initializing SQLite telemetry database at {self.db_path}...")
        with self._get_conn() as conn:
            cursor = conn.cursor()
            
            # Bus Telemetry Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bus_telemetry (
                    timestamp INTEGER NOT NULL,
                    bus_id INTEGER NOT NULL,
                    voltage_magnitude REAL NOT NULL,
                    voltage_angle REAL NOT NULL,
                    active_power REAL NOT NULL,
                    reactive_power REAL NOT NULL,
                    PRIMARY KEY (timestamp, bus_id)
                )
            """)
            
            # Line Telemetry Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS line_telemetry (
                    timestamp INTEGER NOT NULL,
                    line_id TEXT NOT NULL,
                    from_bus INTEGER NOT NULL,
                    to_bus INTEGER NOT NULL,
                    active_power_flow REAL NOT NULL,
                    reactive_power_flow REAL NOT NULL,
                    loading_percent REAL NOT NULL,
                    PRIMARY KEY (timestamp, line_id)
                )
            """)
            
            # Generator Telemetry Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS gen_telemetry (
                    timestamp INTEGER NOT NULL,
                    generator_id INTEGER NOT NULL,
                    bus_id INTEGER NOT NULL,
                    active_power_output REAL NOT NULL,
                    reactive_power_output REAL NOT NULL,
                    voltage_setpoint REAL NOT NULL,
                    PRIMARY KEY (timestamp, generator_id)
                )
            """)
            
            conn.commit()
            logger.info("Database tables created successfully.")

    # --- VALIDATION ENGINE ---
    def validate_bus_telemetry(self, data: Dict[str, Any]) -> bool:
        required = ["timestamp", "bus_id", "voltage_magnitude", "voltage_angle", "active_power", "reactive_power"]
        for field in required:
            if field not in data or data[field] is None:
                logger.warning(f"Validation Failure: Bus metrics missing required field '{field}'")
                return False
                
        # Value boundaries
        v_mag = data["voltage_magnitude"]
        if not (0.0 <= v_mag <= 1.5):
            logger.warning(f"Validation Failure: Invalid voltage magnitude {v_mag} p.u. at Bus {data['bus_id']}")
            return False
            
        # Timestamp check
        now_ms = int(time.time() * 1000)
        ts = data["timestamp"]
        if ts > now_ms + 10000 or ts < now_ms - 3600000: # not in future, not older than 1 hr
            logger.warning(f"Validation Failure: Stale or future timestamp {ts} for Bus {data['bus_id']}")
            return False
            
        return True

    def validate_line_telemetry(self, data: Dict[str, Any]) -> bool:
        required = ["timestamp", "line_id", "from_bus", "to_bus", "active_power_flow", "reactive_power_flow", "loading_percent"]
        for field in required:
            if field not in data or data[field] is None:
                logger.warning(f"Validation Failure: Line flow missing required field '{field}'")
                return False
                
        load_pct = data["loading_percent"]
        if load_pct < 0.0:
            logger.warning(f"Validation Failure: Negative loading percent {load_pct} on Line {data['line_id']}")
            return False
            
        return True

    def validate_gen_telemetry(self, data: Dict[str, Any]) -> bool:
        required = ["timestamp", "generator_id", "bus_id", "active_power_output", "reactive_power_output", "voltage_setpoint"]
        for field in required:
            if field not in data or data[field] is None:
                logger.warning(f"Validation Failure: Generator status missing required field '{field}'")
                return False
                
        v_set = data["voltage_setpoint"]
        if not (0.5 <= v_set <= 1.5):
            logger.warning(f"Validation Failure: Invalid voltage setpoint {v_set} on Gen {data['generator_id']}")
            return False
            
        return True

    # --- WRITE HANDLERS ---
    def save_bus_telemetry(self, data: Dict[str, Any]):
        if not self.validate_bus_telemetry(data):
            return
        try:
            with self._get_conn() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO bus_telemetry 
                    (timestamp, bus_id, voltage_magnitude, voltage_angle, active_power, reactive_power)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (data["timestamp"], data["bus_id"], data["voltage_magnitude"], data["voltage_angle"], data["active_power"], data["reactive_power"]))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to insert bus telemetry: {e}")

    def save_line_telemetry(self, data: Dict[str, Any]):
        if not self.validate_line_telemetry(data):
            return
        try:
            with self._get_conn() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO line_telemetry 
                    (timestamp, line_id, from_bus, to_bus, active_power_flow, reactive_power_flow, loading_percent)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (data["timestamp"], data["line_id"], data["from_bus"], data["to_bus"], data["active_power_flow"], data["reactive_power_flow"], data["loading_percent"]))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to insert line telemetry: {e}")

    def save_gen_telemetry(self, data: Dict[str, Any]):
        if not self.validate_gen_telemetry(data):
            return
        try:
            with self._get_conn() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO gen_telemetry 
                    (timestamp, generator_id, bus_id, active_power_output, reactive_power_output, voltage_setpoint)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (data["timestamp"], data["generator_id"], data["bus_id"], data["active_power_output"], data["reactive_power_output"], data["voltage_setpoint"]))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to insert generator telemetry: {e}")

    # --- QUERY LAYER METHODS ---
    def query_bus(self, bus_id: int, start_time: int, end_time: int) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM bus_telemetry 
                WHERE bus_id = ? AND timestamp >= ? AND timestamp <= ?
                ORDER BY timestamp ASC
            """, (bus_id, start_time, end_time))
            return [dict(row) for row in cursor.fetchall()]

    def query_line(self, line_id: str, start_time: int, end_time: int) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM line_telemetry 
                WHERE line_id = ? AND timestamp >= ? AND timestamp <= ?
                ORDER BY timestamp ASC
            """, (line_id, start_time, end_time))
            return [dict(row) for row in cursor.fetchall()]

    def query_gen(self, gen_id: int, start_time: int, end_time: int) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM gen_telemetry 
                WHERE generator_id = ? AND timestamp >= ? AND timestamp <= ?
                ORDER BY timestamp ASC
            """, (gen_id, start_time, end_time))
            return [dict(row) for row in cursor.fetchall()]

    def get_latest_bus(self, bus_id: int) -> Optional[Dict[str, Any]]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM bus_telemetry 
                WHERE bus_id = ? 
                ORDER BY timestamp DESC LIMIT 1
            """, (bus_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_latest_line(self, line_id: str) -> Optional[Dict[str, Any]]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM line_telemetry 
                WHERE line_id = ? 
                ORDER BY timestamp DESC LIMIT 1
            """, (line_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_latest_gen(self, gen_id: int) -> Optional[Dict[str, Any]]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM gen_telemetry 
                WHERE generator_id = ? 
                ORDER BY timestamp DESC LIMIT 1
            """, (gen_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

db = TelemetryDB()
