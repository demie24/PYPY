# PYPY V10.2 — Imperfect / Black-Box Pathogen: Architecture & Research Specification

This document details the mathematical formulation, system architecture, observation masking strategies, active reconnaissance mechanics, and experimental validation plan for **PYPY V10.2 Imperfect / Black-Box Pathogen**. The goal is to reformulate the attacker problem from a fully observable Markov Decision Process (MDP) to a **Partially Observable Markov Decision Process (POMDP)**.

---

## 1. System Architecture Proposal

The V10.2 Pathogen architecture transitions the agent from a single PPO policy to a two-stage network: a Recurrent Belief Encoder and a Belief-Driven Actor-Critic Policy.

```
[ Power Grid Environment (True State S_t) ]
               │
               ▼
[ Observation Masking Engine (Mode A, B, C, D) ]
               │
               ▼ (Masked Observation O_t)
[ Gated Recurrent Unit (GRU) Belief Encoder ] <─── Previous Action A_t-1
               │
               ▼ (Belief State b_t)
      ┌────────┴────────┐
      ▼                 ▼
[ Actor Policy ]  [ Critic Value ]
  (Attack / Recon Actions A_t)
```

* **Observation Masking Engine**: Intercepts the true grid state $S_t$ and applies masking matrices depending on the selected difficulty mode.
* **GRU Belief Encoder**: A gated recurrent network that processes sequential observations and action histories to maintain a latent belief state $b_t$.
* **Belief-Driven Policy**: Outputs categorical distributions over coordinated attack types, target buses, and active reconnaissance probes.

---

## 2. POMDP Mathematical Formulation

We formally define the cyber-physical attack sequence as a POMDP characterized by the 7-tuple:
$$\mathcal{M} = (\mathcal{S}, \mathcal{A}, \mathcal{T}, \mathcal{R}, \Omega, \mathcal{O}, \gamma)$$

### 2.1 State Space $\mathcal{S}$
The true state $s_t \in \mathcal{S}$ represents the complete physical and cyber status of the grid:
$$s_t = \left( V_t, \theta_t, P_t, Q_t, B_t, K_t, \text{Trust}_t, \text{PINN}_t, \text{Consensus}_t \right)$$
where:
* $V_t, \theta_t, P_t, Q_t \in \mathbb{R}^{39}$: Bus voltages, angles, active injections, and reactive injections.
* $B_t \in \{0, 1\}^{46}$: Breaker statuses for the 46 lines.
* $K_t \in \{0, 1\}^{39}$: Quarantine indicators.
* $\text{Trust}_t \in [0.0, 1.0]^{39}$: Dynamic trust scores.
* $\text{PINN}_t \in [0.0, 1.0]$: Physics validation scores.
* $\text{Consensus}_t$: One-hot representation of the defender decision (`NORMAL`, `WARNING`, `ANOMALY`, `ATTACK_CONFIRMED`, `ISOLATE_COMPONENT`).

### 2.2 Action Space $\mathcal{A}$
The Pathogen's action $a_t \in \mathcal{A}$ is partitioned into physical/cyber attacks and active reconnaissance:
$$a_t = a_t^{\text{attack}} \cup a_t^{\text{recon}}$$
* $a_t^{\text{attack}} = \{\text{NO\_ACTION}, \text{FDIA}, \text{REPLAY}, \text{DOS}, \text{TRIP\_LINE}\}$
* $a_t^{\text{recon}} = \{\text{SCAN\_BUS}(i), \text{SCAN\_LINE}(ij), \text{PROBE\_DEVICE}(i), \text{OBSERVE\_TRAFFIC}(i)\}$

### 2.3 Transition Probability $\mathcal{T}$
The transition dynamics $\mathcal{T}(s' \mid s, a) = \mathbb{P}(s_{t+1} = s' \mid s_t = s, a_t = a)$ are governed by:
1. AC power flow physics equations solved via pandapower.
2. Attacker injections and breaker trips.
3. Defender isolation breaker actions and sensor quarantine resets.

