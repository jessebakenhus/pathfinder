"use client";

import dynamic from "next/dynamic";
import { useCallback, useState } from "react";

const Map = dynamic(() => import("../components/Map"), { ssr: false });

export interface RouteResult {
  path: [number, number][];
  total_distance_km: number;
  node_count: number;
  snapped_lat: number;
  snapped_lon: number;
}

export const ROUTE_COLORS = ["#3b82f6", "#ef4444", "#22c55e", "#f59e0b", "#a855f7"];

export default function Home() {
  const [startPoint, setStartPoint] = useState<[number, number] | null>(null);
  const [distanceKm, setDistanceKm] = useState(5);
  const [routes, setRoutes] = useState<RouteResult[]>([]);
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleMapClick = useCallback((lat: number, lon: number) => {
    setStartPoint([lat, lon]);
    setRoutes([]);
    setSelectedIndex(null);
    setError(null);
  }, []);

  const generateRoutes = async () => {
    if (!startPoint) {
      setError("Click on the map to set a start point first.");
      return;
    }
    setLoading(true);
    setError(null);
    setSelectedIndex(null);
    try {
      const res = await fetch("http://localhost:8000/routes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          lat: startPoint[0],
          lon: startPoint[1],
          distance_km: distanceKm,
        }),
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail ?? "Failed to generate routes.");
      }
      const data = await res.json();
      setRoutes(data.routes);
      setSelectedIndex(0);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error.");
    } finally {
      setLoading(false);
    }
  };

  const selectedRoute = selectedIndex !== null ? routes[selectedIndex] : null;
  const snappedPoint: [number, number] | null = selectedRoute
    ? [selectedRoute.snapped_lat, selectedRoute.snapped_lon]
    : startPoint;

  return (
    <div style={{ display: "flex", height: "100vh" }}>
      {/* ── Sidebar ── */}
      <aside
        style={{
          width: 288,
          flexShrink: 0,
          background: "#111827",
          color: "#e5e7eb",
          padding: "28px 20px",
          display: "flex",
          flexDirection: "column",
          gap: 24,
          boxShadow: "2px 0 12px rgba(0,0,0,.4)",
          zIndex: 10,
          overflowY: "auto",
        }}
      >
        {/* Title */}
        <div>
          <h1 style={{ margin: 0, fontSize: 20, fontWeight: 700, color: "#f9fafb", letterSpacing: "-0.3px" }}>
            Pathfinder
          </h1>
          <p style={{ margin: "4px 0 0", fontSize: 12, color: "#6b7280" }}>
            Random greedy route generator
          </p>
        </div>

        {/* Start point */}
        <div>
          <label style={labelStyle}>START POINT</label>
          <div
            style={{
              background: "#1f2937",
              borderRadius: 8,
              padding: "10px 12px",
              fontSize: 12,
              color: startPoint ? "#93c5fd" : "#4b5563",
              fontFamily: "monospace",
              letterSpacing: "0.3px",
            }}
          >
            {startPoint
              ? `${startPoint[0].toFixed(5)}, ${startPoint[1].toFixed(5)}`
              : "Click on the map…"}
          </div>
        </div>

        {/* Distance slider */}
        <div>
          <label style={labelStyle}>
            TARGET DISTANCE&nbsp;
            <span style={{ color: "#93c5fd", fontWeight: 600 }}>{distanceKm} km</span>
          </label>
          <input
            type="range"
            min={1}
            max={20}
            step={0.5}
            value={distanceKm}
            onChange={(e) => setDistanceKm(Number(e.target.value))}
          />
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: "#4b5563", marginTop: 4 }}>
            <span>1 km</span>
            <span>20 km</span>
          </div>
        </div>

        {/* Generate button */}
        <button
          onClick={generateRoutes}
          disabled={loading || !startPoint}
          style={{
            background: loading || !startPoint ? "#1f2937" : "#2563eb",
            color: loading || !startPoint ? "#4b5563" : "#fff",
            border: "none",
            borderRadius: 8,
            padding: "12px 0",
            fontSize: 14,
            fontWeight: 600,
            cursor: loading || !startPoint ? "not-allowed" : "pointer",
            transition: "background 0.15s",
          }}
        >
          {loading ? "Generating…" : "Generate Routes"}
        </button>

        {/* Error */}
        {error && (
          <div
            style={{
              background: "#1f1010",
              border: "1px solid #7f1d1d",
              borderRadius: 8,
              padding: "10px 12px",
              fontSize: 13,
              color: "#fca5a5",
            }}
          >
            {error}
          </div>
        )}

        {/* Route list */}
        {routes.length > 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <label style={labelStyle}>ROUTES</label>
            {routes.map((r, i) => {
              const color = ROUTE_COLORS[i];
              const isSelected = i === selectedIndex;
              return (
                <button
                  key={i}
                  onClick={() => setSelectedIndex(i)}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 12,
                    background: isSelected ? "#1e3a5f" : "#1f2937",
                    border: isSelected ? `1.5px solid ${color}` : "1.5px solid transparent",
                    borderRadius: 8,
                    padding: "10px 12px",
                    cursor: "pointer",
                    textAlign: "left",
                    transition: "background 0.12s, border-color 0.12s",
                  }}
                >
                  {/* Color dot */}
                  <span
                    style={{
                      width: 12,
                      height: 12,
                      borderRadius: "50%",
                      background: color,
                      flexShrink: 0,
                    }}
                  />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 13, fontWeight: 600, color: isSelected ? "#f9fafb" : "#9ca3af" }}>
                      Route {i + 1}
                    </div>
                    <div style={{ fontSize: 12, color: isSelected ? "#93c5fd" : "#6b7280", marginTop: 2 }}>
                      {r.total_distance_km} km · {r.node_count} waypoints
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        )}

        <div style={{ marginTop: "auto", fontSize: 11, color: "#374151" }}>
          © OpenStreetMap · Düsseldorf, Germany
        </div>
      </aside>

      {/* ── Map ── */}
      <main style={{ flex: 1, position: "relative" }}>
        <Map
          onMapClick={handleMapClick}
          startPoint={snappedPoint}
          routes={routes}
          selectedIndex={selectedIndex}
          onSelectRoute={setSelectedIndex}
        />
      </main>
    </div>
  );
}

const labelStyle: React.CSSProperties = {
  display: "block",
  fontSize: 11,
  fontWeight: 600,
  color: "#6b7280",
  letterSpacing: "0.6px",
  marginBottom: 8,
};
