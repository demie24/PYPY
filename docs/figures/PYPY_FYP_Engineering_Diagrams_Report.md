# PYPY (Protect Your Power, Protect Yourself) FYP Engineering Diagrams

This document contains the official engineering architecture and workflow diagrams for the **PYPY Smart Grid Cybersecurity SaaS & Research Platform**, rendered according to IEEE paper and UniMAP Final Year Project (FYP) academic logbook standards.

---

## Fig M1 Microservices Architecture

![fig_m1_microservices_architecture](./fig_m1_microservices_architecture.png)

### Mermaid Syntax
```mermaid
graph TD
    subgraph Presentation_Layer ["Presentation Layer"]
        User["User / Operator"] -->|HTTP / WS| Dashboard["React Dashboard"]
    end

    subgraph Application_Layer ["Application Layer"]
        Gateway["FastAPI Gateway"] <-->|IPC / Events| MQTT["MQTT Broker (Mosquitto)"]
    end

    Dashboard -->|REST API| Gateway
    Dashboard -->|WS Stream| MQTT

    subgraph Intelligence_Layer ["Intelligence Layer"]
        DigitalTwin["Digital Twin Engine (Pandapower)"]
        subgraph AI_Layer ["AI Subsystem Layer"]
            PINN["Physics-Informed Neural Network (PINN)"]
            STGNN["Spatial-Temporal Graph Neural Net (ST-GNN)"]
            PPO["PPO Reinforcement Learning Agent"]
        end
    end

    MQTT -->|Telemetry| DigitalTwin
    MQTT -->|Grid Events| AI_Layer
    DigitalTwin -->|State Features| AI_Layer

    subgraph Infrastructure_Layer ["Infrastructure Layer"]
        Postgres[(PostgreSQL Database)]
        Redis[(Redis Cache & Broker)]
        Docker[Docker Containers]
    end

    Gateway --> Postgres
    AI_Layer --> Redis
    DigitalTwin --> Docker

```

### PlantUML Syntax
```plantuml
@startuml
skinparam backgroundcolor #FFFFFF
skinparam defaultFontName Arial
skinparam RectangleBackgroundColor #FFFFFF
skinparam RectangleBorderColor #003366
skinparam RectangleFontColor #003366
skinparam RectangleFontStyle bold

package "Presentation Layer" {
  [User / Operator] as User
  [React Dashboard] as Dashboard
}

package "Application Layer" {
  [FastAPI Gateway] as Gateway
  [MQTT Broker] as MQTT
}

package "Intelligence Layer" {
  [Digital Twin Engine (Pandapower)] as DigitalTwin
  package "AI Layer" {
    [Physics-Informed Neural Network (PINN)] as PINN
    [Spatial-Temporal Graph Neural Net (ST-GNN)] as STGNN
    [PPO Reinforcement Learning Agent] as PPO
  }
}

package "Infrastructure Layer" {
  database "PostgreSQL Database" as Postgres
  database "Redis" as Redis
  node "Docker Containers" as Docker
}

User --> Dashboard : Interactions
Dashboard --> Gateway : REST API
Dashboard --> MQTT : WS Stream
Gateway <--> MQTT : Event Bus
MQTT --> DigitalTwin : Telemetry
DigitalTwin --> PINN : Features
DigitalTwin --> STGNN : Graph Topo
DigitalTwin --> PPO : State Vector
Gateway --> Postgres : Persistence
PPO --> Redis : Memory State
Intelligence Layer ..> Docker : Container Runtime

caption Figure M.1 Complete PYPY microservices architecture.
@enduml
```

**Files Generated:**
- SVG: [`fig_m1_microservices_architecture.svg`](./fig_m1_microservices_architecture.svg)
- PNG (300 DPI): [`fig_m1_microservices_architecture.png`](./fig_m1_microservices_architecture.png)
- Draw.io: [`fig_m1_microservices_architecture.drawio`](./fig_m1_microservices_architecture.drawio)
- Mermaid: [`fig_m1_microservices_architecture.mmd`](./fig_m1_microservices_architecture.mmd)
- PlantUML: [`fig_m1_microservices_architecture.puml`](./fig_m1_microservices_architecture.puml)

---

## Fig O1 Physics Detection Pipeline