### 2.4 Observation Space $\Omega$ & Observation Probability $\mathcal{O}$
The observation $o_t \in \Omega$ represents the attacker's masked view of the grid, determined by the mapping:
$$o_t \sim \mathcal{O}(o_t \mid s_t, a_{t-1})$$
Details of this masking strategy across the four modes are formalized in Section 3.

### 2.5 Discount Factor $\gamma$
Set to $\gamma = 0.99$ to incentivize long-term sequential planning (e.g. scanning a bus to gather information before executing a target injection).

---

## 3. Observation Masking Strategy & Noise Models

To simulate varying levels of attacker capabilities, we define four distinct masking operators:

```
MODE A: Full Knowledge (100% Visibility)
[ V, theta, P, Q, Breakers, Trust, PINN, Consensus ] ──> All values visible (No Noise)

MODE B: Limited Knowledge (50% Visibility)
[ V, theta, P, Q, Breakers ] ──> Visible + Low Gaussian Noise (sigma = 0.01)
[ Trust, PINN, Consensus ] ──> Replaced with zero-padding

MODE C: Restricted Knowledge (20% Visibility)
[ Local V, theta, P, Q at compromised buses only ] ──> Visible + High Gaussian Noise (sigma = 0.03)
[ Remainder of grid telemetry & defender states ] ──> Masked as default/noise

MODE D: Black Box Attacker (Topology Only)
[ Adjacency Matrix A ] ──> Visible (No Noise)
[ All real-time telemetry and defender states ] ──> Replaced with zero-padding
```

### 3.1 Adaptive Observation Noise Model
For nominal state parameters $x$ under Mode B and Mode C, observations are contaminated by Gaussian noise:
$$\hat{x} = x + \epsilon_t, \quad \epsilon_t \sim \mathcal{N}(0, \sigma_t^2)$$
The standard deviation $\sigma_t$ scales adaptively based on network-level interference and cyber defenses:
$$\sigma_t = \sigma_0 \cdot \left( 1.0 + \alpha_{\text{DoS}} \cdot \sum_{i \in \text{DoS}} \mathbb{I}_i + \alpha_{\text{Quar}} \cdot \sum_{j \in \text{Quar}} \mathbb{I}_j + (1.0 - \bar{T}_{\text{trust}}) \right)$$
where:
* $\sigma_0$ is the baseline noise standard deviation ($0.01$ for Mode B, $0.03$ for Mode C).
* $\alpha_{\text{DoS}} = 0.50$: Local channel degradation scaling factor under DoS.
* $\alpha_{\text{Quar}} = 0.30$: Local telemetry sandboxing interference factor.
* $\bar{T}_{\text{trust}}$: Average grid trust score. If security defenses are alert, noise levels increase.

---

## 4. Active Reconnaissance & Alert Subsystem

Under Modes B, C, and D, the Pathogen can actively execute scanning commands to gather information. Reconnaissance actions update the observation probability distribution but carry negative rewards (costs) and increase detection risks.

### 4.1 Compounding Detection Alert Probability
The probability of triggering an alert $P_d(t)$ scales non-linearly with consecutive reconnaissance scans:
$$P_d(t) = 1.0 - (1.0 - P_{\text{base}})^k$$
where:
* $P_{\text{base}}$ is the base detection probability of the action:
  * `SCAN_BUS(i)`: $5\%$
  * `SCAN_LINE(ij)`: $2\%$
  * `PROBE_DEVICE(i)`: $15\%$
  * `OBSERVE_TRAFFIC(i)`: $8\%$
* $k$ is the sequence of consecutive scans without a cooling period. The parameter $k$ decays exponentially when the attacker ceases scanning:
  $$k_{t+1} = \max\left(1.0, k_t \cdot \gamma_{\text{cool}}\right)$$
  where $\gamma_{\text{cool}} = 0.85$ is the cooling decay coefficient.

If detection occurs, the target node trust score degrades by $-0.15$, the consensus layer increments its anomaly counter, and the defender's awareness increases, causing visibility parameters to decay.

---

## 5. Dynamic Observability & Defensive Adaptive Environments

