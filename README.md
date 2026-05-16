# Predictive Link-State Routing (PLSR)

<p align="center">
  <b>A proactive routing protocol simulation for EN2150 Communication Network Engineering</b>
</p>

<p align="center">
  <img src="figures/latency_comparison.png" alt="PLSR Latency Comparison" width="650">
</p>

---

## 📌 Project Overview

This repository contains the simulation files for **Predictive Link-State Routing (PLSR)**, a proposed routing protocol designed for the EN2150 Communication Network Engineering routing protocol design assignment.

Traditional link-state routing protocols such as **OSPF** normally react after a link failure or major topology change has already occurred. This reactive behavior can cause packet loss, routing blackholes, and temporary service degradation.

PLSR improves this behavior by monitoring link latency trends and predicting degradation before complete failure. When a link begins to behave abnormally, PLSR increases its dynamic routing cost and reroutes traffic through a healthier backup path.

---

## 🚀 Key Features

- Predictive link degradation detection
- Dynamic routing cost calculation
- EWMA-based latency smoothing
- Proactive rerouting before failure
- HMAC-SHA256 secured predictive Link State Updates
- Sequence-number based replay protection
- OSPF-style baseline comparison
- Python and NetworkX based simulation
- Automatically generated graphs and result logs

---

## 🧠 Proposed Protocol: PLSR

PLSR stands for **Predictive Link-State Routing**.

The protocol extends the idea of traditional link-state routing by introducing predictive monitoring. Instead of waiting for a link to fully fail, each router continuously observes link latency and compares it with a baseline value.

The PLSR cost model considers:

```text
Smoothed latency
Latency deviation from baseline
Latency trend
Packet loss penalty
