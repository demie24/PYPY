# core/services/tenant/tenant_service.py

from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from services.auth.models import Tenant, Subscription, Scenario, UsageMetric
from services.users.user_service import create_user

def onboard_new_tenant(db: Session, name: str, subdomain: str, admin_email: str, admin_password: str) -> Tenant:
    # 0. Validate Duplicates
    existing_subdomain = db.query(Tenant).filter(Tenant.subdomain == subdomain).first()
    if existing_subdomain:
        raise ValueError("Subdomain already registered.")
        
    from services.users.user_service import get_user_by_email
    existing_user = get_user_by_email(db, admin_email)
    if existing_user:
        raise ValueError("Admin email already registered.")

    # 1. Create Tenant
    tenant = Tenant(
        name=name,
        subdomain=subdomain,
        plan_tier="academic_premium" # Start with academic_premium trial
    )
    db.add(tenant)
    db.flush()
    
    # 2. Create 30-day Academic Premium Trial Subscription
    now = datetime.now(timezone.utc)
    trial_sub = Subscription(
        tenant_id=tenant.id,
        plan_name="academic_premium",
        billing_cycle="one-time",
        amount=0.00,
        status="trial",
        payment_provider="manual",
        payment_reference="SYSTEM_FREE_TRIAL",
        started_at=now,
        expires_at=now + timedelta(days=30),
        auto_renew=False
    )
    db.add(trial_sub)
    
    # 3. Create TenantAdmin User
    admin_user = create_user(
        db=db,
        tenant_id=tenant.id,
        email=admin_email,
        plain_password=admin_password,
        first_name="Tenant",
        last_name="Administrator",
        role="admin"
    )
    
    # 4. Initialize Usage Metrics record
    current_period = now.strftime("%Y-%m")
    usage = UsageMetric(
        tenant_id=tenant.id,
        period=current_period
    )
    db.add(usage)
    
    # 5. Populate Scenario templates
    marketplace_templates = [
        {
            "name": "Coordinated FDIA Demo",
            "grid_type": "IEEE39",
            "description": "Demonstrates a coordinated False Data Injection Attack targeting bus voltage state estimation.",
            "config": {"attack_type": "FDIA", "target_bus": 5, "severity": "HIGH", "defense": "FLISR"}
        },
        {
            "name": "Replay Attack Demo",
            "grid_type": "IEEE14",
            "description": "Replays recorded nominal load signatures on a line segment to bypass LSTM detection filters.",
            "config": {"attack_type": "REPLAY", "target_line": "L_line_3", "defense": "NONE"}
        },
        {
            "name": "FLISR Pathogen Self-Healing Demo",
            "grid_type": "IEEE57",
            "description": "Simulates zero-parameter pathogen attack with active FLISR islanding response validation.",
            "config": {"attack_type": "PATHOGEN", "severity": "CRITICAL", "defense": "FLISR"}
        },
        {
            "name": "GPS Spoofing Playbook",
            "grid_type": "IEEE14",
            "description": "Simulates PMU spoofing on generator synchronization phase.",
            "config": {"attack_type": "GPS_SPOOFING", "severity": "HIGH", "defense": "PMU_AUTHENTICATION"}
        },
        {
            "name": "Data Poisoning Injection",
            "grid_type": "IEEE39",
            "description": "Poisons telemetry feeds to trigger false generator tripping.",
            "config": {"attack_type": "DATA_POISONING", "severity": "MEDIUM", "defense": "GNN_STATE_ESTIMATION"}
        },
        {
            "name": "Cascading Failure Loop",
            "grid_type": "IEEE57",
            "description": "Triggers cascading line overloads and safety line breaker trips.",
            "config": {"attack_type": "CASCADING_FAILURE", "severity": "CRITICAL", "defense": "SHEDDING_RESTORE"}
        },
        {
            "name": "Transformer Sabotage Attack",
            "grid_type": "IEEE118",
            "description": "Simulates physical-cyber assault causing transformer overheating.",
            "config": {"attack_type": "TRANSFORMER_SABOTAGE", "severity": "CRITICAL", "defense": "DYNAMIC_RECONFIG"}
        },
        {
            "name": "Islanding Attack Scenario",
            "grid_type": "IEEE14",
            "description": "Forcefully separates secondary subgrids into isolated microgrids.",
            "config": {"attack_type": "ISLANDING", "severity": "MEDIUM", "defense": "ACTIVE_RELOAD"}
        },
        {
            "name": "Ransomware Control Hijack",
            "grid_type": "IEEE39",
            "description": "Locks SCADA console terminals, simulating ransomware payloads.",
            "config": {"attack_type": "RANSOMWARE", "severity": "HIGH", "defense": "BACKUP_RESTORE"}
        },
        {
            "name": "Autonomous RL Pathogen APT",
            "grid_type": "IEEE118",
            "description": "Deploys a reinforcement learning agent to find optimal line tripping sequences.",
            "config": {"attack_type": "RL_PATHOGEN", "severity": "CRITICAL", "defense": "ADAPTIVE_ISLANDING"}
        },
        {
            "name": "Stealth APT Persistent Threat",
            "grid_type": "IEEE57",
            "description": "Establishes long-term persistent stealth backdoor in SCADA router.",
            "config": {"attack_type": "STEALTH_APT", "severity": "HIGH", "defense": "ZERO_TRUST_IDS"}
        }
    ]
    
    for tmpl in marketplace_templates:
        scenario = Scenario(
            tenant_id=tenant.id,
            name=tmpl["name"],
            grid_type=tmpl["grid_type"],
            description=tmpl["description"],
            config=tmpl["config"],
            is_marketplace_template=True
        )
        db.add(scenario)
        
    db.commit()
    return tenant