Observability is not static; it responds dynamically to attacker scans and defender countermeasures. Let $V(t) \in [0.0, 1.0]$ denote the overall visibility fraction of the grid:

$$V(t+1) = \text{clip}\left( V(t) \cdot \prod_{a \in A_{\text{recon}}} (1.0 + g_a) - \sum_{m \in M_{\text{defense}}} d_m, 0.0, 1.0 \right)$$

where:
* $g_a$ is the information gain multiplier per scan ($g_{\text{SCAN}} = 0.15$, $g_{\text{PROBE}} = 0.05$).
* $d_m$ represents the visibility degradation imposed by defensive countermeasures:
  * Telemetry Quarantine: $d_{\text{Quar}} = 0.20$
  * Bus Isolation: $d_{\text{Isolate}} = 0.40$
  * Global Warning State: $d_{\text{Warning}} = 0.10$

This adversarial environment makes the defender adaptively block port scanning and shut down network flows in response to scanning probes.

---

## 6. Information Theory-Based Metrics

To quantify reconnaissance efficiency, we define **Information Gain (IG)** as the reduction in belief state entropy:

$$IG(a) = H(b_{\text{before}}) - H(b_{\text{after}})$$

The belief state distribution over a hidden parameter $X_i$ is modeled as a Gaussian $\mathcal{N}(\mu_{b, i}, \sigma_{b, i}^2)$. The entropy is:
$$H(b) = \frac{1}{2} \ln\left(2\pi e \sigma_{b, i}^2\right)$$
Thus, the Information Gain from action $a$ is:
$$IG(a) = \frac{1}{2} \sum_{i \in \text{Target}} \ln\left( \frac{\sigma_{b, i, \text{before}}^2}{\sigma_{b, i, \text{after}}^2} \right)$$

### 6.1 Scan Efficiency Optimization
The Pathogen is penalized to optimize the **Disruption-to-Information Ratio**:
$$\text{Efficiency} = \frac{R_{\text{disruption}}}{1.0 + \sum IG(a)}$$
This forces the agent to learn to ignore redundant scans that do not resolve uncertainty about critical targets.

---

## 7. Recurrent Belief State Design

Because the true state $s_t$ is hidden, the policy cannot map directly from $o_t$ to $a_t$. The Pathogen utilizes a **Gated Recurrent Unit (GRU)** to construct a sequential memory embedding:

$$b_t = \text{GRU}(b_{t-1}, [o_t \mathbin{\Vert} a_{t-1}])$$

where:
* $b_t \in \mathbb{R}^{64}$: Latent belief state vector.
* $o_t$: Current masked observation vector.
* $a_{t-1}$: Previous action taken by the attacker (one-hot encoded).

The actor network $\pi_\theta(a_t \mid b_t)$ and critic network $V_\phi(b_t)$ are evaluated directly on the belief vector $b_t$:

```
 Belief Vector (b_t) ──> [ Dense Layer ] ──> ReLU ──> [ Categorical Logits ] ──> Action (a_t)
```

---

## 8. Reward Formulation

To balance attack effectiveness against cost and stealth, the POMDP reward function is defined as:

$$R_t = R_{\text{disruption}} + R_{\text{stealth}} - C_{\text{recon}} - P_{\text{detection}}$$

where:
1. **Disruption**: $R_{\text{disruption}} = \sum_{i=1}^{39} \vert V_i - 1.0 \vert + \sum_{ij} \max(0, I_{ij} - 1.5) + 100.0 \cdot \mathbb{I}_{\text{blackout}}$
2. **Stealth**: $R_{\text{stealth}} = +5.0$ if $\text{Consensus}_t = \text{"NORMAL"}$.
3. **Reconnaissance Cost**: $C_{\text{recon}} = \sum_{a \in a_t^{\text{recon}}} \text{cost}(a)$
4. **Detection Penalty**: $P_{\text{detection}} = -50.0 \cdot \mathbb{I}_{\text{Consensus}_t \in \{\text{"ATTACK\_CONFIRMED", "ISOLATE\_COMPONENT"}\}}$

