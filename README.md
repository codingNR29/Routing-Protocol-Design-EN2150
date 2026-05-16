# Predictive Link-State Routing (PLSR) Simulation Files

This folder contains the simulation source code and generated evidence files for the EN2150 Routing Protocol Design report.

## Protocol Summary

The proposed protocol is **Predictive Link-State Routing (PLSR)**. It improves standard OSPF-style link-state routing by:

1. Monitoring current latency against a baseline latency.
2. Smoothing measurements using EWMA.
3. Predicting link degradation using latency trend.
4. Increasing dynamic route cost before complete failure.
5. Sending signed predictive Link State Updates (pLSUs).
6. Verifying pLSUs using HMAC-SHA256 and sequence numbers.

## Folder Structure

```text
PLSR_Project_Files/
├── README.md
├── requirements.txt
├── plsr_simulation.py
├── src/
│   └── plsr_simulation.py
├── figures/
│   ├── topology_diagram.png
│   ├── latency_comparison.png
│   ├── pdr_comparison.png
│   ├── control_overhead.png
│   └── security_verification.png
└── results/
    ├── simulation_log.txt
    ├── simulation_summary.csv
    └── console_output.txt
```

## How to Run

### Step 1: Install dependencies

```bash
pip install -r requirements.txt
```

### Step 2: Run the simulation

```bash
python plsr_simulation.py
```

or:

```bash
python src/plsr_simulation.py
```

## Expected Output

The terminal shows OSPF and PLSR path choices at each time step.

Expected behavior:

- At early time steps, both OSPF and PLSR use the primary route: `R0 -> R1 -> R3`.
- When the `R1 -> R3` link starts degrading, OSPF stays on the primary route because it uses static/base cost.
- PLSR detects degradation and switches to: `R0 -> R2 -> R3`.
- Security output should show:
  - `Valid pLSU accepted: True`
  - `Forged pLSU accepted: False`

## Figures Used in Report

1. `figures/topology_diagram.png` — primary and backup paths.
2. `figures/latency_comparison.png` — OSPF latency rises while PLSR stabilizes after predictive rerouting.
3. `figures/pdr_comparison.png` — Packet Delivery Ratio comparison.
4. `figures/control_overhead.png` — control-plane overhead comparison.
5. `figures/security_verification.png` — HMAC verification result.

## LaTeX Figure Example

```latex
\begin{figure}[H]
    \centering
    \includegraphics[width=0.85\textwidth]{figures/latency_comparison.png}
    \caption{End-to-end latency comparison between standard OSPF and proposed PLSR.}
    \label{fig:latency-comparison}
\end{figure}
```
