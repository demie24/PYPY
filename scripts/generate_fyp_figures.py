#!/usr/bin/env python3
"""
PYPY (Protect Your Power, Protect Yourself) FYP & IEEE Engineering Diagram Generator
Generates SVG, PNG (300 DPI), Draw.io (.drawio), Mermaid (.mmd), and PlantUML (.puml)
for all 7 core system architecture & workflow figures.
"""

import os
import sys
import subprocess

OUTPUT_DIR = os.path.abspath("docs/figures")
os.makedirs(OUTPUT_DIR, exist_ok=True)

COLOR_PRIMARY = "#003366"      # Deep Navy
COLOR_SECONDARY = "#1A5276"    # Steel Blue
COLOR_ACCENT = "#2980B9"       # Bright IEEE Blue
COLOR_LIGHT_BG = "#F8FAFC"     # Container fill
COLOR_BORDER = "#2C3E50"       # Line/Box Border
COLOR_TEXT_MAIN = "#1A252C"    # Main dark text
COLOR_TEXT_MUTED = "#566573"   # Subtext

def wrap_svg(width, height, title, caption, content_svg):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">
  <defs>
    <style>
      .title {{ font-family: 'Arial', 'Helvetica', sans-serif; font-size: 17px; font-weight: bold; fill: {COLOR_PRIMARY}; text-anchor: middle; letter-spacing: 0.5px; }}
      .caption {{ font-family: 'Arial', 'Helvetica', sans-serif; font-size: 13.5px; font-weight: bold; fill: {COLOR_TEXT_MAIN}; text-anchor: middle; }}
      .layer-title {{ font-family: 'Arial', 'Helvetica', sans-serif; font-size: 12px; font-weight: bold; fill: {COLOR_PRIMARY}; letter-spacing: 0.5px; }}
      .box-title {{ font-family: 'Arial', 'Helvetica', sans-serif; font-size: 12px; font-weight: bold; fill: {COLOR_PRIMARY}; text-anchor: middle; }}
      .box-desc {{ font-family: 'Arial', 'Helvetica', sans-serif; font-size: 10.5px; fill: {COLOR_TEXT_MAIN}; text-anchor: middle; }}
      .box-muted {{ font-family: 'Arial', 'Helvetica', sans-serif; font-size: 9.5px; fill: {COLOR_TEXT_MUTED}; text-anchor: middle; }}
      .line-label {{ font-family: 'Arial', 'Helvetica', sans-serif; font-size: 10px; font-weight: bold; fill: {COLOR_SECONDARY}; text-anchor: middle; }}
      .layer-rect {{ fill: #F8FAFC; stroke: #CBD5E1; stroke-width: 1.5px; stroke-dasharray: 4,4; rx: 6px; }}
      .node-rect {{ fill: #FFFFFF; stroke: {COLOR_PRIMARY}; stroke-width: 1.75px; rx: 5px; }}
      .node-fill {{ fill: #F1F5F9; stroke: {COLOR_PRIMARY}; stroke-width: 1.75px; rx: 5px; }}
      .node-rhombus {{ fill: #EBF5FB; stroke: {COLOR_PRIMARY}; stroke-width: 1.75px; }}
      .arrow-line {{ stroke: {COLOR_BORDER}; stroke-width: 1.75px; fill: none; marker-end: url(#arrow); }}
      .dashed-line {{ stroke: {COLOR_SECONDARY}; stroke-width: 1.5px; stroke-dasharray: 4,4; fill: none; marker-end: url(#arrow-blue); }}
    </style>
    <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 10 5 L 0 9 z" fill="{COLOR_BORDER}" />
    </marker>
    <marker id="arrow-blue" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 10 5 L 0 9 z" fill="{COLOR_SECONDARY}" />
    </marker>
  </defs>

  <!-- Background -->
  <rect width="{width}" height="{height}" fill="#FFFFFF" />
  <rect x="15" y="15" width="{width - 30}" height="{height - 30}" fill="none" stroke="#E2E8F0" stroke-width="1.5" />

  <!-- Header Title -->
  <text x="{width / 2}" y="45" class="title">{title.upper()}</text>
  <line x1="{width / 2 - 180}" y1="54" x2="{width / 2 + 180}" y2="54" stroke="{COLOR_PRIMARY}" stroke-width="1.5" />

  <!-- Content -->
  {content_svg}

  <!-- Caption -->
  <text x="{width / 2}" y="{height - 25}" class="caption">{caption}</text>
</svg>'''

def make_drawio(name, title, cells_xml):
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<mxfile host="Electron" agent="Mozilla/5.0" version="21.0.0" type="device">
  <diagram id="{name}" name="{title}">
    <mxGraphModel dx="1200" dy="800" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1169" pageHeight="827" math="0" shadow="0">
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />
        {cells_xml}
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>'''

# ==============================================================================
# FIGURE M.1: Complete PYPY Microservices Architecture
# ==============================================================================
def gen_fig_m1():
    w, h = 1100, 920
    title = "Complete PYPY Microservices Architecture"
    caption = "Figure M.1 Complete PYPY microservices architecture."

    svg_body = '''
    <!-- Presentation Layer -->
    <rect x="50" y="80" width="1000" height="150" class="layer-rect" />
    <text x="70" y="105" class="layer-title">PRESENTATION LAYER</text>

    <rect x="200" y="120" width="220" height="80" class="node-rect" />
    <text x="310" y="152" class="box-title">User / Operator</text>
    <text x="310" y="172" class="box-desc">Grid Dispatcher / Analyst</text>

    <rect x="680" y="120" width="260" height="80" class="node-rect-fill" />
    <text x="810" y="152" class="box-title">React Dashboard</text>
    <text x="810" y="172" class="box-desc">Single-Line Diagram &amp; Alerts UI</text>

    <!-- Arrow Presentation -->
    <path d="M 420 160 L 680 160" class="arrow-line" />
    <text x="550" y="152" class="line-label">HTTP / WebSocket</text>

    <!-- Application Layer -->
    <rect x="50" y="270" width="1000" height="170" class="layer-rect" />
    <text x="70" y="295" class="layer-title">APPLICATION LAYER</text>

    <rect x="200" y="315" width="260" height="90" class="node-rect-fill" />
    <text x="330" y="350" class="box-title">FastAPI Gateway</text>
    <text x="330" y="370" class="box-desc">REST Endpoints, WS Router, JWT</text>

    <rect x="680" y="315" width="260" height="90" class="node-rect-fill" />
    <text x="810" y="350" class="box-title">MQTT Broker</text>
    <text x="810" y="370" class="box-desc">Eclipse Mosquitto (Pub/Sub Bus)</text>

    <path d="M 460 360 L 680 360" class="arrow-line" />
    <text x="570" y="352" class="line-label">Internal IPC / Events</text>

    <path d="M 810 200 L 810 315" class="arrow-line" />
    <text x="825" y="260" class="line-label">WS Stream</text>

    <path d="M 330 200 L 330 315" class="arrow-line" />
    <text x="345" y="260" class="line-label">REST API Calls</text>

    <!-- Intelligence Layer -->
    <rect x="50" y="480" width="1000" height="210" class="layer-rect" />
    <text x="70" y="505" class="layer-title">INTELLIGENCE LAYER</text>

    <rect x="80" y="530" width="260" height="130" class="node-rect" />
    <text x="210" y="585" class="box-title">Digital Twin Engine</text>
    <text x="210" y="605" class="box-desc">Pandapower Solver (IEEE 9-Bus)</text>

    <!-- AI Subsystem Box -->
    <rect x="390" y="515" width="630" height="155" fill="#FFFFFF" stroke="#1A5276" stroke-width="1.5" rx="5" stroke-dasharray="3,3" />
    <text x="410" y="537" class="layer-title" style="font-size:11px;">AI SUBSYSTEM LAYER</text>

    <rect x="410" y="555" width="180" height="90" class="node-rect-fill" />
    <text x="500" y="590" class="box-title">PINN Module</text>
    <text x="500" y="610" class="box-desc">Physics-Informed Neural Net</text>

    <rect x="615" y="555" width="180" height="90" class="node-rect-fill" />
    <text x="705" y="590" class="box-title">ST-GNN Module</text>
    <text x="705" y="610" class="box-desc">Spatial-Temporal Graph Net</text>

    <rect x="820" y="555" width="180" height="90" class="node-rect-fill" />
    <text x="910" y="590" class="box-title">PPO Agent</text>
    <text x="910" y="610" class="box-desc">RL Self-Healing Logic</text>

    <path d="M 810 405 L 810 480 L 210 480 L 210 530" class="arrow-line" />
    <path d="M 810 405 L 810 515" class="arrow-line" />
    <path d="M 340 595 L 410 595" class="arrow-line" />
    <text x="375" y="587" class="line-label">Telemetry</text>

    <!-- Infrastructure Layer -->
    <rect x="50" y="720" width="1000" height="140" class="layer-rect" />
    <text x="70" y="745" class="layer-title">INFRASTRUCTURE LAYER</text>

    <rect x="100" y="760" width="260" height="75" class="node-rect" />
    <text x="230" y="795" class="box-title">PostgreSQL Database</text>
    <text x="230" y="815" class="box-desc">Relational Store (Users, Logs, Audit)</text>

    <rect x="420" y="760" width="260" height="75" class="node-rect" />
    <text x="550" y="795" class="box-title">Redis</text>
    <text x="550" y="815" class="box-desc">Session Cache &amp; Celery Broker</text>

    <rect x="740" y="760" width="260" height="75" class="node-rect" />
    <text x="870" y="795" class="box-title">Docker Containers</text>
    <text x="870" y="815" class="box-desc">Containerization &amp; Deployment</text>

    <path d="M 230 660 L 230 760" class="arrow-line" />
    <path d="M 550 670 L 550 760" class="arrow-line" />
    <path d="M 870 670 L 870 760" class="arrow-line" />
    '''
    svg_full = wrap_svg(w, h, title, caption, svg_body)

    mmd = '''graph TD
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
'''

    puml = '''@startuml
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
@enduml'''

    drawio_xml = make_drawio("fig_m1", title, '''
      <mxCell id="layer_pres" value="PRESENTATION LAYER" style="swimlane;whiteSpace=wrap;html=1;fillColor=#F8FAFC;strokeColor=#CBD5E1;dashPattern=4 4;fontColor=#003366;fontStyle=1;" vertex="1" parent="1">
        <mxGeometry x="40" y="60" width="1000" height="140" as="geometry" />
      </mxCell>
      <mxCell id="node_user" value="User / Operator" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#003366;strokeWidth=2;fontColor=#003366;fontStyle=1;" vertex="1" parent="layer_pres">
        <mxGeometry x="150" y="40" width="200" height="70" as="geometry" />
      </mxCell>
      <mxCell id="node_dashboard" value="React Dashboard" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#F1F5F9;strokeColor=#003366;strokeWidth=2;fontColor=#003366;fontStyle=1;" vertex="1" parent="layer_pres">
        <mxGeometry x="640" y="40" width="220" height="70" as="geometry" />
      </mxCell>
      <mxCell id="edge_user_dash" edge="1" parent="layer_pres" source="node_user" target="node_dashboard">
        <mxGeometry relative="1" as="geometry" />
      </mxCell>
    ''')

    return ("fig_m1_microservices_architecture", svg_full, drawio_xml, mmd, puml)

# ==============================================================================
# FIGURE O.1: Physics-Based Detection Pipeline
# ==============================================================================
def gen_fig_o1():
    w, h = 1100, 680
    title = "Physics-Based Detection Pipeline"
    caption = "Figure O.1 Physics-based anomaly detection workflow."

    svg_body = '''
    <!-- Flow Nodes (Top to Bottom / Linear Stages) -->
    <rect x="100" y="100" width="200" height="65" class="node-rect" />
    <text x="200" y="138" class="box-title">Telemetry Data</text>

    <rect x="360" y="100" width="200" height="65" class="node-rect-fill" />
    <text x="460" y="130" class="box-title">Data Validation</text>
    <text x="460" y="148" class="box-desc">Format &amp; Range Checks</text>

    <rect x="620" y="100" width="200" height="65" class="node-rect" />
    <text x="720" y="130" class="box-title">Kirchhoff Current Law</text>
    <text x="720" y="148" class="box-desc">KCL Residual Verification</text>

    <rect x="840" y="210" width="200" height="65" class="node-rect" />
    <text x="940" y="240" class="box-title">Kirchhoff Voltage Law</text>
    <text x="940" y="258" class="box-desc">KVL Loop Residual Check</text>

    <rect x="580" y="210" width="220" height="65" class="node-rect-fill" />
    <text x="690" y="240" class="box-title">Power Balance Verification</text>
    <text x="690" y="258" class="box-desc">P_gen - P_load = Losses</text>

    <rect x="300" y="210" width="220" height="65" class="node-rect" />
    <text x="410" y="240" class="box-title">Trust Score Calculation</text>
    <text x="410" y="258" class="box-desc">Fused Physical Metrics</text>

    <!-- Decision Diamond -->
    <polygon points="410,340 530,400 410,460 290,400" class="node-rhombus" />
    <text x="410" y="395" class="box-title">Trust Evaluation</text>
    <text x="410" y="412" class="box-desc">Score ≥ Threshold?</text>

    <!-- Output Nodes -->
    <rect x="100" y="520" width="200" height="65" class="node-rect-fill" />
    <text x="200" y="550" class="box-title" style="fill:#1E8449;">Normal Grid State</text>
    <text x="200" y="568" class="box-desc">Normal Operations Logged</text>

    <rect x="520" y="520" width="220" height="65" class="node-rect-fill" />
    <text x="630" y="550" class="box-title" style="fill:#C0392B;">Suspicious / Anomaly</text>
    <text x="630" y="568" class="box-desc">Physical Violation Flagged</text>

    <rect x="820" y="520" width="200" height="65" class="node-rect" />
    <text x="920" y="550" class="box-title">AI Analysis</text>
    <text x="920" y="568" class="box-desc">PINN &amp; ST-GNN Diagnosis</text>

    <!-- Connectors -->
    <path d="M 300 132.5 L 360 132.5" class="arrow-line" />
    <path d="M 560 132.5 L 620 132.5" class="arrow-line" />
    <path d="M 820 132.5 L 940 132.5 L 940 210" class="arrow-line" />
    <path d="M 840 242.5 L 800 242.5" class="arrow-line" />
    <path d="M 580 242.5 L 520 242.5" class="arrow-line" />
    <path d="M 410 275 L 410 340" class="arrow-line" />

    <path d="M 290 400 L 200 400 L 200 520" class="arrow-line" />
    <text x="235" y="390" class="line-label">YES (Normal)</text>

    <path d="M 530 400 L 630 400 L 630 520" class="arrow-line" />
    <text x="590" y="390" class="line-label">NO (Violation)</text>

    <path d="M 740 552.5 L 820 552.5" class="arrow-line" />
    <text x="780" y="544" class="line-label">Escalate</text>
    '''

    full_svg = wrap_svg(w, h, title, caption, svg_body)

    mmd = '''graph TD
    Telemetry["Telemetry Data"] --> DataVal["Data Validation"]
    DataVal --> KCL["Kirchhoff Current Law (KCL)"]
    KCL --> KVL["Kirchhoff Voltage Law (KVL)"]
    KVL --> PowerBal["Power Balance Verification"]
    PowerBal --> TrustScore["Trust Score Calculation"]
    TrustScore --> Decision{"Trust Score ≥ Threshold?"}

    Decision -->|YES| Normal["Normal Grid State"]
    Decision -->|NO| Suspicious["Suspicious / Anomaly Detected"]
    Suspicious --> AIAnalysis["AI Analysis (PINN & ST-GNN)"]
'''

    puml = '''@startuml
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
@enduml'''

    drawio_xml = make_drawio("fig_o1", title, '''
      <mxCell id="node_tele" value="Telemetry" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#003366;strokeWidth=2;fontColor=#003366;fontStyle=1;" vertex="1" parent="1">
        <mxGeometry x="100" y="100" width="180" height="60" as="geometry" />
      </mxCell>
      <mxCell id="node_val" value="Data Validation" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#F8FAFC;strokeColor=#003366;strokeWidth=2;fontColor=#003366;fontStyle=1;" vertex="1" parent="1">
        <mxGeometry x="340" y="100" width="180" height="60" as="geometry" />
      </mxCell>
      <mxCell id="edge_1" edge="1" parent="1" source="node_tele" target="node_val">
        <mxGeometry relative="1" as="geometry" />
      </mxCell>
    ''')

    return ("fig_o1_physics_detection_pipeline", full_svg, drawio_xml, mmd, puml)

# ==============================================================================
# FIGURE P.1: Newton-Raphson AC Power Flow Solver Workflow
# ==============================================================================
def gen_fig_p1():
    w, h = 1050, 840
    title = "Newton-Raphson AC Power Flow Solver Workflow"
    caption = "Figure P.1 Newton-Raphson AC Power Flow Solver workflow."

    svg_body = '''
    <!-- Flow Nodes Vertically Centered -->
    <rect x="400" y="90" width="250" height="60" class="node-rect" />
    <text x="525" y="125" class="box-title">Initialize IEEE Network</text>

    <rect x="400" y="190" width="250" height="60" class="node-rect-fill" />
    <text x="525" y="225" class="box-title">Update Breaker Status</text>

    <rect x="400" y="290" width="250" height="60" class="node-rect-fill" />
    <text x="525" y="325" class="box-title">Update Load Demand</text>

    <rect x="400" y="390" width="250" height="60" class="node-rect" />
    <text x="525" y="425" class="box-title">Construct Admittance Matrix (Y_bus)</text>

    <rect x="400" y="490" width="250" height="65" class="node-rect-fill" />
    <text x="525" y="520" class="box-title">Newton-Raphson Iteration</text>
    <text x="525" y="538" class="box-desc">Solve Mismatch &amp; Update Jacobian</text>

    <!-- Decision Diamond -->
    <polygon points="525,595 645,655 525,715 405,655" class="node-rhombus" />
    <text x="525" y="650" class="box-title">Converged?</text>
    <text x="525" y="668" class="box-desc">|ΔP|, |ΔQ| &lt; ε</text>

    <!-- Output Node -->
    <rect x="760" y="622.5" width="220" height="65" class="node-rect" />
    <text x="870" y="652" class="box-title">Generate Telemetry</text>
    <text x="870" y="670" class="box-desc">Broadcast V, θ, I, Loading</text>

    <!-- Connectors -->
    <path d="M 525 150 L 525 190" class="arrow-line" />
    <path d="M 525 250 L 525 290" class="arrow-line" />
    <path d="M 525 350 L 525 390" class="arrow-line" />
    <path d="M 525 450 L 525 490" class="arrow-line" />
    <path d="M 525 555 L 525 595" class="arrow-line" />

    <!-- Decision YES -->
    <path d="M 645 655 L 760 655" class="arrow-line" />
    <text x="700" y="645" class="line-label">YES</text>

    <!-- Decision NO (Loop back) -->
    <path d="M 405 655 L 260 655 L 260 522.5 L 400 522.5" class="arrow-line" />
    <text x="320" y="645" class="line-label">NO (Repeat Iteration)</text>
    '''

    full_svg = wrap_svg(w, h, title, caption, svg_body)

    mmd = '''graph TD
    Init["Initialize IEEE Network"] --> Breaker["Update Breaker Status"]
    Breaker --> Load["Update Load Demand"]
    Load --> Ybus["Construct Admittance Matrix (Y_bus)"]
    Ybus --> NR["Newton-Raphson Iteration"]
    NR --> Decision{"Converged? (|ΔP|, |ΔQ| < ε)"}
    Decision -->|YES| Telemetry["Generate Telemetry"]
    Decision -->|NO| NR
'''

    puml = '''@startuml
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
@enduml'''

    drawio_xml = make_drawio("fig_p1", title, '''
      <mxCell id="node_init" value="Initialize IEEE Network" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#003366;strokeWidth=2;fontColor=#003366;fontStyle=1;" vertex="1" parent="1">
        <mxGeometry x="400" y="90" width="240" height="60" as="geometry" />
      </mxCell>
    ''')

    return ("fig_p1_newton_raphson_solver", full_svg, drawio_xml, mmd, puml)

# ==============================================================================
# FIGURE P.2: Digital Twin Telemetry Streaming Pipeline
# ==============================================================================
def gen_fig_p2():
    w, h = 1350, 480
    title = "Digital Twin Telemetry Streaming Pipeline"
    caption = "Figure P.2 Digital Twin telemetry streaming workflow."

    svg_body = '''
    <!-- Horizontal Linear Pipeline -->
    <g transform="translate(40, 150)">
      <!-- Stage 1 -->
      <rect x="0" y="0" width="135" height="110" class="node-rect-fill" />
      <text x="67.5" y="45" class="box-title">Digital Twin</text>
      <text x="67.5" y="63" class="box-title">Solver</text>
      <text x="67.5" y="82" class="box-desc">Pandapower</text>

      <path d="M 135 55 L 165 55" class="arrow-line" />

      <!-- Stage 2 -->
      <rect x="165" y="0" width="135" height="110" class="node-rect" />
      <text x="232.5" y="50" class="box-title">Voltage</text>
      <text x="232.5" y="68" class="box-title">Calculation</text>
      <text x="232.5" y="86" class="box-desc">Bus Magnitude V</text>

      <path d="M 300 55 L 330 55" class="arrow-line" />

      <!-- Stage 3 -->
      <rect x="330" y="0" width="135" height="110" class="node-rect" />
      <text x="397.5" y="50" class="box-title">Current</text>
      <text x="397.5" y="68" class="box-title">Calculation</text>
      <text x="397.5" y="86" class="box-desc">Branch Current I</text>

      <path d="M 465 55 L 495 55" class="arrow-line" />

      <!-- Stage 4 -->
      <rect x="495" y="0" width="135" height="110" class="node-rect" />
      <text x="562.5" y="50" class="box-title">Line Loading</text>
      <text x="562.5" y="68" class="box-title">Calculation</text>
      <text x="562.5" y="86" class="box-desc">% Capacity</text>

      <path d="M 630 55 L 660 55" class="arrow-line" />

      <!-- Stage 5 -->
      <rect x="660" y="0" width="135" height="110" class="node-rect-fill" />
      <text x="727.5" y="50" class="box-title">JSON</text>
      <text x="727.5" y="68" class="box-title">Formatting</text>
      <text x="727.5" y="86" class="box-desc">Payload Struct</text>

      <path d="M 795 55 L 825 55" class="arrow-line" />

      <!-- Stage 6 -->
      <rect x="825" y="0" width="135" height="110" class="node-rect" />
      <text x="892.5" y="50" class="box-title">MQTT Topic</text>
      <text x="892.5" y="68" class="box-desc">grid/telemetry</text>

      <path d="M 960 55 L 990 55" class="arrow-line" />

      <!-- Stage 7 -->
      <rect x="990" y="0" width="135" height="110" class="node-rect-fill" />
      <text x="1057.5" y="50" class="box-title">FastAPI</text>
      <text x="1057.5" y="68" class="box-title">Gateway</text>
      <text x="1057.5" y="86" class="box-desc">WS Router</text>

      <path d="M 1125 55 L 1155 55" class="arrow-line" />

      <!-- Stage 8 -->
      <rect x="1155" y="0" width="135" height="110" class="node-rect" />
      <text x="1222.5" y="50" class="box-title">React</text>
      <text x="1222.5" y="68" class="box-title">Dashboard</text>
      <text x="1222.5" y="86" class="box-desc">SLD UI Render</text>
    </g>
    '''

    full_svg = wrap_svg(w, h, title, caption, svg_body)

    mmd = '''graph LR
    Twin["Digital Twin Solver"] --> Volt["Voltage Calculation"]
    Volt --> Curr["Current Calculation"]
    Curr --> Load["Line Loading Calculation"]
    Load --> JSON["JSON Formatting"]
    JSON --> MQTT["MQTT Topic (grid/telemetry)"]
    MQTT --> Gateway["FastAPI Gateway"]
    Gateway --> Dash["React Dashboard"]
'''

    puml = '''@startuml
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
@enduml'''

    drawio_xml = make_drawio("fig_p2", title, '''
      <mxCell id="node_dt" value="Digital Twin Solver" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#F8FAFC;strokeColor=#003366;strokeWidth=2;fontColor=#003366;fontStyle=1;" vertex="1" parent="1">
        <mxGeometry x="40" y="150" width="130" height="110" as="geometry" />
      </mxCell>
    ''')

    return ("fig_p2_telemetry_streaming", full_svg, drawio_xml, mmd, puml)

# ==============================================================================
# FIGURE Q.1: Physics-Informed Neural Network (PINN) Training Workflow
# ==============================================================================
def gen_fig_q1():
    w, h = 1100, 850
    title = "Physics-Informed Neural Network (PINN) Training Workflow"
    caption = "Figure Q.1 Physics-Informed Neural Network training workflow."

    svg_body = '''
    <!-- Encoder-Decoder Pipeline -->
    <rect x="80" y="100" width="180" height="65" class="node-rect" />
    <text x="170" y="138" class="box-title">Input Telemetry</text>

    <rect x="310" y="100" width="180" height="65" class="node-rect-fill" />
    <text x="400" y="138" class="box-title">Encoder</text>

    <rect x="540" y="100" width="180" height="65" class="node-rect" />
    <text x="630" y="130" class="box-title">Latent Representation</text>
    <text x="630" y="148" class="box-desc">Feature Vector z</text>

    <rect x="770" y="100" width="180" height="65" class="node-rect-fill" />
    <text x="860" y="138" class="box-title">Decoder</text>

    <path d="M 260 132.5 L 310 132.5" class="arrow-line" />
    <path d="M 490 132.5 L 540 132.5" class="arrow-line" />
    <path d="M 720 132.5 L 770 132.5" class="arrow-line" />

    <!-- Prediction -->
    <rect x="770" y="220" width="180" height="65" class="node-rect" />
    <text x="860" y="250" class="box-title">Prediction</text>
    <text x="860" y="268" class="box-desc">V_pred, θ_pred</text>

    <path d="M 860 165 L 860 220" class="arrow-line" />

    <!-- Composite Loss Container -->
    <rect x="150" y="320" width="800" height="200" class="layer-rect" />
    <text x="170" y="345" class="layer-title">COMPOSITE LOSS FUNCTION ENGINE</text>

    <rect x="180" y="375" width="220" height="110" class="node-rect" />
    <text x="290" y="415" class="box-title">Supervised Loss</text>
    <text x="290" y="435" class="box-desc">L_data = ||y - y_hat||²</text>
    <text x="290" y="455" class="box-muted">MSE Telemetry Match</text>

    <rect x="440" y="375" width="220" height="110" class="node-rect" />
    <text x="550" y="415" class="box-title">KCL Constraint</text>
    <text x="550" y="435" class="box-desc">L_KCL = ||Σ I_in - Σ I_out||²</text>
    <text x="550" y="455" class="box-muted">Current Law Residual</text>

    <rect x="700" y="375" width="220" height="110" class="node-rect" />
    <text x="810" y="415" class="box-title">KVL Constraint</text>
    <text x="810" y="435" class="box-desc">L_KVL = ||Σ ΔV_loop||²</text>
    <text x="810" y="455" class="box-muted">Voltage Loop Residual</text>

    <path d="M 860 285 L 860 320" class="arrow-line" />

    <!-- Dynamic Weight Balancing -->
    <rect x="410" y="560" width="280" height="65" class="node-rect-fill" />
    <text x="550" y="590" class="box-title">Dynamic Weight Balancing</text>
    <text x="550" y="608" class="box-desc">Adaptive λ_data, λ_kcl, λ_kvl</text>

    <path d="M 290 485 L 290 592.5 L 410 592.5" class="arrow-line" />
    <path d="M 550 485 L 550 560" class="arrow-line" />
    <path d="M 810 485 L 810 592.5 L 690 592.5" class="arrow-line" />

    <!-- Backpropagation & Updated Model -->
    <rect x="410" y="665" width="280" height="60" class="node-rect" />
    <text x="550" y="700" class="box-title">Backpropagation</text>

    <rect x="770" y="665" width="180" height="60" class="node-rect-fill" />
    <text x="860" y="700" class="box-title">Updated Model</text>

    <path d="M 550 625 L 550 665" class="arrow-line" />
    <path d="M 690 695 L 770 695" class="arrow-line" />
    '''

    full_svg = wrap_svg(w, h, title, caption, svg_body)

    mmd = '''graph TD
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
'''

    puml = '''@startuml
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
@enduml'''

    drawio_xml = make_drawio("fig_q1", title, '''
      <mxCell id="node_input" value="Input Telemetry" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#003366;strokeWidth=2;fontColor=#003366;fontStyle=1;" vertex="1" parent="1">
        <mxGeometry x="80" y="100" width="180" height="65" as="geometry" />
      </mxCell>
    ''')

    return ("fig_q1_pinn_training_workflow", full_svg, drawio_xml, mmd, puml)

# ==============================================================================
# FIGURE R.1: PPO Self-Healing Decision Loop
# ==============================================================================
def gen_fig_r1():
    w, h = 1050, 850
    title = "PPO Self-Healing Decision Loop"
    caption = "Figure R.1 PPO self-healing decision loop."

    svg_body = '''
    <!-- Circular / Vertical Loop Stages -->
    <rect x="400" y="85" width="250" height="60" class="node-rect" />
    <text x="525" y="120" class="box-title">Grid State (s_t)</text>

    <rect x="400" y="175" width="250" height="60" class="node-rect-fill" />
    <text x="525" y="210" class="box-title">Observation</text>

    <rect x="400" y="265" width="250" height="60" class="node-rect" />
    <text x="525" y="300" class="box-title">Policy Network (π_θ)</text>

    <rect x="400" y="355" width="250" height="60" class="node-rect-fill" />
    <text x="525" y="390" class="box-title">Action Selection (a_t)</text>

    <rect x="400" y="445" width="250" height="60" class="node-rect" />
    <text x="525" y="480" class="box-title">Breaker Control</text>

    <rect x="400" y="535" width="250" height="60" class="node-rect-fill" />
    <text x="525" y="570" class="box-title">Grid Response</text>

    <rect x="400" y="625" width="250" height="60" class="node-rect" />
    <text x="525" y="660" class="box-title">Reward Calculation</text>

    <rect x="400" y="715" width="250" height="60" class="node-rect-fill" />
    <text x="525" y="750" class="box-title">Policy Update</text>

    <!-- Downward Arrows -->
    <path d="M 525 145 L 525 175" class="arrow-line" />
    <path d="M 525 235 L 525 265" class="arrow-line" />
    <path d="M 525 325 L 525 355" class="arrow-line" />
    <path d="M 525 415 L 525 445" class="arrow-line" />
    <path d="M 525 505 L 525 535" class="arrow-line" />
    <path d="M 525 595 L 525 625" class="arrow-line" />
    <path d="M 525 685 L 525 715" class="arrow-line" />

    <!-- Loop Back Arrow (Repeat) -->
    <path d="M 400 745 L 200 745 L 200 115 L 400 115" class="arrow-line" />
    <text x="140" y="430" class="line-label" transform="rotate(-90 140 430)">Repeat Decision Loop (Next Step s_t+1)</text>
    '''

    full_svg = wrap_svg(w, h, title, caption, svg_body)

    mmd = '''graph TD
    GridState["Grid State (s_t)"] --> Obs["Observation"]
    Obs --> Policy["Policy Network (π_θ)"]
    Policy --> Action["Action Selection (a_t)"]
    Action --> Breaker["Breaker Control"]
    Breaker --> Response["Grid Response"]
    Response --> Reward["Reward Calculation"]
    Reward --> Update["Policy Update"]
    Update -->|Repeat Loop| GridState
'''

    puml = '''@startuml
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
@enduml'''

    drawio_xml = make_drawio("fig_r1", title, '''
      <mxCell id="node_gs" value="Grid State (s_t)" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#003366;strokeWidth=2;fontColor=#003366;fontStyle=1;" vertex="1" parent="1">
        <mxGeometry x="400" y="85" width="250" height="60" as="geometry" />
      </mxCell>
    ''')

    return ("fig_r1_ppo_decision_loop", full_svg, drawio_xml, mmd, puml)

# ==============================================================================
# FIGURE S.1: Grid Resilience Scoring Pipeline
# ==============================================================================
def gen_fig_s1():
    w, h = 1150, 850
    title = "Grid Resilience Scoring Pipeline"
    caption = "Figure S.1 Grid resilience scoring workflow."

    svg_body = '''
    <!-- Sequential Top Pipeline -->
    <rect x="80" y="100" width="200" height="65" class="node-rect" />
    <text x="180" y="138" class="box-title">Cyberattack Event</text>

    <rect x="330" y="100" width="200" height="65" class="node-rect-fill" />
    <text x="430" y="138" class="box-title">Detection</text>

    <rect x="580" y="100" width="200" height="65" class="node-rect" />
    <text x="680" y="138" class="box-title">Isolation</text>

    <rect x="830" y="100" width="200" height="65" class="node-rect-fill" />
    <text x="930" y="138" class="box-title">System Restoration</text>

    <path d="M 280 132.5 L 330 132.5" class="arrow-line" />
    <path d="M 530 132.5 L 580 132.5" class="arrow-line" />
    <path d="M 780 132.5 L 830 132.5" class="arrow-line" />

    <!-- Connector down to Parallel Assessment Container -->
    <path d="M 930 165 L 930 220 L 575 220 L 575 270" class="arrow-line" />

    <!-- Parallel Assessment Container -->
    <rect x="60" y="270" width="1030" height="230" class="layer-rect" />
    <text x="80" y="295" class="layer-title">MULTI-METRIC EVALUATION MODULE</text>

    <rect x="90" y="330" width="220" height="130" class="node-rect" />
    <text x="200" y="375" class="box-title">Voltage Recovery</text>
    <text x="200" y="393" class="box-title">Assessment</text>
    <text x="200" y="415" class="box-desc">R_V Score Component</text>
    <text x="200" y="433" class="box-muted">Bus Voltage Dip &amp; Stability</text>

    <rect x="340" y="330" width="220" height="130" class="node-rect" />
    <text x="450" y="375" class="box-title">Thermal Loading</text>
    <text x="450" y="393" class="box-title">Assessment</text>
    <text x="450" y="415" class="box-desc">R_I Score Component</text>
    <text x="450" y="433" class="box-muted">Branch Overload Penalty</text>

    <rect x="590" y="330" width="220" height="130" class="node-rect" />
    <text x="700" y="375" class="box-title">Switching Operation</text>
    <text x="700" y="393" class="box-title">Assessment</text>
    <text x="700" y="415" class="box-desc">R_S Score Component</text>
    <text x="700" y="433" class="box-muted">Breaker Wear &amp; Reconfigs</text>

    <rect x="840" y="330" width="220" height="130" class="node-rect" />
    <text x="950" y="375" class="box-title">Restoration Time</text>
    <text x="950" y="393" class="box-title">Assessment</text>
    <text x="950" y="415" class="box-desc">R_T Score Component</text>
    <text x="950" y="433" class="box-muted">Recovery Latency (sec)</text>

    <!-- Aggregator Output Node -->
    <rect x="420" y="580" width="310" height="80" class="node-rect-fill" />
    <text x="575" y="615" class="box-title" style="font-size:14px;">Grid Resilience Score</text>
    <text x="575" y="638" class="box-desc">Composite Metric R = w1·R_V + w2·R_I + w3·R_S + w4·R_T</text>

    <path d="M 200 460 L 200 580 L 420 580" class="arrow-line" />
    <path d="M 450 460 L 450 580" class="arrow-line" />
    <path d="M 700 460 L 700 580" class="arrow-line" />
    <path d="M 950 460 L 950 580 L 730 580" class="arrow-line" />
    '''

    full_svg = wrap_svg(w, h, title, caption, svg_body)

    mmd = '''graph TD
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
'''

    puml = '''@startuml
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
@enduml'''

    drawio_xml = make_drawio("fig_s1", title, '''
      <mxCell id="node_attack" value="Cyberattack Event" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#003366;strokeWidth=2;fontColor=#003366;fontStyle=1;" vertex="1" parent="1">
        <mxGeometry x="80" y="100" width="200" height="65" as="geometry" />
      </mxCell>
    ''')

    return ("fig_s1_grid_resilience_scoring", full_svg, drawio_xml, mmd, puml)

# ==============================================================================
# MAIN EXECUTION PIPELINE
# ==============================================================================
def main():
    generators = [
        gen_fig_m1,
        gen_fig_o1,
        gen_fig_p1,
        gen_fig_p2,
        gen_fig_q1,
        gen_fig_r1,
        gen_fig_s1
    ]

    report_md = """# PYPY (Protect Your Power, Protect Yourself) FYP Engineering Diagrams

This document contains the official engineering architecture and workflow diagrams for the **PYPY Smart Grid Cybersecurity SaaS & Research Platform**, rendered according to IEEE paper and UniMAP Final Year Project (FYP) academic logbook standards.

---

"""

    for gen in generators:
        name, svg_content, drawio_content, mmd_content, puml_content = gen()

        # 1. Save SVG
        svg_path = os.path.join(OUTPUT_DIR, f"{name}.svg")
        with open(svg_path, "w", encoding="utf-8") as f:
            f.write(svg_content)

        # 2. Render PNG via ImageMagick (300 DPI)
        png_path = os.path.join(OUTPUT_DIR, f"{name}.png")
        try:
            subprocess.run(["convert", "-density", "300", svg_path, png_path], check=True)
            print(f"✅ Generated 300 DPI PNG: {png_path}")
        except Exception as e:
            print(f"⚠️ Failed to generate PNG via ImageMagick: {e}")

        # 3. Save Draw.io XML (.drawio)
        drawio_path = os.path.join(OUTPUT_DIR, f"{name}.drawio")
        with open(drawio_path, "w", encoding="utf-8") as f:
            f.write(drawio_content)

        # 4. Save Mermaid (.mmd)
        mmd_path = os.path.join(OUTPUT_DIR, f"{name}.mmd")
        with open(mmd_path, "w", encoding="utf-8") as f:
            f.write(mmd_content)

        # 5. Save PlantUML (.puml)
        puml_path = os.path.join(OUTPUT_DIR, f"{name}.puml")
        with open(puml_path, "w", encoding="utf-8") as f:
            f.write(puml_content)

        print(f"✨ Successfully generated all 5 formats for: {name}")

        # Append to master report
        report_md += f"## {name.replace('_', ' ').title()}\n\n"
        report_md += f"![{name}](./{name}.png)\n\n"
        report_md += "### Mermaid Syntax\n```mermaid\n" + mmd_content + "\n```\n\n"
        report_md += "### PlantUML Syntax\n```plantuml\n" + puml_content + "\n```\n\n"
        report_md += f"**Files Generated:**\n- SVG: [`{name}.svg`](./{name}.svg)\n- PNG (300 DPI): [`{name}.png`](./{name}.png)\n- Draw.io: [`{name}.drawio`](./{name}.drawio)\n- Mermaid: [`{name}.mmd`](./{name}.mmd)\n- PlantUML: [`{name}.puml`](./{name}.puml)\n\n---\n\n"

    # Write master markdown documentation
    report_path = os.path.join(OUTPUT_DIR, "PYPY_FYP_Engineering_Diagrams_Report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_md)
    print(f"\n📑 Master report compiled at: {report_path}")

if __name__ == "__main__":
    main()
