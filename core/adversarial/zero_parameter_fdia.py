"""
Zero-Parameter FDIA (False Data Injection Attack) Generator — PYPY V10.7.

Generates stealth measurement perturbations without access to:
  - Jacobian matrices
  - PTDF matrices
  - State estimation models
  - Full topology knowledge

Physics rationale:
  Classical FDIA: a = Hc  (requires H = measurement Jacobian)
  Zero-Param:     a = physics_plausible_perturbation(V_nom ± δ)
                  where δ is bounded by IEEE stealth constraints

Stealth constraints (IEEE C37.118 / IEC 61850):
  |δV| ≤ 0.05 pu   (voltage measurement noise floor)
  |δP| ≤ 0.10 pu   (power measurement tolerance)
  |δf| ≤ 0.15 Hz   (frequency deviation below UFLS threshold)

All computations: pure NumPy.
"""
import os
import sys
import numpy as np
from typing import Dict, List, Optional, Tuple

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, project_root)


# ---------------------------------------------------------------------------
# Stealth bounds (IEEE/IEC standards)
# ---------------------------------------------------------------------------
VOLTAGE_STEALTH_BOUND  = 0.05   # pu  — below SCADA gross-error threshold
POWER_STEALTH_BOUND    = 0.10   # pu  — within measurement uncertainty
FREQUENCY_STEALTH_BOUND = 0.15  # Hz  — below UFLS relay setpoint

# Nominal operating values
V_NOMINAL_PU   = 1.00   # pu (flat-start nominal)
F_NOMINAL_HZ   = 60.0   # Hz (North America); also supports 50 Hz
F_NOMINAL_EU   = 50.0   # Hz (Europe/Asia)


# ---------------------------------------------------------------------------
# Attack strategies
# ---------------------------------------------------------------------------
STRATEGIES = ("voltage_only", "power_only", "frequency_only", "combined", "stealthy")