This forces the agent to optimize the timing of scans: scanning too much depletes rewards and triggers alarms, while scanning too little leads to failed attacks due to high state uncertainty.

---

## 9. Experimental Validation Methodology

We propose a validation suite to evaluate the impact of information restriction on attack performance:

```
[ Validation Suite ]
   ├── Config 1: Mode A (Full Observability) ──> Base reference
   ├── Config 2: Mode B (Limited)           ──> Evaluate lack of defense awareness
   ├── Config 3: Mode C (Restricted)        ──> Evaluate local-only tracking
   └── Config 4: Mode D (Black-Box)         ──> Evaluate topology-only inference
```

### 9.1 Evaluated Metrics
* **Blackout Success Rate**: Percentage of episodes resulting in a solver non-convergence.
* **Detection Latency**: Number of steps from the first attack action to a `WARNING` or `ANOMALY` classification in the consensus layer.
* **Reconnaissance Efficiency Ratio**:
  $$\text{Efficiency} = \frac{\text{Disruption Score}}{\text{Total Recon Costs}}$$
* **Policy Entropy**: Measures policy randomization under high uncertainty.
* **Learning Speed**: Episodes required to converge to optimal policy.

### 9.2 Verification of Emergent Reconnaissance
To confirm the emergence of "Scan-then-Attack" sequences, the training log compiles:
* **Scan Frequency**: Number of active recon actions per episode.
* **Attack Delay After Scan**: Number of waiting steps between a scan execution and a physical trip command.
* **Information Gain Delta**: Difference in node uncertainty before and after scan sequences.

---

## 10. Publication-Quality Figures List

To visually document the results of these experiments, we define the following 3 output plots:
1. `recon_frequency_vs_episodes.png`: Shows how scanning frequency decays as the agent learns optimal target selection and avoids detection penalties.
2. `information_gain_vs_episodes.png`: Plots the average entropy reduction ($IG$) per scan step over training.
3. `scan_then_attack_patterns.png`: Tracks the temporal correlation between scanning events and attack execution, showing the development of coordinated reconnaissance campaigns.

---

## 11. Computational Complexity Analysis

* **Adaptive Noise & Masking**: Masking and adding noise is computationally trivial, requiring an element-wise matrix multiplication and drawing from a Gaussian distribution:
  $$\text{Complexity: } \mathcal{O}(D)$$
  where $D=293$. It executes in $<10$ microseconds.
* **Entropy & Information Gain**: Computing Gaussian entropy requires only retrieving the variance vector of the belief state, mapping to $\mathcal{O}(V)$ operations where $V=39$.
* **Training Scaling**: Due to the partially observable state space, the PPO agent requires a recurrent network (GRU). Training time will scale by $\sim 3\times$ compared to standard feed-forward networks, taking approximately $3,000$ to $4,500$ episodes for convergence. The inference execution time is $< 0.2$ ms, maintaining real-time simulator compatibility.

---

## 12. Development Roadmap

### Phase 1: POMDP Environment Wrapper (Weeks 1-2)
* **Objective**: Create `ImperfectPathogenEnv` implementing the observation masks, Gaussian noise models, dynamic visibility, and alert probabilities.
* **Milestone**: Unit tests validating noise variance scaling and masking shapes.

### Phase 2: GRU Belief Agent (Weeks 3-4)
* **Objective**: Integrate the GRU layer into `PathogenAgent`. Train the agent under Mode B (Limited Knowledge).
* **Milestone**: Stable training curves under 50% observability.

### Phase 3: Active Reconnaissance Policies (Weeks 5-6)
* **Objective**: Retrain the agent under Mode C (Restricted Knowledge). Verify if the agent learns to schedule `SCAN_BUS` and `SCAN_LINE` actions dynamically.
* **Milestone**: Emergence of "Scan-then-Attack" sequential patterns.

### Phase 4: Black-Box Validation (Weeks 7-8)
* **Objective**: Train and evaluate under Mode D. Compare performance metrics across all modes.
* **Milestone**: Write V10.2 Final Research Report and compile comparative graphs.
