"""
CutLine Discovery Engine — PYPY V10.7 Zero-Parameter FDIA Pathogen.

Discovers network vulnerabilities using graph-theoretic analysis only.
Requires ZERO topology parameters — operates purely on adjacency structure.

Algorithms implemented:
  1. Tarjan's bridge-finding algorithm — O(V+E)
  2. Articulation point detection — O(V+E)
  3. Islanding Risk Score — composite metric per line
  4. Cut-set enumeration — k-connectivity analysis

No Jacobian, PTDF, or state estimation model required.
"""
import os
import sys
import numpy as np
from typing import List, Dict, Set, Tuple, Optional

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, project_root)


# ---------------------------------------------------------------------------
# Internal graph representation
# ---------------------------------------------------------------------------

class _GraphContext:
    """Lightweight adjacency structure built from topo.lines."""

    def __init__(self, topo):
        self.n = topo.num_buses
        self.adj: Dict[int, List[Tuple[int, str]]] = {i: [] for i in range(self.n)}
        self.lines = topo.lines
        self.line_ids: List[str] = []
        self.line_endpoints: Dict[str, Tuple[int, int]] = {}

        for line in topo.lines:
            f, t, lid = line["from"], line["to"], line["id"]
            self.adj[f].append((t, lid))
            self.adj[t].append((f, lid))
            if lid not in self.line_endpoints:
                self.line_endpoints[lid] = (f, t)
                self.line_ids.append(lid)

        # Build set of load buses and generator buses for islanding risk
        self.load_buses: Set[int] = set(topo.loads.keys()) if hasattr(topo, "loads") else set()
        self.gen_buses: Set[int] = set(topo.generators.keys()) if hasattr(topo, "generators") else set()
        self.load_power: Dict[int, float] = {}
        if hasattr(topo, "loads"):
            for b, info in topo.loads.items():
                self.load_power[b] = info.get("P_nom", 1.0)


# ---------------------------------------------------------------------------
# Main engine
# ---------------------------------------------------------------------------