class ZeroParameterFDIA:
    """
    Zero-parameter False Data Injection Attack generator.

    Generates physically plausible measurement perturbations that:
    1. Stay within IEEE stealth bounds (evade gross-error detection)
    2. Are internally consistent (spoofed V implies spoofed P)
    3. Target cut-lines to cause islanding under partial observability
    """

    def __init__(self,
                 topo,
                 seed: int = 42,
                 v_bound: float = VOLTAGE_STEALTH_BOUND,
                 p_bound: float = POWER_STEALTH_BOUND,
                 f_bound: float = FREQUENCY_STEALTH_BOUND,
                 nominal_freq: float = F_NOMINAL_HZ):
        self.topo = topo
        self.rng = np.random.RandomState(seed)
        self.v_bound = v_bound
        self.p_bound = p_bound
        self.f_bound = f_bound
        self.nominal_freq = nominal_freq

        # Build nominal measurement vectors
        self._build_nominal_measurements()

    # ------------------------------------------------------------------
    # Nominal measurement initialization
    # ------------------------------------------------------------------

    def _build_nominal_measurements(self):
        """Build nominal (clean) measurement vectors from topology."""
        n_buses = self.topo.num_buses
        n_lines = len(self.topo.lines)

        # Nominal voltages: all buses at V_nom ± small random noise (simulate real SCADA)
        self.V_nom = np.ones(n_buses, dtype=np.float32) * V_NOMINAL_PU
        # Add small gaussian noise to simulate sensor imperfection
        self.V_nom += self.rng.randn(n_buses).astype(np.float32) * 0.002

        # Nominal power injections (from topology generators/loads)
        self.P_nom = np.zeros(n_buses, dtype=np.float32)
        for bus, gen_info in self.topo.generators.items():
            self.P_nom[bus] += gen_info.get("P_nom", 0.0)
        for bus, load_info in self.topo.loads.items():
            self.P_nom[bus] -= load_info.get("P_nom", 0.0)

        # Nominal line flows (uniform approximation: scale by susceptance)
        self.P_line_nom = np.zeros(n_lines, dtype=np.float32)
        for i, line in enumerate(self.topo.lines):
            x = line.get("X", 0.1)
            b = 1.0 / max(abs(x), 1e-6)
            # Heuristic: flow ∝ b × ΔV (assume ΔV ≈ 0.01 pu)
            self.P_line_nom[i] = b * 0.01

        # Nominal frequency (one per system)
        self.f_nom = float(self.nominal_freq)

        # Bus angle reference (flat-start)
        self.theta_nom = np.zeros(n_buses, dtype=np.float32)

        # Map line_id → index
        self._lid_to_idx = {line["id"]: i for i, line in enumerate(self.topo.lines)}
        self._bus_to_idx = {i: i for i in range(n_buses)}

    # ------------------------------------------------------------------
    # 1. Voltage spoofing
    # ------------------------------------------------------------------

    def spoof_voltage(self,
                      bus_id: int,
                      delta_v: Optional[float] = None,
                      direction: str = "drop") -> Tuple[np.ndarray, float]:
        """
        Generate spoofed voltage measurement for bus `bus_id`.

        Args:
            bus_id:   Target bus index
            delta_v:  Magnitude of perturbation (pu). If None, sample in [0.01, v_bound].
            direction: 'drop' (decrease V) or 'boost' (increase V)

        Returns:
            V_spoofed: (n_buses,) spoofed voltage vector
            actual_delta: applied perturbation magnitude
        """
        if delta_v is None:
            delta_v = self.rng.uniform(0.01, self.v_bound)
        delta_v = np.clip(delta_v, 0.0, self.v_bound)

        V_spoofed = self.V_nom.copy()
        sign = -1.0 if direction == "drop" else +1.0
        V_spoofed[bus_id] = np.clip(
            V_spoofed[bus_id] + sign * delta_v,
            0.90, 1.10  # hard physical bounds
        )
        return V_spoofed, delta_v

    def spoof_voltage_multi(self,
                             bus_ids: List[int],
                             delta_v: float = 0.03,
                             direction: str = "drop") -> np.ndarray:
        """Spoof voltages at multiple buses simultaneously."""
        V_spoofed = self.V_nom.copy()
        sign = -1.0 if direction == "drop" else +1.0
        for bus in bus_ids:
            dv = self.rng.uniform(0.005, delta_v)
            V_spoofed[bus] = np.clip(V_spoofed[bus] + sign * dv, 0.90, 1.10)
        return V_spoofed

    # ------------------------------------------------------------------
    # 2. Power spoofing
    # ------------------------------------------------------------------

    def spoof_power(self,
                    line_id: str,
                    delta_p: Optional[float] = None,
                    consistent_with_v: Optional[np.ndarray] = None,
                    P_spoofed: Optional[np.ndarray] = None) -> Tuple[np.ndarray, float]:
        """
        Generate spoofed power flow measurement for line `line_id`.

        If `consistent_with_v` is provided, power is adjusted to be consistent
        with the spoofed voltage (DC power flow approximation): P = b*(θi - θj)
        This prevents cross-measurement inconsistency detection.

        Args:
            line_id:           Target line ID
            delta_p:           Power perturbation (pu). Sampled if None.
            consistent_with_v: Optional spoofed voltage array for consistency
            P_spoofed:         Optional input array to modify in-place (for multiple lines)

        Returns:
            P_line_spoofed: (n_lines,) spoofed line power vector
            actual_delta:   applied delta
        """
        if delta_p is None:
            delta_p = self.rng.uniform(0.01, self.p_bound)
        delta_p = np.clip(delta_p, 0.0, self.p_bound)

        idx = self._lid_to_idx.get(line_id, -1)
        if P_spoofed is None:
            P_spoofed = self.P_line_nom.copy()

        if idx < 0:
            return P_spoofed, 0.0

        if consistent_with_v is not None:
            # DC approximation: P_line ≈ b × (θ_f - θ_t)
            # We perturb the angle difference implied by the spoofed V
            line_info = self.topo.lines[idx]
            f, t = line_info["from"], line_info["to"]
            x = line_info.get("X", 0.1)
            b = 1.0 / max(abs(x), 1e-6)
            # Implied angle from voltage magnitude difference (approximation)
            dV = float(consistent_with_v[f]) - float(consistent_with_v[t])
            P_consistent = b * dV
            # Add a small perturbation around the consistent value
            noise = self.rng.uniform(-delta_p * 0.1, delta_p * 0.1)
            P_spoofed[idx] = P_consistent + noise
        else:
            # Simple additive perturbation (maximally deceptive: flip direction)
            sign = self.rng.choice([-1.0, 1.0])
            P_spoofed[idx] += sign * delta_p

        return P_spoofed, delta_p

    def spoof_power_injection(self,
                               bus_id: int,
                               delta_p: Optional[float] = None) -> np.ndarray:
        """Spoof bus power injection measurement."""
        if delta_p is None:
            delta_p = self.rng.uniform(0.01, self.p_bound)
        delta_p = np.clip(delta_p, 0.0, self.p_bound)

        P_inj_spoofed = self.P_nom.copy()
        sign = self.rng.choice([-1.0, 1.0])
        P_inj_spoofed[bus_id] += sign * delta_p
        return P_inj_spoofed

    # ------------------------------------------------------------------
    # 3. Frequency spoofing
    # ------------------------------------------------------------------

    def spoof_frequency(self,
                         region: str = "NA",
                         delta_f: Optional[float] = None,
                         trend: str = "decline") -> Tuple[float, float]:
        """
        Generate spoofed frequency measurement.

        Stealth constraint: |δf| ≤ 0.15 Hz (below UFLS relay setpoints of 59.5 Hz)
        IEEE C37.118: frequency measurement resolution = 0.001 Hz

        Args:
            region: 'NA' (60 Hz) or 'EU' (50 Hz)
            delta_f: perturbation magnitude (Hz). Sampled if None.
            trend:   'decline' (under-frequency) or 'rise' (over-frequency)

        Returns:
            f_spoofed: spoofed frequency (Hz)
            delta_f:   applied perturbation
        """
        f_base = F_NOMINAL_HZ if region == "NA" else F_NOMINAL_EU

        if delta_f is None:
            delta_f = self.rng.uniform(0.01, self.f_bound)
        delta_f = np.clip(delta_f, 0.0, self.f_bound)

        sign = -1.0 if trend == "decline" else +1.0
        f_spoofed = f_base + sign * delta_f

        # Hard stealth bound: stay above UFLS = 59.5 (NA) / 49.5 (EU)
        ufls_threshold = 59.5 if region == "NA" else 49.5
        f_spoofed = max(f_spoofed, ufls_threshold + 0.05)

        return float(f_spoofed), float(delta_f)

    def spoof_frequency_ramp(self,
                              region: str = "NA",
                              n_steps: int = 5,
                              final_delta: float = 0.12) -> np.ndarray:
        """
        Generate a ramped frequency deviation sequence (multi-step FDIA).
        Ramp prevents sudden jump detection.

        Returns array of shape (n_steps,) with spoofed frequencies.
        """
        f_base = F_NOMINAL_HZ if region == "NA" else F_NOMINAL_EU
        deltas = np.linspace(0, final_delta, n_steps)
        return f_base - deltas  # declining trend

    # ------------------------------------------------------------------
    # 4. Combined FDIA generation
    # ------------------------------------------------------------------

    def generate_fdia(self,
                       target_lines: List[str],
                       strategy: str = "stealthy",
                       region: str = "NA") -> Dict:
        """
        Generate a complete FDIA attack vector targeting specified lines.

        Args:
            target_lines: List of line_ids to target
            strategy:     One of STRATEGIES
            region:       'NA' or 'EU' (for frequency)

        Returns:
            attack_dict with keys:
              'V_spoofed'        : (n_buses,) voltage measurements
              'P_line_spoofed'   : (n_lines,) line power measurements
              'P_inj_spoofed'    : (n_buses,) bus power injections
              'f_spoofed'        : float, frequency
              'delta_V_norm'     : L2 norm of voltage perturbation
              'delta_P_norm'     : L2 norm of power perturbation
              'delta_f'          : frequency perturbation (Hz)
              'strategy'         : strategy name
              'target_lines'     : list of targeted line IDs
              'stealth_score'    : estimated stealth (1=perfectly stealthy)
              'target_buses'     : buses affected
        """
        if strategy not in STRATEGIES:
            raise ValueError(f"Unknown strategy '{strategy}'. Choose from {STRATEGIES}")

        # Collect buses adjacent to target lines
        target_buses = set()
        for lid in target_lines:
            idx = self._lid_to_idx.get(lid, -1)
            if idx >= 0:
                line = self.topo.lines[idx]
                target_buses.add(line["from"])
                target_buses.add(line["to"])
        target_bus_list = list(target_buses)

        # Initialize with nominal values
        V_sp = self.V_nom.copy()
        P_line_sp = self.P_line_nom.copy()
        P_inj_sp  = self.P_nom.copy()
        f_sp = self.f_nom
        df = 0.0

        # --- Strategy execution ---
        if strategy == "voltage_only":
            V_sp = self.spoof_voltage_multi(target_bus_list,
                                             delta_v=self.v_bound * 0.8)

        elif strategy == "power_only":
            for lid in target_lines:
                P_line_sp, _ = self.spoof_power(lid, delta_p=self.p_bound * 0.8, P_spoofed=P_line_sp)

        elif strategy == "frequency_only":
            f_sp, df = self.spoof_frequency(region=region,
                                             delta_f=self.f_bound * 0.8)

        elif strategy == "combined":
            # Apply all three
            V_sp = self.spoof_voltage_multi(target_bus_list, delta_v=self.v_bound * 0.6)
            for lid in target_lines:
                P_line_sp, _ = self.spoof_power(lid, delta_p=self.p_bound * 0.6,
                                                  consistent_with_v=V_sp, P_spoofed=P_line_sp)
            f_sp, df = self.spoof_frequency(region=region, delta_f=self.f_bound * 0.6)

        elif strategy == "stealthy":
            # Minimal perturbation: stay well within stealth bounds
            # Use consistency between V and P to avoid cross-measurement detection
            V_sp = self.spoof_voltage_multi(target_bus_list, delta_v=self.v_bound * 0.4)
            for lid in target_lines:
                P_line_sp, _ = self.spoof_power(lid, delta_p=self.p_bound * 0.3,
                                                  consistent_with_v=V_sp, P_spoofed=P_line_sp)
            # Tiny frequency drift
            f_sp, df = self.spoof_frequency(region=region,
                                             delta_f=self.f_bound * 0.2)
            # Spoof power injections at affected buses
            for bus in target_bus_list:
                P_inj_sp = self.spoof_power_injection(bus, delta_p=self.p_bound * 0.2)

        # --- Compute stealth metrics ---
        delta_V = V_sp - self.V_nom
        delta_P = P_line_sp - self.P_line_nom
        delta_V_norm = float(np.linalg.norm(delta_V))
        delta_P_norm = float(np.linalg.norm(delta_P))

        # Stealth score: 1 = perfectly stealthy, 0 = fully detectable
        v_stealth = 1.0 - delta_V_norm / (self.v_bound * np.sqrt(self.topo.num_buses))
        p_stealth = 1.0 - delta_P_norm / (self.p_bound * np.sqrt(len(self.topo.lines)))
        f_stealth = 1.0 - abs(df) / self.f_bound
        stealth_score = float(np.clip(
            0.4 * v_stealth + 0.35 * p_stealth + 0.25 * f_stealth, 0.0, 1.0
        ))

        return {
            "V_spoofed":       V_sp,
            "P_line_spoofed":  P_line_sp,
            "P_inj_spoofed":   P_inj_sp,
            "f_spoofed":       f_sp,
            "delta_V_norm":    delta_V_norm,
            "delta_P_norm":    delta_P_norm,
            "delta_f":         df,
            "strategy":        strategy,
            "target_lines":    target_lines,
            "target_buses":    list(target_buses),
            "stealth_score":   stealth_score,
        }

    # ------------------------------------------------------------------
    # 5. Jacobian-simulation FDIA (for baseline comparison)
    # ------------------------------------------------------------------

    def generate_jacobian_sim_fdia(self,
                                    target_lines: List[str],
                                    region: str = "NA") -> Dict:
        """
        Simulates a Jacobian-aware FDIA (oracle baseline).
        Uses the DC power flow B-matrix to construct H-consistent perturbation.
        This represents the upper-bound attacker who KNOWS the Jacobian.

        Used only as scientific baseline — not zero-parameter.
        """
        # Build simplified Jacobian from DC power flow B matrix
        try:
            from core.analytics.ptdf_engine import build_b_matrix
            B = build_b_matrix(self.topo)
        except Exception:
            B = np.eye(self.topo.num_buses, dtype=np.float32)

        n = self.topo.num_buses
        # Choose attack vector c (voltage angle changes)
        c = np.zeros(n, dtype=np.float32)
        target_buses = set()
        for lid in target_lines:
            idx = self._lid_to_idx.get(lid, -1)
            if idx >= 0:
                line = self.topo.lines[idx]
                f, t = line["from"], line["to"]
                target_buses.add(f)
                target_buses.add(t)
                c[f] += 0.03
                c[t] -= 0.03

        # Attack vector in measurement space: a = B @ c (approximation of H @ c)
        a = B @ c
        a_norm = np.linalg.norm(a)
        if a_norm > 1e-6:
            a = a / a_norm * self.p_bound * 0.8  # normalize to p_bound

        V_sp = self.V_nom.copy()
        for bus in target_buses:
            V_sp[bus] = np.clip(V_sp[bus] - 0.02, 0.90, 1.10)

        P_inj_sp = self.P_nom + a[:n]
        P_line_sp = self.P_line_nom.copy()

        delta_V = V_sp - self.V_nom
        delta_P = P_line_sp - self.P_line_nom
        f_sp, df = self.spoof_frequency(region=region, delta_f=self.f_bound * 0.5)

        stealth_score = float(np.clip(
            0.4 * (1 - np.linalg.norm(delta_V) / (self.v_bound * np.sqrt(n)))
            + 0.35 * (1 - np.linalg.norm(delta_P) / (self.p_bound * np.sqrt(len(self.topo.lines))))
            + 0.25 * (1 - abs(df) / self.f_bound),
            0.0, 1.0
        ))

        return {
            "V_spoofed":      V_sp,
            "P_line_spoofed": P_line_sp,
            "P_inj_spoofed":  P_inj_sp,
            "f_spoofed":      f_sp,
            "delta_V_norm":   float(np.linalg.norm(delta_V)),
            "delta_P_norm":   float(np.linalg.norm(delta_P)),
            "delta_f":        df,
            "strategy":       "jacobian_sim",
            "target_lines":   target_lines,
            "target_buses":   list(target_buses),
            "stealth_score":  stealth_score,
        }

    # ------------------------------------------------------------------
    # 6. Random FDIA baseline
    # ------------------------------------------------------------------

    def generate_random_fdia(self, region: str = "NA") -> Dict:
        """
        Random FDIA: uniform perturbations (no strategy).
        Used as lower-bound baseline.
        """
        n_buses = self.topo.num_buses
        n_lines = len(self.topo.lines)

        V_sp = self.V_nom + self.rng.uniform(
            -self.v_bound, self.v_bound, n_buses).astype(np.float32)
        V_sp = np.clip(V_sp, 0.90, 1.10)

        P_sp = self.P_line_nom + self.rng.uniform(
            -self.p_bound, self.p_bound, n_lines).astype(np.float32)

        P_inj_sp = self.P_nom + self.rng.uniform(
            -self.p_bound, self.p_bound, n_buses).astype(np.float32)

        df = self.rng.uniform(0.0, self.f_bound)
        f_sp = self.f_nom - df

        # Random targets: any k random lines
        k = min(5, n_lines)
        target_idx = self.rng.choice(n_lines, size=k, replace=False)
        target_lines = [self.topo.lines[i]["id"] for i in target_idx]

        delta_V = V_sp - self.V_nom
        delta_P = P_sp - self.P_line_nom
        stealth_score = float(np.clip(
            0.4 * (1 - np.linalg.norm(delta_V) / (self.v_bound * np.sqrt(n_buses)))
            + 0.35 * (1 - np.linalg.norm(delta_P) / (self.p_bound * np.sqrt(n_lines)))
            + 0.25 * (1 - df / self.f_bound),
            0.0, 1.0
        ))

        return {
            "V_spoofed":      V_sp,
            "P_line_spoofed": P_sp,
            "P_inj_spoofed":  P_inj_sp,
            "f_spoofed":      f_sp,
            "delta_V_norm":   float(np.linalg.norm(delta_V)),
            "delta_P_norm":   float(np.linalg.norm(delta_P)),
            "delta_f":        df,
            "strategy":       "random",
            "target_lines":   target_lines,
            "target_buses":   [],
            "stealth_score":  stealth_score,
        }
