"use client";

import { MessageSquare, Sparkles, Zap, Network, Brain } from "lucide-react";

const FEATURE_PILLS = [
  { icon: <Zap   className="w-3 h-3" aria-hidden="true" />, label: "Vector Search",   className: "badge-vector" },
  { icon: <Network className="w-3 h-3" aria-hidden="true" />, label: "Graph Traversal", className: "badge-graph"  },
  { icon: <Brain className="w-3 h-3" aria-hidden="true" />, label: "Memory-aware",    className: "badge-memory" },
];

/**
 * ChatPanel — center panel for conversational code analysis.
 * Phase 1: empty state showcasing the three retrieval modes.
 * Phase 7+: full streaming chat with LangGraph orchestration.
 */
export default function ChatPanel() {
  return (
    <div className="flex flex-col h-full">
      {/* ── Header ──────────────────────────────────────────────────────── */}
      <div className="panel-header" style={{ borderBottom: "1px solid var(--border)" }}>
        <MessageSquare className="w-4 h-4" style={{ color: "var(--accent)" }} aria-hidden="true" />
        <span className="text-xs font-semibold uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>
          Chat
        </span>
        <div className="flex gap-1.5 ml-auto">
          {FEATURE_PILLS.map((p) => (
            <span
              key={p.label}
              className={`flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium ${p.className}`}
            >
              {p.icon}
              {p.label}
            </span>
          ))}
        </div>
      </div>

      {/* ── Messages area ────────────────────────────────────────────────── */}
      <div
        className="flex-1 overflow-y-auto flex flex-col items-center justify-center gap-6 p-8 fade-up"
        aria-label="Chat messages"
        aria-live="polite"
      >
        {/* Hero glow orb */}
        <div
          className="relative w-20 h-20 rounded-full flex items-center justify-center"
          style={{
            background: "radial-gradient(circle, rgba(108,99,255,0.3) 0%, transparent 70%)",
            boxShadow: "0 0 60px rgba(108,99,255,0.4)",
          }}
          aria-hidden="true"
        >
          <div
            className="w-14 h-14 rounded-full flex items-center justify-center"
            style={{ background: "linear-gradient(135deg, var(--accent), #38bdf8)" }}
          >
            <Sparkles className="w-7 h-7 text-white" />
          </div>
        </div>

        <div className="text-center max-w-sm">
          <h1 className="text-xl font-bold gradient-text text-glow mb-2">
            Codebase Intelligence Agent
          </h1>
          <p className="text-sm leading-relaxed" style={{ color: "var(--text-muted)" }}>
            Upload a repository, then ask anything — architecture questions, bug traces,
            dependency analysis, and more. Powered by hybrid RAG.
          </p>
        </div>

        {/* Example prompts */}
        <div className="flex flex-col gap-2 w-full max-w-sm" role="list" aria-label="Example questions">
          {[
            "Where is authentication handled?",
            "Trace the request lifecycle for /api/login",
            "Which packages are unused?",
          ].map((prompt) => (
            <button
              key={prompt}
              role="listitem"
              className="text-left text-xs px-4 py-3 rounded-xl transition-all duration-200 hover:scale-[1.02] active:scale-95"
              style={{
                background: "var(--bg-elevated)",
                border: "1px solid var(--border-bright)",
                color: "var(--text-primary)",
              }}
              aria-label={`Ask: ${prompt}`}
            >
              <span style={{ color: "var(--accent)" }}>→ </span>
              {prompt}
            </button>
          ))}
        </div>
      </div>

      {/* ── Input bar ────────────────────────────────────────────────────── */}
      <div
        className="p-4"
        style={{ borderTop: "1px solid var(--border)", background: "var(--bg-panel)" }}
      >
        <div
          className="flex items-center gap-3 px-4 py-3 rounded-xl"
          style={{ background: "var(--bg-elevated)", border: "1px solid var(--border-bright)" }}
          role="group"
          aria-label="Message input"
        >
          <input
            id="chat-input"
            type="text"
            placeholder="Upload a repository first to begin asking questions…"
            disabled
            className="flex-1 bg-transparent text-sm outline-none placeholder:text-sm"
            style={{ color: "var(--text-primary)" }}
            aria-label="Chat message input"
            aria-disabled="true"
          />
          <button
            id="chat-send-btn"
            disabled
            className="px-3 py-1.5 rounded-lg text-xs font-semibold opacity-40 cursor-not-allowed"
            style={{ background: "var(--accent)", color: "white" }}
            aria-label="Send message (disabled until repository is loaded)"
          >
            Send
          </button>
        </div>
        <p className="text-center text-[10px] mt-2" style={{ color: "var(--text-dim)" }}>
          gemma4 · qwen3-embedding:4b · Qdrant · Neo4j AuraDB · Mem0
        </p>
      </div>
    </div>
  );
}
