"use client";

import { FolderOpen, Upload, GitFork } from "lucide-react";

/**
 * RepoPanel — left sidebar showing the repository file tree.
 * Phase 1: empty state with upload CTA.
 * Phase 2+: populated from ingestion job metadata.
 */
export default function RepoPanel() {
  return (
    <>
      {/* ── Header ──────────────────────────────────────────────────────── */}
      <div className="panel-header">
        <FolderOpen className="w-4 h-4" style={{ color: "var(--accent)" }} aria-hidden="true" />
        <span className="text-xs font-semibold uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>
          Repository
        </span>
      </div>

      {/* ── Empty State ──────────────────────────────────────────────────── */}
      <div
        className="flex flex-col items-center justify-center flex-1 gap-4 p-6 text-center fade-up"
        aria-label="No repository loaded"
      >
        <div
          className="w-14 h-14 rounded-2xl flex items-center justify-center"
          style={{ background: "var(--bg-hover)", border: "1px solid var(--border-bright)" }}
          aria-hidden="true"
        >
          <GitFork className="w-7 h-7" style={{ color: "var(--text-muted)" }} />
        </div>

        <div>
          <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
            No repo loaded
          </p>
          <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
            Upload a ZIP or paste a GitHub URL to begin analysis
          </p>
        </div>

        <button
          id="upload-repo-btn"
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all duration-200 hover:scale-105 active:scale-95"
          style={{
            background: "linear-gradient(135deg, var(--accent), var(--accent-dim))",
            color: "white",
            boxShadow: "0 4px 15px var(--accent-glow)",
          }}
          aria-label="Upload repository"
        >
          <Upload className="w-3.5 h-3.5" aria-hidden="true" />
          Upload Repo
        </button>
      </div>
    </>
  );
}
