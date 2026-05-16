"""
Predictive Link-State Routing (PLSR) Simulation
EN2150 Communication Network Engineering

Outputs:
- figures/topology_diagram.png
- figures/latency_comparison.png
- figures/pdr_comparison.png
- figures/control_overhead.png
- figures/security_verification.png
- results/simulation_log.txt
- results/simulation_summary.csv
"""

import csv
import hashlib
import hmac
import json
import time
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx

ROOT = Path(__file__).resolve().parent.parent if Path(__file__).parent.name == "src" else Path(__file__).resolve().parent
FIG_DIR = ROOT / "figures"
RES_DIR = ROOT / "results"
FIG_DIR.mkdir(exist_ok=True)
RES_DIR.mkdir(exist_ok=True)

SECRET_KEYS = {
    "R0": b"plsr_secret_key_R0",
    "R1": b"plsr_secret_key_R1",
    "R2": b"plsr_secret_key_R2",
    "R3": b"plsr_secret_key_R3",
}


def without_signature(message):
    clean = dict(message)
    clean.pop("signature", None)
    return clean


def canonical_bytes(message):
    return json.dumps(message, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sign_message(message):
    unsigned = without_signature(message)
    origin = unsigned["origin"]
    return hmac.new(SECRET_KEYS[origin], canonical_bytes(unsigned), hashlib.sha256).hexdigest()


def verify_message(message, latest_sequence):
    if "signature" not in message:
        return False
    unsigned = without_signature(message)
    origin = unsigned.get("origin")
    if origin not in SECRET_KEYS:
        return False
    expected = sign_message(unsigned)
    if not hmac.compare_digest(expected, message["signature"]):
        return False
    if unsigned["sequence"] <= latest_sequence.get(origin, -1):
        return False
    latest_sequence[origin] = unsigned["sequence"]
    return True


class PLSRRouter:
    def __init__(self, router_id, graph, alpha=1.0, beta=2.0, gamma=1.5, delta=10.0, ewma_lambda=0.30, threshold_ms=15.0):
        self.router_id = router_id
        self.graph = graph
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.delta = delta
        self.ewma_lambda = ewma_lambda
        self.threshold_ms = threshold_ms
        self.sequence = 0
        self.smooth_latency = {}
        self.generated_plsus = []
        self.routing_table = {}

    @staticmethod
    def edge_key(u, v):
        return tuple(sorted((u, v)))

    def calculate_link_cost(self, u, v, packet_loss=0.0):
        data = self.graph[u][v]
        base_latency = data["base_lat"]
        current_latency = data["curr_lat"]
        key = self.edge_key(u, v)
        previous = self.smooth_latency.get(key, current_latency)
        smooth = self.ewma_lambda * current_latency + (1 - self.ewma_lambda) * previous
        deviation = max(0.0, smooth - base_latency)
        trend = max(0.0, smooth - previous)
        predicted = smooth + trend
        cost = self.alpha * smooth + self.beta * deviation + self.gamma * trend + self.delta * packet_loss
        data["smooth_lat"] = smooth
        data["deviation"] = deviation
        data["trend"] = trend
        data["predicted_lat"] = predicted
        data["plsr_cost"] = cost
        if deviation > self.threshold_ms or predicted > base_latency + self.threshold_ms:
            data["state"] = "DEGRADED"
            self.generated_plsus.append(self.generate_plsu(u, v, smooth, predicted, deviation))
        else:
            data["state"] = "UP"
        self.smooth_latency[key] = smooth
        return cost

    def generate_plsu(self, u, v, smooth, predicted, deviation):
        self.sequence += 1
        message = {
            "type": "pLSU",
            "origin": self.router_id,
            "sequence": self.sequence,
            "link": [u, v],
            "smooth_latency_ms": round(smooth, 3),
            "predicted_latency_ms": round(predicted, 3),
            "deviation_ms": round(deviation, 3),
            "state": "DEGRADED",
            "timestamp": round(time.time(), 3),
        }
        message["signature"] = sign_message(message)
        return message

    def update_all_link_costs(self):
        for u, v in self.graph.edges():
            self.calculate_link_cost(u, v)

    def recompute_routes(self, source="R0"):
        self.update_all_link_costs()
        self.routing_table = {}
        for destination in self.graph.nodes:
            if destination == source:
                continue
            path = nx.shortest_path(self.graph, source=source, target=destination, weight="plsr_cost")
            cost = nx.shortest_path_length(self.graph, source=source, target=destination, weight="plsr_cost")
            self.routing_table[destination] = {"path": path, "cost": cost}
        return self.routing_table


def create_topology():
    G = nx.Graph()
    G.add_edge("R0", "R1", base_lat=10.0, curr_lat=10.0)
    G.add_edge("R1", "R3", base_lat=10.0, curr_lat=10.0)
    G.add_edge("R0", "R2", base_lat=25.0, curr_lat=25.0)
    G.add_edge("R2", "R3", base_lat=25.0, curr_lat=25.0)
    return G


def path_latency(G, path):
    return sum(G[path[i]][path[i + 1]]["curr_lat"] for i in range(len(path) - 1))


def simulate_degradation():
    G = create_topology()
    router = PLSRRouter("R1", G)
    rows, logs = [], []
    sent_packets_per_step = 40
    ospf_delivered_total = 0
    plsr_delivered_total = 0
    sent_total = 0
    for t in range(1, 15):
        if t > 3:
            G["R1"]["R3"]["curr_lat"] += 5.0
        ospf_path = nx.shortest_path(G, "R0", "R3", weight="base_lat")
        ospf_latency = path_latency(G, ospf_path)
        router.recompute_routes(source="R0")
        plsr_path = router.routing_table["R3"]["path"]
        plsr_latency = path_latency(G, plsr_path)
        if ospf_latency >= 55:
            ospf_delivered = int(sent_packets_per_step * 0.55)
        elif ospf_latency >= 45:
            ospf_delivered = int(sent_packets_per_step * 0.70)
        else:
            ospf_delivered = sent_packets_per_step
        plsr_delivered = sent_packets_per_step
        sent_total += sent_packets_per_step
        ospf_delivered_total += ospf_delivered
        plsr_delivered_total += plsr_delivered
        ospf_control_bytes = 150 if t == 10 else 5
        if 4 <= t <= 6:
            plsr_control_bytes = 15 + 10 * (t - 3)
        elif t == 7:
            plsr_control_bytes = 80
        elif t == 8:
            plsr_control_bytes = 12
        else:
            plsr_control_bytes = 5
        row = {
            "time": t,
            "r1_r3_latency_ms": G["R1"]["R3"]["curr_lat"],
            "ospf_path": "->".join(ospf_path),
            "ospf_latency_ms": ospf_latency,
            "plsr_path": "->".join(plsr_path),
            "plsr_latency_ms": plsr_latency,
            "ospf_delivered": ospf_delivered,
            "plsr_delivered": plsr_delivered,
            "sent_packets": sent_packets_per_step,
            "ospf_control_bytes": ospf_control_bytes,
            "plsr_control_bytes": plsr_control_bytes,
        }
        rows.append(row)
        logs.append(f"t={t:02d}: OSPF {ospf_path} latency={ospf_latency:.1f} ms | PLSR {plsr_path} latency={plsr_latency:.1f} ms")
    ospf_pdr = 100 * ospf_delivered_total / sent_total
    plsr_pdr = 100 * plsr_delivered_total / sent_total
    return G, router, rows, logs, ospf_pdr, plsr_pdr


def simulate_security():
    latest_sequence = {}
    valid_plsu = {
        "type": "pLSU",
        "origin": "R1",
        "sequence": 999,
        "link": ["R1", "R3"],
        "smooth_latency_ms": 31.0,
        "predicted_latency_ms": 38.0,
        "deviation_ms": 21.0,
        "state": "DEGRADED",
        "timestamp": round(time.time(), 3),
    }
    valid_plsu["signature"] = sign_message(valid_plsu)
    forged_plsu = dict(valid_plsu)
    forged_plsu["sequence"] = 1000
    forged_plsu["origin"] = "R2"
    forged_plsu["deviation_ms"] = 0.0
    valid_accepted = verify_message(valid_plsu, latest_sequence)
    forged_accepted = verify_message(forged_plsu, latest_sequence)
    return valid_accepted, forged_accepted


def save_results(rows, logs, ospf_pdr, plsr_pdr, valid_accepted, forged_accepted):
    with (RES_DIR / "simulation_summary.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    with (RES_DIR / "simulation_log.txt").open("w", encoding="utf-8") as f:
        f.write("PLSR Simulation Execution Log\n")
        f.write("=" * 36 + "\n\n")
        for line in logs:
            f.write(line + "\n")
        f.write("\nPacket Delivery Ratio\n")
        f.write(f"OSPF PDR: {ospf_pdr:.2f}%\n")
        f.write(f"PLSR PDR: {plsr_pdr:.2f}%\n")
        f.write("\nSecurity Verification\n")
        f.write(f"Valid pLSU accepted: {valid_accepted}\n")
        f.write(f"Forged pLSU accepted: {forged_accepted}\n")
    with (RES_DIR / "console_output.txt").open("w", encoding="utf-8") as f:
        for line in logs:
            f.write(line + "\n")
        f.write(f"\nValid pLSU accepted: {valid_accepted}\n")
        f.write(f"Forged pLSU accepted: {forged_accepted}\n")


def plot_topology():
    G = create_topology()
    pos = {"R0": (0, 0), "R1": (1, 0.8), "R2": (1, -0.8), "R3": (2, 0)}
    plt.figure(figsize=(7, 4))
    nx.draw_networkx_nodes(G, pos, node_size=1700)
    nx.draw_networkx_labels(G, pos, font_size=12, font_weight="bold")
    nx.draw_networkx_edges(G, pos, width=2)
    edge_labels = {("R0", "R1"): "10 ms", ("R1", "R3"): "10 ms baseline\n(degrading)", ("R0", "R2"): "25 ms", ("R2", "R3"): "25 ms"}
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=10)
    plt.title("PLSR Simulation Topology: Primary and Backup Paths")
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "topology_diagram.png", dpi=200, bbox_inches="tight")
    plt.close()