![fig_o1_physics_detection_pipeline](./fig_o1_physics_detection_pipeline.png)

### Mermaid Syntax
```mermaid
graph TD
    Telemetry["Telemetry Data"] --> DataVal["Data Validation"]
    DataVal --> KCL["Kirchhoff Current Law (KCL)"]
    KCL --> KVL["Kirchhoff Voltage Law (KVL)"]
    KVL --> PowerBal["Power Balance Verification"]
    PowerBal --> TrustScore["Trust Score Calculation"]
    TrustScore --> Decision{"Trust Score ≥ Threshold?"}

    Decision -->|YES| Normal["Normal Grid State"]
    Decision -->|NO| Suspicious["Suspicious / Anomaly Detected"]
    Suspicious --> AIAnalysis["AI Analysis (PINN & ST-GNN)"]

```

### PlantUML Syntax
```plantuml
@startuml
skinparam backgroundcolor #FFFFFF
skinparam defaultFontName Arial
skinparam ActivityBackgroundColor #F8FAFC
skinparam ActivityBorderColor #003366
skinparam ActivityFontColor #003366
skinparam ActivityFontStyle bold

start
:Telemetry Data;
:Data Validation;
:Kirchhoff Current Law (KCL);
:Kirchhoff Voltage Law (KVL);
:Power Balance Verification;
:Trust Score Calculation;

if (Trust Score >= Threshold?) then (Yes)
  :Normal Grid State;
else (No)
  :Suspicious / Anomaly Detected;
  :AI Analysis;
endif
stop

caption Figure O.1 Physics-based anomaly detection workflow.
@enduml
```

**Files Generated:**
- SVG: [`fig_o1_physics_detection_pipeline.svg`](./fig_o1_physics_detection_pipeline.svg)
- PNG (300 DPI): [`fig_o1_physics_detection_pipeline.png`](./fig_o1_physics_detection_pipeline.png)
- Draw.io: [`fig_o1_physics_detection_pipeline.drawio`](./fig_o1_physics_detection_pipeline.drawio)
- Mermaid: [`fig_o1_physics_detection_pipeline.mmd`](./fig_o1_physics_detection_pipeline.mmd)
- PlantUML: [`fig_o1_physics_detection_pipeline.puml`](./fig_o1_physics_detection_pipeline.puml)

---

## Fig P1 Newton Raphson Solver

![fig_p1_newton_raphson_solver](./fig_p1_newton_raphson_solver.png)

### Mermaid Syntax
```mermaid
graph TD
    Init["Initialize IEEE Network"] --> Breaker["Update Breaker Status"]
    Breaker --> Load["Update Load Demand"]
    Load --> Ybus["Construct Admittance Matrix (Y_bus)"]
    Ybus --> NR["Newton-Raphson Iteration"]
    NR --> Decision{"Converged? (|ΔP|, |ΔQ| < ε)"}
    Decision -->|YES| Telemetry["Generate Telemetry"]
    Decision -->|NO| NR

```

### PlantUML Syntax
```plantuml
@startuml
skinparam backgroundcolor #FFFFFF
skinparam defaultFontName Arial
skinparam ActivityBackgroundColor #F8FAFC
skinparam ActivityBorderColor #003366
skinparam ActivityFontColor #003366
skinparam ActivityFontStyle bold

start
:Initialize IEEE Network;
:Update Breaker Status;
:Update Load Demand;
:Construct Admittance Matrix;
repeat
  :Newton-Raphson Iteration;
repeat while (Converged?) is (NO)
->YES;
:Generate Telemetry;
stop

caption Figure P.1 Newton-Raphson AC Power Flow Solver workflow.
@enduml
```

**Files Generated:**
- SVG: [`fig_p1_newton_raphson_solver.svg`](./fig_p1_newton_raphson_solver.svg)
- PNG (300 DPI): [`fig_p1_newton_raphson_solver.png`](./fig_p1_newton_raphson_solver.png)
- Draw.io: [`fig_p1_newton_raphson_solver.drawio`](./fig_p1_newton_raphson_solver.drawio)
- Mermaid: [`fig_p1_newton_raphson_solver.mmd`](./fig_p1_newton_raphson_solver.mmd)
- PlantUML: [`fig_p1_newton_raphson_solver.puml`](./fig_p1_newton_raphson_solver.puml)

