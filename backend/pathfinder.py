import random
from typing import List

import networkx as nx
import numpy as np


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Spherical distance in km between two (lat, lon) points."""
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(a))


def _edge_length_km(G, u: int, v: int) -> float:
    """Get the shortest edge length (in km) between two nodes."""
    edge_data = G.get_edge_data(u, v) or {}
    return min((d.get("length", 50) for d in edge_data.values()), default=50) / 1000.0


def random_greedy_route(
    G, start_node: int, target_km: float, seed: int | None = None
) -> List[int]:
    """
    Random greedy pathfinding algorithm for loop routes.

    Phase 1 – Outward walk:
      At each step, sample a neighbor weighted by its haversine distance from
      the origin. Nodes farther from the start are preferred, creating an
      outward-exploring bias while retaining randomness.

    Phase 2 – Return leg:
      From the turnaround node, compute the shortest path back to start via
      Dijkstra (networkx). Concatenate both legs.

    Args:
        G: Undirected OSMnx graph.
        start_node: Node ID to start and end at.
        target_km: Desired total route length.
        seed: Optional random seed for reproducibility.

    Returns:
        Ordered list of node IDs forming the route.
    """
    if seed is not None:
        random.seed(seed)

    start = G.nodes[start_node]
    start_lat, start_lon = start["y"], start["x"]

    path: List[int] = [start_node]
    current = start_node
    accumulated_km = 0.0
    half_target = target_km / 2.0

    # --- Phase 1: outward walk ---
    while accumulated_km < half_target:
        neighbors = list(G.neighbors(current))
        if not neighbors:
            break

        # Avoid the last few visited nodes to prevent tight back-and-forth loops
        recent = set(path[-4:])
        candidates = [n for n in neighbors if n not in recent] or neighbors

        # Weight by distance from origin — farther = more attractive when outbound
        weights = []
        for n in candidates:
            nd = G.nodes[n]
            d = haversine_km(start_lat, start_lon, nd["y"], nd["x"])
            weights.append(max(d, 0.01))  # guard against zero weight

        next_node = random.choices(candidates, weights=weights, k=1)[0]
        accumulated_km += _edge_length_km(G, current, next_node)
        path.append(next_node)
        current = next_node

    # --- Phase 2: return to start via Dijkstra ---
    try:
        return_path = nx.shortest_path(G, current, start_node, weight="length")
        return path + return_path[1:]
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return path


def path_distance_km(G, path: List[int]) -> float:
    """Sum edge weights along a path; returns total distance in km."""
    return sum(_edge_length_km(G, path[i], path[i + 1]) for i in range(len(path) - 1))
