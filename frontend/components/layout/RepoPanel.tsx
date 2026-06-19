"use client";

import { useState, useCallback, useRef } from "react";
import {
  FolderOpen,
  Upload,
  GitFork,
  Link,
  Loader2,
  CheckCircle2,
  AlertCircle,
  FileCode,
  FolderTree,
} from "lucide-react";

import { uploadRepoByUrl, uploadRepoZip, fetchJobStatus, getErrorMessage } from "@/lib/api";
import type { IngestionJob } from "@/lib/types";

type JobMeta = IngestionJob;

const STATUS_LABELS: Record<NonNullable<JobMeta["status"]>, string> = {
  idle:      "Ready",
  pending:   "Queued…",
  cloning:   "Cloning repository…",
  parsing:   "Scanning files…",
  embedding: "Generating embeddings…",
  graphing:  "Building graph…",
  ready:     "Ready",
  failed:    "Failed",
};

const STATUS_PROGRESS: Record<NonNullable<JobMeta["status"]>, number> = {
  idle: 0, pending: 5, cloning: 20, parsing: 45,
  embedding: 70, graphing: 90, ready: 100, failed: 0,
};

/**
 * RepoPanel — left sidebar with upload modal and live ingestion progress.
 * Uses axios service layer (lib/api.ts) for all API calls.
 */
