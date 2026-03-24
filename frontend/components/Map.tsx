"use client";

import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { MapContainer, Marker, Polyline, TileLayer, useMapEvents } from "react-leaflet";
import { ROUTE_COLORS, RouteResult } from "../app/page";

// Fix Leaflet's broken default icon in webpack builds
delete (L.Icon.Default.prototype as unknown as Record<string, unknown>)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

// ── Click handler ──────────────────────────────────────────────────────────

function ClickHandler({ onClick }: { onClick: (lat: number, lon: number) => void }) {
  useMapEvents({
    click(e) {
      onClick(e.latlng.lat, e.latlng.lng);
    },
  });
  return null;
}

// ── Map component ──────────────────────────────────────────────────────────

interface MapProps {
  onMapClick: (lat: number, lon: number) => void;
  startPoint: [number, number] | null;
  routes: RouteResult[];
  selectedIndex: number | null;
  onSelectRoute: (index: number) => void;
}

export default function Map({ onMapClick, startPoint, routes, selectedIndex, onSelectRoute }: MapProps) {
  return (
    <MapContainer
      center={[51.2254, 6.7763]} // Düsseldorf city centre
      zoom={13}
      style={{ height: "100%", width: "100%" }}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      <ClickHandler onClick={onMapClick} />

      {startPoint && <Marker position={startPoint} />}

      {/* Unselected routes rendered first (below) */}
      {routes.map((route, i) => {
        if (i === selectedIndex || route.path.length < 2) return null;
        return (
          <Polyline
            key={i}
            positions={route.path}
            pathOptions={{ color: ROUTE_COLORS[i], weight: 3, opacity: 0.35 }}
            eventHandlers={{ click: () => onSelectRoute(i) }}
          />
        );
      })}

      {/* Selected route rendered on top */}
      {selectedIndex !== null && routes[selectedIndex]?.path.length > 1 && (
        <Polyline
          key={`selected-${selectedIndex}`}
          positions={routes[selectedIndex].path}
          pathOptions={{ color: ROUTE_COLORS[selectedIndex], weight: 5, opacity: 0.9 }}
        />
      )}
    </MapContainer>
  );
}
