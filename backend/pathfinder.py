import random
from typing import List

import networkx as nx
import numpy as np


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(a))


def _edge_length_km(G, u: int, v: int) -> float:
    edge_data = G.get_edge_data(u, v) or {}
    return min((d.get("length", 50) for d in edge_data.values()), default=50) / 1000.0


def _destination_point(lat: float, lon: float, bearing_deg: float, dist_km: float):
    """Point reached by travelling dist_km in bearing_deg from (lat, lon)."""
    R = 6371.0
    lat_r, lon_r, b = np.radians(lat), np.radians(lon), np.radians(bearing_deg)
    d = dist_km / R
    lat2 = np.arcsin(np.sin(lat_r) * np.cos(d) + np.cos(lat_r) * np.sin(d) * np.cos(b))
    lon2 = lon_r + np.arctan2(
        np.sin(b) * np.sin(d) * np.cos(lat_r),
        np.cos(d) - np.sin(lat_r) * np.sin(lat2),
    )
    return float(np.degrees(lat2)), float(np.degrees(lon2))


def _nearest_node(node_ids: list, coords: np.ndarray, lat: float, lon: float) -> int:
    """Vectorised O(n) nearest-node search."""
    lat_r = np.radians(lat)
    lats_r = np.radians(coords[:, 0])
    lons_r = np.radians(coords[:, 1])
    dlat = lats_r - lat_r
    dlon = lons_r - np.radians(lon)
    a = np.sin(dlat / 2) ** 2 + np.cos(lat_r) * np.cos(lats_r) * np.sin(dlon / 2) ** 2
    return node_ids[int(np.argmin(a))]  # argmin of a ↔ argmin of haversine


def random_greedy_route(
    G, start_node: int, target_km: float, seed: int | None = None
) -> List[int]:
    """
    Anchor-point loop routing.

    Places N waypoints evenly around an imaginary circle whose circumference
    equals target_km, snaps each to the nearest walkable graph node, then
    connects them in order via Dijkstra. Produces clean, oval-shaped loops
    similar to Strava's route builder.

    Args:
        G:           Undirected OSMnx walking graph.
        start_node:  Node to start and end at.
        target_km:   Target loop length in km.
        seed:        Optional random seed.

    Returns:
        Ordered list of node IDs (first == last == start_node).
    """
    if seed is not None:
        random.seed(seed)

    start = G.nodes[start_node]
    start_lat, start_lon = start["y"], start["x"]

    # Pre-build node array once for fast nearest-node queries
    node_ids = list(G.nodes())
    coords = np.array([[G.nodes[n]["y"], G.nodes[n]["x"]] for n in node_ids])

    # ── Imaginary loop circle ──────────────────────────────────────────────
    # Circumference = target_km  →  radius = target_km / (2π)
    # Centre is placed one radius ahead of the start in a random direction.
    loop_radius_km = target_km / (2 * np.pi)
    initial_bearing = random.uniform(0, 360)
    center_lat, center_lon = _destination_point(
        start_lat, start_lon, initial_bearing, loop_radius_km
    )

    # ── Anchor points on the circle ───────────────────────────────────────
    # N points, evenly spaced.  fraction=0 ≈ start,  fraction=1 = start.
    # We skip fraction=0 (already at start) and set the last anchor = start_node
    # so the route closes cleanly.
    N = 6
    anchors: List[int] = []
    for i in range(1, N + 1):
        fraction = i / N
        angle = (initial_bearing + 180 + fraction * 360) % 360
        alat, alon = _destination_point(center_lat, center_lon, angle, loop_radius_km)
        node = _nearest_node(node_ids, coords, alat, alon)
        anchors.append(node)
    anchors[-1] = start_node  # enforce hard close back to start

    # ── Route through anchors with Dijkstra ───────────────────────────────
    # Work on a copy so we can penalise already-used edges without mutating G.
    H = G.copy()
    REVISIT_PENALTY = 10  # multiply edge weight by this if already traversed

    visited_edges: set = set()
    full_path: List[int] = [start_node]
    current = start_node
    for anchor in anchors:
        if anchor == current:
            continue
        try:
            segment = nx.shortest_path(H, current, anchor, weight="length")
            full_path.extend(segment[1:])
            # Penalise the edges we just used so future segments avoid them.
            for u, v in zip(segment[:-1], segment[1:]):
                edge_key = (min(u, v), max(u, v))
                if edge_key not in visited_edges:
                    visited_edges.add(edge_key)
                    edge_data = H.get_edge_data(u, v)
                    if edge_data:
                        for k in edge_data:
                            edge_data[k]["length"] = (
                                edge_data[k].get("length", 50) * REVISIT_PENALTY
                            )
            current = anchor
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            continue  # skip unreachable anchor, try the next one

    return full_path


def path_distance_km(G, path: List[int]) -> float:
    return sum(_edge_length_km(G, path[i], path[i + 1]) for i in range(len(path) - 1))