export default function RepoPanel() {
  const [mode, setMode] = useState<"url" | "zip">("url");
  const [urlInput, setUrlInput] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const [job, setJob] = useState<JobMeta | null>(null);
  const [loading, setLoading] = useState(false);
  const [showUpload, setShowUpload] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pollRef = useRef<NodeJS.Timeout | null>(null);

  // ── Polling ───────────────────────────────────────────────────────────────
  const startPolling = useCallback((jobId: string) => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const data = await fetchJobStatus(jobId);
        setJob(data);
        if (data.status === "ready" || data.status === "failed") {
          clearInterval(pollRef.current!);
        }
      } catch { /* silent — job status stays stale until next poll */ }
    }, 2000);
  }, []);

  // ── Submit URL ────────────────────────────────────────────────────────────
  const handleUrlSubmit = async () => {
    if (!urlInput.trim()) return;
    setLoading(true);
    try {
      const data = await uploadRepoByUrl(urlInput.trim());
      setJob(data);
      setShowUpload(false);
      startPolling(data.job_id);
    } catch (e: unknown) {
      setJob({ job_id: "", status: "failed", error_message: getErrorMessage(e) });
    } finally {
      setLoading(false);
    }
  };

  // ── Submit ZIP ────────────────────────────────────────────────────────────
  const handleZipUpload = async (file: File) => {
    setLoading(true);
    try {
      const data = await uploadRepoZip(file);
      setJob(data);
      setShowUpload(false);
      startPolling(data.job_id);
    } catch (e: unknown) {
      setJob({ job_id: "", status: "failed", error_message: getErrorMessage(e) });
    } finally {
      setLoading(false);
    }
  };

  const progress = job?.status ? STATUS_PROGRESS[job.status] ?? 0 : 0;
  const isWorking = job && !["idle", "ready", "failed"].includes(job.status ?? "");

  return (
    <>
      {/* ── Header ──────────────────────────────────────────────────────── */}
      <div className="panel-header">
        <FolderOpen className="w-4 h-4" style={{ color: "var(--accent)" }} aria-hidden />
        <span className="text-xs font-semibold uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>
          Repository
        </span>
        {(!job || job.status === "failed") && (
          <button
            id="open-upload-btn"
            onClick={() => setShowUpload(true)}
            className="ml-auto p-1 rounded-md transition-colors hover:bg-[var(--bg-hover)]"
            title="Upload repository"
            aria-label="Upload repository"
          >
            <Upload className="w-3.5 h-3.5" style={{ color: "var(--accent)" }} />
          </button>
        )}
      </div>

      {/* ── Upload Modal (inline) ────────────────────────────────────────── */}
      {showUpload && (
        <div className="p-4 border-b fade-up" style={{ borderColor: "var(--border)" }}>
          {/* Tab switcher */}
          <div
            className="flex rounded-lg overflow-hidden mb-3"
            style={{ background: "var(--bg-hover)" }}
            role="tablist"
            aria-label="Upload method"
          >
            {(["url", "zip"] as const).map((m) => (
              <button
                key={m}
                role="tab"
                aria-selected={mode === m}
                onClick={() => setMode(m)}
                className="flex-1 py-1.5 text-xs font-medium transition-all"
                style={{
                  background: mode === m ? "var(--accent)" : "transparent",
                  color: mode === m ? "white" : "var(--text-muted)",
                  borderRadius: "6px",
                }}
              >
                {m === "url" ? "GitHub URL" : "ZIP File"}
              </button>
            ))}
          </div>

          {mode === "url" ? (
            <div className="flex flex-col gap-2">
              <input
                id="github-url-input"
                type="url"
                value={urlInput}
                onChange={(e) => setUrlInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleUrlSubmit()}
                placeholder="https://github.com/owner/repo"
                className="w-full text-xs px-3 py-2 rounded-lg outline-none"
                style={{
                  background: "var(--bg-elevated)",
                  border: "1px solid var(--border-bright)",
                  color: "var(--text-primary)",
                }}
                aria-label="GitHub repository URL"
              />
              <div className="flex gap-2">
                <button
                  id="cancel-upload-btn"
                  onClick={() => setShowUpload(false)}
                  className="flex-1 py-1.5 text-xs rounded-lg transition-colors"
                  style={{ background: "var(--bg-hover)", color: "var(--text-muted)" }}
                >
                  Cancel
                </button>
                <button
                  id="submit-url-btn"
                  onClick={handleUrlSubmit}
                  disabled={loading || !urlInput.trim()}
                  className="flex-1 py-1.5 text-xs rounded-lg font-semibold flex items-center justify-center gap-1.5 disabled:opacity-50"
                  style={{ background: "var(--accent)", color: "white" }}
                  aria-label="Analyse repository URL"
                >
                  {loading
                    ? <Loader2 className="w-3 h-3 animate-spin" />
                    : <Link className="w-3 h-3" />}
                  Analyse
                </button>
              </div>
            </div>
          ) : (
            <div
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragOver(false);
                const f = e.dataTransfer.files[0];
                if (f) handleZipUpload(f);
              }}
              onClick={() => fileInputRef.current?.click()}
              className="flex flex-col items-center gap-2 py-6 rounded-xl cursor-pointer transition-all"
              style={{
                border: `1px dashed ${dragOver ? "var(--accent)" : "var(--border-bright)"}`,
                background: dragOver ? "rgba(108,99,255,0.08)" : "var(--bg-elevated)",
              }}
              role="button"
              aria-label="Upload ZIP file"
            >
              <Upload
                className="w-5 h-5"
                style={{ color: dragOver ? "var(--accent)" : "var(--text-muted)" }}
              />
              <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                Drop ZIP here or click to browse
              </p>
              <input
                ref={fileInputRef}
                type="file"
                accept=".zip"
                className="hidden"
                aria-hidden
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) handleZipUpload(f);
                }}
              />
            </div>
          )}
        </div>
      )}

      {/* ── Job Status / Progress ────────────────────────────────────────── */}
      {job && (
        <div className="p-4 fade-up" style={{ borderBottom: "1px solid var(--border)" }}>
          <div className="flex items-center gap-2 mb-2">
            {job.status === "ready"  && <CheckCircle2 className="w-4 h-4 flex-none" style={{ color: "var(--success)" }} />}
            {job.status === "failed" && <AlertCircle  className="w-4 h-4 flex-none" style={{ color: "var(--error)"   }} />}
            {isWorking               && <Loader2      className="w-4 h-4 flex-none animate-spin" style={{ color: "var(--accent)" }} />}
            <span className="text-xs font-medium truncate" style={{ color: "var(--text-primary)" }}>
              {job.repo_name ?? "Repository"}
            </span>
          </div>

          <p className="text-[11px] mb-2" style={{ color: "var(--text-muted)" }}>
            {job.status === "failed"
              ? job.error_message
              : STATUS_LABELS[job.status ?? "idle"]}
          </p>

          {job.status !== "failed" && (
            <div
              className="w-full rounded-full overflow-hidden"
              style={{ height: "3px", background: "var(--border-bright)" }}
              role="progressbar"
              aria-valuenow={progress}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label={`Ingestion progress: ${progress}%`}
            >
              <div
                className="h-full rounded-full transition-all duration-700"
                style={{
                  width: `${progress}%`,
                  background: "linear-gradient(90deg, var(--accent), #38bdf8)",
                }}
              />
            </div>
          )}

          {job.metadata && (
            <div className="flex flex-wrap gap-1 mt-2">
              <span className="text-[10px] px-2 py-0.5 rounded-full badge-vector">
                {job.metadata.total_files} files
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded-full badge-graph capitalize">
                {job.metadata.primary_language}
              </span>
              {job.metadata.frameworks.slice(0, 2).map((fw) => (
                <span key={fw} className="text-[10px] px-2 py-0.5 rounded-full badge-memory capitalize">
                  {fw}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── File Tree (ready state) ──────────────────────────────────────── */}
      {job?.status === "ready" && job.metadata?.top_level_entries && (
        <div
          className="flex-1 overflow-y-auto p-2 fade-up"
          role="tree"
          aria-label="Repository file tree"
        >
          <p className="text-[10px] uppercase tracking-widest px-2 mb-1" style={{ color: "var(--text-dim)" }}>
            Files
          </p>
          {job.metadata.top_level_entries.map((entry) => (
            <div
              key={entry}
              className="flex items-center gap-2 px-2 py-1 rounded-md text-xs cursor-pointer hover:bg-[var(--bg-hover)] transition-colors"
              style={{ color: "var(--text-muted)" }}
              role="treeitem"
              aria-selected={false}
            >
              {entry.includes(".") ? (
                <FileCode className="w-3 h-3 flex-none" style={{ color: "var(--accent)" }} aria-hidden />
              ) : (
                <FolderTree className="w-3 h-3 flex-none" style={{ color: "var(--warning)" }} aria-hidden />
              )}
              <span className="truncate">{entry}</span>
            </div>
          ))}
        </div>
      )}

      {/* ── Empty State ──────────────────────────────────────────────────── */}
      {!job && !showUpload && (
        <div className="flex flex-col items-center justify-center flex-1 gap-4 p-6 text-center fade-up">
          <div
            className="w-14 h-14 rounded-2xl flex items-center justify-center"
            style={{ background: "var(--bg-hover)", border: "1px solid var(--border-bright)" }}
            aria-hidden
          >
            <GitFork className="w-7 h-7" style={{ color: "var(--text-muted)" }} />
          </div>
          <div>
            <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>No repo loaded</p>
            <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
              Upload a ZIP or paste a GitHub URL to begin
            </p>
          </div>
          <button
            id="upload-repo-btn"
            onClick={() => setShowUpload(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all hover:scale-105 active:scale-95"
            style={{
              background: "linear-gradient(135deg, var(--accent), var(--accent-dim))",
              color: "white",
              boxShadow: "0 4px 15px var(--accent-glow)",
            }}
            aria-label="Upload repository"
          >
            <Upload className="w-3.5 h-3.5" aria-hidden />
            Upload Repo
          </button>
        </div>
      )}
    </>
  );
}
