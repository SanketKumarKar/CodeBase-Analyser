"use client";

import { Share2, Layers } from "lucide-react";

/**
 * GraphPanel — right sidebar for the architecture graph visualization.
 * Phase 1: empty state.
 * Phase 5+: React Flow graph fed by GET /repo/graph.
 * Phase 8+: highlights active call chain on chat citation click.
 */
export default function GraphPanel() {
  return (
    <>
      {/* ── Header ──────────────────────────────────────────────────────── */}
      <div className="panel-header" style={{ borderLeft: "1px solid var(--border)" }}>
        <Share2 className="w-4 h-4" style={{ color: "var(--accent)" }} aria-hidden="true" />
        <span className="text-xs font-semibold uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>
          Architecture
        </span>
      </div>

      {/* ── Empty State ──────────────────────────────────────────────────── */}
      <div
        className="flex flex-col items-center justify-center flex-1 gap-4 p-5 text-center fade-up"
        style={{ borderLeft: "1px solid var(--border)" }}
        aria-label="No graph loaded"
      >
        {/* Animated placeholder graph nodes */}
        <div className="relative w-32 h-32" aria-hidden="true">
          {/* Centre node */}
          <div
            className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-10 h-10 rounded-xl flex items-center justify-center glow-accent"
            style={{ background: "linear-gradient(135deg, var(--accent), var(--accent-dim))" }}
          >
            <Layers className="w-5 h-5 text-white" />
          </div>
          {/* Orbiting decorative nodes */}
          {[
            { top: "0%",  left: "50%", delay: "0s"    },
            { top: "50%", left: "0%",  delay: "0.2s"  },
            { top: "50%", left: "90%", delay: "0.4s"  },
            { top: "85%", left: "25%", delay: "0.6s"  },
            { top: "85%", left: "65%", delay: "0.8s"  },
          ].map((pos, i) => (
            <div
              key={i}
              className="absolute w-5 h-5 rounded-md"
              style={{
                top: pos.top, left: pos.left,
                transform: "translate(-50%, -50%)",
                background: "var(--bg-hover)",
                border: "1px solid var(--border-bright)",
                animation: `pulse-dot 2s ease-in-out ${pos.delay} infinite`,
              }}
            />
          ))}
          {/* Decorative connecting lines (SVG) */}
          <svg className="absolute inset-0 w-full h-full" aria-hidden="true">
            <line x1="50%" y1="50%" x2="50%" y2="10%" stroke="var(--border-bright)" strokeWidth="1" strokeDasharray="3 2" />
            <line x1="50%" y1="50%" x2="10%" y2="50%" stroke="var(--border-bright)" strokeWidth="1" strokeDasharray="3 2" />
            <line x1="50%" y1="50%" x2="90%" y2="50%" stroke="var(--border-bright)" strokeWidth="1" strokeDasharray="3 2" />
            <line x1="50%" y1="50%" x2="28%" y2="88%" stroke="var(--border-bright)" strokeWidth="1" strokeDasharray="3 2" />
            <line x1="50%" y1="50%" x2="68%" y2="88%" stroke="var(--border-bright)" strokeWidth="1" strokeDasharray="3 2" />
          </svg>
        </div>

        <div>
          <p className="text-xs font-medium" style={{ color: "var(--text-primary)" }}>
            No graph yet
          </p>
          <p className="text-[11px] mt-1 leading-relaxed" style={{ color: "var(--text-muted)" }}>
            Graph will render after ingestion — showing functions, classes, modules, and their relationships.
          </p>
        </div>

        {/* Legend */}
        <div className="flex flex-col gap-1.5 w-full text-[10px]" role="list" aria-label="Graph node types">
          {[
            { color: "#6c63ff", label: "Function / Method" },
            { color: "#22d3a5", label: "Class" },
            { color: "#38bdf8", label: "API Route" },
            { color: "#fb923c", label: "Package / Dep" },
          ].map((item) => (
            <div key={item.label} className="flex items-center gap-2" role="listitem">
              <div className="w-3 h-3 rounded-sm flex-none" style={{ background: item.color }} aria-hidden="true" />
              <span style={{ color: "var(--text-muted)" }}>{item.label}</span>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}
