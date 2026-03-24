import random
from contextlib import asynccontextmanager
from pathlib import Path

import osmnx as ox
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from pathfinder import path_distance_km, random_greedy_route

# ---------------------------------------------------------------------------
# Graph – loaded once at startup, optionally cached on disk
# ---------------------------------------------------------------------------

CACHE_PATH = Path(__file__).parent.parent / "experiment" / "cache" / "duesseldorf_walk.graphml"
PLACE = "Düsseldorf, Germany"

G = None  # undirected walking graph


@asynccontextmanager
async def lifespan(app: FastAPI):
    global G
    if CACHE_PATH.exists():
        print(f"Loading graph from cache: {CACHE_PATH}")
        G = ox.load_graphml(CACHE_PATH)
    else:
        print(f"Downloading OSM graph for {PLACE} …")
        raw = ox.graph_from_place(PLACE, network_type="walk")
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        ox.save_graphml(raw, CACHE_PATH)
        print(f"Graph cached to {CACHE_PATH}")
        G = raw

    G = ox.convert.to_undirected(G)
    print(f"Graph ready — {len(G.nodes):,} nodes, {len(G.edges):,} edges")
    yield
    G = None


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="Pathfinder API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class RouteRequest(BaseModel):
    lat: float = Field(..., description="Start latitude")
    lon: float = Field(..., description="Start longitude")
    distance_km: float = Field(..., ge=0.5, le=30, description="Target distance (km)")
    seed: int | None = Field(None, description="Random seed for reproducibility")


class RouteResponse(BaseModel):
    path: list[list[float]]
    total_distance_km: float
    node_count: int
    snapped_lat: float
    snapped_lon: float


class RoutesResponse(BaseModel):
    routes: list[RouteResponse]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

NUM_ROUTES = 5


@app.get("/health")
def health():
    return {"status": "ok", "graph_loaded": G is not None}


def _build_route_response(start_node: int, distance_km: float, seed: int) -> RouteResponse:
    path_nodes = random_greedy_route(G, start_node, distance_km, seed=seed)
    coords = [[G.nodes[n]["y"], G.nodes[n]["x"]] for n in path_nodes]
    total_km = path_distance_km(G, path_nodes)
    snapped = G.nodes[start_node]
    return RouteResponse(
        path=coords,
        total_distance_km=round(total_km, 2),
        node_count=len(path_nodes),
        snapped_lat=snapped["y"],
        snapped_lon=snapped["x"],
    )


@app.post("/routes", response_model=RoutesResponse)
def generate_routes(req: RouteRequest):
    if G is None:
        raise HTTPException(503, detail="Graph is still loading, try again shortly.")

    try:
        start_node = ox.nearest_nodes(G, req.lon, req.lat)
    except Exception as e:
        raise HTTPException(400, detail=f"Could not find nearest node: {e}")

    base_seed = req.seed if req.seed is not None else random.randint(0, 10_000)

    routes: list[RouteResponse] = []
    for i in range(NUM_ROUTES):
        try:
            routes.append(_build_route_response(start_node, req.distance_km, seed=base_seed + i))
        except Exception as e:
            raise HTTPException(500, detail=f"Route {i + 1} generation failed: {e}")

    return RoutesResponse(routes=routes)
