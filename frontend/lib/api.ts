/**
 * lib/api.ts — Axios instance and typed API service functions.
 *
 * All HTTP calls go through this module. Never call fetch() directly in components.
 * Each function returns a typed result or throws an AxiosError with a user-facing message.
 */

import axios, { AxiosError, AxiosInstance } from "axios";
import type {
  IngestionJob,
  HealthResponse,
  VectorSearchResponse,
  GraphData,
  ChatQueryRequest,
} from "./types";

// ── Axios instance ────────────────────────────────────────────────────────────

const BASE_URL =
  typeof window !== "undefined"
    ? (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000")
    : (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000");

export const apiClient: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 30_000,
  headers: {
    "Content-Type": "application/json",
  },
});

// ── Response interceptor — extract user-friendly error messages ───────────────

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<{ detail?: string | { msg: string }[] }>) => {
    const data = error.response?.data;
    let message = "An unexpected error occurred.";

    if (data?.detail) {
      if (typeof data.detail === "string") {
        message = data.detail;
      } else if (Array.isArray(data.detail)) {
        message = data.detail.map((d) => d.msg).join("; ");
      }
    } else if (error.message) {
      message = error.message;
    }

    // Attach clean message so UI can display it without parsing raw AxiosError
    (error as AxiosError & { userMessage: string }).userMessage = message;
    return Promise.reject(error);
  }
);

// ── Helper — extract userMessage from caught errors ───────────────────────────

export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    return (error as AxiosError & { userMessage?: string }).userMessage ?? error.message;
  }
  if (error instanceof Error) return error.message;
  return "Unknown error";
}

// ── Health ────────────────────────────────────────────────────────────────────

export async function fetchHealth(): Promise<HealthResponse> {
  const { data } = await apiClient.get<HealthResponse>("/health");
  return data;
}

// ── Repository Ingestion ──────────────────────────────────────────────────────

/**
 * Upload a repository by GitHub URL.
 * Returns the created ingestion job (status: "pending").
 */
export async function uploadRepoByUrl(githubUrl: string): Promise<IngestionJob> {
  const form = new FormData();
  form.append("github_url", githubUrl);
  const { data } = await apiClient.post<IngestionJob>("/repo/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

/**
 * Upload a repository as a ZIP file.
 * Accepts an optional onUploadProgress callback for a progress bar.
 */
export async function uploadRepoZip(
  file: File,
  onUploadProgress?: (percent: number) => void
): Promise<IngestionJob> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await apiClient.post<IngestionJob>("/repo/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress: (evt) => {
      if (onUploadProgress && evt.total) {
        onUploadProgress(Math.round((evt.loaded / evt.total) * 100));
      }
    },
  });
  return data;
}

/**
 * Poll ingestion job status.
 */
export async function fetchJobStatus(jobId: string): Promise<IngestionJob> {
  const { data } = await apiClient.get<IngestionJob>(`/repo/status/${jobId}`);
  return data;
}

// ── Vector Search ─────────────────────────────────────────────────────────────

export interface VectorSearchRequest {
  query: string;
  repo_id: string;
  top_k?: number;
}

export async function vectorSearch(
  req: VectorSearchRequest
): Promise<VectorSearchResponse> {
  const { data } = await apiClient.post<VectorSearchResponse>("/search/vector", req);
  return data;
}

// ── Graph ─────────────────────────────────────────────────────────────────────

export async function fetchRepoGraph(repoId: string): Promise<GraphData> {
  const { data } = await apiClient.get<GraphData>("/repo/graph", {
    params: { repo_id: repoId },
  });
  return data;
}

// ── Memory ────────────────────────────────────────────────────────────────────

export interface MemoryEntry {
  id: string;
  content: string;
  created_at: string;
}

export async function fetchMemoryHistory(
  userId = "default",
  repoId: string
): Promise<MemoryEntry[]> {
  const { data } = await apiClient.get<MemoryEntry[]>("/memory/history", {
    params: { user_id: userId, repo_id: repoId },
  });
  return data;
}

// ── Chat ──────────────────────────────────────────────────────────────────────

/**
 * Send a chat query — returns a ReadableStream for SSE streaming.
 * The caller is responsible for reading and parsing the stream.
 */
export async function streamChatQuery(req: ChatQueryRequest): Promise<Response> {
  const response = await fetch(`${BASE_URL}/chat/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail ?? `Chat request failed: ${response.status}`);
  }
  return response;
}
