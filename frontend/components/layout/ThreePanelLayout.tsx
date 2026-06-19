"use client";

import React from "react";

interface ThreePanelLayoutProps {
  left: React.ReactNode;
  center: React.ReactNode;
  right: React.ReactNode;
}

/**
 * ThreePanelLayout — the core app shell.
 *
 * Left  : Repository explorer (fixed 260px)
 * Center: Chat interface (flex-1, fills remaining space)
 * Right : Architecture graph (fixed 320px)
 *
 * Panels are separated by thin 1px borders matching the design token --border.
 */
export default function ThreePanelLayout({ left, center, right }: ThreePanelLayoutProps) {
  return (
    <main
      className="flex flex-1 overflow-hidden"
      style={{ height: "calc(100vh - 48px)" }}
      aria-label="Main application workspace"
    >
      {/* ── Left Panel — Repository Explorer ─────────────────────────────── */}
      <aside
        className="panel flex-none"
        style={{ width: "var(--sidebar-width)" }}
        aria-label="Repository file explorer"
      >
        {left}
      </aside>

      {/* ── Center Panel — Chat Interface ─────────────────────────────────── */}
      <section
        className="flex flex-col flex-1 overflow-hidden"
        style={{ background: "var(--bg-base)", borderRight: "1px solid var(--border)" }}
        aria-label="Chat interface"
      >
        {center}
      </section>

      {/* ── Right Panel — Architecture Graph ──────────────────────────────── */}
      <aside
        className="panel flex-none"
        style={{ width: "var(--graph-width)", borderRight: "none" }}
        aria-label="Architecture graph visualization"
      >
        {right}
      </aside>
    </main>
  );
}