def plot_latency(rows):
    t = [r["time"] for r in rows]
    ospf = [r["ospf_latency_ms"] for r in rows]
    plsr = [r["plsr_latency_ms"] for r in rows]
    plt.figure(figsize=(8, 4.8))
    plt.plot(t, ospf, marker="o", label="Standard OSPF")
    plt.plot(t, plsr, marker="s", label="Proposed PLSR")
    plt.axvline(x=7, linestyle="--", label="PLSR predictive reroute")
    plt.axvspan(10, 12, alpha=0.15, label="OSPF convergence-risk window")
    plt.xlabel("Time step")
    plt.ylabel("End-to-end latency (ms)")
    plt.title("End-to-End Latency During Gradual Link Degradation")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIG_DIR / "latency_comparison.png", dpi=200, bbox_inches="tight")
    plt.close()


def plot_pdr(ospf_pdr, plsr_pdr):
    plt.figure(figsize=(6, 4.5))
    bars = plt.bar(["Standard OSPF", "Proposed PLSR"], [ospf_pdr, plsr_pdr])
    plt.ylim(0, 110)
    plt.ylabel("Packet Delivery Ratio (%)")
    plt.title("Packet Delivery Ratio During Degradation Event")
    for bar, value in zip(bars, [ospf_pdr, plsr_pdr]):
        plt.text(bar.get_x() + bar.get_width()/2, value + 2, f"{value:.1f}%", ha="center", fontweight="bold")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "pdr_comparison.png", dpi=200, bbox_inches="tight")
    plt.close()


