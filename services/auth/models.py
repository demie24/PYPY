# core/services/auth/models.py

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Boolean, DateTime, Integer, Numeric, ForeignKey, JSON, Table
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Tenant(Base):
    __tablename__ = 'tenants'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    subdomain = Column(String(100), unique=True, nullable=False)
    plan_tier = Column(String(50), nullable=False, default='free') # 'free', 'academic_premium', 'enterprise'
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="tenant", cascade="all, delete-orphan")
    scenarios = relationship("Scenario", back_populates="tenant", cascade="all, delete-orphan")
    simulator_runs = relationship("SimulatorRun", back_populates="tenant", cascade="all, delete-orphan")
    experiments = relationship("Experiment", back_populates="tenant", cascade="all, delete-orphan")
    saved_reports = relationship("SavedReport", back_populates="tenant", cascade="all, delete-orphan")
    audit_trails = relationship("AuditTrail", back_populates="tenant", cascade="all, delete-orphan")
    usage_metrics = relationship("UsageMetric", back_populates="tenant", cascade="all, delete-orphan")

class User(Base):
    __tablename__ = 'users'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    role = Column(String(50), nullable=False, default='operator') # 'admin', 'operator', 'auditor'
    is_super_admin = Column(Boolean, default=False)
    is_founder = Column(Boolean, default=False)
    email_verified = Column(Boolean, default=False)
    verification_token = Column(String(255), nullable=True)
    verification_expiry = Column(DateTime(timezone=True), nullable=True)
    reset_token = Column(String(255), nullable=True)
    reset_expiry = Column(DateTime(timezone=True), nullable=True)
    failed_login_attempts = Column(Integer, default=0)
    lockout_until = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    tenant = relationship("Tenant", back_populates="users")
    experiments = relationship("Experiment", back_populates="user", cascade="all, delete-orphan")
    saved_reports = relationship("SavedReport", back_populates="user", cascade="all, delete-orphan")

class Subscription(Base):
    __tablename__ = 'subscriptions'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    plan_name = Column(String(50), nullable=False) # 'free', 'academic_premium', 'enterprise'
    billing_cycle = Column(String(20), nullable=False) # 'monthly', 'yearly', 'one-time'
    amount = Column(Numeric(10, 2), default=0.00)
    status = Column(String(50), nullable=False, default='active') # 'active', 'expired', 'cancelled', 'trial'
    payment_provider = Column(String(50)) # 'stripe', 'toyyibpay', 'manual'
    payment_reference = Column(String(255))
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True))
    auto_renew = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    tenant = relationship("Tenant", back_populates="subscriptions")

class Coupon(Base):
    __tablename__ = 'coupons'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(100), unique=True, nullable=False)
    target_plan = Column(String(50), nullable=False) # 'academic_premium', 'enterprise'
    valid_until = Column(DateTime(timezone=True))
    usage_limit = Column(Integer, default=1)
    used_count = Column(Integer, default=0)
    duration_days = Column(Integer, default=30)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class CouponRedemption(Base):
    __tablename__ = 'coupon_redemptions'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    coupon_id = Column(UUID(as_uuid=True), ForeignKey('coupons.id', ondelete='CASCADE'), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    redeemed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class UsageMetric(Base):
    __tablename__ = 'usage_metrics'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    period = Column(String(20), nullable=False) # e.g. '2026-06'
    simulations_run = Column(Integer, default=0)
    ai_messages_used = Column(Integer, default=0)
    reports_generated = Column(Integer, default=0)
    storage_used_mb = Column(Numeric(10, 2), default=0.00)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    tenant = relationship("Tenant", back_populates="usage_metrics")

class Scenario(Base):
    __tablename__ = 'scenarios'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(255), nullable=False)
    grid_type = Column(String(50), nullable=False) # 'IEEE14', 'IEEE39', 'IEEE57', 'IEEE118'
    description = Column(String)
    config = Column(JSON, nullable=False)
    is_marketplace_template = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    tenant = relationship("Tenant", back_populates="scenarios")
    simulator_runs = relationship("SimulatorRun", back_populates="scenario")

class SimulatorRun(Base):
    __tablename__ = 'simulator_runs'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    scenario_id = Column(UUID(as_uuid=True), ForeignKey('scenarios.id', ondelete='SET NULL'))
    celery_task_id = Column(String(255), unique=True)
    status = Column(String(50), nullable=False, default='PENDING') # 'PENDING', 'RUNNING', 'STOPPED', 'FAILED'
    started_at = Column(DateTime(timezone=True))
    stopped_at = Column(DateTime(timezone=True))
    bcm_rto_seconds = Column(Integer, default=0)
    bcm_rpo_seconds = Column(Integer, default=0)
    total_load_shed_mwh = Column(Numeric(10, 2), default=0.00)
    estimated_financial_loss = Column(Numeric(12, 2), default=0.00)
    progress_percentage = Column(Integer, default=0)

    tenant = relationship("Tenant", back_populates="simulator_runs")
    scenario = relationship("Scenario", back_populates="simulator_runs")
    experiment_results = relationship("ExperimentResult", back_populates="run")

