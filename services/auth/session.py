# core/services/auth/session.py

import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from services.auth.models import Base

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./core/gateway/telemetry.db"
)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

def init_db():
    Base.metadata.create_all(bind=engine)
    from sqlalchemy import text
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE simulator_runs ADD COLUMN progress_percentage INTEGER DEFAULT 0"))
    except Exception:
        pass
    for col, col_type in [
        ("detection_rate", "NUMERIC(5, 2) DEFAULT 0.00"),
        ("recovery_time_seconds", "INTEGER DEFAULT 0"),
        ("attack_success_rate", "NUMERIC(5, 2) DEFAULT 0.00"),
        ("telemetry_history", "TEXT"),
        ("scada_events", "TEXT"),
        ("attack_events", "TEXT"),
        ("flisr_actions", "TEXT")
    ]:
        try:
            with engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE experiment_results ADD COLUMN {col} {col_type}"))
        except Exception:
            pass
        
    # Seed scenario templates if table is empty
    from services.auth.models import ScenarioTemplate
    import uuid
    db = SessionLocal()
    try:
        if db.query(ScenarioTemplate).count() == 0:
            default_templates = [
                ScenarioTemplate(
                    id=uuid.uuid4(),
                    name="FDIA Attack",
                    description="Launches a coordinated False Data Injection Attack targeting bus voltage measurements to bypass traditional Bad Data Detection filter sweeps.",
                    grid_type="IEEE39",
                    category="Attack",
                    difficulty="Intermediate",
                    mitre_attack_id="T0811",
                    mitre_attack_name="Inhibit Response Function",
                    objective="Manipulate grid voltage state estimates by injection stealth values to force unsafe generator tripping actions.",
                    timeline=["T0: Attacker intercepts SCADA link", "T5: False voltage vector injection", "T30: Bad data detection bypass confirmation", "T60: Voltage limit violations trigger alarm"],
                    impact="Potential cascade blackout if generator triggers false voltage limits.",
                    required_plan="free",
                    config={"duration_seconds": 60, "attack_vector": [1.05, 1.06], "anomaly_type": "fdia"}
                ),
                ScenarioTemplate(
                    id=uuid.uuid4(),
                    name="Replay Attack",
                    description="Replays historical nominal sensor readings during active breaker tripping to delay control room operator response times.",
                    grid_type="IEEE14",
                    category="Attack",
                    difficulty="Beginner",
                    mitre_attack_id="T0843",
                    mitre_attack_name="Data Replay",
                    objective="Keep the operators blind by looping previous standard nominal metrics during system failures.",
                    timeline=["T0: Attack starts telemetry capture", "T10: Telemetry replay starts", "T25: Breaker 5 manually tripped", "T50: SCADA screen shows stable Nominal metrics"],
                    impact="Operator unaware of physical line outages until grid stabilizer fails.",
                    required_plan="free",
                    config={"duration_seconds": 60, "playback_file": "nominal_14.json", "anomaly_type": "replay"}
                ),
                ScenarioTemplate(
                    id=uuid.uuid4(),
                    name="Stealth Pathogen",
                    description="Injects stealthy, zero-parameter voltage offsets designed to bypass LSTM state classification networks, leading to systemic outages.",
                    grid_type="IEEE118",
                    category="Attack",
                    difficulty="Expert",
                    mitre_attack_id="T0806",
                    mitre_attack_name="Brute Force",
                    objective="Introduce a slow drift pattern into the state estimators that doesn't trigger neural network anomalies.",
                    timeline=["T0: Slow drift initiation", "T20: Residual analysis threshold check", "T45: Load balancing algorithm acts on skewed measurements"],
                    impact="Slow thermal decay across multiple critical lines.",
                    required_plan="academic_premium",
                    config={"duration_seconds": 90, "drift_slope": 0.002, "anomaly_type": "pathogen"}
                ),
                ScenarioTemplate(
                    id=uuid.uuid4(),
                    name="Cascading Failure",
                    description="Simulates initial breaker failures initiating sequential overloading and thermal line trips across the system.",
                    grid_type="IEEE57",
                    category="Contingency",
                    difficulty="Intermediate",
                    mitre_attack_id="T0807",
                    mitre_attack_name="Modify Parameter",
                    objective="Induce line failures and track how the rest of the loops dynamic loads redistribute to verify grid stability rules.",
                    timeline=["T0: Line 8 tripped by lightning/fault", "T12: Load rerouted to Line 9", "T30: Line 9 thermal limit exceeded, trips", "T45: Islanding occurs"],
                    impact="Load shed triggers on multiple buses; islanding of Bus 12.",
                    required_plan="free",
                    config={"duration_seconds": 60, "outage_lines": [8, 9], "anomaly_type": "cascade"}
                ),
                ScenarioTemplate(
                    id=uuid.uuid4(),
                    name="Generator Trip",
                    description="Simulates the sudden disconnection of a major power supply unit to test load-shedding and recovery metrics.",
                    grid_type="IEEE14",
                    category="Contingency",
                    difficulty="Beginner",
                    mitre_attack_id="T0814",
                    mitre_attack_name="Denial of Control Service",
                    objective="Observe frequency decay rate and track recovery curve.",
                    timeline=["T0: Generator 2 trips", "T5: Grid frequency drops to 59.5Hz", "T10: Underfrequency load shedding triggered", "T20: System frequency stabilizes"],
                    impact="RTO metrics assessment for automatic load recovery.",
                    required_plan="free",
                    config={"duration_seconds": 45, "trip_unit": 2, "anomaly_type": "generator_trip"}
                ),
                ScenarioTemplate(
                    id=uuid.uuid4(),
                    name="Blackout Cascade",
                    description="Simulates a complete grid collapse scenario following coordinated multi-bus attacks.",
                    grid_type="IEEE118",
                    category="Attack",
                    difficulty="Expert",
                    mitre_attack_id="T0831",
                    mitre_attack_name="System Shutdown",
                    objective="Test total blackout recovery operations under full cyber range parameters.",
                    timeline=["T0: Coordinated attacks on Bus 4, 9, and 12", "T15: Global voltage collapse", "T30: Black start sequence initiated", "T90: Re-synchronization of isolated islands"],
                    impact="Full system blackout. Test blackout recovery command structures.",
                    required_plan="research_lab",
                    config={"duration_seconds": 120, "target_buses": [4, 9, 12], "anomaly_type": "blackout"}
                ),
                ScenarioTemplate(
                    id=uuid.uuid4(),
                    name="FLISR Validation",
                    description="Triggers fault events to evaluate the performance of Fault Location, Isolation, and Service Restoration algorithms.",
                    grid_type="IEEE39",
                    category="Validation",
                    difficulty="Advanced",
                    mitre_attack_id="T0836",
                    mitre_attack_name="Modify Program",
                    objective="Verify that FLISR restores power within designated RTO threshold windows.",
                    timeline=["T0: Fault placed on Line 15", "T2: Switch 3 isolates faulted zone", "T8: Restoration switch 10 closed, powering bus 5"],
                    impact="Service restoration validation for critical subgrids.",
                    required_plan="academic_premium",
                    config={"duration_seconds": 60, "fault_line": 15, "anomaly_type": "flisr"}
                )
            ]
            db.add_all(default_templates)
            db.commit()
    except Exception as e:
        db.rollback()
        print(f"Failed to seed scenario templates: {e}")
    finally:
        db.close()

@contextmanager
def get_db_context():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