class CutLineDiscoveryEngine:
    """
    Graph-theoretic cut-line discovery for smart-grid islanding attacks.

    Operates purely on network adjacency — no power-flow parameters needed.
    """

    def __init__(self, topo, seed: int = 42):
        self.topo = topo
        self.rng = np.random.RandomState(seed)
        self._G = _GraphContext(topo)
        # Cache
        self._bridges: Optional[List[str]] = None
        self._aps: Optional[List[int]] = None
        self._risk: Optional[Dict[str, float]] = None

    # ------------------------------------------------------------------
    # 1. Bridge detection (Tarjan's algorithm)
    # ------------------------------------------------------------------

    def discover_bridges(self) -> List[str]:
        """
        Finds all bridges in the graph using Tarjan's DFS algorithm.
        A bridge is an edge whose removal disconnects the graph.

        Returns list of line_ids that are bridges.
        Time complexity: O(V + E)
        """
        if self._bridges is not None:
            return self._bridges

        G = self._G
        n = G.n
        visited = [False] * n
        disc = [-1] * n          # discovery time
        low = [-1] * n           # lowest disc reachable
        parent = [-1] * n
        timer = [0]
        bridge_set: Set[str] = set()

        def _dfs(u: int):
            visited[u] = True
            disc[u] = low[u] = timer[0]
            timer[0] += 1

            for v, lid in G.adj[u]:
                if not visited[v]:
                    parent[v] = u
                    _dfs(v)
                    low[u] = min(low[u], low[v])
                    # Bridge condition
                    if low[v] > disc[u]:
                        bridge_set.add(lid)
                elif v != parent[u]:
                    low[u] = min(low[u], disc[v])

        # Handle disconnected components
        sys.setrecursionlimit(max(10000, n * 20))
        for i in range(n):
            if not visited[i]:
                _dfs(i)

        self._bridges = list(bridge_set)
        return self._bridges

    # ------------------------------------------------------------------
    # 2. Articulation point detection
    # ------------------------------------------------------------------

    def discover_articulation_points(self) -> List[int]:
        """
        Finds all articulation points (cut vertices) in the graph.
        An articulation point is a vertex whose removal disconnects the graph.

        Returns list of bus indices that are articulation points.
        Time complexity: O(V + E)
        """
        if self._aps is not None:
            return self._aps

        G = self._G
        n = G.n
        visited = [False] * n
        disc = [-1] * n
        low = [-1] * n
        parent = [-1] * n
        ap_set: Set[int] = set()
        timer = [0]

        def _dfs(u: int):
            child_count = 0
            visited[u] = True
            disc[u] = low[u] = timer[0]
            timer[0] += 1

            for v, lid in G.adj[u]:
                if not visited[v]:
                    child_count += 1
                    parent[v] = u
                    _dfs(v)
                    low[u] = min(low[u], low[v])

                    # AP condition: root with ≥2 children, or non-root with low[v] >= disc[u]
                    if parent[u] == -1 and child_count > 1:
                        ap_set.add(u)
                    if parent[u] != -1 and low[v] >= disc[u]:
                        ap_set.add(u)
                elif v != parent[u]:
                    low[u] = min(low[u], disc[v])

        sys.setrecursionlimit(max(10000, n * 20))
        for i in range(n):
            if not visited[i]:
                _dfs(i)

        self._aps = sorted(ap_set)
        return self._aps

    # ------------------------------------------------------------------
    # 3. Cut-line enumeration (bridges + high-betweenness non-bridges)
    # ------------------------------------------------------------------

    def discover_cut_lines(self, top_k: int = 10) -> List[Dict]:
        """
        Discovers the most dangerous cut-lines for islanding attacks.

        Strategy:
          1. True bridges (guaranteed islanding if tripped)
          2. Near-bridges: lines on many shortest paths (approximated by
             counting BFS paths through each line)
          3. Scored by islanding_risk

        Returns list of dicts: {line_id, is_bridge, risk_score, rank}
        """
        bridges = set(self.discover_bridges())
        risk_scores = self.compute_islanding_risk()

        # Combine bridge information with risk scores
        results = []
        for lid in self._G.line_ids:
            results.append({
                "line_id": lid,
                "is_bridge": lid in bridges,
                "risk_score": risk_scores.get(lid, 0.0),
                "from_bus": self._G.line_endpoints[lid][0],
                "to_bus": self._G.line_endpoints[lid][1],
            })

        # Sort by bridge first, then risk score
        results.sort(key=lambda x: (-int(x["is_bridge"]), -x["risk_score"]))
        for i, r in enumerate(results):
            r["rank"] = i + 1

        return results[:top_k]

    # ------------------------------------------------------------------
    # 4. Islanding Risk Score
    # ------------------------------------------------------------------

    def compute_islanding_risk(self) -> Dict[str, float]:
        """
        Computes islanding risk score for every line.

        Risk = w1 * bridge_flag
             + w2 * load_separation_score
             + w3 * betweenness_approx
             + w4 * degree_product_norm

        All components are normalized to [0, 1].
        Returns dict: {line_id: risk_score in [0,1]}
        """
        if self._risk is not None:
            return self._risk

        G = self._G
        bridges = set(self.discover_bridges())
        n_lines = len(G.line_ids)

        if n_lines == 0:
            self._risk = {}
            return self._risk

        bridge_flag = np.zeros(n_lines)
        load_sep = np.zeros(n_lines)
        btw_approx = np.zeros(n_lines)
        deg_prod = np.zeros(n_lines)

        # Degree of each bus
        degrees = np.array([len(G.adj[i]) for i in range(G.n)], dtype=np.float32)

        # Total load power
        total_load = sum(G.load_power.values()) if G.load_power else 1.0
        total_load = max(total_load, 1e-9)

        for i, lid in enumerate(G.line_ids):
            f, t = G.line_endpoints[lid]

            # --- Bridge flag ---
            bridge_flag[i] = 1.0 if lid in bridges else 0.0

            # --- Load separation: estimate load on each side of the cut ---
            # Remove this line and measure load imbalance between components
            load_side_a, load_side_b = self._estimate_load_split(lid)
            # Max separation at 50/50 split = 0; worst at 0/100 = 1
            frac = min(load_side_a, load_side_b) / total_load
            load_sep[i] = 1.0 - 2.0 * frac  # 1.0 if all load on one side

            # --- Betweenness approximation: BFS sample ---
            btw_approx[i] = self._approx_betweenness(lid)

            # --- Degree product normalized ---
            deg_prod[i] = degrees[f] * degrees[t]

        # Normalize each component
        def _norm(arr):
            lo, hi = arr.min(), arr.max()
            if hi - lo < 1e-9:
                return arr * 0
            return (arr - lo) / (hi - lo)

        bridge_flag_n = _norm(bridge_flag)
        load_sep_n    = _norm(load_sep)
        btw_n         = _norm(btw_approx)
        deg_prod_n    = _norm(deg_prod)

        # Weighted sum
        risk = 0.40 * bridge_flag_n + 0.30 * load_sep_n + 0.20 * btw_n + 0.10 * deg_prod_n

        self._risk = {lid: float(risk[i]) for i, lid in enumerate(G.line_ids)}
        return self._risk

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _estimate_load_split(self, remove_lid: str) -> Tuple[float, float]:
        """BFS-based load split estimation when line `remove_lid` is removed."""
        G = self._G
        f, t = G.line_endpoints[remove_lid]

        # BFS from f, excluding the removed line
        visited_a = set()
        queue = [f]
        visited_a.add(f)
        while queue:
            curr = queue.pop(0)
            for nb, lid in G.adj[curr]:
                if lid == remove_lid:
                    continue
                if nb not in visited_a:
                    visited_a.add(nb)
                    queue.append(nb)

        load_a = sum(G.load_power.get(b, 0.0) for b in visited_a)
        load_b = sum(G.load_power.get(b, 0.0) for b in range(G.n) if b not in visited_a)
        return load_a, load_b

    def _approx_betweenness(self, target_lid: str) -> float:
        """
        Approximates line betweenness using k random BFS shortest-path samples.
        Returns fraction of sampled paths passing through this line.
        """
        G = self._G
        n = G.n
        k = min(20, n)
        sampled = self.rng.choice(n, size=k * 2, replace=False if n >= k * 2 else True)
        sources = sampled[:k]
        targets_list = sampled[k:]

        count_through = 0
        count_total = 0

        for s, t_node in zip(sources, targets_list):
            if s == t_node:
                continue
            path_lines = self._bfs_path_lines(s, t_node)
            if path_lines is not None:
                count_total += 1
                if target_lid in path_lines:
                    count_through += 1

        return count_through / max(count_total, 1)

    def _bfs_path_lines(self, src: int, dst: int) -> Optional[Set[str]]:
        """BFS shortest path from src to dst; returns set of line IDs on path."""
        G = self._G
        if src == dst:
            return set()
        visited = {src: None}  # node → (parent, lid)
        queue = [src]
        found = False
        while queue and not found:
            curr = queue.pop(0)
            for nb, lid in G.adj[curr]:
                if nb not in visited:
                    visited[nb] = (curr, lid)
                    if nb == dst:
                        found = True
                        break
                    queue.append(nb)

        if dst not in visited:
            return None

        # Trace path
        path_lines = set()
        node = dst
        while visited[node] is not None:
            parent_node, lid = visited[node]
            path_lines.add(lid)
            node = parent_node
        return path_lines

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def get_top_k_cut_lines(self, k: int = 5) -> List[str]:
        """Returns top-k line_ids ranked by islanding risk."""
        risk = self.compute_islanding_risk()
        sorted_lines = sorted(risk.keys(), key=lambda lid: -risk[lid])
        return sorted_lines[:k]

    def bridge_recall(self, ground_truth_bridges: List[str]) -> float:
        """Compute recall of bridge detection vs known ground truth."""
        detected = set(self.discover_bridges())
        gt_set = set(ground_truth_bridges)
        if len(gt_set) == 0:
            return 1.0
        return len(detected & gt_set) / len(gt_set)

    def bridge_precision(self, ground_truth_bridges: List[str]) -> float:
        """Compute precision of bridge detection vs known ground truth."""
        detected = set(self.discover_bridges())
        gt_set = set(ground_truth_bridges)
        if len(detected) == 0:
            return 0.0
        return len(detected & gt_set) / len(detected)

    def summary(self) -> Dict:
        """Return summary statistics for this grid."""
        bridges = self.discover_bridges()
        aps = self.discover_articulation_points()
        risk = self.compute_islanding_risk()
        top5 = self.get_top_k_cut_lines(5)
        return {
            "grid": self.topo.grid_name if hasattr(self.topo, "grid_name") else "unknown",
            "n_buses": self._G.n,
            "n_lines": len(self._G.line_ids),
            "n_bridges": len(bridges),
            "n_articulation_points": len(aps),
            "bridge_fraction": len(bridges) / max(len(self._G.line_ids), 1),
            "top5_cut_lines": top5,
            "max_risk": max(risk.values()) if risk else 0.0,
            "mean_risk": float(np.mean(list(risk.values()))) if risk else 0.0,
        }
