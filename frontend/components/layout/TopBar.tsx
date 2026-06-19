"use client";

import { useState, useEffect } from "react";
import { Activity, Cpu, Database, GitBranch, Server } from "lucide-react";
import { fetchHealth } from "@/lib/api";
import type { HealthResponse } from "@/lib/types";


const SERVICE_ICONS: Record<string, React.ReactNode> = {
  qdrant:   <Database  className="w-3 h-3" aria-hidden="true" />,
  neo4j:    <GitBranch className="w-3 h-3" aria-hidden="true" />,
  redis:    <Server    className="w-3 h-3" aria-hidden="true" />,
  postgres: <Database  className="w-3 h-3" aria-hidden="true" />,
  ollama:   <Cpu       className="w-3 h-3" aria-hidden="true" />,
};

/**
 * TopBar — application header with live service health indicators.
 * Health is polled every 30 seconds.
 */
export default function TopBar() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchHealthData = async () => {
    try {
      const data = await fetchHealth();
      setHealth(data);
    } catch {
      setHealth(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealthData();
    const interval = setInterval(fetchHealthData, 30_000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header
      className="flex items-center justify-between px-4 flex-none"
      style={{
        height: "var(--panel-header)",
        background: "var(--bg-elevated)",
        borderBottom: "1px solid var(--border)",
        zIndex: 10,
      }}
      role="banner"
    >
      {/* ── Brand ─────────────────────────────────────────────────────────── */}
      <div className="flex items-center gap-2">
        <div
          className="w-7 h-7 rounded-lg flex items-center justify-center glow-accent"
          style={{ background: "linear-gradient(135deg, var(--accent), var(--accent-dim))" }}
          aria-hidden="true"
        >
          <Activity className="w-4 h-4 text-white" />
        </div>
        <span className="text-sm font-semibold gradient-text tracking-wide">
          Codebase Intelligence
        </span>
      </div>

      {/* ── Service health pills ───────────────────────────────────────────── */}
      <nav aria-label="Service health status" className="flex items-center gap-2">
        {loading ? (
          <div className="flex gap-1.5" aria-busy="true" aria-label="Loading health status">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="skeleton w-16 h-5 rounded-full" />
            ))}
          </div>
        ) : health ? (
          Object.entries(health.services).map(([name, svc]) => (
            <div
              key={name}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium"
              style={{
                background: svc.status === "ok"
                  ? "rgba(34, 211, 165, 0.1)"
                  : "rgba(244, 63, 94, 0.1)",
                border: `1px solid ${svc.status === "ok" ? "rgba(34,211,165,0.25)" : "rgba(244,63,94,0.25)"}`,
                color: svc.status === "ok" ? "var(--success)" : "var(--error)",
              }}
              title={`${name}: ${svc.latency_ms}ms${svc.detail ? " — " + svc.detail : ""}`}
              role="status"
              aria-label={`${name} is ${svc.status}`}
            >
              <span
                className="status-dot"
                style={{ background: svc.status === "ok" ? "var(--success)" : "var(--error)" }}
                aria-hidden="true"
              />
              {SERVICE_ICONS[name]}
              <span className="capitalize hidden sm:inline">{name}</span>
            </div>
          ))
        ) : (
          <span className="text-xs" style={{ color: "var(--text-muted)" }}>
            API offline
          </span>
        )}
      </nav>
    </header>
  );
}