---

## Fig P2 Telemetry Streaming

![fig_p2_telemetry_streaming](./fig_p2_telemetry_streaming.png)

### Mermaid Syntax
```mermaid
graph LR
    Twin["Digital Twin Solver"] --> Volt["Voltage Calculation"]
    Volt --> Curr["Current Calculation"]
    Curr --> Load["Line Loading Calculation"]
    Load --> JSON["JSON Formatting"]
    JSON --> MQTT["MQTT Topic (grid/telemetry)"]
    MQTT --> Gateway["FastAPI Gateway"]
    Gateway --> Dash["React Dashboard"]

```

### PlantUML Syntax
```plantuml
@startuml
skinparam backgroundcolor #FFFFFF
skinparam defaultFontName Arial
skinparam ActivityBackgroundColor #F8FAFC
skinparam ActivityBorderColor #003366
skinparam ActivityFontColor #003366
skinparam ActivityFontStyle bold

start
:Digital Twin Solver;
:Voltage Calculation;
:Current Calculation;
:Line Loading Calculation;
:JSON Formatting;
:MQTT Topic;
:FastAPI Gateway;
:React Dashboard;
stop

caption Figure P.2 Digital Twin telemetry streaming workflow.
@enduml
```

**Files Generated:**
- SVG: [`fig_p2_telemetry_streaming.svg`](./fig_p2_telemetry_streaming.svg)
- PNG (300 DPI): [`fig_p2_telemetry_streaming.png`](./fig_p2_telemetry_streaming.png)
- Draw.io: [`fig_p2_telemetry_streaming.drawio`](./fig_p2_telemetry_streaming.drawio)
- Mermaid: [`fig_p2_telemetry_streaming.mmd`](./fig_p2_telemetry_streaming.mmd)
- PlantUML: [`fig_p2_telemetry_streaming.puml`](./fig_p2_telemetry_streaming.puml)

---

## Fig Q1 Pinn Training Workflow

![fig_q1_pinn_training_workflow](./fig_q1_pinn_training_workflow.png)

### Mermaid Syntax
```mermaid
graph TD
    Input["Input Telemetry"] --> Enc["Encoder"]
    Enc --> Latent["Latent Representation (z)"]
    Latent --> Dec["Decoder"]
    Dec --> Pred["Prediction"]

    subgraph LossEngine ["Composite Loss Function Engine"]
        L_Data["Supervised Loss (L_data)"]
        L_KCL["KCL Constraint (L_KCL)"]
        L_KVL["KVL Constraint (L_KVL)"]
    end

    Pred --> LossEngine
    L_Data --> WeightBal["Dynamic Weight Balancing"]
    L_KCL --> WeightBal
    L_KVL --> WeightBal

    WeightBal --> Backprop["Backpropagation"]
    Backprop --> ModelUpdate["Updated Model"]

```

### PlantUML Syntax
```plantuml
@startuml
skinparam backgroundcolor #FFFFFF
skinparam defaultFontName Arial
skinparam ActivityBackgroundColor #F8FAFC
skinparam ActivityBorderColor #003366
skinparam ActivityFontColor #003366
skinparam ActivityFontStyle bold

start
:Input Telemetry;
:Encoder;
:Latent Representation;
:Decoder;
:Prediction;
partition "Loss Function Engine" {
  fork
    :Supervised Loss;
  fork again
    :KCL Constraint;
  fork again
    :KVL Constraint;
  end fork
}
:Dynamic Weight Balancing;
:Backpropagation;
:Updated Model;
stop

caption Figure Q.1 Physics-Informed Neural Network training workflow.
@enduml
```

**Files Generated:**
- SVG: [`fig_q1_pinn_training_workflow.svg`](./fig_q1_pinn_training_workflow.svg)
- PNG (300 DPI): [`fig_q1_pinn_training_workflow.png`](./fig_q1_pinn_training_workflow.png)
- Draw.io: [`fig_q1_pinn_training_workflow.drawio`](./fig_q1_pinn_training_workflow.drawio)
- Mermaid: [`fig_q1_pinn_training_workflow.mmd`](./fig_q1_pinn_training_workflow.mmd)
- PlantUML: [`fig_q1_pinn_training_workflow.puml`](./fig_q1_pinn_training_workflow.puml)

