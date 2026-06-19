/**
 * lib/types.ts — Shared TypeScript types for all API responses.
 * Used by the axios service layer and UI components.
 */

// ── Ingestion ─────────────────────────────────────────────────────────────────

export type JobStatus =
  | "idle"
  | "pending"
  | "cloning"
  | "parsing"
  | "embedding"
  | "graphing"
  | "ready"
  | "failed";

export interface RepoMetadata {
  total_files: number;
  total_bytes: number;
  total_size_mb: number;
  primary_language: string;
  frameworks: string[];
  languages: Record<string, number>;
  top_level_entries: string[];
}

export interface IngestionJob {
  job_id: string;
  status: JobStatus;
  repo_url?: string | null;
  repo_name?: string | null;
  metadata?: RepoMetadata | null;
  error_message?: string | null;
  total_files?: number | null;
  processed_files?: number | null;
  total_chunks?: number | null;
  created_at?: string | null;
  updated_at?: string | null;
}

// ── Code Chunk (Phase 3+) ─────────────────────────────────────────────────────

export type ChunkType = "function" | "class" | "method" | "module" | "import" | "coarse";

export interface CodeChunk {
  chunk_id: string;
  repo_id: string;
  file_path: string;
  language: string;
  chunk_type: ChunkType;
  name: string | null;
  code: string;
  start_line: number;
  end_line: number;
  imports: string[];
  decorators: string[];
  parent_name: string | null;
  is_coarse: boolean;
}

// ── Search (Phase 4+) ─────────────────────────────────────────────────────────

export interface VectorSearchResult {
  chunk: CodeChunk;
  score: number;
}

export interface VectorSearchResponse {
  results: VectorSearchResult[];
  query: string;
  total: number;
}

// ── Graph (Phase 5+) ─────────────────────────────────────────────────────────

export interface GraphNode {
  id: string;
  type: "Function" | "Class" | "Module" | "APIRoute" | "DatabaseTable" | "Package" | "EnvironmentVariable";
  label: string;
  file?: string;
  language?: string;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: "CALLS" | "IMPORTS" | "USES" | "QUERIES" | "CONNECTS";
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

// ── Chat (Phase 7+) ───────────────────────────────────────────────────────────

export type RetrievalSource = "vector" | "graph" | "memory";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: RetrievalSource[];
  chunks?: CodeChunk[];
  timestamp: string;
}

export interface ChatQueryRequest {
  query: string;
  repo_id: string;
  user_id?: string;
}

// ── Health ────────────────────────────────────────────────────────────────────

export interface ServiceCheck {
  status: "ok" | "error";
  latency_ms: number;
  detail?: string;
}

export interface HealthResponse {
  status: "ok" | "error";
  services: Record<string, ServiceCheck>;
  version: string;
}