class SimulationAuditLog(Base):
    __tablename__ = 'simulation_audit_logs'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    job_id = Column(UUID(as_uuid=True), nullable=False)
    action = Column(String(50), nullable=False)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    actor = Column(String(100), default="system")
    details = Column(String(500))

class Experiment(Base):
    __tablename__ = 'experiments'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(String)
    grid_type = Column(String(50), nullable=False)
    archived = Column(Boolean, default=False)
    locked = Column(Boolean, default=False)
    read_only = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    tenant = relationship("Tenant", back_populates="experiments")
    user = relationship("User", back_populates="experiments")
    results = relationship("ExperimentResult", back_populates="experiment", cascade="all, delete-orphan")

class ExperimentResult(Base):
    __tablename__ = 'experiment_results'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    experiment_id = Column(UUID(as_uuid=True), ForeignKey('experiments.id', ondelete='CASCADE'), nullable=False)
    run_id = Column(UUID(as_uuid=True), ForeignKey('simulator_runs.id', ondelete='SET NULL'))
    resilience_score = Column(Numeric(5, 2), nullable=False)
    rto_seconds = Column(Integer, nullable=False)
    rpo_seconds = Column(Integer, nullable=False)
    total_load_shed_mwh = Column(Numeric(10, 2), nullable=False)
    financial_loss = Column(Numeric(12, 2), nullable=False)
    attack_strategy = Column(String(100))
    mitigation_applied = Column(String(100))
    verdict = Column(String(50), nullable=False) # 'NOMINAL', 'DEGRADED', 'BLACKOUT'
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    detection_rate = Column(Numeric(5, 2), default=0.00)
    recovery_time_seconds = Column(Integer, default=0)
    attack_success_rate = Column(Numeric(5, 2), default=0.00)
    telemetry_history = Column(JSON)
    scada_events = Column(JSON)
    attack_events = Column(JSON)
    flisr_actions = Column(JSON)

    experiment = relationship("Experiment", back_populates="results")
    run = relationship("SimulatorRun", back_populates="experiment_results")

class SavedReport(Base):
    __tablename__ = 'saved_reports'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    grid_type = Column(String(50), nullable=False)
    report_metadata = Column(JSON)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    tenant = relationship("Tenant", back_populates="saved_reports")
    user = relationship("User", back_populates="saved_reports")

class AuditTrail(Base):
    __tablename__ = 'audit_trails'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    action = Column(String(255), nullable=False)
    ip_address = Column(String(45), nullable=False)
    user_agent = Column(String)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    tenant = relationship("Tenant", back_populates="audit_trails")

class ScenarioTemplate(Base):
    __tablename__ = 'scenario_templates'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(String)
    grid_type = Column(String(50), nullable=False)
    category = Column(String(100), nullable=False)
    difficulty = Column(String(50), nullable=False)
    mitre_attack_id = Column(String(50))
    mitre_attack_name = Column(String(255))
    objective = Column(String)
    timeline = Column(JSON)
    impact = Column(String)
    required_plan = Column(String(50), default="free")
    config = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class FavoriteScenario(Base):
    __tablename__ = 'favorite_scenarios'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    template_id = Column(UUID(as_uuid=True), ForeignKey('scenario_templates.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    template = relationship("ScenarioTemplate")

class ExperimentTag(Base):
    __tablename__ = 'experiment_tags'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    experiment_id = Column(UUID(as_uuid=True), ForeignKey('experiments.id', ondelete='CASCADE'), nullable=False)
    tag = Column(String(50), nullable=False)

    experiment = relationship("Experiment")

class ExperimentShare(Base):
    __tablename__ = 'experiment_shares'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    experiment_id = Column(UUID(as_uuid=True), ForeignKey('experiments.id', ondelete='CASCADE'), nullable=False)
    shared_with_tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=True)
    shared_with_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=True)
    shared_by_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    experiment = relationship("Experiment")
    shared_with_tenant = relationship("Tenant", foreign_keys=[shared_with_tenant_id])
    shared_with_user = relationship("User", foreign_keys=[shared_with_user_id])
    shared_by_user = relationship("User", foreign_keys=[shared_by_user_id])

class CopilotMessage(Base):
    __tablename__ = 'copilot_messages'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    role = Column(String(50), nullable=False) # 'user' or 'assistant'
    content = Column(String, nullable=False)
    citations = Column(JSON) # e.g. [{"type": "scenario", "name": "FDIA Attack"}]
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    tenant = relationship("Tenant")