---

## Fig R1 Ppo Decision Loop

![fig_r1_ppo_decision_loop](./fig_r1_ppo_decision_loop.png)

### Mermaid Syntax
```mermaid
graph TD
    GridState["Grid State (s_t)"] --> Obs["Observation"]
    Obs --> Policy["Policy Network (π_θ)"]
    Policy --> Action["Action Selection (a_t)"]
    Action --> Breaker["Breaker Control"]
    Breaker --> Response["Grid Response"]
    Response --> Reward["Reward Calculation"]
    Reward --> Update["Policy Update"]
    Update -->|Repeat Loop| GridState

```

### PlantUML Syntax
```plantuml
@startuml
skinparam backgroundcolor #FFFFFF
skinparam defaultFontName Arial
skinparam ActivityBackgroundColor #F8FAFC
skinparam ActivityBorderColor #003366
skinparam ActivityFontColor #003366
skinparam ActivityFontStyle bold

start
repeat
  :Grid State (s_t);
  :Observation;
  :Policy Network (π_θ);
  :Action Selection (a_t);
  :Breaker Control;
  :Grid Response;
  :Reward Calculation;
  :Policy Update;
repeat while (Repeat Loop)

caption Figure R.1 PPO self-healing decision loop.
@enduml
```

**Files Generated:**
- SVG: [`fig_r1_ppo_decision_loop.svg`](./fig_r1_ppo_decision_loop.svg)
- PNG (300 DPI): [`fig_r1_ppo_decision_loop.png`](./fig_r1_ppo_decision_loop.png)
- Draw.io: [`fig_r1_ppo_decision_loop.drawio`](./fig_r1_ppo_decision_loop.drawio)
- Mermaid: [`fig_r1_ppo_decision_loop.mmd`](./fig_r1_ppo_decision_loop.mmd)
- PlantUML: [`fig_r1_ppo_decision_loop.puml`](./fig_r1_ppo_decision_loop.puml)

---

## Fig S1 Grid Resilience Scoring

![fig_s1_grid_resilience_scoring](./fig_s1_grid_resilience_scoring.png)

### Mermaid Syntax
```mermaid
graph TD
    Attack["Cyberattack Event"] --> Detect["Detection"]
    Detect --> Isolate["Isolation"]
    Isolate --> Restore["System Restoration"]

    subgraph MultiMetric ["Multi-Metric Evaluation Module"]
        V_Assess["Voltage Recovery Assessment (R_V)"]
        I_Assess["Thermal Loading Assessment (R_I)"]
        S_Assess["Switching Operation Assessment (R_S)"]
        T_Assess["Restoration Time Assessment (R_T)"]
    end

    Restore --> MultiMetric
    MultiMetric --> ResilienceScore["Grid Resilience Score Aggregator"]

```

### PlantUML Syntax
```plantuml
@startuml
skinparam backgroundcolor #FFFFFF
skinparam defaultFontName Arial
skinparam ActivityBackgroundColor #F8FAFC
skinparam ActivityBorderColor #003366
skinparam ActivityFontColor #003366
skinparam ActivityFontStyle bold

start
:Cyberattack Event;
:Detection;
:Isolation;
:System Restoration;
partition "Multi-Metric Evaluation Module" {
  fork
    :Voltage Recovery Assessment;
  fork again
    :Thermal Loading Assessment;
  fork again
    :Switching Operation Assessment;
  fork again
    :Restoration Time Assessment;
  end fork
}
:Grid Resilience Score;
stop

caption Figure S.1 Grid resilience scoring workflow.
@enduml
```

**Files Generated:**
- SVG: [`fig_s1_grid_resilience_scoring.svg`](./fig_s1_grid_resilience_scoring.svg)
- PNG (300 DPI): [`fig_s1_grid_resilience_scoring.png`](./fig_s1_grid_resilience_scoring.png)
- Draw.io: [`fig_s1_grid_resilience_scoring.drawio`](./fig_s1_grid_resilience_scoring.drawio)
- Mermaid: [`fig_s1_grid_resilience_scoring.mmd`](./fig_s1_grid_resilience_scoring.mmd)
- PlantUML: [`fig_s1_grid_resilience_scoring.puml`](./fig_s1_grid_resilience_scoring.puml)

---