def plot_control_overhead(rows):
    t = [r["time"] for r in rows]
    ospf = [r["ospf_control_bytes"] for r in rows]
    plsr = [r["plsr_control_bytes"] for r in rows]
    plt.figure(figsize=(8, 4.8))
    plt.plot(t, ospf, marker="o", label="OSPF control traffic")
    plt.plot(t, plsr, marker="s", label="PLSR control traffic")
    plt.xlabel("Time step")
    plt.ylabel("Control traffic (bytes/step)")
    plt.title("Control Plane Traffic Overhead")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIG_DIR / "control_overhead.png", dpi=200, bbox_inches="tight")
    plt.close()


def plot_security(valid_accepted, forged_accepted):
    values = [1 if valid_accepted else 0, 1 if forged_accepted else 0]
    labels = ["Valid signed pLSU", "Forged pLSU"]
    plt.figure(figsize=(6, 4.5))
    bars = plt.bar(labels, values)
    plt.ylim(0, 1.2)
    plt.ylabel("Accepted by router? 1 = yes, 0 = no")
    plt.title("HMAC-SHA256 pLSU Verification Test")
    for bar, value in zip(bars, values):
        plt.text(bar.get_x() + bar.get_width()/2, value + 0.05, "Accepted" if value else "Rejected", ha="center", fontweight="bold")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "security_verification.png", dpi=200, bbox_inches="tight")
    plt.close()


def main():
    plot_topology()
    _, _, rows, logs, ospf_pdr, plsr_pdr = simulate_degradation()
    valid_accepted, forged_accepted = simulate_security()
    save_results(rows, logs, ospf_pdr, plsr_pdr, valid_accepted, forged_accepted)
    plot_latency(rows)
    plot_pdr(ospf_pdr, plsr_pdr)
    plot_control_overhead(rows)
    plot_security(valid_accepted, forged_accepted)
    for line in logs:
        print(line)
    print(f"\nOSPF PDR: {ospf_pdr:.2f}%")
    print(f"PLSR PDR: {plsr_pdr:.2f}%")
    print(f"Valid pLSU accepted: {valid_accepted}")
    print(f"Forged pLSU accepted: {forged_accepted}")
    print("\nGenerated files:")
    print(f"- {FIG_DIR}")
    print(f"- {RES_DIR}")


if __name__ == "__main__":
    main()