class SimulationAuditLog(Base):
    __tablename__ = 'simulation_audit_logs'
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    job_id = Column(UUID(as_uuid=True), nullable=True)
    action = Column(String(100), nullable=False)  # e.g. LAUNCH, CANCEL, COMPLETE
    actor = Column(String(100), default="system")  # user email or "system"
    details = Column(String, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    tenant = relationship("Tenant")

# ═══════════════════════════════════════════════════════════════════════════════
# V11.8 — Operations, Observability & Security Models
# ═══════════════════════════════════════════════════════════════════════════════

class JWTBlacklist(Base):
    """Revoked JWT token IDs — checked on every authenticated request."""
    __tablename__ = 'jwt_blacklist'
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    jti = Column(String(255), unique=True, nullable=False, index=True)  # JWT ID claim
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    blacklisted_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    reason = Column(String(100), default="logout")  # logout / revoked / security

    user = relationship("User")


class IPBlock(Base):
    """IP addresses blocked from accessing the gateway."""
    __tablename__ = 'ip_blocks'
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ip_address = Column(String(45), nullable=False, index=True)
    reason = Column(String(255), nullable=True)
    blocked_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    blocked_until = Column(DateTime(timezone=True), nullable=True)
    active = Column(Boolean, default=True)


class SecurityAuditEvent(Base):
    """Security-relevant audit events (logins, failures, blocks, admin actions)."""
    __tablename__ = 'security_audit_events'
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='SET NULL'), nullable=True)
    event_type = Column(String(100), nullable=False)   # LOGIN_SUCCESS, LOGIN_FAILURE, ACCOUNT_LOCKED, IP_BLOCKED
    description = Column(String(512), nullable=True)
    ip_address = Column(String(45), default="unknown")
    occurred_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = relationship("User")
    tenant = relationship("Tenant")


class AlertEvent(Base):
    """Fired alerts from the alert evaluation engine."""
    __tablename__ = 'alert_events'
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id = Column(String(100), nullable=False)
    rule_name = Column(String(255), nullable=False)
    severity = Column(String(50), nullable=False)   # critical / warning / info
    message = Column(String(512), nullable=True)
    fired_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    acknowledged = Column(Boolean, default=False)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    acknowledged_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)


class BackupRecord(Base):
    """Records of all backup runs performed by the backup engine."""
    __tablename__ = 'backup_records'
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    backup_type = Column(String(100), nullable=False)   # postgres / reports / configs / files
    filename = Column(String(512), nullable=False)
    filepath = Column(String(1024), nullable=True)
    size_mb = Column(Numeric(10, 3), default=0)
    schedule = Column(String(50), default="on_demand")  # daily / weekly / monthly / on_demand
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    status = Column(String(50), default="completed")    # completed / failed
    error_message = Column(String(512), nullable=True)


class OperationLog(Base):
    """Aggregated log entries from all PYPY Grid services."""
    __tablename__ = 'operation_logs'
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service = Column(String(100), nullable=False)   # gateway / copilot / simulation / billing etc.
    level = Column(String(20), nullable=False)      # DEBUG / INFO / WARNING / ERROR / CRITICAL
    message = Column(String(2048), nullable=False)
    extra = Column(JSON, nullable=True)             # Additional structured context
    logged_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='SET NULL'), nullable=True)

    tenant = relationship("Tenant")


class SystemMetricSnapshot(Base):
    """Point-in-time system metric snapshots for charting and alerting."""
    __tablename__ = 'system_metric_snapshots'
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cpu_percent = Column(Numeric(6, 2), default=0)
    ram_percent = Column(Numeric(6, 2), default=0)
    disk_percent = Column(Numeric(6, 2), default=0)
    ram_used_mb = Column(Integer, default=0)
    active_simulations = Column(Integer, default=0)
    queue_length = Column(Integer, default=0)
    active_websockets = Column(Integer, default=0)
    api_requests_per_min = Column(Integer, default=0)
    avg_latency_ms = Column(Numeric(10, 2), default=0)
    error_rate_percent = Column(Numeric(6, 2), default=0)
    captured_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)


# ═══════════════════════════════════════════════════════════════════════════════
# V11.9 — Commercial Launch Models
# ═══════════════════════════════════════════════════════════════════════════════

class UserNotification(Base):
    """In-app notifications for users (billing alerts, sim complete, system news)."""
    __tablename__ = 'user_notifications'
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=True)
    type = Column(String(100), nullable=False)  # 'billing', 'simulation', 'security', 'system'
    title = Column(String(255), nullable=False)
    message = Column(String(1024), nullable=False)
    read = Column(Boolean, default=False)
    action_url = Column(String(512), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = relationship("User")
    tenant = relationship("Tenant")


class SupportTicket(Base):
    """Customer support tickets."""
    __tablename__ = 'support_tickets'
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='SET NULL'), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    subject = Column(String(255), nullable=False)
    description = Column(String(4096), nullable=False)
    category = Column(String(100), default='general')  # 'billing', 'technical', 'account', 'general'
    priority = Column(String(50), default='normal')    # 'low', 'normal', 'high', 'urgent'
    status = Column(String(50), default='open')        # 'open', 'in_progress', 'resolved', 'closed'
    assigned_to = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    resolution_notes = Column(String(2048), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    tenant = relationship("Tenant")
    user = relationship("User", foreign_keys=[user_id])
    assignee = relationship("User", foreign_keys=[assigned_to])


class WorkspaceProfile(Base):
    """Stores first-time setup wizard results for each user."""
    __tablename__ = 'workspace_profiles'
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)
    institution = Column(String(255), nullable=True)
    research_focus = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    preferred_grid = Column(String(50), default='IEEE39')  # IEEE14/39/57/118
    setup_completed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User")
