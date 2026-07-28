import os
import sys
import numpy as np
import networkx as nx

# Setup paths to import sibling modules
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(current_dir)
sys.path.append(parent_dir)
sys.path.append(os.path.join(parent_dir, "digital_twin"))

from grid_topology import GridTopology

class TopologyAnalyzer:
    def __init__(self, topo: GridTopology = None):
        self.topo = topo if topo is not None else GridTopology()
        self.num_buses = self.topo.num_buses
        
        # Build networkx Graph representation of IEEE 39-Bus Grid
        self.G = nx.Graph()
        self.G.add_nodes_from(range(self.num_buses))
        
        for k, line in enumerate(self.topo.lines):
            u = line["from"]
            v = line["to"]
            # Store resistance/reactance as weights
            r = line["R"]
            x = line["X"]
            z_mag = np.sqrt(r**2 + x**2) if (r**2 + x**2) > 0 else 1e-4
            self.G.add_edge(u, v, weight=z_mag, id=line["id"], index=k)
            
    def critical_nodes(self, top_n=5) -> list:
        """
        Identify top critical nodes (buses) based on structural betweenness centrality.
        """
        # Betweenness centrality measures the fraction of all shortest paths that pass through a node
        centrality = nx.betweenness_centrality(self.G)
        sorted_nodes = sorted(centrality.items(), key=lambda item: item[1], reverse=True)
        return [{"bus_id": node, "centrality_score": float(score)} for node, score in sorted_nodes[:top_n]]
        
    def critical_lines(self, top_n=5) -> list:
        """
        Identify top critical branches based on edge betweenness centrality.
        """
        edge_centrality = nx.edge_betweenness_centrality(self.G)
        sorted_edges = sorted(edge_centrality.items(), key=lambda item: item[1], reverse=True)
        
        results = []
        for (u, v), score in sorted_edges[:top_n]:
            # Find line ID
            edge_data = self.G[u][v]
            results.append({
                "from": u,
                "to": v,
                "line_id": edge_data["id"],
                "centrality_score": float(score)
            })
        return results
        
    def vulnerability_scores(self, node_risks: np.ndarray = None) -> dict:
        """
        Computes local vulnerability scores for all 39 buses.
        If current node_risks (from GNN model inference) are provided, we fuse them with
        structural pagerank centrality.
        """
        pagerank = nx.pagerank(self.G)
        
        vuln_dict = {}
        for i in range(self.num_buses):
            structural = pagerank[i]
            if node_risks is not None:
                # Weighted average: 40% structural, 60% physical dynamic risk
                dynamic = float(node_risks[i])
                score = 0.4 * structural * 39 + 0.6 * dynamic
            else:
                score = float(structural * 39)
            vuln_dict[i] = score
            
        return vuln_dict
        
    def propagation_paths(self, source_bus: int, target_bus: int) -> list:
        """
        Finds the shortest electrical propagation path between a source bus and a target bus.
        """
        try:
            path = nx.shortest_path(self.G, source=source_bus, target=target_bus, weight="weight")
            return [int(n) for n in path]
        except nx.NetworkXNoPath:
            return []
            
    def get_vulnerable_regions(self, threshold=1.0, node_risks: np.ndarray = None) -> list:
        """
        Groups nodes that have vulnerability scores above a certain threshold into regions (connected components).
        """
        vuln_scores = self.vulnerability_scores(node_risks)
        high_vuln_nodes = [node for node, score in vuln_scores.items() if score > threshold]
        
        # Get subgraph of highly vulnerable nodes
        subgraph = self.G.subgraph(high_vuln_nodes)
        components = list(nx.connected_components(subgraph))
        
        regions = []
        for i, comp in enumerate(components):
            regions.append({
                "region_id": i + 1,
                "nodes": [int(n) for n in comp],
                "mean_vulnerability": float(np.mean([vuln_scores[n] for n in comp]))
            })
        return sorted(regions, key=lambda r: r["mean_vulnerability"], reverse=True)
